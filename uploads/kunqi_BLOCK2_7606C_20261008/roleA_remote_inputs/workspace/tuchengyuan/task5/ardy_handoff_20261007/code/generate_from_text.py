"""Fresh text + canonical scene conditions -> ARDY -> offline adaptation -> SONIC.

This is a right-hand red-cube reach/grasp/lift workflow, not a general skill parser.
"""
import argparse
import json
import os
from pathlib import Path
import subprocess
import sys
import time


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('prompt')
    p.add_argument('--case',default='center',choices=['center','near','far','left','right'])
    p.add_argument('--seed',type=int,default=0)
    p.add_argument('--out',type=Path,required=True)
    p.add_argument('--generate-only',action='store_true')
    args=p.parse_args();out=args.out.resolve();out.mkdir(parents=True,exist_ok=False)
    if os.environ.get('MUSA_VISIBLE_DEVICES')!='4':p.error('Use authorized GPU4: MUSA_VISIBLE_DEVICES=4')
    from canonical_grasp import other_controllers
    busy=other_controllers()
    if busy:raise RuntimeError('Shared controller channel busy: '+str(busy))
    code=Path(__file__).resolve().parent;ardy=Path('/workspace/group2/workspace/fuyuhan/ardy')
    env=os.environ.copy()
    env.update(CUDA_VISIBLE_DEVICES='4',MUSA_VISIBLE_DEVICES='4',TEXT_ENCODER_MODE='local',
        TEXT_ENCODERS_DIR=str(ardy/'text_encoders'),HF_HUB_OFFLINE='1',TRANSFORMERS_OFFLINE='1')
    trace=dict(prompt=args.prompt,case_id=args.case,seed=args.seed,generation_mode='fresh',
        task='right-hand red-cube grasp and lift',duration_seconds=16,
        hand_schedule={'hand':'right','left':'open','close_seconds':[8,10]},
        spatial_target_source='shared case coordinates -> explicit constraints, not numbers parsed from prompt',stages=[])
    def run(stage,cmd,cwd=None):
        t=time.monotonic();print('START',stage,flush=True)
        with (out/(stage+'.log')).open('w') as f:
            result=subprocess.run(cmd,cwd=cwd,env=env,stdout=f,stderr=subprocess.STDOUT)
        trace['stages'].append(dict(stage=stage,command=cmd,wall_seconds=time.monotonic()-t,exit_code=result.returncode))
        (out/'pipeline.json').write_text(json.dumps(trace,indent=2)+'\n')
        print('END',stage,result.returncode,trace['stages'][-1]['wall_seconds'],flush=True)
        return result.returncode
    source=out/'source';raw=source/'reference/motion/ardy_motion'
    steps=[('prepare_conditions',[sys.executable,str(code/'prepare_conditions.py'),'--out',str(source),
            '--case',args.case,'--seed',str(args.seed),'--prompt',args.prompt],None),
        ('ardy_generation',[sys.executable,str(ardy/'scripts/generate.py'),args.prompt,'--model','g1',
            '--checkpoints_dir',str(ardy/'checkpoints'),'--duration','16','--seed',str(args.seed),
            '--constraints',str(source/'constraints.json'),'--output',str(raw)],ardy),
        ('trajectory_adaptation',[sys.executable,str(code/'retarget_from_ardy.py'),'--source',str(source),
            '--out',str(out/'candidate'),'--preserve-world-wrist','--clearance','.03'],None)]
    for stage,cmd,cwd in steps:
        if stage=='ardy_generation':raw.parent.mkdir(parents=True,exist_ok=True)
        if run(stage,cmd,cwd):return 2
    if args.generate_only:return 0
    replay_code=run('canonical_replay',[sys.executable,str(code/'canonical_grasp.py'),
        '--candidate',str(out/'candidate'),'--out',str(out/'run_01')])
    if (out/'run_01/result.json').exists():
        run('independent_validation',[sys.executable,str(code/'validate_grasp_run.py'),str(out/'run_01')])
    return replay_code


if __name__=='__main__':raise SystemExit(main())
