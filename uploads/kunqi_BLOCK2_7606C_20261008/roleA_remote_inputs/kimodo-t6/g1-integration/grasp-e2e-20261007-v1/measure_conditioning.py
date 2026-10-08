#!/usr/bin/env python3
"""Read actual generated model/canonical FK residuals without changing motion."""
import argparse,json,sys
from pathlib import Path
import numpy as np
import torch
from scipy.spatial.transform import Rotation
from export_kimodo_reference import canonical,write_json
sys.path.insert(0,'/workspace/group2/kimodo-t6/g1-integration/coordinate-repair-20261007-v2')
from kimodo.skeleton import G1Skeleton34
from kimodo.exports.mujoco import MujocoQposConverter
from kimodo_condition_coordinates import qpos_to_motion_dict_exact

def main():
    p=argparse.ArgumentParser();p.add_argument('--task',type=Path,required=True);p.add_argument('--generation',type=Path,required=True);a=p.parse_args()
    task=json.loads((a.task/'task.json').read_text());plan=np.load(a.task/'task_plan.npz');raw=np.load(a.generation/'raw_motion.npz');q=np.loadtxt(a.generation/'raw_motion.csv',delimiter=',')
    c=MujocoQposConverter(G1Skeleton34());expected=qpos_to_motion_dict_exact(c,plan['source_qpos'],30)
    m,d,bn,hn=canonical(task);names=task['source_qpos_joint_order'];qa=[m.joint(n).qposadr[0] for n in names]
    import mujoco
    wrists=[m.body(side+'_wrist_yaw_link').id for side in ('left','right')]
    pos=[];quat=[];limits=[]
    for row in q:
        d.qpos[:]=task['initial_qpos'];d.qpos[:7]=row[:7];d.qpos[qa]=row[7:];mujoco.mj_forward(m,d)
        pos.append(d.xpos[wrists].copy());quat.append(d.xquat[wrists].copy())
        limits.append([max(0,float(m.joint(n).range[0]-v),float(v-m.joint(n).range[1])) for n,v in zip(names,row[7:])])
    actual=np.asarray(pos);wp=plan['wrist_world_pos'];werr=np.linalg.norm(actual-wp,axis=-1)
    sk=c.skeleton;gp=expected['posed_joints'].numpy();modelerror=np.linalg.norm(raw['posed_joints']-gp,axis=-1)
    framewise=[dict(frame=i,time_s=i/30,root_position_error_m=float(np.linalg.norm(q[i,:3]-plan['source_qpos'][i,:3])),
                    left_wrist_error_m=float(werr[i,0]),right_wrist_error_m=float(werr[i,1])) for i in range(len(q))]
    summary=dict(actual_frames=len(q),raw_root_position_error_max_m=max(r['root_position_error_m'] for r in framewise),
                 canonical_right_wrist_error_max_m=float(werr[:,1].max()),canonical_right_wrist_grasp_lift_hold_error_max_m=float(werr[240:,1].max()),
                 sdk_joint_position_error_max_m=float(modelerror.max()),joint_limit_violation_max_rad=float(np.max(limits)),
                 physical_success=None,expert_valid=None)
    write_json(a.generation/'conditioning_metrics.json',dict(summary=summary,framewise=framewise));print(json.dumps(summary,indent=2))
if __name__=='__main__':main()
