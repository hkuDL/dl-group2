"""Actual condition pose and JSON save/load checks; diagnostic only, no generation."""
import os,sys,json,tempfile,hashlib
from pathlib import Path
import numpy as np,torch,mujoco
import xml.etree.ElementTree as ET
os.environ.update(GIT_CONFIG_COUNT='2',GIT_CONFIG_KEY_0='safe.directory',GIT_CONFIG_VALUE_0='/workspace/group2/dl-group2',GIT_CONFIG_KEY_1='safe.directory',GIT_CONFIG_VALUE_1='/workspace/group2/GR00T-WholeBodyControl')
sys.path[:0]=['/workspace/group2/dl-group2/scripts','/workspace/group2/kimodo-t6/g1-integration/coordinate-repair-20261007-v2']
from kimodo.skeleton import G1Skeleton34
from kimodo.exports.mujoco import MujocoQposConverter
from kimodo.constraints import FullBodyConstraintSet,EndEffectorConstraintSet,save_constraints_lst,load_constraints_lst
from kimodo_condition_coordinates import qpos_to_motion_dict_exact
import inspect,kimodo.geometry,kimodo.constraints,kimodo.skeleton.kinematics
from scene import load_scene
from cases import reset_case
BASE=Path('/workspace/group2');c=MujocoQposConverter(G1Skeleton34());sk=c.skeleton
protected=[Path(inspect.getfile(MujocoQposConverter)),Path(kimodo.geometry.__file__),Path(kimodo.constraints.__file__),Path(kimodo.skeleton.kinematics.__file__),Path(c.xml_path),Path(sk.folder)/'joints.p',Path(sk.folder)/'rest_pose_local_rot.p',BASE/'kimodo-t6/g1-integration/kimodo_to_t7_reference.py',BASE/'dl-group2/scenes/tabletop.xml',BASE/'GR00T-WholeBodyControl/decoupled_wbc/control/robot_model/model_data/g1/g1_29dof_with_hand_rev_1_0_activatedfinger.xml']
hashes_before={str(p):hashlib.sha256(p.read_bytes()).hexdigest() for p in protected}
src=BASE/'workspace/tuchengyuan/task5/ardy_handoff_20261007/candidates/center/setting.npz'
spec=json.loads(src.with_suffix('.json').read_text())
with np.load(src,allow_pickle=False) as z:poses=z['conditioning_qpos'].copy()
names=lambda p:[j.get('name') for j in ET.parse(p).findall('.//worldbody//joint') if j.get('type')!='free']
sn=names(BASE/'workspace/fuyuhan/ardy/ardy/assets/skeletons/g1skel34/xml/g1.xml');tn=names(c.xml_path)
poses=np.c_[poses[:,:7],poses[:,7:][:,[sn.index(n) for n in tn]]].astype(np.float32)
model,_=load_scene(supported=False,robot_path=BASE/'GR00T-WholeBodyControl/decoupled_wbc/control/robot_model/model_data/g1/g1_29dof_with_hand_rev_1_0_activatedfinger.xml')
initial=np.asarray(spec['initial_qpos']);root=int(model.joint('floating_base_joint').qposadr[0]);qa=[int(model.joint(n).qposadr[0]) for n in tn]
neutral=np.r_[initial[root:root+7],initial[qa]].astype(np.float32)
poses=np.vstack([neutral,poses])
original=c.qpos_to_motion_dict(poses,30,root_quat_w_first=True,mujoco_rest_zero=False)
old=c.to_qpos(original['local_rot_mats'][None],original['root_positions'][None],root_quat_w_first=True,mujoco_rest_zero=False).numpy()[0]
mode=os.environ.get('COORDINATE_TEST_MODE','matrix')
motion=original if mode=='original' else qpos_to_motion_dict_exact(c,poses,30)
q=c.to_qpos(motion['local_rot_mats'][None],motion['root_positions'][None],root_quat_w_first=True,mujoco_rest_zero=False).numpy()[0]
error=float(np.max(abs(q-poses)))
assert error<=1e-6,f'Actual canonical pose conversion exceeds 1e-6: {error}'
# Ordinal test indices are intentionally not episode frame indices; do not use
# this diagnostic JSON as task conditions or infer timing from fps=30 here.
indices=torch.arange(len(poses))
full=FullBodyConstraintSet(sk,indices,motion['posed_joints'],motion['global_rot_mats'])
eef=EndEffectorConstraintSet(sk,indices,motion['posed_joints'],motion['global_rot_mats'],None,joint_names=['RightHand','LeftHand','LeftFoot','RightFoot','Hips'])
with tempfile.TemporaryDirectory(prefix='kimodo-coordinate-json-') as temp:
 path=Path(temp)/'diagnostic_constraints.json'
 if mode=='matrix':
  from kimodo_pose_constraint_codec import make_pose_constraint_record,save_pose_constraint_record,load_pose_constraints
  record=make_pose_constraint_record(c,poses,indices.numpy(),30,fullbody_rows=np.arange(len(poses)),purpose='coordinate_diagnostic_not_episode_conditions')
  save_pose_constraint_record(path,record)
  loaded,codec_metadata=load_pose_constraints(path,c)
  try: save_pose_constraint_record(path,record)
  except FileExistsError: pass
  else: raise AssertionError('Existing conditions overwritten')
  for kind in ['schema','frames','matrix','target','nan']:
   broken=json.loads(json.dumps(record))
   if kind=='schema': broken['schema']='unsupported'
   if kind=='frames': broken['frame_indices'][1]=broken['frame_indices'][0]
   if kind=='matrix': broken['local_rot_mats'][0][0][0][0]=0
   if kind=='target': broken['canonical_qpos'][0][7]+=.1
   if kind=='nan': broken['root_positions'][0][0]=float('nan')
   bad=Path(temp)/f'bad_{kind}.json';bad.write_text(json.dumps(broken))
   try: load_pose_constraints(bad,c)
   except ValueError: pass
   else: raise AssertionError(f'Corrupted {kind} accepted')
 else:
  save_constraints_lst(str(path),[full,eef])
  loaded=load_constraints_lst(str(path),sk)
  codec_metadata=None
 loaded_errors=[]
 for obj in loaded:
  local=sk.global_rots_to_local_rots(obj.global_joints_rots)
  restored=c.to_qpos(local[None],obj.global_joints_positions[None,:,sk.root_idx],root_quat_w_first=True,mujoco_rest_zero=False).numpy()[0]
  e=float(np.max(abs(restored-poses)));loaded_errors.append(e)
  print(json.dumps({'diagnostic_constraint':obj.name,'max_error':e,'argmax':[int(x) for x in np.unravel_index(np.argmax(abs(restored-poses)),poses.shape)],'neutral_max':float(np.max(abs(restored[0]-poses[0])))}),flush=True)
  if os.environ.get('COORDINATE_DIAGNOSTIC')!='1':
   assert e<=1e-6,f'Constraint JSON lost canonical pose: {e}'
