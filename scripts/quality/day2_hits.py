"""Day 2 비정상 값 기준에 걸린 샘플 목록을 만든다 (원본 대조가 필요한 A-05, A-06, A-02, A-07).

기준은 docs/quality/day2-abnormal-template.md ③을 따른다.
  A-05 같은 구간 안 이웃 Cα 거리 < 2.7Å
  A-06 사슬에서 3칸 이상 떨어진 Cα끼리 최소 거리 < 3.0Å
  A-02 가장 많은 한 글자의 비율 ≥ 50%
  A-07 중심에서 가장 먼 Cα까지 거리 ≥ 87Å

사용: python scripts/quality/day2_hits.py <레포 경로> <작업 폴더>
출력: <작업 폴더>/a05_hits.json, <작업 폴더>/hits_067.json
"""
import collections, csv, io, json, sys, zipfile
from pathlib import Path
import numpy as np
from scipy.spatial.distance import pdist, squareform

ROOT, WORK = Path(sys.argv[1]), Path(sys.argv[2])
pub = ROOT / 'data/public'
tr = {r['id']: r for r in csv.DictReader(open(pub / 'train.csv', encoding='utf-8'))}
dom = {r['id']: r['domain_id'] for r in csv.DictReader(open(ROOT / 'data/private/id_mapping.csv', encoding='utf-8'))}

a05, a06, a02, a07 = [], [], [], []
with zipfile.ZipFile(pub / 'train_structures.zip') as z:
    for name in z.namelist():
        i = name[:-4]
        f = np.load(io.BytesIO(z.read(name)), allow_pickle=False)
        p, m, s = f['pos'], f['ca_mask'], f['segment_index']
        seq, lab, N = tr[i]['sequence'], tr[i]['label'], len(m)
        d = np.linalg.norm(np.diff(p, axis=0), axis=1)
        ok = m[:-1] & m[1:] & (s[1:] == s[:-1])
        for k in np.where(ok & (d < 2.7))[0]:
            a05.append(dict(id=i, label=lab, N=N, k=int(k), pair=seq[k] + seq[k + 1], d=round(float(d[k]), 3), dom=dom[i]))
        idx = np.where(m)[0]
        D = squareform(pdist(p[idx])); sep = np.abs(idx[:, None] - idx[None, :]); D[sep < 3] = np.inf
        close = np.argwhere(np.triu(D < 3.0))
        if len(close):
            a06.append(dict(id=i, label=lab, N=N, dom=dom[i],
                            pairs=[(int(idx[a]), int(idx[b]), round(float(D[a, b]), 3)) for a, b in close]))
        aa, n = collections.Counter(seq).most_common(1)[0]
        if n / len(seq) >= 0.5:
            a02.append(dict(id=i, label=lab, N=N, dom=dom[i], aa=aa, frac=n / len(seq)))
        P = p[m]; r = np.linalg.norm(P - P.mean(0), axis=1)
        if r.max() >= 87:
            a07.append(dict(id=i, label=lab, N=N, dom=dom[i], rmax=float(r.max()), far=int(idx[r.argmax()])))

WORK.mkdir(parents=True, exist_ok=True)
json.dump(a05, open(WORK / 'a05_hits.json', 'w', encoding='utf-8'), ensure_ascii=False)
json.dump(dict(a06=a06, a02=a02, a07=a07), open(WORK / 'hits_067.json', 'w', encoding='utf-8'), ensure_ascii=False)
print(f'A-05 {len(a05)}쌍 ({len({h["id"] for h in a05})}개 구조), A-06 {len(a06)}, A-02 {len(a02)}, A-07 {len(a07)}')
