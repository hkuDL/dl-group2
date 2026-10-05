#!/usr/bin/env python3
"""Apply the grasp finger schedule and measure ARDY reference reach accuracy."""
import argparse,json,xml.etree.ElementTree as ET
from pathlib import Path
import numpy as np
import mujoco

def main():
    repo=Path(__file__).resolve().parents[2]
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('motion_dir',type=Path)
    args=parser.parse_args(); out=args.motion_dir
    spec=json.loads((out/'grasp_spec.json').read_text())
    qpos=np.loadtxt(out/'ardy_motion.csv',delimiter=',',ndmin=2)
    names=[j.get('name') for j in ET.parse(repo.parent/'ardy/ardy/assets/skeletons/g1skel34/xml/g1.xml').findall('.//worldbody//joint') if j.get('type')!='free']
    m=mujoco.MjModel.from_xml_path(spec['scene']); d=mujoco.MjData(m)
    jq=np.array([m.joint(n).qposadr[0] for n in names]); wrist=m.body('right_wrist_yaw_link').id
    centers=[]
    for q in qpos:
        d.qpos[:7]=q[:7]; d.qpos[jq]=q[7:]
        mujoco.mj_kinematics(m,d)
        centers.append(d.xpos[wrist]+d.xmat[wrist].reshape(3,3)@spec['grasp_offset'])
    centers=np.array(centers)
    frames=np.array(spec['frames']); goals=np.array(spec['grasp_center_goals'])
    errors=np.linalg.norm(centers[frames]-goals,axis=1)
    n=len(np.loadtxt(out/'joint_pos.csv',delimiter=',',ndmin=2,skiprows=1))
    t=np.arange(n)/50
    u=np.clip((t-spec['close'][0])/(spec['close'][1]-spec['close'][0]),0,1); u=u*u*(3-2*u)
    hand=np.array(spec['right_hand_open'])[None]*(1-u[:,None])+np.array(spec['right_hand_closed'])[None]*u[:,None]
    for side,values in [('right',hand),('left',np.zeros_like(hand))]:
        header=','.join(side+'_'+n for n in ['thumb_0','thumb_1','thumb_2','middle_0','middle_1','index_0','index_1'])
        np.savetxt(out/f'{side}_hand_pos.csv',values,delimiter=',',header=header,comments='')
    (out/'hand_plan.json').write_text(json.dumps({'generator':'scene_conditioned_grasp_schedule','fps':50,'frames':n,'transition_start':6.,'transition_end':7.,'open':spec['right_hand_open'],'closed':spec['right_hand_closed']},indent=2))
    quality={'source':'ARDY constrained generation; body not replaced','root_first':qpos[0,:3].tolist(),'root_last':qpos[-1,:3].tolist(),'reach_error_mean_m':float(errors.mean()),'reach_error_max_m':float(errors.max()),'hand_center_at_6s':centers[150].tolist(),'hand_center_at_11s':centers[275].tolist(),'reach_errors_m':errors.tolist()}
    (out/'reference_quality.json').write_text(json.dumps(quality,indent=2))
    print(json.dumps({k:v for k,v in quality.items() if k!='reach_errors_m'},indent=2))

if __name__=='__main__': main()
