"""Predeclared five-case, two-replay development test; no retry-until-success."""
import argparse
import json
import os
from pathlib import Path
import subprocess
import sys
import time


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--package',type=Path,required=True)
    args=p.parse_args();root=args.package.resolve();code=root/'code';out=root/'grid_v1'
    out.mkdir(exist_ok=False)
    config=json.loads(Path('/workspace/group2/dl-group2/configs/grasp_cases.json').read_text())
    protocol=dict(test_type='development robustness, not held-out final comparison',cases=config['cases'],
        repeats_per_case=2,source_generation_seed=0,source_mode='cached_ardy_coordinate_retarget',
        task_duration_seconds=16,shared_legacy_config_duration_seconds=config['duration_seconds'],
        duration_reason='shared schema v3 and frozen ARDY clip use 16 seconds; no per-case duration tuning',
        wrist_clearance_m=.03,xy_correction='known case target minus original ARDY center target; 4-7s smooth blend',
        no_per_case_tuning=True,no_retry_until_success=True,interactive_user_corrections_per_trial=0)
    (out/'protocol.json').write_text(json.dumps(protocol,indent=2)+'\n')
    rows=[]
    def save():
        attempted=[r for r in rows if r.get('result')]
        summary=dict(protocol=protocol,trials=rows,
            executed_replays=len(attempted),planned_replays=2*len(config['cases']),
            physical_successes=sum(r['result']['physical_success'] for r in attempted),
            expert_successes=sum(r.get('independent_expert_confirmed',False) for r in attempted))
        (out/'summary.json').write_text(json.dumps(summary,indent=2)+'\n')
    for case in config['cases']:
        candidate=root/'candidates'/case['id']
        if case['id']!='center':
            t=time.monotonic()
            cmd=[sys.executable,str(code/'raise_wrist_candidate.py'),'--source',str(root/'candidates/integrated'),
                '--out',str(candidate),'--height','.03','--case',case['id']]
            with (out/f"prepare_{case['id']}.log").open('w') as f:r=subprocess.run(cmd,stdout=f,stderr=subprocess.STDOUT)
            preparation_seconds=time.monotonic()-t
            if r.returncode:
                rows.append(dict(case=case,stage='candidate_preparation_failed',exit_code=r.returncode,preparation_seconds=preparation_seconds))
                save();print('PREPARATION_FAILED',case['id'],flush=True);continue
        else:preparation_seconds=None
        for repeat in (1,2):
            name=f"{case['id']}_r{repeat}";run=out/name;t=time.monotonic()
            cmd=[sys.executable,str(code/'canonical_grasp.py'),'--candidate',str(candidate),'--out',str(run)]
            with (out/(name+'.log')).open('w') as f:r=subprocess.run(cmd,stdout=f,stderr=subprocess.STDOUT)
            row=dict(case=case,repeat=repeat,exit_code=r.returncode,total_replay_process_wall_seconds=time.monotonic()-t,
                candidate_preparation_seconds=preparation_seconds,source_generation_wall_seconds=None,
                runtime_user_corrections=0,reference=str(candidate),run=str(run))
            if (run/'result.json').exists():
                row['result']=json.loads((run/'result.json').read_text())
                with (out/(name+'_validation.log')).open('w') as f:
                    subprocess.run([sys.executable,str(code/'validate_grasp_run.py'),str(run)],stdout=f,stderr=subprocess.STDOUT)
                if (run/'validation.json').exists():row['independent_expert_confirmed']=json.loads((run/'validation.json').read_text())['expert_valid_confirmed']
                print(name, {k:row['result'][k] for k in ['physical_success','expert_valid','recorded_frames','failure_reasons']},flush=True)
            else:row['stage']='no_rollout_result';print(name,'NO_RESULT',r.returncode,flush=True)
            rows.append(row);save()
            if r.returncode not in (0,2) or any('Concurrent' in x for x in row.get('result',{}).get('failure_reasons',[])):
                print('STOP: execution environment needs inspection',flush=True);return 2
    save();print('GRID_COMPLETE',out,flush=True);return 0


if __name__=='__main__':raise SystemExit(main())
