#!/usr/bin/env python3
"""Export actual Kimodo qpos to canonical SONIC; offline adaptation is opt-in."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import sys
import numpy as np
from scipy.spatial.transform import Rotation, Slerp

PROJECT=Path('/workspace/group2/dl-group2')
SONIC=Path('/workspace/group2/GR00T-WholeBodyControl')
ROBOT=SONIC/'decoupled_wbc/control/robot_model/model_data/g1/g1_29dof_with_hand_rev_1_0_activatedfinger.xml'
BODY_INDEXES=[0,4,10,18,5,11,19,9,16,22,28,17,23,29]

def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def write_json(p,x):Path(p).write_text(json.dumps(x,indent=2,allow_nan=False)+'\n')

def verify_generation(task_dir,generation_dir,task,gen):
    if gen.get('model_generation_run') is not True or gen.get('model_name')!='Kimodo-G1-RP-v1':
        raise ValueError('Actual Kimodo generation is required; dry-run/fixtures cannot be replay candidates')
    if gen.get('actual_frames')!=487 or gen.get('requested_frames')!=487 or gen.get('actual_source_last_timestamp_s')!=16.2:
        raise ValueError('Incomplete actual source duration/frame count')
    if gen.get('task_id')!=task['task_id']:raise ValueError('Generation/task identity mismatch')
    for name in ('task.json','task_plan.npz','pose_constraints.json'):
        path=(task_dir/name).resolve()
        if gen['source_hashes'].get(str(path))!=sha(path):raise ValueError('Generation/task hash mismatch '+name)
    for name,key in [('raw_motion.npz','raw_sha256'),('raw_motion.csv','raw_qpos_sha256')]:
        if gen.get(key)!=sha(generation_dir/name):raise ValueError('Generated raw hash mismatch '+name)
    if not gen.get('checkpoint_hashes'):raise ValueError('Missing checkpoint provenance')
    for name,expected in gen['checkpoint_hashes'].items():
        checkpoint=Path('/workspace/group2/kimodo-t6/g1-integration/checkpoints/Kimodo-G1-RP-v1')/name
        if sha(checkpoint)!=expected:raise ValueError('Checkpoint changed '+name)

def resample(q,fps,t):
    q=np.asarray(q,dtype=float);t=np.asarray(t,dtype=float)
    if q.ndim!=2 or q.shape[1]!=36 or len(q)<2 or not np.isfinite(q).all():raise ValueError('Invalid finite source qpos(T,36)')
    if fps!=30 or len(t)!=810 or not np.array_equal(t,np.arange(810)/50):raise ValueError('Expected source30Hz/reference810x50Hz')
    source_t=np.arange(len(q))/fps
    if source_t[-1]<16.2 or t[-1]>source_t[-1]:raise ValueError('Insufficient raw coverage; extrapolation/last-pose padding forbidden')
    if not np.allclose(np.linalg.norm(q[:,3:7],axis=1),1,atol=1e-5,rtol=0):raise ValueError('Source quaternion not unit')
    out=np.empty((len(t),36))
    for col in list(range(3))+list(range(7,36)):out[:,col]=np.interp(t,source_t,q[:,col])
    out[:,3:7]=Slerp(source_t,Rotation.from_quat(q[:,[4,5,6,3]]))(t).as_quat()[:,[3,0,1,2]]
    return out

def frame_zero_report(q,initial,h):
    vals=dict(body_max_error_rad=float(np.max(abs(q[0,7:]-initial[7:]))),root_max_error_m=float(np.max(abs(q[0,:3]-initial[:3]))),
        root_quat_max_error=float(np.max(abs(q[0,3:7]-initial[3:7]))),hand_max_error_rad=float(np.max(abs(h[0]))))
    vals['pass']=all(vals[k]<= (1e-10 if k.startswith('hand') else 1e-6) for k in vals)
    return vals

def canonical(task):
    os.environ['SONIC_REPO']=str(SONIC);sys.path[:0]=[str(PROJECT/'scripts'),str(SONIC)]
    import project_paths
    project_paths.default_robot_xml=lambda:ROBOT
    import mujoco
    from scene import load_scene
    from expert_trajectory import orders
    from cases import read_cases,reset_case
    m,d=load_scene(supported=False,robot_path=ROBOT)
    known={c['id']:c for c in read_cases()['cases']}
    if task['case']!=known[task['case']['id']]:raise ValueError('Case differs from canonical shared case')
    reset_case(m,d,task['case'])
    bn,hn,_=orders()
    if task['body_joint_order']!=bn or task['hand_joint_order']!=hn:raise ValueError('Joint name/order mismatch')
    if (m.nq,m.nv,m.nu,m.neq)!=(57,55,43,0):raise ValueError('Scene structure mismatch')
    initial=np.asarray(task.get('initial_qpos',task.get('initial_qpos57')),float)
    velocity=np.asarray(task.get('initial_qvel',task.get('initial_qvel55')),float)
    if initial.shape!=(57,) or velocity.shape!=(55,) or not np.isfinite(np.r_[initial,velocity]).all():raise ValueError('Invalid initial state')
    d.qpos[:]=initial;d.qvel[:]=velocity;mujoco.mj_forward(m,d)
    return m,d,bn,hn

def adapt(q,t,m,d,names,clearance,lift_margin):
    import mujoco
    from grasp_reference import GraspReference
    plan=GraspReference(m,d);original=mujoco.MjData(m)
    qa=np.array([m.joint(n).qposadr[0] for n in names]);rqa=int(m.joint('floating_base_joint').qposadr[0])
    initial=np.r_[d.qpos[rqa:rqa+7],d.qpos[qa]]
    result=np.tile(initial,(len(q),1));u=np.clip(t/1.5,0,1);u=u*u*(3-2*u)
    start=d.xpos[plan.wrist].copy();rotation=d.xmat[plan.wrist].reshape(3,3).copy();rows=[]
    armcols=[names.index(m.joint(int(j)).name)+7 for j in plan.arm]
    for k,row in enumerate(q):
        original.qpos[:]=d.qpos;original.qpos[rqa:rqa+7]=row[:7];original.qpos[qa]=row[7:];mujoco.mj_forward(m,original)
        rawp=original.xpos[plan.wrist].copy();rawr=original.xmat[plan.wrist].reshape(3,3).copy()
        target=start+u[k]*(rawp-start)
        for amount,a,b in [(clearance,4,7),(lift_margin,10,12)]:
            v=np.clip((t[k]-a)/(b-a),0,1);target[2]+=amount*v*v*(3-2*v)
        plan.rotation=Slerp([0,1],Rotation.from_matrix([rotation,rawr]))([u[k]]).as_matrix()[0]
        if k:plan.ik(target)
        mujoco.mj_forward(m,plan.plan)
        err=float(np.linalg.norm(plan.plan.xpos[plan.wrist]-target))
        rot_error=float((Rotation.from_matrix(plan.plan.xmat[plan.wrist].reshape(3,3))*Rotation.from_matrix(plan.rotation).inv()).magnitude())
        result[k,armcols]=plan.plan.qpos[plan.aq]
        rows.append(dict(frame=k,time_s=float(t[k]),raw_wrist_world_pos=rawp.tolist(),target_wrist_world_pos=target.tolist(),position_error_m=err,orientation_error_rad=rot_error,
            max_qpos_change=float(np.max(abs(result[k]-row))),world_wrist_entry_blend=float(u[k])))
    return result,rows

def angular_velocity(quat):
    n,b=quat.shape[:2];r=Rotation.from_quat(quat[:,:,[1,2,3,0]].reshape(-1,4))
    delta=(r[b:]*r[:-b].inv()).as_rotvec().reshape(n-1,b,3)*50
    v=np.empty((n,b,3));v[0]=delta[0];v[-1]=delta[-1];v[1:-1]=(delta[:-1]+delta[1:])/2
    return v

def main():
    p=argparse.ArgumentParser(description=__doc__)
    for name in ('task','generation','out'):p.add_argument('--'+name,type=Path,required=True)
    p.add_argument('--adapt',choices=['neutral-world-wrist'])
    p.add_argument('--clearance',type=float,default=0.)
    p.add_argument('--lift-margin',type=float,default=0.)
    args=p.parse_args()
    if args.out.exists():p.error('Fresh output required')
    if (args.clearance or args.lift_margin) and not args.adapt:p.error('Clearance/lift require explicit adaptation')
    if not np.isfinite([args.clearance,args.lift_margin]).all() or min(args.clearance,args.lift_margin)<0:p.error('Invalid adaptation heights')
    args.out.mkdir(parents=True);out=args.out.resolve()
    task=json.loads((args.task/'task.json').read_text());gen=json.loads((args.generation/'generation.json').read_text())
    verify_generation(args.task,args.generation,task,gen)
    if task['task_id']!=gen['task_id']:raise ValueError('task_id mismatch')
    names=gen['source_qpos_joint_order']
    if len(names)!=29 or len(set(names))!=29 or set(names)!=set(task['body_joint_order']):raise ValueError('Wrong source joint names')
    raw=args.generation/'raw_motion.npz';rawcsv=args.generation/'raw_motion.csv'
    q=np.loadtxt(rawcsv,delimiter=',',ndmin=2)
    required={'local_rot_mats':(34,3,3),'root_positions':(3,), 'posed_joints':(34,3),'global_rot_mats':(34,3,3), 'smooth_root_pos':(3,), 'foot_contacts':(4,), 'global_root_heading':(2,)}
    with np.load(raw,allow_pickle=False) as source:
        for key,shape in required.items():
            if source[key].shape!=(len(q),*shape) or not np.isfinite(source[key]).all():raise ValueError('Invalid raw field '+key)
    plan=np.load(args.task/'task_plan.npz',allow_pickle=False);t=plan['timestamps'];h=plan['hand_ref_q'];hd=plan['hand_ref_dq']
    if h.shape!=(810,14) or hd.shape!=h.shape or not np.isfinite(np.r_[h.ravel(),hd.ravel()]).all():raise ValueError('Invalid hand plan')
    fps=gen.get('fps',gen.get('source_fps'))
    q50=resample(q,fps,t);m,d,bn,hn=canonical(task)
    qa=np.array([m.joint(n).qposadr[0] for n in names]);rqa=int(m.joint('floating_base_joint').qposadr[0])
    initial=np.r_[d.qpos[rqa:rqa+7],d.qpos[qa]];zero=frame_zero_report(q50,initial,h)
    hashes={str(f.resolve()):sha(f) for f in [args.task/'task.json',args.task/'task_plan.npz',args.generation/'generation.json',raw,rawcsv]}
    metadata=dict(task_id=task['task_id'],contract_version=task['contract_version'],source='actual Kimodo generation',raw_source=str(rawcsv.resolve()),raw_motion=str(raw.resolve()),source_hashes=hashes,
        body_joint_order=bn,hand_joint_order=hn,source_qpos_joint_order=names,units={'positions':'m','angles':'rad','time':'s'},quaternion_order='wxyz',velocity_frame='world',raw_frame_zero=zero,
        raw_vs_adapted='adapted' if args.adapt else 'raw',physical_success=None,expert_valid=None)
    write_json(out/'export_metadata.json',metadata)
    if not zero['pass'] and not args.adapt:
        write_json(out/'export_result.json',dict(status='REFUSED_NONCANONICAL_FRAME_ZERO',playable=False,**zero));return 2
    if args.adapt:
        q50,rows=adapt(q50,t,m,d,names,args.clearance,args.lift_margin)
        write_json(out/'adaptation_perframe.json',rows)
        metadata['postprocessing']=dict(mode=args.adapt,entry_blend_s=1.5,clearance_m=args.clearance,clearance_blend_s=[4,7],lift_margin_m=args.lift_margin,lift_blend_s=[10,12],
            max_wrist_position_error_m=max(r['position_error_m'] for r in rows),max_wrist_orientation_error_rad=max(r['orientation_error_rad'] for r in rows),offline_ik_only=True)
        write_json(out/'export_metadata.json',metadata)
        if metadata['postprocessing']['max_wrist_position_error_m']>.02:raise ValueError('World wrist preservation >.02m; reference refused')
    zero_after=frame_zero_report(q50,initial,h)
    if not zero_after['pass']:raise ValueError('Output frame zero still noncanonical')
    import mujoco
    body_ids=[m.body('pelvis').id]+[int(m.jnt_bodyid[m.joint(bn[i-1]).id]) for i in BODY_INDEXES[1:]]
    pos=np.empty((810,14,3));quat=np.empty((810,14,4));fk=mujoco.MjData(m);geometry=[]
    for k,row in enumerate(q50):
        fk.qpos[:]=d.qpos;fk.qpos[rqa:rqa+7]=row[:7];fk.qpos[qa]=row[7:];mujoco.mj_forward(m,fk)
        pos[k]=fk.xpos[body_ids];quat[k]=fk.xquat[body_ids]
        geometry.append([float(fk.xpos[m.body('pelvis').id,2]),float(fk.xpos[m.body('left_ankle_roll_link').id,2]),float(fk.xpos[m.body('right_ankle_roll_link').id,2])])
    if not np.allclose(np.linalg.norm(quat,axis=-1),1,atol=1e-5):raise ValueError('FK quaternions not unit')
    canonical_q=q50[:,[names.index(n)+7 for n in bn]];linear=np.gradient(pos,.02,axis=0);angular=angular_velocity(quat)
    arrays=dict(timestamps=t,body_ref_q=canonical_q,body_ref_dq=np.gradient(canonical_q,.02,axis=0),hand_ref_q=h,hand_ref_dq=hd,
        root_ref_pos=q50[:,:3],root_ref_quat=q50[:,3:7],root_lin_vel=linear[:,0],root_ang_vel=angular[:,0])
    np.savez_compressed(out/'reference.npz',**arrays)
    motion=out/'reference/motion';motion.mkdir(parents=True)
    values=dict(joint_pos=arrays['body_ref_q'],joint_vel=arrays['body_ref_dq'],body_pos=pos,body_quat=quat,body_lin_vel=linear,body_ang_vel=angular)
    headers={}
    for key,value in values.items():
        flat=value.reshape(810,-1)
        if key.startswith('joint'):header=[('joint_' if key=='joint_pos' else 'joint_vel_')+str(i) for i in range(29)]
        else:
            axes='wxyz' if key=='body_quat' else 'xyz';suffix={'body_lin_vel':'vel_','body_ang_vel':'angvel_'}.get(key,'')
            header=[f'body_{i}_{suffix}{axis}' for i in range(14) for axis in axes]
        headers[key]=header;np.savetxt(motion/(key+'.csv'),flat,delimiter=',',fmt='%.12g',header=','.join(header),comments='')
    for side in ('left','right'):
        labels=[side+'_'+n for n in ['thumb_0','thumb_1','thumb_2','middle_0','middle_1','index_0','index_1']]
        cols=[hn.index(side+'_hand_'+label[len(side)+1:]+'_joint') for label in labels]
        np.savetxt(motion/(side+'_hand_pos.csv'),h[:,cols],delimiter=',',fmt='%.12g',header=','.join(labels),comments='')
    (motion/'metadata.txt').write_text('Metadata for: motion\nBody part indexes:\n['+' '.join(map(str,BODY_INDEXES))+']\n\nTotal timesteps: 810\n')
    metadata.update(headers=headers,body_part_indexes=BODY_INDEXES,body_part_names=[m.body(i).name for i in body_ids],frame_zero=zero_after,torso_feet_z_min=np.min(geometry,axis=0).tolist(),torso_feet_z_max=np.max(geometry,axis=0).tolist())
    write_json(out/'export_metadata.json',metadata)
    setting=dict(metadata,case=task['case'],initial_qpos=d.qpos.tolist(),initial_qvel=d.qvel.tolist(),prompt=task['prompt'],seed=task['seed'],task_path=str(args.task.resolve()),generation_path=str(args.generation.resolve()))
    write_json(out/'setting.json',setting);write_json(out/'export_result.json',dict(status='REFERENCE_READY',playable=True,physical_success=None,expert_valid=None))
    print(json.dumps(dict(status='REFERENCE_READY',out=str(out),frames=810,raw_frame_zero=zero)));return 0

if __name__=='__main__':raise SystemExit(main())
