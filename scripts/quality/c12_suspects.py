"""C-12 의심 지점 목록을 만든다.

두 이웃 칸이 모두 좌표를 갖고 거리가 4.5Å 이하인데 segment_index가 바뀐 곳을 모은다.
원본 domain 이름이 필요하므로 data/private/id_mapping.csv를 읽는다.

사용: python scripts/quality/c12_suspects.py <레포 경로> <작업 폴더> [train|test]
출력: <작업 폴더>/suspects.json (c12_classify.py 입력)
"""
import csv, io, json, sys, zipfile
from pathlib import Path
import numpy as np

ROOT, WORK = Path(sys.argv[1]), Path(sys.argv[2])
SPLIT = sys.argv[3] if len(sys.argv) > 3 else 'train'
base = ROOT / ('data/public' if SPLIT == 'train' else 'data/private')
rows = {r['id']: r for r in csv.DictReader(open(base / f'{SPLIT}.csv', encoding='utf-8'))}
dom = {r['id']: r['domain_id'] for r in csv.DictReader(open(ROOT / 'data/private/id_mapping.csv', encoding='utf-8'))}
labels = {}
if SPLIT == 'test':
    labels = {r['id']: r['label'] for r in csv.DictReader(open(ROOT / 'data/private/labels.csv', encoding='utf-8'))}

out = []
with zipfile.ZipFile(base / f'{SPLIT}_structures.zip') as z:
    for name in z.namelist():
        i = name[:-4]
        f = np.load(io.BytesIO(z.read(name)), allow_pickle=False)
        pos, m, seg = f['pos'], f['ca_mask'], f['segment_index']
        d = np.linalg.norm(np.diff(pos, axis=0), axis=1)
        odd = np.where(m[:-1] & m[1:] & (seg[1:] != seg[:-1]) & (d <= 4.5))[0]
        if len(odd):
            out.append({'id': i, 'label': rows[i].get('label') or labels.get(i, ''), 'domain': dom[i],
                        'seq': rows[i]['sequence'], 'breaks': [int(k) for k in odd],
                        'dist': [round(float(d[k]), 2) for k in odd]})

WORK.mkdir(parents=True, exist_ok=True)
json.dump(out, open(WORK / 'suspects.json', 'w', encoding='utf-8'), ensure_ascii=False)
print(f'{SPLIT}: 의심 지점 {sum(len(o["breaks"]) for o in out)}곳, 구조 {len(out)}개 → {WORK / "suspects.json"}')
