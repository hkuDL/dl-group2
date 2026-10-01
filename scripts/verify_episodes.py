"""Validate saved schema, time alignment, name mappings and reference CSVs."""
import argparse
import json
from pathlib import Path
import numpy as np
from record_episode import BODY_NAMES,HAND_NAMES
from scene import ROOT


def validate(folder):
    meta=json.loads((folder/'metadata.json').read_text(encoding='utf-8'))
    with np.load(folder/'states.npz',allow_pickle=False) as file:
        states={k:file[k] for k in file.files}
    with np.load(folder/'images.npz',allow_pickle=False) as file:
        images={k:file[k] for k in file.files}
    t=states['timestamps'];n=len(t);ni=len(images['obs_indices'])
    assert n==meta['sample_count'] and ni==meta['image_count']
    assert meta['body_joint_names']==BODY_NAMES and meta['hand_joint_names']==HAND_NAMES
    expected={'body_q':29,'body_dq':29,'body_ref_q':29,'body_ref_dq':29,
              'hand_q':7,'hand_dq':7,'hand_ref_q':7,'hand_ref_dq':7,
              'root_pos':3,'root_quat':4,'root_ref_pos':3,'root_ref_quat':4,
              'block_pos':3,'block_quat':4,'eef_pos':3,'eef_quat':4}
    for key,width in expected.items():
        assert states[key].shape==(n,width),(folder,key,states[key].shape)
        assert np.isfinite(states[key]).all(),(folder,key)
    assert np.allclose(t,np.arange(n)/meta['config']['state_hz'],atol=1e-10)
    assert states['action_valid'].shape==(n,) and not states['action_valid'][-1]
    for key in ('contact_thumb','contact_index','contact_middle'):
        assert states[key].shape==(n,) and states[key].dtype==np.bool_
    for key in ('root_quat','root_ref_quat','block_quat','eef_quat'):
        assert np.allclose(np.linalg.norm(states[key],axis=1),1,atol=1e-6)
    for group,names in [('body',BODY_NAMES),('hand',HAND_NAMES)]:
        ids=[meta['qpos_joint_names'].index(name) for name in names]
        qa=np.asarray(meta['jnt_qposadr'])[ids];va=np.asarray(meta['jnt_dofadr'])[ids]
        assert np.array_equal(states[group+'_q'],states['qpos'][:,qa])
        assert np.array_equal(states[group+'_dq'],states['qvel'][:,va])
    if meta['result']['completed']:
        assert np.max(abs(states['body_q']-states['body_ref_q']))>1e-5, 'Actual/ref may have been incorrectly copied'
    ratio=meta['config']['state_hz']//meta['config']['image_hz']
    assert np.array_equal(images['obs_indices'],np.arange(0,n,ratio))
    assert np.array_equal(images['image_timestamps'],t[images['obs_indices']])
    for key in ('head_rgb','wrist_rgb'):
        assert images[key].shape==(ni,meta['config']['image_height'],meta['config']['image_width'],3)
        assert images[key].dtype==np.uint8 and images[key].std()>5
    assert bool(states['success'])==meta['result']['success']
    if meta['result']['completed']:
        assert abs(t[-1]-meta['config']['duration_seconds'])<1e-9
    if meta['result']['success']:
        assert folder.parent.name=='success'
        lifted=states['block_pos'][:,2]-states['block_pos'][0,2]>=.10
        contacts=states['contact_thumb']&(states['contact_index']|states['contact_middle'])
        assert np.all((lifted&contacts)[-int(2*meta['config']['state_hz']):])
        mapping={'joint_pos':'body_ref_q','joint_vel':'body_ref_dq','body_pos':'root_ref_pos',
                 'body_quat':'root_ref_quat','hand_ref_q':'hand_ref_q','timestamps':'timestamps'}
        for csv,key in mapping.items():
            value=np.loadtxt(folder/'body_reference'/(csv+'.csv'),delimiter=',')
            assert value.shape==states[key].shape and np.allclose(value,states[key],atol=1e-9)
    else:
        assert folder.parent.name=='failure' and not (folder/'body_reference').exists()
    return {'case_id':meta['case']['id'],'success':meta['result']['success'],
            'states':n,'frames_per_camera':ni,'episode':folder.name}


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('root',type=Path,nargs='?',default=ROOT/'outputs/episodes')
    args=parser.parse_args()
    folders=sorted(args.root.glob('success/*/metadata.json'))+sorted(args.root.glob('failure/*/metadata.json'))
    if not folders:raise SystemExit('No episodes found')
    results=[validate(path.parent) for path in folders]
    print(json.dumps({'validated':len(results),'episodes':results},indent=2))


if __name__=='__main__':main()
