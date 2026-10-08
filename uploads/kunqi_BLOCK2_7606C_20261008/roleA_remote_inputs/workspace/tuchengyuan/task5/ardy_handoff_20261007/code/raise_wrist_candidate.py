"""Offline ARDY trajectory adaptation: raise right wrist over table, preserve rotation."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import xml.etree.ElementTree as ET

import mujoco
import numpy as np


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--source',type=Path,required=True)
    p.add_argument('--out',type=Path,required=True)
    p.add_argument('--height',type=float,default=.015)
    p.add_argument('--case',help='Shared grasp_cases.json case; default preserves source case')
    args=p.parse_args()
    if not 0<args.height<=.05:p.error('Height must be (0, .05] metres')
    if args.out.exists():p.error('Output exists')
    project=Path('/workspace/group2/dl-group2')
    sonic=Path('/workspace/group2/GR00T-WholeBodyControl')
    ardy=Path('/workspace/group2/workspace/fuyuhan/ardy')
    robot=sonic/'decoupled_wbc/control/robot_model/model_data/g1/g1_29dof_with_hand_rev_1_0_activatedfinger.xml'
    converter=ardy.parent/'GR00T-WholeBodyControl/gear_sonic_deploy/reference/convert_ardy.py'
    os.environ['SONIC_REPO']=str(sonic)
    sys.path[:0]=[str(project/'scripts'),str(sonic)]
    import project_paths
    project_paths.default_robot_xml=lambda:robot
    from scene import load_scene
    from cases import read_cases,reset_case
    from grasp_reference import GraspReference
    spec=json.loads((args.source/'setting.json').read_text())
    model,data=load_scene(supported=False,robot_path=robot)
    data.qpos[:]=spec['initial_qpos'];mujoco.mj_forward(model,data)
    source_xy=np.array(spec['case']['block_xy'],float)
    original_generation_case=spec.get('original_generation_case',spec['case'])
    case=spec['case']
    if args.case:
        case=next((c for c in read_cases()['cases'] if c['id']==args.case),None)
        if case is None:raise ValueError('Unknown shared case '+args.case)
        if case.get('block_yaw_deg',0)!=spec['case'].get('block_yaw_deg',0):
            raise ValueError('This adapter supports translation only, not a yaw change')
    delta_xy=np.array(case['block_xy'])-source_xy
    names=[j.get('name') for j in ET.parse(ardy/'ardy/assets/skeletons/g1skel34/xml/g1.xml').findall('.//worldbody//joint') if j.get('type')!='free']
    jq=np.array([model.joint(n).qposadr[0] for n in names])
    original=np.loadtxt(args.source/'stationary_ardy.csv',delimiter=',',ndmin=2)
    q=original.copy();plan=GraspReference(model,data)
    cols=[names.index(model.joint(j).name)+7 for j in plan.arm]
    errors=[]
    for k,row in enumerate(original):
        data.qpos[:7]=row[:7];data.qpos[jq]=row[7:]
        mujoco.mj_forward(model,data)
        target=data.xpos[plan.wrist].copy()
        u=np.clip((k/25-4)/3,0,1);blend=u*u*(3-2*u)
        target[:2]+=delta_xy*blend
        target[2]+=args.height*blend
        plan.rotation=data.xmat[plan.wrist].reshape(3,3).copy()
        plan.plan.qpos[:]=data.qpos
        if u>0:plan.ik(target)
        mujoco.mj_forward(model,plan.plan)
        errors.append(float(np.linalg.norm(plan.plan.xpos[plan.wrist]-target)))
        q[k,cols]=plan.plan.qpos[plan.aq]
    if max(errors)>.001:raise RuntimeError(f'IK error too high: {max(errors)}')
    args.out.mkdir(parents=True)
    for n in ['setting.npz','constraints.json']:
        shutil.copy2(args.source/n,args.out/n)
    np.savetxt(args.out/'stationary_ardy.csv',q,delimiter=',')
    spec['source']='ARDY world-wrist IK retargeting plus smooth right-wrist table clearance; canonical SONIC execution'
    spec['postprocessing'].update(parent_candidate=str(args.source),wrist_clearance_height_m=args.height,
        clearance_blend_seconds=[4,7],orientation_preserved=True,max_ik_error_m=max(errors),
        target_xy_translation_m=delta_xy.tolist(),target_translation_blend_seconds=[4,7])
    spec['generation_mode']='cached_ardy_coordinate_retarget; no fresh text sampling'
    initial=np.array(spec['initial_qpos']);reset_case(model,data,case)
    cube_qadr=int(model.joint('task_cube_free').qposadr[0])
    initial[cube_qadr:cube_qadr+7]=data.qpos[cube_qadr:cube_qadr+7]
    spec.update(case=case,initial_qpos=initial.tolist(),cube_initial_position=initial[cube_qadr:cube_qadr+3].tolist())
    spec['original_generation_case']=original_generation_case
    spec['constraints_usage']='Preserved original ARDY conditioning; not regenerated or applied to the new case'
    saved=dict(np.load(args.out/'setting.npz',allow_pickle=False))
    saved['initial_qpos']=initial
    np.savez(args.out/'setting.npz',**saved)
    spec['adaptation_script_sha256']=hashlib.sha256(Path(__file__).read_bytes()).hexdigest()
    spec['converter_path']=str(converter)
    spec['converter_sha256']=hashlib.sha256(converter.read_bytes()).hexdigest()
    (args.out/'setting.json').write_text(json.dumps(spec,indent=2)+'\n')
    subprocess.run([sys.executable,str(converter),str(Path(spec['raw_source']).with_suffix('.npz')),
        '--ardy-repo',str(ardy),'--qpos-csv',str(args.out/'stationary_ardy.csv'),
        '--output-dir',str(args.out/'reference/motion')],check=True)
    for n in ['left_hand_pos.csv','right_hand_pos.csv','hand_plan.json']:
        shutil.copy2(args.source/'reference/motion'/n,args.out/'reference/motion'/n)
    print(json.dumps(dict(out=str(args.out),height_m=args.height,max_ik_error_m=max(errors)),indent=2))


if __name__=='__main__':main()
