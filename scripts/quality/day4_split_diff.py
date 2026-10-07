"""두 데이터 버전 사이에 학습/평가 분할이 얼마나 바뀌었는지 원본 domain 기준으로 비교한다 (Day 4 E-05).

샘플 ID는 버전마다 다시 매겨지므로 id_mapping.csv의 원본 domain으로 대응시킨다.
평가 샘플의 정답은 클래스별 개수로만 출력한다.

사용: python scripts/quality/day4_split_diff.py <레포 경로> <이전 커밋> [<현재 커밋, 기본 HEAD>]
"""
import collections, csv, io, subprocess, sys

ROOT, OLD = sys.argv[1], sys.argv[2]
NEW = sys.argv[3] if len(sys.argv) > 3 else 'HEAD'

def load(rev):
    g = lambda p: subprocess.run(['git', '-C', ROOT, 'show', f'{rev}:{p}'], capture_output=True, check=True).stdout.decode('utf-8')
    m = {r['id']: r['domain_id'] for r in csv.DictReader(io.StringIO(g('data/private/id_mapping.csv')))}
    lab = {r['id']: r['label'] for r in csv.DictReader(io.StringIO(g('data/public/train.csv')))}
    part = {}
    for r in csv.DictReader(io.StringIO(g('data/private/labels.csv'))):
        lab[r['id']] = r['label']; part[m[r['id']]] = r['partition']
    fold = {m[r['id']]: r['fold'] for r in csv.DictReader(io.StringIO(g('data/public/validation_split.csv')))}
    train = {m[i] for i in m if i.startswith('TRAIN')}
    test = {m[i]: lab[i] for i in m if i.startswith('TEST')}
    return train, test, part, fold

otr, ote, opart, ofold = load(OLD)
ntr, nte, npart, nfold = load(NEW)
print(f'{OLD} → {NEW}')
print(f'  학습 → 평가 {len(otr & set(nte))}, 평가 → 학습 {len(set(ote) & ntr)}, '
      f'평가 유지 {len(set(ote) & set(nte))} / {len(nte)}, 빠진 domain {len((otr | set(ote)) - (ntr | set(nte)))}')
same = set(opart) & set(npart)
print(f'  Public/Private가 바뀐 평가 {sum(opart[d] != npart[d] for d in same)} / {len(same)}')
samef = set(ofold) & set(nfold)
print(f'  fit/validation이 바뀐 학습 {sum(ofold[d] != nfold[d] for d in samef)} / {len(samef)}')
ca, cb = collections.Counter(ote.values()), collections.Counter(nte.values())
keep = collections.Counter(l for d, l in nte.items() if d in ote)
print('  클래스  이전 평가  현재 평가  유지  바뀐 비율')
for l in sorted(cb, key=lambda x: [int(p) for p in x.split('.')]):
    print(f'  {l:6} {ca[l]:8} {cb[l]:9} {keep[l]:5}  {1 - keep[l] / cb[l]:.0%}')
