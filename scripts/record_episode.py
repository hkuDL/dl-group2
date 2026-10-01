"""Synchronized 50 Hz states/references and 10 Hz head/wrist RGB episodes."""
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import platform
import subprocess
import uuid

import mujoco
import numpy as np
from scene import ROOT, ROBOT

BODY_NAMES = ([f'{side}_{part}_joint' for side in ('left','right') for part in
              ('hip_pitch','hip_roll','hip_yaw','knee','ankle_pitch','ankle_roll')]
              + [f'waist_{a}_joint' for a in ('yaw','roll','pitch')]
              + [f'{side}_{part}_joint' for side in ('left','right') for part in
                 ('shoulder_pitch','shoulder_roll','shoulder_yaw','elbow','wrist_roll','wrist_pitch','wrist_yaw')])
HAND_NAMES = ['right_hand_'+part+'_joint' for part in
              ('thumb_0','thumb_1','thumb_2','index_0','index_1','middle_0','middle_1')]
STAGES = {'reach':0,'lower':1,'close':2,'lift':3,'hold':4}


def git_output(*args, cwd=ROOT):
    result=subprocess.run(['git',*args],cwd=cwd,text=True,capture_output=True)
    return result.stdout.strip() if result.returncode==0 else None


def provenance():
    files=[*sorted((ROOT/'scripts').glob('*.py')),*sorted((ROOT/'scenes').glob('*.xml')),
           *sorted((ROOT/'configs').glob('*.json'))]
    return {
        'project_commit':git_output('rev-parse','HEAD'),
        'project_status':git_output('status','--short'),
        'third_party_commit':git_output('rev-parse','HEAD',cwd=ROOT/'third_party/GR00T-WholeBodyControl'),
        'third_party_status':git_output('status','--short',cwd=ROOT/'third_party/GR00T-WholeBodyControl'),
        'source_sha256':{str(p.relative_to(ROOT)):hashlib.sha256(p.read_bytes()).hexdigest() for p in files},
        'robot_xml':str(ROBOT.relative_to(ROOT)),
        'robot_xml_sha256':hashlib.sha256(ROBOT.read_bytes()).hexdigest(),
        'python':platform.python_version(),'mujoco':mujoco.__version__,'numpy':np.__version__,
    }


def save_rgb(path, pixels):
    import struct,zlib
    def chunk(kind, payload):
        return struct.pack('!I',len(payload))+kind+payload+struct.pack('!I',zlib.crc32(kind+payload)&0xffffffff)
    height,width=pixels.shape[:2]
    header=struct.pack('!2I5B',width,height,8,2,0,0,0)
    raw=b''.join(b'\x00'+row.tobytes() for row in pixels)
    Path(path).write_bytes(b'\x89PNG\r\n\x1a\n'+chunk(b'IHDR',header)+chunk(b'IDAT',zlib.compress(raw))+chunk(b'IEND',b''))


