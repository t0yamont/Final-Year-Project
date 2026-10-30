"""Verify saved output bytes against a run manifest; never inspects credentials/cache."""
import argparse
import hashlib
import json
from pathlib import Path


def verify(directory):
    root=Path(directory).resolve()
    manifest=json.loads((root/'manifest.json').read_text(encoding='utf-8-sig'))
    entries=manifest.get('outputs',manifest.get('outputs_sha256'))
    if entries is None:
        raise ValueError('manifest has no outputs contract')
    items=entries.items() if isinstance(entries,dict) else ((x['path'],x['sha256']) for x in entries)
    rows=[]
    for name,expected in items:
        target=(root/name).resolve()
        if not target.is_relative_to(root):
            raise ValueError('manifest output escapes run directory')
        actual=hashlib.sha256(target.read_bytes()).hexdigest() if target.is_file() else None
        rows.append(dict(path=name,matched=actual==expected))
    return dict(run=str(root),verified_outputs=len(rows),passed=bool(rows) and all(x['matched'] for x in rows),outputs=rows)


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('directory',type=Path)
    args=parser.parse_args()
    result=verify(args.directory)
    print(json.dumps(result,indent=2))
    raise SystemExit(0 if result['passed'] else 1)