matrix=c.kimodo_to_mujoco_matrix.numpy();canonical_export_errors=[];deltas=[];angle_deltas=[]
for i,(target,exported) in enumerate(zip(poses,q)):
 data=mujoco.MjData(model);recovered=mujoco.MjData(model)
 for d,qp in [(data,target),(recovered,exported)]:
  reset_case(model,d,spec['case']);d.qpos[:]=initial;d.qpos[root:root+7]=qp[:7];d.qpos[qa]=qp[7:];mujoco.mj_forward(model,d)
 for side in ['left','right']:
  body=model.body(f'{side}_wrist_yaw_link').id;j=sk.bone_order_names.index(f'{side}_wrist_yaw_skel')
  canonical_export_errors.append(float(np.linalg.norm(data.xpos[body]-recovered.xpos[body])))
  model_world=matrix@motion['posed_joints'][i,j].numpy()
  deltas.append(model_world-data.xpos[body])
  model_rot=matrix@motion['global_rot_mats'][i,j].numpy()@matrix.T
  rel=model_rot@data.xmat[body].reshape(3,3).T
  angle_deltas.append(float(np.arccos(np.clip((np.trace(rel)-1)/2,-1,1))))
assert max(canonical_export_errors)<=1e-5
delta=np.stack(deltas)
hashes_after={str(p):hashlib.sha256(p.read_bytes()).hexdigest() for p in protected}
assert hashes_before==hashes_after,'Protected files changed'
print(json.dumps({'fixture':'canonical neutral + existing ARDY conditioning poses; not Kimodo generated','pose_count':len(poses),'old_root_body_max_error':float(np.max(abs(old-poses))),'fixed_root_body_max_error':error,'constraint_json_roundtrip_max_errors':loaded_errors,'codec_metadata':codec_metadata,'canonical_wrist_target_vs_exported_max_error_m':max(canonical_export_errors),'model_vs_canonical_wrist_origin_distance_range_m':[float(np.linalg.norm(delta,axis=1).min()),float(np.linalg.norm(delta,axis=1).max())],'model_vs_canonical_wrist_rotation_error_range_rad':[min(angle_deltas),max(angle_deltas)],'wrist_delta_span_xyz_m':np.ptp(delta,axis=0).tolist(),'pose_based_conditions_verified':True,'world_coordinates_are_identity_mapping':False,'episode_timing_validated':False,'generated_task':False,'physics_steps':0,'protected_hashes':hashes_after,'protected_files_unchanged':True,'tampered_inputs_rejected':mode=='matrix'},indent=2))
