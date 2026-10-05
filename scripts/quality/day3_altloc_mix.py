"""이웃 Cα 간격이 정상 범위를 벗어난 쌍을 원본과 대조해 서로 다른 모양(altloc)이 섞였는지 판정한다 (P-30 잔여).

1단계 (flags): 같은 구간 안 이웃 Cα 간격이 2.7Å 미만, 3.05 ~ 3.6Å, 3.98Å 초과인 쌍을 뽑는다.
  정상 trans(약 3.8Å)와 cis(약 2.9Å)를 뺀 범위다.
2단계 (check): 원본 사슬에 대응시켜(여러 조각을 이어 붙인 domain은 조각별로) 모양 조합마다 간격을 잰다.
  데이터 간격이 서로 다른 모양끼리의 조합에서만 나오면 "모양 섞임".

사용:
  python scripts/quality/day3_altloc_mix.py flags <레포 경로> <작업 폴더> [train|test]   # → <작업 폴더>/adjacent_flags.json
  python scripts/quality/fetch_pdb.py <작업 폴더> <작업 폴더>/adjacent_flags.json
  python scripts/quality/day3_altloc_mix.py check <레포 경로> <작업 폴더> [train|test]   # → <작업 폴더>/altloc_mix.json
"""
import collections, csv, gzip, io, json, os, sys, zipfile
from pathlib import Path
import numpy as np

MODE, ROOT, WORK = sys.argv[1], Path(sys.argv[2]), Path(sys.argv[3])
SPLIT = sys.argv[4] if len(sys.argv) > 4 else 'test'
base = ROOT / ('data/public' if SPLIT == 'train' else 'data/private')
AA = {'ALA':'A','CYS':'C','ASP':'D','GLU':'E','PHE':'F','GLY':'G','HIS':'H','ILE':'I','LYS':'K','LEU':'L','MET':'M',
      'ASN':'N','PRO':'P','GLN':'Q','ARG':'R','SER':'S','THR':'T','VAL':'V','TRP':'W','TYR':'Y'}
dom = {r['id']: r['domain_id'] for r in csv.DictReader(open(ROOT / 'data/private/id_mapping.csv', encoding='utf-8'))}

if MODE == 'flags':
    flags, allD = [], []
    with zipfile.ZipFile(base / f'{SPLIT}_structures.zip') as z:
        for n in z.namelist():
            f = np.load(io.BytesIO(z.read(n)), allow_pickle=False); p, m, s = f['pos'], f['ca_mask'], f['segment_index']
            d = np.linalg.norm(np.diff(p, axis=0), axis=1); ok = m[:-1] & m[1:] & (s[1:] == s[:-1]); allD.append(d[ok])
            for k in np.where(ok & ((d < 2.7) | ((d > 3.05) & (d < 3.6)) | (d > 3.98)))[0]:
                flags.append(dict(id=n[:-4], k=int(k), d=round(float(d[k]), 3), dom=dom[n[:-4]]))
    D = np.concatenate(allD)
    print(f'{SPLIT}: 이웃 쌍 {len(D)}, 백분위(0.1/50/99.9%) {np.round(np.percentile(D, [0.1, 50, 99.9]), 3)}, '
          f'뽑힌 쌍 {len(flags)} (구조 {len({x["id"] for x in flags})}개)')
    WORK.mkdir(parents=True, exist_ok=True)
    json.dump(flags, open(WORK / 'adjacent_flags.json', 'w'))
    sys.exit()

def read_pdb(path, ch):
    for l in gzip.open(path, 'rt', errors='replace'):
        if l.startswith('ENDMDL'): return
        if l.startswith('ATOM') and l[21] == ch and l[17:20] in AA:
            yield (int(l[22:26]), l[26].strip()), AA[l[17:20]], l[12:16].strip(), l[16].strip(), \
                np.array([float(l[30:38]), float(l[38:46]), float(l[46:54])])

