"""C-12에서 끊긴 지점이 실제로 결합된 이웃인지 원본에서 잰다 (D-01 삽입 코드 경계, N-01).

끊긴 두 잔기마다 원본 PDB에서
  - 앞 잔기 C ↔ 뒤 잔기 N 거리 (펩타이드 결합이면 약 1.33Å)
  - REMARK 465(관측 안 된 잔기)에 사이 번호가 있는지
를 확인한다.

사용: python scripts/quality/day3_boundary.py <레포 경로> <작업 폴더> [분류 이름 ...]
  <작업 폴더>/c12_result.json, <작업 폴더>/pdb/ 필요 (c12_classify.py, fetch_pdb.py)
  분류 이름 기본값: '삽입코드 경계' (D-01). N-01은 '연속인데 끊김 (설명 불가)'
"""
import csv, gzip, json, re, sys
from pathlib import Path
import numpy as np

ROOT, WORK = Path(sys.argv[1]), Path(sys.argv[2])
CATS = set(sys.argv[3:]) or {'삽입코드 경계'}
AA = {'ALA','CYS','ASP','GLU','PHE','GLY','HIS','ILE','LYS','LEU','MET','ASN','PRO','GLN','ARG','SER','THR','VAL','TRP','TYR'}
dom = {r['id']: r['domain_id'] for r in csv.DictReader(open(ROOT / 'data/private/id_mapping.csv', encoding='utf-8'))}

out = []
for i, lab, cat, a, b, d in json.load(open(WORK / 'c12_result.json', encoding='utf-8'))['rows']:
    if cat not in CATS: continue
    pdb, ch = dom[i][:4].upper(), dom[i][4]
    atoms, r465 = {}, []
    for line in gzip.open(WORK / 'pdb' / f'{pdb}.pdb.gz', 'rt', errors='replace'):
        if line.startswith('ENDMDL'): break
        if line.startswith('REMARK 465') and len(line) > 26 and line[19] == ch: r465.append(line[21:27].strip())
        if line.startswith('ATOM') and line[21] == ch and line[16] in ' A' and line[17:20] in AA:
            k = line[22:27].replace(' ', '')
            atoms[(k, line[12:16].strip())] = np.array([float(line[30:38]), float(line[38:46]), float(line[46:54])])
    C, N = atoms.get((a, 'C')), atoms.get((b, 'N'))
    cn = round(float(np.linalg.norm(C - N)), 2) if C is not None and N is not None else None
    na = int(re.match(r'-?\d+', a).group())
    between = [x for x in r465 if re.fullmatch(rf'{na + 1}|{na}[A-Z]', x)]
    out.append(dict(id=i, cat=cat, a=a, b=b, ca=d, cn=cn, missing_between=between))

for o in out: print(o['id'], o['a'], '→', o['b'], 'Cα', o['ca'], 'C–N', o['cn'], '사이 누락', o['missing_between'])
cns = [o['cn'] for o in out if o['cn'] is not None]
print(f'{len(out)}곳, 구조 {len({o["id"] for o in out})}개, C–N {min(cns)} ~ {max(cns)}Å, '
      f'결합(<1.5Å) {sum(c < 1.5 for c in cns)}, 사이 누락 기록 {sum(bool(o["missing_between"]) for o in out)}')
