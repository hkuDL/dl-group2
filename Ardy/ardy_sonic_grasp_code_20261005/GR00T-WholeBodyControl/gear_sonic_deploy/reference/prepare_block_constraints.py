#!/usr/bin/env python3
"""Prepare ARDY keyframe conditions from the existing block scene (no XML changes)."""
import argparse, json, sys
from pathlib import Path
import xml.etree.ElementTree as ET
import numpy as np
import mujoco
import torch
from scipy.optimize import least_squares
from scipy.spatial.transform import Rotation

ARM=['waist_pitch_joint','right_shoulder_pitch_joint','right_shoulder_roll_joint','right_shoulder_yaw_joint','right_elbow_joint','right_wrist_roll_joint','right_wrist_pitch_joint','right_wrist_yaw_joint']
GRASP_OFFSET=np.array([.125,.045,0.])

def main():
    repo=Path(__file__).resolve().parents[2]
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output-dir',required=True,type=Path)
    parser.add_argument('--ardy-repo',type=Path,default=repo.parent/'ardy')
    parser.add_argument('--scene',type=Path,default=repo/'gear_sonic/data/robot_model/model_data/g1/scene_43dof_blocks.xml')
    parser.add_argument('--root-x',type=float,default=.25)
    parser.add_argument('--arms-at-sides',action='store_true')
    args=parser.parse_args()
    sys.path.insert(0,str(args.ardy_repo))
    from ardy.skeleton import G1Skeleton34
    from ardy.exports.mujoco import MujocoQposConverter
    from ardy.constraints import FullBodyConstraintSet, RightHandConstraintSet, LeftFootConstraintSet, RightFootConstraintSet, Root2DConstraintSet, EndEffectorConstraintSet, save_constraints_lst
    skel=G1Skeleton34()
    converter=MujocoQposConverter(skel)
    model=mujoco.MjModel.from_xml_path(str(args.scene.resolve()))
    data=mujoco.MjData(model)
    names=[j.get('name') for j in ET.parse(converter.xml_path).findall('.//worldbody//joint') if j.get('type')!='free']
    joint_q=np.array([model.joint(n).qposadr[0] for n in names])
    arm_j=np.array([model.joint(n).id for n in ARM])
    arm_q=model.jnt_qposadr[arm_j]
    wrist=model.body('right_wrist_yaw_link').id
    block=model.body('wood_block').id
    target=data.qpos[model.joint('wood_block_free').qposadr[0]:][:3].copy()
    target[2]=.73
    nominal=data.qpos.copy()
    for side in ['left','right']:
        for n,v in [('hip_pitch',-.1),('knee',.3),('ankle_pitch',-.2)]:
            nominal[model.joint(side+'_'+n+'_joint').qposadr[0]]=v
    if args.arms_at_sides:
        for side,roll in [('left',.15),('right',-.15)]:
            nominal[model.joint(side+'_shoulder_roll_joint').qposadr[0]]=roll
            nominal[model.joint(side+'_elbow_joint').qposadr[0]]=1.4
    M=converter.mujoco_to_ardy_matrix.numpy()
    axes=converter._mujoco_joint_axis_values_ardy_space.numpy()
    indexes=converter._mujoco_indices_to_ardy_indices.numpy()
    offsets=converter._rot_offsets_f2q.numpy()
    def dictionary(qpos):
        local=np.tile(np.eye(3),(34,1,1))
        local[indexes]=np.einsum('nij,njk->nik',offsets[indexes].transpose(0,2,1),Rotation.from_rotvec(axes*qpos[joint_q,None]).as_matrix())
        local[0]=M@Rotation.from_quat(qpos[[4,5,6,3]]).as_matrix()@M.T
        return torch.tensor(local,dtype=torch.float32),torch.tensor(M@qpos[:3],dtype=torch.float32)
    seed=np.array([.2,-.6,-.2,0,1,0,.5,0.])
    bounds=model.jnt_range[arm_j].T
    def solve(point,seed):
        data.qpos[:]=nominal
        data.qpos[0]=args.root_x
        def residual(q):
            data.qpos[arm_q]=q
            mujoco.mj_kinematics(model,data)
            R=data.xmat[wrist].reshape(3,3)
            p=data.xpos[wrist]+R@GRASP_OFFSET
            return np.r_[5*(p-point),Rotation.from_matrix(R).as_rotvec()]
        fit=least_squares(residual,np.clip(seed,bounds[0]+1e-6,bounds[1]-1e-6),bounds=(bounds[0]+1e-6,bounds[1]-1e-6),max_nfev=180)
        residual(fit.x)
        error=float(np.linalg.norm(data.xpos[wrist]+data.xmat[wrist].reshape(3,3)@GRASP_OFFSET-point))
        if error>.02: raise RuntimeError(f'Unreachable condition: {error:.3f} m')
        return data.qpos.copy(),fit.x,error

    duration=12.; fps=25; count=int(duration*fps)
    frames=np.r_[np.arange(75,count,5),count-1]
    poses=[]; errors=[]; goals=[]
    def smooth(t,a,b):
        u=np.clip((t-a)/(b-a),0,1)
        return u*u*(3-2*u)
    for frame in frames:
        t=frame/fps
        z=.16*(1-smooth(t,3,5))+.16*smooth(t,8,10)
        point=target+np.array([0,0,z])
        pose,seed,error=solve(point,seed)
        poses.append(pose); errors.append(error); goals.append(point.tolist())
    local,roots=zip(*(dictionary(q) for q in poses))
    local=torch.stack(local); roots=torch.stack(roots)
    # Check coordinate conversion before using these poses as model conditions.
    reconstructed=converter.dict_to_qpos({'local_rot_mats':local[None],'root_positions':roots[None]},device='cpu')[0]
    source=np.stack(poses)[:,np.r_[np.arange(7),joint_q]]
    roundtrip=float(np.max(np.abs(reconstructed-source)))
    if roundtrip>1e-4: raise RuntimeError(f'Coordinate conversion error: {roundtrip}')
    grots,gpos,_=skel.fk(local,roots)
    initial_local,initial_root=dictionary(nominal)
    ir,ip,_=skel.fk(initial_local[None].repeat(2,1,1,1),initial_root[None].repeat(2,1))
    all_frames=torch.arange(count)
    x=np.array([args.root_x*smooth(t/fps,1,3) for t in range(count)])
    root2d=torch.tensor(np.stack([np.zeros(count),x],axis=1),dtype=torch.float32)
    constraints=[FullBodyConstraintSet(skel,torch.tensor([0,25]),ip,ir),Root2DConstraintSet(skel,all_frames,root2d),EndEffectorConstraintSet(skel,torch.tensor(frames),gpos,grots,None,joint_names=['RightHand','LeftFoot','RightFoot','Hips']+(['LeftHand'] if args.arms_at_sides else []))]
    args.output_dir.mkdir(parents=True,exist_ok=True)
    save_constraints_lst(str(args.output_dir/'constraints.json'),constraints)
    spec={'arms_at_sides':args.arms_at_sides,'initial_arm_pose':{'left_shoulder_roll_joint':.15,'right_shoulder_roll_joint':-.15,'left_elbow_joint':1.4,'right_elbow_joint':1.4} if args.arms_at_sides else {},'scene':str(args.scene.resolve()),'block':target.tolist(),'duration':duration,'fps':fps,'frames':frames.tolist(),'grasp_center_goals':goals,'ik_errors_m':errors,'roundtrip_max_error':roundtrip,'approach':[3.,5.],'close':[6.,7.],'lift':[8.,10.],'right_hand_open':[0,-.1,-.1,.15,.15,.15,.15],'right_hand_closed':[0,-.8,-1.2,1.2,1.3,1.2,1.3],'grasp_offset':GRASP_OFFSET.tolist()}
    (args.output_dir/'grasp_spec.json').write_text(json.dumps(spec,indent=2))
    np.savez(args.output_dir/'conditioning_poses.npz',qpos=source,frame_indices=frames)
    print('IK error (max):',max(errors),'Coordinate error:',roundtrip)
    print('Constraints:',args.output_dir/'constraints.json')

if __name__=='__main__': main()
