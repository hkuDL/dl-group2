"""Supported physical red-cube grasp: IK + torque PD, not SONIC/free standing."""
import argparse
import json
from pathlib import Path
import time
import mujoco
import numpy as np
from scene import load_scene
from grasp import Grasp


def save_image(model, data, path):
    import struct
    import zlib
    def chunk(kind, payload):
        return (struct.pack('!I', len(payload)) + kind + payload
                + struct.pack('!I', zlib.crc32(kind + payload) & 0xffffffff))
    with mujoco.Renderer(model, height=720, width=960) as renderer:
        options=mujoco.MjvOption();options.geomgroup[0]=0
        renderer.update_scene(data, camera='task_overview',scene_option=options)
        pixels=renderer.render()
        header=struct.pack('!2I5B',960,720,8,2,0,0,0)
        raw=b''.join(b'\x00'+row.tobytes() for row in pixels)
        Path(path).write_bytes(b'\x89PNG\r\n\x1a\n'+chunk(b'IHDR',header)
                              +chunk(b'IDAT',zlib.compress(raw))+chunk(b'IEND',b''))


class Episode:
    def __init__(self, model, data):
        self.model,self.data=model,data
        self.controller=Grasp(model,data)
        self.steps=0
        self.hold=self.max_hold=self.max_lift=0.
        self.stage=''
        self.robot_table_steps=0
        self.robot_table_bodies=set()

    def prepare(self):
        m,d,g=self.model,self.data,self.controller
        if self.steps%5==0:g.control(d.time)
        g.apply()

    def step(self,recorder=None):
        m,d,g=self.model,self.data,self.controller
        self.prepare()
        if recorder is not None:recorder.capture(self)
        mujoco.mj_step(m,d)
        mujoco.mj_forward(m,d)
        if not np.isfinite(d.qpos).all() or not np.isfinite(d.qvel).all():
            raise RuntimeError('Non-finite simulation state')
        if any(w.number for w in d.warning):
            raise RuntimeError('MuJoCo reported a simulation warning')
        names=g.contacts()
        lift=float(d.xpos[g.cube,2]-g.origin[2])
        self.max_lift=max(self.max_lift,lift)
        thumb=any('right_hand_thumb' in n for n in names)
        fingers=any('right_hand_index' in n or 'right_hand_middle' in n for n in names)
        valid=lift>=.10 and thumb and fingers and 'task_table' not in names
        self.hold=self.hold+m.opt.timestep if valid else 0.
        self.max_hold=max(self.max_hold,self.hold)
        table=m.body('task_table').id
        for contact in d.contact:
            b1,b2=m.geom_bodyid[contact.geom1],m.geom_bodyid[contact.geom2]
            other=b2 if b1==table else b1 if b2==table else -1
            if other>0 and other!=g.cube:
                self.robot_table_steps+=1
                self.robot_table_bodies.add(m.body(other).name)
                break
        self.steps+=1
        if g.stage!=self.stage:
            self.stage=g.stage
            print(f'{d.time:5.2f}s {self.stage}',flush=True)

    def report(self):
        g=self.controller
        return {
            'mode':'supported_physics_ik_pd','sonic':False,
            'pelvis_supported':True,'object_attached':False,
            'simulation_seconds':float(self.data.time),
            'final_lift_m':float(self.data.xpos[g.cube,2]-g.origin[2]),
            'max_lift_m':self.max_lift,
            'max_continuous_grasp_hold_seconds':self.max_hold,
            'success':bool(self.hold>=2.0),
            'final_continuous_grasp_hold_seconds':self.hold,
            'criterion':'Lift >= 0.10 m with opposing finger contacts and no cube/table contact for >= 2 s',
            'final_cube_contacts':g.contacts(),
            'robot_table_contact_steps':self.robot_table_steps,
            'robot_table_contact_bodies':sorted(self.robot_table_bodies),
        }


