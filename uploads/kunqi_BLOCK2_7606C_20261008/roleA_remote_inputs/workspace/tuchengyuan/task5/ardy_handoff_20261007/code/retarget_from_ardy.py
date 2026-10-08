"""Explicit ARDY trajectory postprocessing, never physical state manipulation."""
import argparse
import json
from pathlib import Path
import shutil
import subprocess
import sys
import xml.etree.ElementTree as ET
import numpy as np
import mujoco
from scipy.spatial.transform import Rotation, Slerp
from prepare_conditions import initialize, ARDY, SONIC, CONVERTER
from grasp_reference import GraspReference


def main():
    p=argparse.ArgumentParser()
    p.add_argument('--source',type=Path,required=True)
    p.add_argument('--out',type=Path,required=True)
    p.add_argument('--preserve-world-wrist',action='store_true')
    p.add_argument('--lift-margin',type=float,default=0.,help='Additional reference height, blended from 10 to 12 s')
    p.add_argument('--clearance',type=float,default=.03)
    args=p.parse_args()
    args.out.mkdir(exist_ok=False)
    for name in ['setting.npz','setting.json','constraints.json']:
        shutil.copy2(args.source/name,args.out/name)
    source_spec=json.loads((args.source/'setting.json').read_text())
    model,data,_,_=initialize(source_spec['case']['id'])
    raw=args.source/'reference/motion/ardy_motion.csv'
    q=np.loadtxt(raw,delimiter=',',ndmin=2)
    names=[j.get('name') for j in ET.parse(ARDY/'ardy/assets/skeletons/g1skel34/xml/g1.xml').findall('.//worldbody//joint') if j.get('type')!='free']
    source=q.copy()
    q[:,:7]=data.qpos[:7]
    keep=['right_'+n+'_joint' for n in ['shoulder_pitch','shoulder_roll','shoulder_yaw','elbow','wrist_roll','wrist_pitch','wrist_yaw']]
    u=np.clip(np.arange(len(q))/25/1.5,0,1);u=u*u*(3-2*u)
    for i,name in enumerate(names):
        nominal=data.qpos[model.joint(name).qposadr[0]]
        if name in keep:q[:,i+7]=nominal+u*(q[:,i+7]-nominal)
        else:q[:,i+7]=nominal
    if args.preserve_world_wrist:
        # Keep the ARDY end-effector path in world coordinates when removing its
        # torso/root sway. IK re-expresses that path in the neutral body frame.
        plan=GraspReference(model,data)
        original=mujoco.MjData(model)
        jq=np.array([model.joint(n).qposadr[0] for n in names])
        arm_columns=[names.index(n)+7 for n in keep]
        initial_pos=data.xpos[plan.wrist].copy()
        initial_rotation=data.xmat[plan.wrist].reshape(3,3).copy()
        errors=[]
        for k,row in enumerate(source):
            original.qpos[:]=data.qpos;original.qpos[:7]=row[:7];original.qpos[jq]=row[7:]
            mujoco.mj_forward(model,original)
            target=initial_pos+u[k]*(original.xpos[plan.wrist]-initial_pos)
            lift_u=np.clip((k/25-10)/2,0,1)
            target[2]+=args.lift_margin*lift_u*lift_u*(3-2*lift_u)
            cu=np.clip((k/25-4)/3,0,1)
            target[2]+=args.clearance*cu*cu*(3-2*cu)
            rotation=original.xmat[plan.wrist].reshape(3,3)
            plan.rotation=Slerp([0,1],Rotation.from_matrix([initial_rotation,rotation]))([u[k]]).as_matrix()[0]
            plan.ik(target)
            mujoco.mj_forward(model,plan.plan)
            error=float(np.linalg.norm(plan.plan.xpos[plan.wrist]-target));errors.append(error)
            if error>.02:raise RuntimeError(f'World wrist cannot be preserved: frame {k}, error {error}')
            q[k,arm_columns]=plan.plan.qpos[plan.aq]
        (args.out/'retarget_quality.json').write_text(json.dumps(dict(max_error_m=max(errors),mean_error_m=float(np.mean(errors))),indent=2))
    adapted=args.out/'stationary_ardy.csv'
    np.savetxt(adapted,q,delimiter=',')
    spec=json.loads((args.out/'setting.json').read_text())
    spec.update(source='ARDY right-arm trajectory with explicit neutral-root/legs/left-arm projection and 1.5s entry blend',
                raw_source=str(raw),postprocessing=dict(right_arm_preserved_after_s=1.5,root_legs_left_arm='neutral reference only; actual body remains SONIC-controlled'))
    if args.preserve_world_wrist:
        spec.update(source='ARDY world-space wrist trajectory retargeted by arm IK to a neutral standing reference; SONIC controls actual body',
            postprocessing=dict(preserve='ARDY world-space right-wrist position/orientation after 1.5s entry blend',
                root_legs_left_arm='neutral reference; actual remains SONIC controlled',max_wrist_position_error_m=max(errors)))
        spec['postprocessing']['additional_reference_lift_m']=args.lift_margin
        spec['postprocessing']['wrist_clearance_height_m']=args.clearance
        spec['postprocessing']['clearance_blend_seconds']=[4,7]
        spec['generation_mode']='fresh_text_conditioned_ARDY_with_scene_constraints'
    (args.out/'setting.json').write_text(json.dumps(spec,indent=2)+'\n')
    subprocess.run([sys.executable,str(CONVERTER),
        str(args.source/'reference/motion/ardy_motion.npz'),'--qpos-csv',str(adapted),
        '--ardy-repo',str(ARDY),'--output-dir',str(args.out/'reference/motion')],check=True)
    # The canonical independent hand PD consumes name-mapped absolute targets.
    href=np.load(args.source/'setting.npz')['hand_ref_q']
    hn=source_spec['hand_joint_order']
    for side in ['left','right']:
        labels=[side+'_'+n for n in ['thumb_0','thumb_1','thumb_2','middle_0','middle_1','index_0','index_1']]
        ix=[hn.index(side+'_hand_'+n[len(side)+1:]+'_joint') for n in labels]
        np.savetxt(args.out/'reference/motion'/f'{side}_hand_pos.csv',href[:,ix],delimiter=',',header=','.join(labels),comments='')
    (args.out/'reference/motion/hand_plan.json').write_text(json.dumps(dict(hand='right',fps=50,close=[8,10],generator='canonical_scene_rule'))+'\n')


if __name__=='__main__':main()