def read_cif(path, ch):
    lines = gzip.open(path, 'rt', errors='replace').read().splitlines(); cols = []; i = 0; model = None
    while i < len(lines):
        if lines[i].startswith('_atom_site.'):
            while lines[i].startswith('_atom_site.'): cols.append(lines[i].split('.')[1].strip()); i += 1
            ix = {c: n for n, c in enumerate(cols)}
            while i < len(lines) and lines[i].startswith(('ATOM', 'HETATM')):
                t = lines[i].split(); i += 1
                if t[0] != 'ATOM' or t[ix['auth_asym_id']] != ch or t[ix['label_comp_id']] not in AA: continue
                model = model or t[ix['pdbx_PDB_model_num']]
                if t[ix['pdbx_PDB_model_num']] != model: return
                ic = t[ix['pdbx_PDB_ins_code']]; al = t[ix['label_alt_id']]
                yield (int(t[ix['auth_seq_id']]), '' if ic in '?.' else ic), AA[t[ix['label_comp_id']]], \
                    t[ix['label_atom_id']].strip('"'), '' if al in '?.' else al, \
                    np.array([float(t[ix['Cartn_x']]), float(t[ix['Cartn_y']]), float(t[ix['Cartn_z']])])
            return
        i += 1

def piecewise(cs, seq, order):
    """domain 서열을 앞에서부터 가장 길게 일치하는 조각으로 나눠 원본 잔기에 대응 (불연속 domain 대응)."""
    out, i = [], 0
    while i < len(seq):
        best = (0, 0)
        for st in range(len(cs)):
            L = 0
            while i + L < len(seq) and st + L < len(cs) and cs[st + L] == seq[i + L]: L += 1
            if L > best[1]: best = (st, L)
        if best[1] < 5 and len(seq) - i >= 5: return None
        out += order[best[0]:best[0] + best[1]]; i += best[1]
    return out

seqs = {r['id']: r['sequence'] for r in csv.DictReader(open(base / f'{SPLIT}.csv', encoding='utf-8'))}
by = collections.defaultdict(list)
for f in json.load(open(WORK / 'adjacent_flags.json')): by[f['id']].append(f)
res, stat = [], collections.Counter()
for sid, fl in by.items():
    pdb, ch = fl[0]['dom'][:4].upper(), fl[0]['dom'][4]
    p = WORK / 'pdb' / f'{pdb}.pdb.gz'
    src = read_pdb(p, ch) if p.exists() else read_cif(WORK / 'pdb' / f'{pdb}.cif.gz', ch)
    R, order = {}, []
    for k, aa, name, alt, xyz in src:
        if k not in R: R[k] = {'aa': aa, 'ca': {}}; order.append(k)
        if name == 'CA': R[k]['ca'][alt] = xyz
    keys = piecewise(''.join(R[k]['aa'] for k in order), seqs[sid], order)
    for f in fl:
        if keys is None: cat, combos = '원본 대응 실패', {}
        else:
            a, b = R[keys[f['k']]]['ca'], R[keys[f['k'] + 1]]['ca']
            combos = {(x or '-') + (y or '-'): round(float(np.linalg.norm(a[x] - b[y])), 2) for x in a for y in b}
            match = [c for c, v in combos.items() if abs(v - f['d']) < 0.02]
            if len(a) == 1 and len(b) == 1: cat = '원본 그대로' if match else '원본과 다름'
            elif match and all(c[0] != c[1] and '-' not in c for c in match): cat = '모양 섞임'
            else: cat = '여러 모양, 섞이지 않음'
        stat[cat] += 1; res.append(dict(id=sid, k=f['k'], d=f['d'], cat=cat, combos=combos))
print(dict(stat))
for r in res:
    if r['cat'] != '원본 그대로' and r['cat'] != '여러 모양, 섞이지 않음': print(r['id'], r['k'], r['d'], r['cat'], r['combos'])
json.dump(res, open(WORK / 'altloc_mix.json', 'w', encoding='utf-8'), ensure_ascii=False)
