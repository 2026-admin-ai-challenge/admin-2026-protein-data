"""A-01, A-03, A-04, A-07, A-08 판별 자료 계산 (학습 데이터, 읽기 전용).

A-08의 끊김 원인은 c12_classify.py 결과(c12_result.json)를 쓴다.
사용: python scripts/quality/day2_shape_verify.py <레포 경로> <작업 폴더>/pdb <작업 폴더>/c12_result.json <작업 폴더>/rest.json
"""
import csv, gzip, io, json, sys, zipfile, collections
import numpy as np

ROOT, PDBDIR, C12, OUT = sys.argv[1:5]
z = zipfile.ZipFile(f'{ROOT}/data/public/train_structures.zip')
tr = {r['id']: r for r in csv.DictReader(open(f'{ROOT}/data/public/train.csv', encoding='utf-8'))}
ft = {r['id']: r for r in csv.DictReader(open(f'{ROOT}/data/public/train_features.csv', encoding='utf-8'))}
dom = {r['id']: r['domain_id'] for r in csv.DictReader(open(f'{ROOT}/data/private/id_mapping.csv', encoding='utf-8'))}
c12 = collections.defaultdict(collections.Counter)
for row in json.load(open(C12, encoding='utf-8'))['rows']:
    cat = row[2]
    c12[row[0]]['A' if '버그' in cat else ('C' if cat == '사이에 다른 잔기' else 'B')] += 1
A, B = 3.9079961828505057, 0.2770167717615794

def header(pdb):
    method, resol = '', None
    try:
        for line in gzip.open(f'{PDBDIR}/{pdb}.pdb.gz', 'rt', errors='replace'):
            if line.startswith('EXPDTA'): method = line[10:].strip()
            if line.startswith('REMARK   2 RESOLUTION.'):
                try: resol = float(line[23:30])
                except ValueError: pass
            if line.startswith('ATOM'): break
    except FileNotFoundError:
        return None, None
    return method, resol

rec = {}
for n in z.namelist():
    i = n[:-4]
    f = np.load(io.BytesIO(z.read(n)), allow_pickle=False)
    pos, m, seg = f['pos'].astype(float), f['ca_mask'], f['segment_index']
    N = len(m); idx = np.where(m)[0]; P = pos[m]; c = P.mean(0)
    dist = np.linalg.norm(P - c, axis=1)
    rg = float(np.sqrt((dist ** 2).mean())); rmax = float(dist.max())
    ratio = rg / (A * N ** B); s1 = float(ft[i]['shape_1'])
    nseg = int(len(np.unique(seg)))
    if not (N >= 417 or ratio >= 2 or s1 >= 0.95 or rmax >= 87 or nseg >= 9):
        continue
    # 꼬리 판정: 중심에서 먼 잔기가 사슬 끝쪽 짧은 구간에 몰려 있는가
    far = idx[dist > 0.5 * rmax]
    fpos = int(idx[dist.argmax()])
    end_n = int(0.15 * N)
    tail = len(far) <= 0.2 * N and (far.max() < end_n or far.min() >= N - end_n)
    # 꼬리를 뺀 나머지의 퍼짐
    core = P[dist <= 0.5 * rmax]
    core_rg = float(np.sqrt(((core - core.mean(0)) ** 2).sum(1).mean())) if len(core) > 3 else None
    d = np.linalg.norm(np.diff(pos, axis=0), axis=1)
    br = seg[1:] != seg[:-1]
    both = m[:-1] & m[1:]
    causes = {'좌표 누락': int((br & ~both).sum()), '4.5Å 초과': int((br & both & (d > 4.5)).sum()),
              '번호 불연속(정상)': c12[i].get('B', 0), '떨어진 조각': c12[i].get('C', 0), 'C-12 버그': c12[i].get('A', 0)}
    rec[i] = dict(id=i, label=tr[i]['label'], N=N, dom=dom[i], rg=rg, ratio=ratio, shape1=s1, rmax=rmax, nseg=nseg,
                  far_n=int(len(far)), far_pos=fpos, tail=bool(tail), core_rg=core_rg, causes=causes)

for r in rec.values():
    if r['rmax'] >= 87:
        r['method'], r['resol'] = header(r['dom'][:4].upper())
json.dump(rec, open(OUT, 'w', encoding='utf-8'), ensure_ascii=False)

def show(title, cond):
    xs = [r for r in rec.values() if cond(r)]
    print(f'== {title}: {len(xs)}', collections.Counter(r['label'] for r in xs).most_common(8), 'tail', sum(r['tail'] for r in xs))
    return xs
a01 = show('A-01', lambda r: r['N'] >= 417)
print('  A-01 nseg dist', collections.Counter(min(r['nseg'], 6) for r in a01).most_common())
a03 = show('A-03', lambda r: r['ratio'] >= 2)
print('  A-03 non-helix classes', [(r['id'], r['label'], round(r['ratio'], 2), r['tail'], r['far_n']) for r in a03 if r['label'][0] not in '146'])
a04 = show('A-04', lambda r: r['shape1'] >= 0.95)
print('  A-04 non-helix', [(r['id'], r['label'], round(r['shape1'], 3), r['tail']) for r in a04 if r['label'][0] not in '146'])
print('  A-03∩A-04', len([r for r in rec.values() if r['ratio'] >= 2 and r['shape1'] >= 0.95]))
a07 = show('A-07', lambda r: r['rmax'] >= 87)
for r in sorted(a07, key=lambda r: -r['rmax']):
    print('  ', r['id'], r['label'], r['N'], round(r['rmax']), 'ratio', round(r['ratio'], 2), 'tail', r['tail'], 'far_n', r['far_n'], 'farpos', r['far_pos'], (r.get('method') or '')[:12], r.get('resol'))
a08 = show('A-08', lambda r: r['nseg'] >= 9)
for r in sorted(a08, key=lambda r: -r['nseg']):
    print('  ', r['id'], r['label'], r['N'], r['nseg'], r['causes'])
