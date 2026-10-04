"""A-02 기준(50%) 아래의 알라닌 부분 채움 후보를 찾는다.

서열에 A가 8개 이상 연속인 구조를 뽑는다. 자연 단백질에서는 드물어서, 실험자가 서열을 모르는 구간을
알라닌으로 채운 모델일 가능성이 높다. 뽑힌 구조는 원본 PDB의 DBREF와 UniProt 실제 서열로 확인한다.

사용: python scripts/quality/day3_ala_runs.py <레포 경로>
"""
import collections, csv, re, sys
from pathlib import Path

ROOT = Path(sys.argv[1])
for name, p in [('train', ROOT / 'data/public/train.csv'), ('test', ROOT / 'data/private/test.csv')]:
    runs, cand = collections.Counter(), []
    for r in csv.DictReader(open(p, encoding='utf-8')):
        s = r['sequence']; m = max((len(x) for x in re.findall('A+', s)), default=0)
        runs[m] += 1
        if m >= 8: cand.append((r['id'], m, round(s.count('A') / len(s), 2), len(s)))
    print(f'{name}: A 최대 연속 5 이상 {sum(v for k, v in runs.items() if k >= 5)}개, 8 이상 {len(cand)}개')
    for c in sorted(cand, key=lambda x: -x[1]): print('  ', c)