def main():
    from queue import SimpleQueue
    from cases import DEFAULT_CONFIG,read_cases,case_index,reset_case
    from record_episode import EpisodeRecorder
    from scene import ROOT
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--preview',action='store_true',help='Free-base scene, physics paused')
    parser.add_argument('--check',action='store_true',help='Only validate model loading')
    parser.add_argument('--headless',action='store_true',help='Run physics without a GUI')
    parser.add_argument('--duration',type=float,help='Override JSON simulation duration')
    parser.add_argument('--seconds',type=float,help='Limit GUI wall time')
    parser.add_argument('--render',help='Save final PNG, or initial PNG with --preview')
    parser.add_argument('--report',help='Write episode metrics as JSON')
    parser.add_argument('--config',type=Path,default=DEFAULT_CONFIG)
    parser.add_argument('--case',default='1',help='JSON case ID or one-based index')
    parser.add_argument('--output',type=Path,default=ROOT/'outputs/episodes')
    parser.add_argument('--no-record',action='store_true',help='Debug only: disable full episode recording')
    args=parser.parse_args()
    if (args.duration is not None and args.duration<=0) or (args.seconds is not None and args.seconds<=0):
        parser.error('Durations must be positive')
    config=read_cases(args.config)
    if args.duration is not None:config['duration_seconds']=args.duration
    index=case_index(config,args.case)
    m,d=load_scene(supported=not args.preview)
    if m.nu!=43:raise RuntimeError(f'Expected 43 actuators, got {m.nu}')
    print(f'G1: nq={m.nq}, nv={m.nv}, nu={m.nu}',flush=True)
    print('PREVIEW: physics paused' if args.preview else
          'SUPPORTED PHYSICS: pelvis welded to world; IK + PD; no SONIC; cube has no attachment.',flush=True)
    if args.check:return
    episode=recorder=None

    def finish(completed,reason=None):
        if recorder is not None and recorder.saved is None:
            recorder.finish(episode,completed,reason)

    def start_case(new_index):
        nonlocal index,episode,recorder
        if recorder is not None:
            finish(False,'manual_reset_before_completion')
            recorder.close()
        index=new_index%len(config['cases'])
        case=config['cases'][index]
        reset_case(m,d,case)
        episode=None if args.preview else Episode(m,d)
        recorder=None
        if episode and not args.no_record:
            recorder=EpisodeRecorder(m,config,case,args.output)
            episode.prepare();recorder.capture(episode)
        print(f"CASE {index+1}/{len(config['cases'])}: {case['id']} xy={case['block_xy']}",flush=True)

    def done():
        return episode is not None and episode.steps*m.opt.timestep>=config['duration_seconds']-1e-9

    def complete():
        if recorder is not None and recorder.saved is None:
            episode.prepare();recorder.capture(episode)
            finish(True)

    start_case(index)
    if args.headless or args.render:
        if episode:
            try:
                while not done():episode.step(recorder)
                complete()
            except Exception:
                finish(False,'simulation_exception')
                raise
            finally:
                if recorder is not None:recorder.close()
    else:
        from mujoco import viewer as mjviewer
        keys=SimpleQueue()
        try:
            with mjviewer.launch_passive(m,d,key_callback=keys.put) as viewer:
                viewer.cam.lookat[:] = [.25, 0, .75]  # 相机注视的位置
                viewer.cam.distance = 2.8            # 相机到注视点的距离
                viewer.cam.azimuth = -155            # 水平方向角度
                viewer.cam.elevation = -18           # 俯仰角度
                viewer.opt.geomgroup[0]=0
                viewer.cam.type=mujoco.mjtCamera.mjCAMERA_FREE  # Keep robot foreground, table background.
                viewer.cam.fixedcamid=-1
                start=time.monotonic()
                last=d.time
                print('GUI_OPENED | R: reset current | N/P: next/previous',flush=True)
                while viewer.is_running():
                    frame_start=time.monotonic()
                    if args.seconds is not None and frame_start-start>=args.seconds:break
                    while not keys.empty():
                        key=keys.get()
                        target=index if key in (82,114) else index+1 if key in (78,110) else index-1 if key in (80,112) else None
                        if target is not None:
                            try:
                                with viewer.lock():start_case(target)
                            except Exception as error:
                                print(f'case switch failed: {type(error).__name__}: {error}',flush=True)
                    # MuJoCo's own Reset button only calls mj_resetData, so the cube goes back to
                    # the XML default and Grasp keeps the stale plan/origin. Re-sync everything.
                    if d.time+1e-9<last:
                        try:
                            with viewer.lock():start_case(index)
                        except Exception as error:
                            print(f'case switch failed: {type(error).__name__}: {error}',flush=True)
                        print('MuJoCo reset detected: replaying current case',flush=True)
                    last=d.time
                    if episode and not done():
                        for _ in range(10):
                            if done():break
                            episode.step(recorder)
                        if done():
                            complete()
                            print(json.dumps(episode.report(),indent=2),flush=True)
                            print('Finished. R: replay; N: next position.',flush=True)
                    viewer.sync()
                    time.sleep(max(0,0.02-(time.monotonic()-frame_start)))
        finally:
            if recorder is not None:
                finish(done(),'viewer_closed_before_completion')
                recorder.close()
    if args.render:save_image(m,d,args.render)
    if episode:
        result=episode.report()
        print(json.dumps(result,indent=2),flush=True)
        if args.report:Path(args.report).write_text(json.dumps(result,indent=2)+'\n')
        if (args.headless or args.render) and not result['success']:raise SystemExit(1)


if __name__=='__main__':main()
