"""원본 PDB 파일을 RCSB에서 받는다. 이미 있으면 건너뛴다.

입력 JSON에서 domain 이름(예: 1jqgA01)의 앞 4글자를 PDB ID로 쓴다.
PDB 형식(.pdb.gz)이 없으면 mmCIF(.cif.gz)를 받는다.

사용: python scripts/quality/fetch_pdb.py <작업 폴더> <입력 JSON> [<입력 JSON> ...]
저장: <작업 폴더>/pdb/
"""
import json, sys, urllib.request, urllib.error
from pathlib import Path

WORK = Path(sys.argv[1])
ids = set()
for p in sys.argv[2:]:
    data = json.load(open(p, encoding='utf-8'))
    items = data if isinstance(data, list) else [x for v in data.values() if isinstance(v, list) for x in v]
    if isinstance(data, dict) and not items:
        items = list(data.values())
    for o in items:
        d = o.get('domain') or o.get('dom')
        if d: ids.add(d[:4].upper())

out = WORK / 'pdb'; out.mkdir(parents=True, exist_ok=True)
got, skip, fail = 0, 0, []
for pid in sorted(ids):
    if (out / f'{pid}.pdb.gz').exists() or (out / f'{pid}.cif.gz').exists():
        skip += 1; continue
    for ext in ('pdb.gz', 'cif.gz'):
        try:
            with urllib.request.urlopen(f'https://files.rcsb.org/download/{pid}.{ext}', timeout=120) as r:
                (out / f'{pid}.{ext}').write_bytes(r.read())
            got += 1; break
        except urllib.error.HTTPError:
            continue
    else:
        fail.append(pid)
print(f'받음 {got}, 이미 있음 {skip}, 실패 {len(fail)} {fail}')
