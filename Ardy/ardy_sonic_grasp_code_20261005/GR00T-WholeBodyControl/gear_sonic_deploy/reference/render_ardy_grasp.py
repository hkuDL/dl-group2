#!/usr/bin/env python3
"""Render recorded physics states in the original block scene."""
import argparse,json
from pathlib import Path
import imageio.v2 as imageio
import mujoco,numpy as np

def main():
    repo=Path(__file__).resolve().parents[2]
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('playback_dir',type=Path)
    args=parser.parse_args(); out=args.playback_dir
    result=json.loads((out/'result.json').read_text())
    saved=np.load(out/'simulation.npz')
    start=result.get('playback_start_at',result['controller_ready_at']+2)
    choose=(saved['states'][:,0]>=start-.5)&(saved['states'][:,0]<=start+11.8)
    m=mujoco.MjModel.from_xml_path(str(repo/result['scene']))
    m.vis.global_.offwidth=1280; m.vis.global_.offheight=720
    d=mujoco.MjData(m)
    renderer=mujoco.Renderer(m,height=720,width=1280)
    camera=mujoco.MjvCamera()
    camera.lookat[:]=[.35,0,.85]; camera.distance=2.; camera.azimuth=135; camera.elevation=-20
    option=mujoco.MjvOption(); option.sitegroup[:]=0
    frames=[]
    for i in np.flatnonzero(choose)[::2]:
        d.qpos[:]=saved['qpos'][i]; d.qvel[:]=saved['qvel'][i]
        mujoco.mj_forward(m,d)
        renderer.update_scene(d,camera=camera,scene_option=option)
        frames.append(renderer.render().copy())
    for sec in [0,5,6,7,10]:
        k=min(len(frames)-1,int((sec+.5)*25)); imageio.imwrite(out/f'frame_{sec}.png',frames[k])
    renderer.close()
    imageio.mimsave(out/'ardy_sonic.mp4',frames,fps=25,codec='h264',format='pyav')
    imageio.imwrite(out/'final.png',frames[-1])
    print(out/'ardy_sonic.mp4')

if __name__=='__main__': main()
