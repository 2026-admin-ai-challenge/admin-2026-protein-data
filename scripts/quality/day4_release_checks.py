"""배포 파일과 데이터에 숨김 평가 자료가 새는 경로가 있는지 점검한다 (Day 4 배포 점검의 데이터 쪽 항목).

B-04 ~ B-07  공개 파일·zip 안쪽(중첩 zip 포함)에 평가 입력·정답·분할·평가 ID·원본 domain 이름이 있는지
B-06         metadata.json의 seed·분할 비율 (공개 API가 그대로 내보내면 위반)
B-10         예제가 학습 샘플이고 평가와 겹치지 않으며, 입력에 정답 열이 없고 출력이 공개 학습 라벨과 같은지
B-11         공개 CSV 열과 NPZ 배열 키
V-01         ID 순서(10구간)와 라벨·Public/Private의 카이제곱 검정, 이웃 같은 라벨 비율
V-02         구조 zip의 파일 시간·순서·주석·추가 정보
V-03         클래스별 압축 크기 ÷ 길이
V-08         metadata 합계 - 학습 개수 = 실제 평가 개수인 클래스 수

평가 샘플의 정답은 출력하지 않는다. 웹사이트 코드(공개 API, 오류 안내, 채점 격리)는 이 스크립트 범위 밖이다.

사용: python scripts/quality/day4_release_checks.py <레포 경로>
"""
import collections, csv, io, json, os, re, sys, zipfile
from pathlib import Path
import numpy as np
from scipy.stats import chi2_contingency

ROOT = Path(sys.argv[1])
pub, priv = ROOT / 'data/public', ROOT / 'data/private'
rows = lambda p: list(csv.DictReader(open(p, encoding='utf-8')))
tr = rows(pub / 'train.csv'); te = rows(priv / 'test.csv')
lab = {r['id']: r for r in rows(priv / 'labels.csv')}
domains = {r['domain_id'] for r in rows(priv / 'id_mapping.csv')}
test_ids = {r['id'] for r in te}; test_seqs = {r['sequence'] for r in te}
private_names = {p.name for p in priv.iterdir()}

# B-04 ~ B-07, B-11
def scan_text(text, is_csv=False):
    hits = []
    if 'TEST_' in text: hits.append('TEST_ ID')
    if any(d in domains for d in re.findall(r'\b[0-9][a-z0-9]{3}[A-Za-z0-9][0-9]{2}\b', text)): hits.append('원본 domain')
    if is_csv and 'partition' in text.splitlines()[0].split(','): hits.append('partition 열')
    return hits

def scan_zip(name, data, depth=0):
    z = zipfile.ZipFile(io.BytesIO(data))
    for n in z.namelist():
        base = os.path.basename(n)
        if base in private_names or base.startswith('test') or 'TEST_' in n:
            print(f'   {"  " * depth}{name}/{n}: 비공개·평가 이름')
        if n.endswith('.zip'):
            scan_zip(f'{name}/{n}', z.read(n), depth + 1)
        elif n.endswith(('.csv', '.py', '.json', '.md', '.txt', '.ipynb')):
            h = scan_text(z.read(n).decode('utf-8', 'replace'), n.endswith('.csv'))
            if h: print(f'   {"  " * depth}{name}/{n}: {h}')
        elif n.endswith('.npz') and n == z.namelist()[0]:
            print(f'   {"  " * depth}{name}: NPZ 키 {np.load(io.BytesIO(z.read(n))).files}')

print('B-04 ~ B-07 · B-11 공개 파일 (문제 있는 것만 출력):')
for f in sorted(os.listdir(pub)):
    p = pub / f
    if f in private_names or f.startswith('test'): print(f'   {f}: 비공개·평가 이름')
    if f.endswith('.zip'): scan_zip(f, p.read_bytes())
    elif f.endswith(('.csv', '.json', '.md')):
        text = p.read_text(encoding='utf-8')
        h = scan_text(text, f.endswith('.csv'))
        if h: print(f'   {f}: {h}')
        if f.endswith('.csv'):
            print(f'   {f}: 열 {text.splitlines()[0]}, 평가 ID {sum(i in text for i in test_ids)}, '
                  f'평가 서열 완전 일치 행 {sum(1 for r in csv.DictReader(io.StringIO(text)) if r.get("sequence") in test_seqs)}')

