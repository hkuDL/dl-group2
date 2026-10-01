"""Run all JSON positions, retaining both complete successes and failures."""
import argparse
from datetime import datetime,timezone
import json
from pathlib import Path
import shutil
import uuid
from cases import DEFAULT_CONFIG,read_cases,reset_case,case_index
from scene import ROOT,load_scene
from pick_red_cube import Episode
from record_episode import EpisodeRecorder,provenance


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--config',type=Path,default=DEFAULT_CONFIG)
    parser.add_argument('--output',type=Path,default=ROOT/'outputs/episodes')
    parser.add_argument('--case',help='Only one case ID or one-based index')
    parser.add_argument('--repeats',type=int,help='Override repeats per position')
    args=parser.parse_args()
    config=read_cases(args.config)
    repeats=config['repeats'] if args.repeats is None else args.repeats
    if repeats<1:parser.error('repeats must be positive')
    config['repeats']=repeats
    selected=config['cases'] if args.case is None else [config['cases'][case_index(config,args.case)]]
    run_id=datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ')+'_'+uuid.uuid4().hex[:6]
    run_dir=args.output/'runs'/run_id;run_dir.mkdir(parents=True,exist_ok=False)
    (run_dir/'config.json').write_text(json.dumps(config,indent=2,ensure_ascii=False),encoding='utf-8')
    prov=provenance()
    (run_dir/'provenance.json').write_text(json.dumps(prov,indent=2),encoding='utf-8')
    for relative in prov['source_sha256']:
        destination=run_dir/'source'/relative;destination.parent.mkdir(parents=True,exist_ok=True)
        shutil.copy2(ROOT/relative,destination)
    m,d=load_scene(supported=True)
    results=[]
    for case in selected:
        for repeat in range(repeats):
            reset_case(m,d,case)
            episode=Episode(m,d)
            recorder=EpisodeRecorder(m,config,case,args.output,repeat,run_id)
            print(f"CASE {case['id']} xy={case['block_xy']} repeat={repeat+1}/{repeats}",flush=True)
            reason=None;complete=False
            try:
                while episode.steps*m.opt.timestep<config['duration_seconds']-1e-9:
                    episode.step(recorder)
                episode.prepare();recorder.capture(episode)
                complete=True
            except Exception as exc:
                reason=f'{type(exc).__name__}: {exc}'
                print(reason,flush=True)
            try:
                path=recorder.finish(episode,complete,reason)
                result=json.loads((path/'metadata.json').read_text())['result']
                results.append({'case_id':case['id'],'repeat':repeat+1,'path':str(path),**result})
            finally:recorder.close()
    summary={'run_id':run_id,'attempts':len(results),'successes':sum(r['success'] for r in results),'episodes':results}
    (run_dir/'summary.json').write_text(json.dumps(summary,indent=2),encoding='utf-8')
    print(json.dumps(summary,indent=2),flush=True)
    if summary['successes']!=summary['attempts']:raise SystemExit(1)


if __name__=='__main__':main()
