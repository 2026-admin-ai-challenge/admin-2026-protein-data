"""1차 보고서(P-01 ~ P-33)의 샘플이 수정된 데이터에서 어떻게 됐는지 추적한다.

데이터를 다시 만들면 샘플 ID가 다시 매겨지므로 옛 ID → 원본 domain → 새 ID로 대응시킨다.
옛 id_mapping.csv는 1차 데이터 커밋에서 git으로 꺼낸다.

사용: python scripts/quality/day3_track.py <레포 경로> <1차 커밋> <작업 폴더>
  <작업 폴더>/c12_result.json(학습), <작업 폴더>/test/c12_result.json(평가)이 있으면 구간 번호 판정도 함께 출력
"""
import csv, io, json, subprocess, sys, zipfile
from pathlib import Path
import numpy as np

ROOT, OLD, WORK = Path(sys.argv[1]), sys.argv[2], Path(sys.argv[3])
old_map = subprocess.run(['git', '-C', str(ROOT), 'show', f'{OLD}:data/private/id_mapping.csv'],
                         capture_output=True, check=True).stdout.decode('utf-8')
old = {r['id']: r['domain_id'] for r in csv.DictReader(io.StringIO(old_map))}
new = {r['domain_id']: r['id'] for r in csv.DictReader(open(ROOT / 'data/private/id_mapping.csv', encoding='utf-8'))}
excl = {r['domain_id'] for r in csv.DictReader(open(ROOT / 'data/private/quality_exclusions.csv', encoding='utf-8'))}
zips = {'TRAIN': zipfile.ZipFile(ROOT / 'data/public/train_structures.zip'),
        'TEST': zipfile.ZipFile(ROOT / 'data/private/test_structures.zip')}
c12 = {}
for p in (WORK / 'c12_result.json', WORK / 'test/c12_result.json'):
    if p.exists(): c12.update(json.load(open(p, encoding='utf-8'))['per'])

P = {'P-01': 'TRAIN_000912', 'P-02': 'TRAIN_017945', 'P-03': 'TRAIN_002659', 'P-04': 'TRAIN_006635', 'P-05': 'TRAIN_019951',
     'P-06': 'TRAIN_021392', 'P-07': 'TRAIN_002531', 'P-08': 'TRAIN_004174', 'P-09': 'TRAIN_019540', 'P-10': 'TRAIN_001613',
     'P-11': 'TRAIN_002130', 'P-12': 'TRAIN_003018', 'P-13': 'TRAIN_004546', 'P-14': 'TRAIN_007679', 'P-15': 'TRAIN_011557',
     'P-16': 'TRAIN_013948', 'P-17': 'TRAIN_015421', 'P-18': 'TRAIN_016950', 'P-19': 'TRAIN_018306', 'P-20': 'TRAIN_021196',
     'P-21': 'TRAIN_002675', 'P-22': 'TRAIN_004183', 'P-23': 'TRAIN_004916', 'P-24': 'TRAIN_015138', 'P-25': 'TRAIN_015317',
     'P-26': 'TEST_000276', 'P-27': 'TRAIN_011580', 'P-28': 'TRAIN_013465', 'P-29': 'TRAIN_011436', 'P-30': 'TRAIN_020408',
     'P-32': 'TRAIN_013812', 'P-33': 'TRAIN_019948'}
P31 = ['TRAIN_014147', 'TRAIN_010933', 'TRAIN_021295', 'TRAIN_014621', 'TRAIN_021350', 'TRAIN_018672', 'TRAIN_005671',
       'TRAIN_002853', 'TRAIN_010180', 'TRAIN_016048', 'TRAIN_021392', 'TRAIN_016293', 'TRAIN_017363', 'TRAIN_010183',
       'TRAIN_017119', 'TRAIN_019579']

def status(oid):
    d = old[oid]; nid = new.get(d)
    if nid is None:
        return oid, None, '제외 (quality_exclusions.csv)' if d in excl else '제외 (생성 필터)', None
    f = np.load(io.BytesIO(zips[nid.split('_')[0]].read(nid + '.npz')), allow_pickle=False)
    return oid, nid, f'구간 {int(f["segment_index"].max()) + 1}개', c12.get(nid, {}).get('cats', {})

for k, oid in P.items():
    print(k, *status(oid))
print('P-31', [status(o)[2] for o in P31])