class EpisodeRecorder:
    def __init__(self, model, config, case, output_root, repeat=0, run_id=None):
        self.m,self.config,self.case=model,config,case
        self.output_root=Path(output_root)
        self.repeat,self.run_id=repeat,run_id
        self.rows=[];self.head=[];self.wrist=[];self.obs_indices=[]
        self.saved=None;self.last_step=-1
        self.state_stride=self.stride(config['state_hz'])
        self.image_stride=self.stride(config['image_hz'])
        if self.image_stride%self.state_stride:
            raise ValueError('Image samples must coincide with state samples')
        self.bj=np.array([model.joint(n).id for n in BODY_NAMES])
        self.hj=np.array([model.joint(n).id for n in HAND_NAMES])
        self.bq=model.jnt_qposadr[self.bj];self.bv=model.jnt_dofadr[self.bj]
        self.hq=model.jnt_qposadr[self.hj];self.hv=model.jnt_dofadr[self.hj]
        self.root_q=model.joint('floating_base_joint').qposadr[0]
        self.block_q=model.joint('task_cube_free').qposadr[0]
        self.renderer=mujoco.Renderer(model,height=config['image_height'],width=config['image_width'])
        self.render_options=mujoco.MjvOption()
        self.render_options.geomgroup[0]=0  # Hide duplicate collision meshes, not physics.

    def stride(self,hz):
        value=1/(self.m.opt.timestep*hz)
        if abs(value-round(value))>1e-8:raise ValueError('Sampling rate must divide simulation rate')
        return int(round(value))

    def capture(self,episode):
        step=episode.steps
        if step%self.state_stride or step==self.last_step:return
        self.last_step=step
        d,g=episode.data,episode.controller
        names=g.contacts()
        r,c=self.root_q,self.block_q
        self.rows.append({
            'timestamps':step*self.m.opt.timestep,
            'body_q':d.qpos[self.bq].copy(),'body_dq':d.qvel[self.bv].copy(),
            'hand_q':d.qpos[self.hq].copy(),'hand_dq':d.qvel[self.hv].copy(),
            'body_ref_q':g.plan.qpos[self.bq].copy(),'hand_ref_q':g.plan.qpos[self.hq].copy(),
            'root_pos':d.qpos[r:r+3].copy(),'root_quat':d.qpos[r+3:r+7].copy(),
            'root_ref_pos':g.plan.qpos[r:r+3].copy(),'root_ref_quat':g.plan.qpos[r+3:r+7].copy(),
            'block_pos':d.qpos[c:c+3].copy(),'block_quat':d.qpos[c+3:c+7].copy(),
            'eef_pos':d.xpos[g.wrist].copy(),'eef_quat':d.xquat[g.wrist].copy(),
            'contact_thumb':any('right_hand_thumb' in n for n in names),
            'contact_index':any('right_hand_index' in n for n in names),
            'contact_middle':any('right_hand_middle' in n for n in names),
            'phase':STAGES[g.stage],
            'qpos':d.qpos.copy(),'qvel':d.qvel.copy(),'ctrl':d.ctrl.copy(),
        })
        if step%self.image_stride==0:
            for name,dest in [('head_rgb',self.head),('wrist_rgb',self.wrist)]:
                self.renderer.update_scene(d,camera=name,scene_option=self.render_options)
                dest.append(self.renderer.render().copy())
            self.obs_indices.append(len(self.rows)-1)

    def finish(self,episode,completed=True,reason=None):
        if self.saved is not None:return self.saved
        if not self.rows:raise RuntimeError('Cannot save an episode without observations')
        arrays={key:np.asarray([row[key] for row in self.rows]) for key in self.rows[0]}
        for key in ('body','hand'):
            q=arrays[key+'_ref_q']
            arrays[key+'_ref_dq']=(np.gradient(q,arrays['timestamps'],axis=0,edge_order=1)
                                  if len(q)>1 else np.zeros_like(q))
        result=episode.report()
        result['success']=bool(completed and result['success'])
        result['completed']=bool(completed)
        result['failure_reason']=None if result['success'] else reason or 'lift_or_contact_hold_criterion_not_met'
        arrays['success']=np.asarray(result['success'])
        arrays['action_valid']=np.ones(len(self.rows),dtype=bool)
        arrays['action_valid'][-1]=False
        images={'head_rgb':np.asarray(self.head,dtype=np.uint8),
                'wrist_rgb':np.asarray(self.wrist,dtype=np.uint8),
                'obs_indices':np.asarray(self.obs_indices,dtype=np.int64)}
        images['image_timestamps']=arrays['timestamps'][images['obs_indices']]
        now=datetime.now(timezone.utc)
        name=f"{now.strftime('%Y%m%dT%H%M%S%fZ')}_{self.case['id']}_r{self.repeat+1}_{uuid.uuid4().hex[:6]}"
        category='success' if result['success'] else 'failure'
        pending=self.output_root/'_pending'/name
        pending.mkdir(parents=True,exist_ok=False)
        np.savez_compressed(pending/'states.npz',**arrays)
        np.savez_compressed(pending/'images.npz',**images)
        cameras={}
        for name_cam in ('head_rgb','wrist_rgb'):
            cid=self.m.camera(name_cam).id
            cameras[name_cam]={
                'parent_body':self.m.body(self.m.cam_bodyid[cid]).name,
                'local_pos':self.m.cam_pos[cid].tolist(),'local_quat_wxyz':self.m.cam_quat[cid].tolist(),
                'fovy_degrees':float(self.m.cam_fovy[cid]),
                'width':self.config['image_width'],'height':self.config['image_height'],
            }
        metadata={
            'schema_version':1,'episode_id':name,'run_id':self.run_id,'created_utc':now.isoformat(),
            'case':self.case,'repeat_index':self.repeat,'instruction':self.config['instruction'],
            'config':self.config,'seed':None,'randomization':'none; repeats are deterministic reproducibility checks',
            'result':result,'positive_bc_candidate':result['success'],
            'clean_bc_eligible':bool(result['success'] and result['robot_table_contact_steps']==0),
            'quality_flags':['supported_pelvis']+(['robot_table_contact'] if result['robot_table_contact_steps'] else []),
            'body_joint_names':BODY_NAMES,'hand_joint_names':HAND_NAMES,
            'actuator_names':[self.m.actuator(i).name for i in range(self.m.nu)],
            'qpos_joint_names':[self.m.joint(i).name for i in range(self.m.njnt)],
            'jnt_qposadr':self.m.jnt_qposadr.tolist(),'jnt_dofadr':self.m.jnt_dofadr.tolist(),
            'phase_codes':STAGES,'units':{'position':'m','angle':'rad','time':'s','torque':'N*m'},
            'pose_frame':'MuJoCo world','quaternion_order':'wxyz',
            'eef_frame':'right_wrist_yaw_link body origin (not a fingertip or grasp center)',
            'privileged_fields':['block_pos','block_quat','eef_pos','eef_quat','contact_thumb','contact_index','contact_middle'],
            'observation_action_alignment':'State at t and currently commanded reference at t, captured before integration; final row action_valid=false',
            'reference_velocity_method':'np.gradient of 50 Hz reference positions; central interior, one-sided endpoints; postprocessed label, not a separate controller command',
            'controller':'scripted IK + torque PD + qfrc_bias; reference updates 100 Hz, torque 500 Hz',
            'kp':episode.controller.kp.tolist(),'kd':episode.controller.kd.tolist(),
            'contact_definition':'MuJoCo generated contact presence between cube and named finger bodies, not a force threshold',
            'root_reference':'Fixed initial floating-base pose used by the support; actual root pose stored separately',
            'cameras':cameras,'sample_count':len(self.rows),'image_count':len(self.obs_indices),
            'sonic_export_status':'Intermediate named-joint reference; deployment compatibility not validated',
            'provenance':provenance(),
        }
        (pending/'metadata.json').write_text(json.dumps(metadata,indent=2,ensure_ascii=False)+'\n',encoding='utf-8')
        if result['success']:
            export=pending/'body_reference';export.mkdir()
            mapping={'joint_pos':'body_ref_q','joint_vel':'body_ref_dq',
                     'body_pos':'root_ref_pos','body_quat':'root_ref_quat','hand_ref_q':'hand_ref_q'}
            for filename,key in mapping.items():np.savetxt(export/(filename+'.csv'),arrays[key],delimiter=',',fmt='%.12g')
            np.savetxt(export/'timestamps.csv',arrays['timestamps'],delimiter=',',fmt='%.12g')
        if self.head:
            save_rgb(pending/'head_first.png',self.head[0]);save_rgb(pending/'head_last.png',self.head[-1])
            save_rgb(pending/'wrist_first.png',self.wrist[0]);save_rgb(pending/'wrist_last.png',self.wrist[-1])
        final=self.output_root/category/pending.name
        final.parent.mkdir(parents=True,exist_ok=True)
        pending.rename(final)
        row={'episode_id':final.name,'path':str(final.relative_to(self.output_root)),
             'case_id':self.case['id'],'repeat_index':self.repeat,'run_id':self.run_id,**result}
        with (self.output_root/'manifest.jsonl').open('a',encoding='utf-8') as stream:
            stream.write(json.dumps(row,ensure_ascii=False)+'\n')
        self.saved=final
        print(f'SAVED {final}',flush=True)
        return final

    def close(self):
        self.renderer.close()