# B-06
meta = json.loads((pub / 'metadata.json').read_text(encoding='utf-8'))
print(f'B-06 metadata.json: seed {meta.get("seed")!r}, split {meta.get("split")}')

# B-10
trl = {r['id']: r['label'] for r in tr}
ex_in = rows(pub / 'example_input.csv'); ex_out = rows(pub / 'example_output.csv')
print(f'B-10 예제: 입력 열 {list(ex_in[0])}, 학습 샘플 {all(r["id"] in trl for r in ex_in)}, '
      f'평가와 겹침 {sum(r["id"] in test_ids for r in ex_in)}, 출력 라벨 = 학습 라벨 {all(trl[r["id"]] == r["label"] for r in ex_out)}')

# V-01
def chi_p(order_labels, nb=10):
    n = len(order_labels); tab = collections.defaultdict(collections.Counter)
    for k, l in enumerate(order_labels): tab[k * nb // n][l] += 1
    L = sorted(set(order_labels))
    return chi2_contingency(np.array([[tab[b][l] for l in L] for b in range(nb)]))[1]

def neighbor(order_labels):
    same = sum(a == b for a, b in zip(order_labels, order_labels[1:])) / (len(order_labels) - 1)
    c = collections.Counter(order_labels)
    return same, sum((v / len(order_labels)) ** 2 for v in c.values())

for name, ids, get in [('학습', [r['id'] for r in tr], lambda i: trl[i]), ('평가', [r['id'] for r in te], lambda i: lab[i]['label'])]:
    ordered = [get(i) for i in sorted(ids)]
    same, exp = neighbor(ordered)
    print(f'V-01 {name}: 행 순서 = ID 순서 {ids == sorted(ids)}, ID 순서 vs 라벨 p = {chi_p(ordered):.3f}, '
          f'이웃 같은 라벨 {same:.3f} (무작위 기대 {exp:.3f})')
print(f'V-01 평가: ID 순서 vs Public/Private p = {chi_p([lab[i]["partition"] for i in sorted(test_ids)]):.3f}')

# V-02, V-03
for zp, labels, seq in [(pub / 'train_structures.zip', trl, {r['id']: r['sequence'] for r in tr}),
                        (priv / 'test_structures.zip', {i: lab[i]['label'] for i in test_ids}, {r['id']: r['sequence'] for r in te})]:
    info = zipfile.ZipFile(zp).infolist(); order = [i.filename[:-4] for i in info]
    size = collections.defaultdict(list)
    for i in info: size[labels[i.filename[:-4]]].append(i.compress_size / len(seq[i.filename[:-4]]))
    means = [np.mean(v) for v in size.values()]
    print(f'V-02 {zp.name}: 파일 시간 종류 {len({i.date_time for i in info})}, ID 순서 {order == sorted(order)}, '
          f'주석 {sum(bool(i.comment) for i in info)}, 추가 정보 {sum(bool(i.extra) for i in info)}')
    print(f'V-03 {zp.name}: 클래스별 압축 크기 ÷ 길이 {min(means):.2f} ~ {max(means):.2f} 바이트')

# V-08
trc = collections.Counter(trl.values()); tec = collections.Counter(lab[i]['label'] for i in test_ids)
spc = meta['stats']['samples_per_class']
print(f'V-08 metadata 합계 - 학습 = 실제 평가 개수: {sum(spc.get(k, 0) - trc[k] == tec[k] for k in tec)}/{len(tec)}개 클래스, '
      f'distribution_scope {meta["stats"].get("distribution_scope")!r}')
