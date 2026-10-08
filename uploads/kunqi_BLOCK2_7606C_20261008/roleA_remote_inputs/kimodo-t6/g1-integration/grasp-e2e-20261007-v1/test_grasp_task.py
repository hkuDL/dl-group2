"""Actual CPU IK/clock/finger acceptance, run after prepare_grasp_task."""
import argparse,json
from pathlib import Path
import numpy as np

def main():
    p=argparse.ArgumentParser();p.add_argument('--task',type=Path,required=True);a=p.parse_args()
    assert (a.task/'task.json').exists(),'New task compiler has not produced task.json'
    s=json.loads((a.task/'task.json').read_text());z=np.load(a.task/'task_plan.npz',allow_pickle=False)
    n=s['reference_frames'];ns=s['source_min_frames']
    assert n>=800 and s['duration_s']>=16
    assert z['timestamps'].shape==(n,) and z['source_qpos'].shape==(ns,36)
    assert z['hand_ref_q'].shape==(n,14) and z['hand_ref_dq'].shape==(n,14)
    assert all(np.isfinite(z[k]).all() for k in z.files)
    np.testing.assert_allclose(z['timestamps'],np.arange(n)/50,rtol=0,atol=1e-12)
    np.testing.assert_allclose(z['source_timestamps'],np.arange(ns)/30,rtol=0,atol=1e-12)
    assert z['source_timestamps'][-1]>=z['timestamps'][-1]
    assert len(set(s['body_joint_order']))==29 and len(set(s['hand_joint_order']))==14
    np.testing.assert_allclose(z['hand_ref_q'][0],0,atol=1e-10,rtol=0)
    np.testing.assert_allclose(z['hand_ref_q'][:,:7],0,atol=1e-10,rtol=0)
    nonzero=np.flatnonzero(np.max(abs(z['hand_ref_q'][:,7:]),axis=1)>1e-8)
    assert len(nonzero)>0 and 8<=z['timestamps'][nonzero[0]]<=8.04
    np.testing.assert_allclose(z['hand_ref_q'][500:]-z['hand_ref_q'][500],0,atol=1e-8)
    np.testing.assert_allclose(z['hand_ref_dq'],np.gradient(z['hand_ref_q'],z['timestamps'],axis=0),atol=1e-9)
    metrics=json.loads((a.task/'planning_metrics.json').read_text())
    assert metrics['grasp_and_lift_position_error_max_m']<=.02
    assert metrics['joint_limits_pass'] and metrics['frame_zero_pass']
    assert not metrics['physics_replay_run'] and not metrics['model_generation_run']
    c=json.loads((a.task/'pose_constraints.json').read_text())
    assert c['schema']=='kimodo_canonical_pose_constraints_v1' and c['frame_indices'][-1]<ns
    assert not c['direct_world_coordinate_copy']
    print(json.dumps({'passed':True,'source_frames':ns,'reference_frames':n,
         'first_finger_closure_s':float(z['timestamps'][nonzero[0]]),'planning_metrics':metrics},indent=2))
if __name__=='__main__':main()
