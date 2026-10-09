"""Run inside va-train. Copy Amy's work without overwriting T6 or moving her venv."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import shlex
import shutil
import subprocess
from datetime import datetime

def digest(path):
    h = hashlib.sha256()
    with path.open('rb') as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b''):
            h.update(chunk)
    return h.hexdigest()

def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--source', type=Path, default=Path('/workspace/group2/workspace/amy/kimodo-work'))
    p.add_argument('--destination', type=Path, default=Path('/workspace/group2/kimodo-t6/g1-integration'))
    a = p.parse_args()
    src, dst = a.source.resolve(), a.destination.resolve()
    if dst.exists():
        raise RuntimeError(f'Destination already exists; nothing overwritten: {dst}')
    if not dst.parent.is_dir() or src == dst or src in dst.parents or dst in src.parents:
        raise RuntimeError('Invalid source/destination or missing T6 parent directory')
    required = ['.venv/bin/activate', 'kimodo-upload/kimodo/scripts/generate.py',
                'kimodo-upload/kimodo/model/llm2vec/llm2vec.py',
                'checkpoints/Kimodo-G1-RP-v1/config.yaml',
                'checkpoints/Kimodo-G1-RP-v1/model.safetensors',
                'outputs/g1_smoke_right_hand.npz', 'outputs/g1_right_hand_100steps.npz']
    for name in required:
        if not (src / name).is_file():
            raise RuntimeError(f'Missing required file: {src / name}')
    if not (src / 'checkpoints/Kimodo-G1-RP-v1/stats').is_dir():
        raise RuntimeError('Checkpoint stats directory missing')
    def ignore(folder, names):
        return [n for n in names if n in ('.venv', '__pycache__', '.cache') or n.endswith('.tar.gz')]
    files = []
    for folder, dirs, names in os.walk(src, followlinks=False):
        dirs[:] = [n for n in dirs if n not in ignore(folder, dirs)]
        files.extend(Path(folder) / n for n in names if n not in ignore(folder, names) and not (Path(folder) / n).is_symlink())
    size = sum(f.stat().st_size for f in files)
    if shutil.disk_usage(dst.parent).free < size + 256 * 1024 * 1024:
        raise RuntimeError('Insufficient free disk space')
    stage = dst.parent / (dst.name + '.staging-' + datetime.now().strftime('%Y%m%d-%H%M%S-%f'))
    shutil.copytree(src, stage, symlinks=True, ignore=ignore)
    checks = {}
    for f in files:
        relative = f.relative_to(src)
        before, after = digest(f), digest(stage / relative)
        if before != after:
            raise RuntimeError(f'Checksum mismatch: {relative}; staging retained at {stage}')
        checks[str(relative)] = before
    git_info = {}
    for label, command in [('commit', ['rev-parse', 'HEAD']), ('branch', ['branch', '--show-current']), ('status', ['status', '--short']), ('diff', ['diff', '--binary'])]:
        result = subprocess.run(['git', '-C', str(src / 'kimodo-upload'), *command], capture_output=True, text=True, errors='replace')
        git_info[label] = {'returncode': result.returncode, 'stdout': result.stdout, 'stderr': result.stderr}
    (stage / 'merge-manifest.json').write_text(json.dumps({'source': str(src), 'destination': str(dst), 'created': datetime.now().isoformat(), 'status': 'files_verified_execution_not_tested', 'sha256': checks, 'git': git_info}, ensure_ascii=False, indent=2), encoding='utf-8')
    env = '\n'.join([
        '# Source this file inside va-train; keep the original venv in place.',
        'source ' + shlex.quote(str(src / '.venv/bin/activate')),
        'export PYTHONPATH=' + shlex.quote(str(dst / 'kimodo-upload')) + ':${PYTHONPATH:-}',
        'export CHECKPOINT_DIR=' + shlex.quote(str(dst / 'checkpoints')),
        'export TEXT_ENCODERS_DIR=/workspace/group2/workspace/fuyuhan/ardy/text_encoders',
        'export TEXT_ENCODER_DEVICE=cpu',
        'export KIMODO_DEVICE="${KIMODO_DEVICE:-musa:1}"',
        'export HF_HUB_OFFLINE=1 TRANSFORMERS_OFFLINE=1',
        'cd ' + shlex.quote(str(dst / 'kimodo-upload')), ''])
    (stage / 'activate-g1.sh').write_text(env, encoding='utf-8')
    for name in ['T7_Kimodo_G1_交接手册.md', 'merge_into_t6.py']:
        here = Path(__file__).resolve().parent / name
        if here.is_file():
            shutil.copy2(here, stage / name)
    if dst.exists():
        raise RuntimeError('Destination appeared during copy; staging retained')
    stage.rename(dst)
    print(f'MERGE FILES VERIFIED: {dst} ({len(checks)} files)')
    print('Runtime and grasp success remain unverified. Original source and venv retained.')
    print(f'source {dst}/activate-g1.sh')

if __name__ == '__main__':
    main()
