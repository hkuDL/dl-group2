"""Verify the recovered source snapshot without loading models or simulation."""
from pathlib import Path
import ast
import hashlib
import json

ROOT = Path(__file__).resolve().parents[1]


def main():
    manifest = json.loads((ROOT / 'SOURCE_MANIFEST.json').read_text())
    count = 0
    for item in manifest['files']:
        relative = Path(item['path'])
        if relative.is_absolute() or '..' in relative.parts:
            raise ValueError('Invalid manifest path')
        path = ROOT / relative
        content = path.read_bytes()
        if hashlib.sha256(content).hexdigest() != item['sha256']:
            raise ValueError('Recovered source changed: ' + str(relative))
        if len(content) != item['bytes']:
            raise ValueError('Recovered source size changed: ' + str(relative))
        if path.suffix == '.py':
            ast.parse(content, filename=str(relative))
        count += 1
    print(json.dumps({'source_files_verified': count, 'source_hashes': 'PASS',
                      'python_syntax': 'PASS', 'models_loaded': False}))


if __name__ == '__main__':
    main()
