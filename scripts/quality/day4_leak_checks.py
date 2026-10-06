"""학습·평가 사이 누출과 공개 파일의 숨김 정보를 점검한다 (Day 4 E-04, E-06, E-07, E-08, R-01).

E-04 서열 포함: 평가 서열이 학습 서열 안에 통째로 들어 있거나 그 반대인 쌍 (완전히 같은 경우는 C-06)
E-06 거의 같은 서열: E-04가 아닌 쌍 중, 평가 서열의 8글자 조각 50% 이상이 한 학습 서열에 있는 쌍을 뽑아
     짧은 쪽 길이 기준으로 위치를 맞춘(빈칸 없는) 최대 일치율을 계산. 85% 이상을 기록
E-07 같은 특징값: 31개 특징값이 완전히 같은 학습·평가 쌍
E-08 같은 PDB 항목: 평가 샘플 중 원본 domain의 PDB ID(앞 4글자)가 학습에도 있는 수 (참고용)
R-01 공개 파일: data/public/ 파일과 zip 안쪽에 비공개 파일 이름, TEST_ ID, 원본 domain 이름이 있는지.
     metadata.json 합계 - 학습 개수가 실제 평가 개수와 같은지.

평가 샘플의 정답은 화면에 출력하지 않는다(라벨 일치 여부는 개수로만 출력).

사용: python scripts/quality/day4_leak_checks.py <레포 경로>
"""
import collections, csv, json, os, re, sys, zipfile
from pathlib import Path

ROOT = Path(sys.argv[1])
pub, priv = ROOT / 'data/public', ROOT / 'data/private'
rows = lambda p: list(csv.DictReader(open(p, encoding='utf-8')))
tr = {r['id']: r for r in rows(pub / 'train.csv')}
te = {r['id']: r['sequence'] for r in rows(priv / 'test.csv')}
lab = {r['id']: r['label'] for r in rows(priv / 'labels.csv')}
mp = {r['id']: r['domain_id'] for r in rows(priv / 'id_mapping.csv')}

# E-04
cont = [(t, i) for t, s in te.items() for i, r in tr.items() if s in r['sequence'] or r['sequence'] in s]
print(f'E-04 서열 포함: {len(cont)}쌍 (평가 {len({t for t, _ in cont})}개), '
      f'라벨 같음 {sum(lab[t] == tr[i]["label"] for t, i in cont)}쌍, '
      f'같은 PDB {sum(mp[t][:4] == mp[i][:4] for t, i in cont)}쌍')
for t, i in cont: print('  ', t, i)

# E-06
K = 8
idx = collections.defaultdict(set)
for i, r in tr.items():
    s = r['sequence']
    for p in range(len(s) - K + 1): idx[s[p:p + K]].add(i)
contset = set(cont); cand = 0; near = []
for t, s in te.items():
    km = {s[p:p + K] for p in range(len(s) - K + 1)}
    c = collections.Counter(i for k in km for i in idx.get(k, ()))
    for i, n in c.items():
        if n / len(km) < 0.5: continue
        cand += 1
        if (t, i) in contset: continue
        b = tr[i]['sequence']
        best = max(sum(1 for k in range(len(s)) if 0 <= k - off < len(b) and s[k] == b[k - off])
                   for off in range(-len(b) + 1, len(s)))
        idn = best / min(len(s), len(b))
        if idn >= 0.85: near.append((t, i, idn))
print(f'E-06 거의 같은 서열: 8글자 조각 50% 이상 공유 {cand}쌍 → 포함 관계 제외 후 85% 이상 {len(near)}쌍 '
      f'(평가 {len({x[0] for x in near})}개), 95% 이상 {sum(x[2] >= .95 for x in near)}쌍')
for t, i, idn in sorted(near, key=lambda x: -x[2]): print(f'   {t} {i} {idn:.0%}')
print(f'   E-04 + E-06 평가 샘플 합계 {len({t for t, _ in cont} | {x[0] for x in near})}개')

# E-07
ft = {tuple(r.values())[1:] for r in rows(pub / 'train_features.csv')}
print('E-07 같은 특징값:', sum(tuple(r.values())[1:] in ft for r in rows(priv / 'test_features.csv')))

# E-08
pdb_tr = {mp[i][:4] for i in tr}; chain_tr = {mp[i][:5] for i in tr}
print(f'E-08 같은 PDB 항목: 평가 {sum(mp[t][:4] in pdb_tr for t in te)}개 (같은 사슬 {sum(mp[t][:5] in chain_tr for t in te)}개)')

# R-01
private_names = {p.name for p in priv.iterdir()}
domains = set(mp.values())
def scan(text):
    hits = []
    if 'TEST_' in text: hits.append('TEST_ ID')
    if any(d in domains for d in re.findall(r'\b[0-9][a-z0-9]{3}[A-Za-z0-9][0-9]{2}\b', text)): hits.append('원본 domain')
    return hits
print('R-01 공개 파일:')
for f in sorted(os.listdir(pub)):
    p = pub / f
    if f.endswith('.zip'):
        z = zipfile.ZipFile(p); names = z.namelist()
        bad = [n for n in names if os.path.basename(n) in private_names or 'TEST_' in n]
        txt = {n: scan(z.read(n).decode('utf-8', 'replace')) for n in names if n.endswith(('.csv', '.py', '.json', '.md', '.txt', '.ipynb'))}
        print(f'   {f}: {len(names)}개, 비공개 이름 {bad}, 내용 {[(n, h) for n, h in txt.items() if h]}')
    elif f.endswith(('.csv', '.json', '.md')):
        print(f'   {f}: 내용 {scan(p.read_text(encoding="utf-8"))}')
stats = json.loads((pub / 'metadata.json').read_text(encoding='utf-8'))['stats']
trc = collections.Counter(r['label'] for r in tr.values()); tec = collections.Counter(lab.values())
derived = {k: v - trc[k] for k, v in stats['samples_per_class'].items()}
ratio = [tec[k] / trc[k] for k in tec]
print(f'   metadata.json 합계 - 학습 = 실제 평가 개수: {sum(derived[k] == tec[k] for k in tec)}/{len(tec)}개 클래스 일치, '
      f'평가/학습 비율 {min(ratio):.3f} ~ {max(ratio):.3f}')
print(f'   sequence_length max {stats["sequence_length"]["max"]} (학습 최대 {max(len(r["sequence"]) for r in tr.values())})')
