"""평가 데이터를 학습 데이터 자리에 놓은 임시 폴더를 만든다.

Day 1·2 스크립트는 data/public/train*.csv와 train_structures.zip을 읽는다. 이 폴더를 <레포 경로> 자리에
넘기면 같은 스크립트를 고치지 않고 평가 데이터에 돌릴 수 있다.
  train.csv              ← test.csv + labels.csv의 label
  train_features.csv     ← test_features.csv
  train_structures.zip   ← test_structures.zip
  validation_split.csv   ← Public은 fit, Private은 validation (C-14 자리에서 Public/Private 분할을 본다)

사용: python scripts/quality/day3_test_view.py <레포 경로> <임시 폴더>
"""
import csv, shutil, sys
from pathlib import Path

ROOT, OUT = Path(sys.argv[1]), Path(sys.argv[2])
priv = ROOT / 'data/private'
(OUT / 'data/public').mkdir(parents=True, exist_ok=True)
(OUT / 'data/private').mkdir(parents=True, exist_ok=True)
for p in priv.iterdir():
    shutil.copy(p, OUT / 'data/private' / p.name)
shutil.copy(priv / 'test_structures.zip', OUT / 'data/public/train_structures.zip')
shutil.copy(priv / 'test_features.csv', OUT / 'data/public/train_features.csv')
shutil.copy(ROOT / 'data/public/metadata.json', OUT / 'data/public/metadata.json')

lab = {r['id']: r for r in csv.DictReader(open(priv / 'labels.csv', encoding='utf-8'))}
rows = list(csv.DictReader(open(priv / 'test.csv', encoding='utf-8')))
with open(OUT / 'data/public/train.csv', 'w', newline='', encoding='utf-8') as f:
    w = csv.writer(f); w.writerow(['id', 'sequence', 'label'])
    for r in rows: w.writerow([r['id'], r['sequence'], lab[r['id']]['label']])
with open(OUT / 'data/public/validation_split.csv', 'w', newline='', encoding='utf-8') as f:
    w = csv.writer(f); w.writerow(['id', 'fold'])
    for r in rows: w.writerow([r['id'], 'fit' if lab[r['id']]['partition'] == 'public' else 'validation'])
print(f'평가 {len(rows)}개 → {OUT}')
