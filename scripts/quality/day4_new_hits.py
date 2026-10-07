"""이번에 비정상 값 기준(A-01 ~ A-08)에 걸린 샘플 중, 이전 점검에서 판정한 적 없는 것을 찾는다 (Day 4 A 신규 판정).

데이터를 다시 만들면 분할과 샘플 ID가 바뀌어 처음 기준에 걸리는 샘플이 생길 수 있다.
원본 domain 기준으로 Day 2(학습, 44e28e4)·Day 3(평가, 797d114) 샘플 목록과 대조하고,
처음 걸린 샘플만 원본 대조 대상으로 출력한다.

사용: python scripts/quality/day4_new_hits.py <레포 경로> <학습 작업 폴더> <평가 작업 폴더>
  두 작업 폴더에 day2_hits.py의 hits_067.json, day2_shape_verify.py의 rest.json이 있어야 한다
  (평가 작업 폴더는 day3_test_view.py로 만든 폴더에 Day 2 스크립트를 돌린 결과)
"""
import csv, io, json, subprocess, sys
from pathlib import Path

ROOT, WTR, WTE = sys.argv[1], Path(sys.argv[2]), Path(sys.argv[3])

def mapping(rev):
    t = subprocess.run(['git', '-C', ROOT, 'show', f'{rev}:data/private/id_mapping.csv'], capture_output=True, check=True).stdout.decode('utf-8')
    return {r['id']: r['domain_id'] for r in csv.DictReader(io.StringIO(t))}

m_day2, m_day3, m_now = mapping('44e28e4'), mapping('797d114'), mapping('HEAD')
judged = set()
for r in csv.reader(open(Path(ROOT) / 'docs/quality/day2-abnormal-samples.csv', encoding='utf-8-sig')):
    if r[1] in m_day2: judged.add((r[0], m_day2[r[1]]))            # 점검 항목, 샘플 ID
for r in csv.reader(open(Path(ROOT) / 'docs/quality/day3-test-samples.csv', encoding='utf-8-sig')):
    if r[2] in m_day3: judged.add((r[1], m_day3[r[2]]))            # 기록번호, 항목, 샘플 ID

hits = []
for split, w in [('학습', WTR), ('평가', WTE)]:
    for i, r in json.load(open(w / 'rest.json', encoding='utf-8')).items():
        for item, hit in [('A-01', r['N'] >= 417), ('A-03', r['ratio'] >= 2), ('A-04', r['shape1'] >= 0.95),
                          ('A-07', r['rmax'] >= 87), ('A-08', r['nseg'] >= 9)]:
            if hit: hits.append((split, item, i))
    for x in json.load(open(w / 'hits_067.json', encoding='utf-8'))['a02']: hits.append((split, 'A-02', x['id']))

new = [h for h in hits if (h[1], m_now[h[2]]) not in judged]
print(f'기준에 걸린 {len(hits)}건 중 이전에 판정한 것 {len(hits) - len(new)}건, 처음 걸린 것 {len(new)}건')
for h in new: print('  ', *h)
