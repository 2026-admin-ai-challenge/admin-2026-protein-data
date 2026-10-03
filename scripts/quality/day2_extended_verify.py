"""나선형이 아닌 클래스에서 길쭉하거나 멀리 뻗은 구조 10개를 원본과 대조: 실험 방법, 해상도, 먼 잔기의 주변 밀도·B-factor.

사용: python scripts/quality/day2_extended_verify.py <레포 경로> <작업 폴더>/pdb <작업 폴더>/rest.json <작업 폴더>/ext.json
"""
import csv, gzip, io, json, sys, zipfile
import numpy as np

ROOT, PDBDIR, REST, OUT = sys.argv[1:5]
AA3 = {'ALA':'A','CYS':'C','ASP':'D','GLU':'E','PHE':'F','GLY':'G','HIS':'H','ILE':'I','LYS':'K','LEU':'L',
       'MET':'M','ASN':'N','PRO':'P','GLN':'Q','ARG':'R','SER':'S','THR':'T','VAL':'V','TRP':'W','TYR':'Y'}
IDS = ['TRAIN_000850','TRAIN_001432','TRAIN_002247','TRAIN_004323','TRAIN_005750','TRAIN_010885','TRAIN_011351',
       'TRAIN_019889','TRAIN_017673','TRAIN_001096']
z = zipfile.ZipFile(f'{ROOT}/data/public/train_structures.zip')
tr = {r['id']: r['sequence'] for r in csv.DictReader(open(f'{ROOT}/data/public/train.csv', encoding='utf-8'))}
rest = json.load(open(REST, encoding='utf-8'))

def runs(ix):
    out, s = [], None
    for a in sorted(ix):
        if s is None: s = p = a
        elif a == p + 1: p = a
        else: out.append((s, p)); s = p = a
    if s is not None: out.append((s, p))
    return out

res = []
for i in IDS:
    r = rest[i]; pdb, ch = r['dom'][:4].upper(), r['dom'][4]
    f = np.load(io.BytesIO(z.read(i + '.npz')), allow_pickle=False)
    pos, m = f['pos'].astype(float), f['ca_mask']; idx = np.where(m)[0]; P = pos[m]
    dist = np.linalg.norm(P - P.mean(0), axis=1); far = idx[dist > 0.5 * dist.max()]
    # 이웃 밀도: 10Å 안의 Cα 개수 (먼 잔기 vs 나머지)
    D = np.linalg.norm(P[:, None] - P[None], axis=2); dens = (D < 10).sum(1) - 1
    farmask = dist > 0.5 * dist.max()
    method, resol, bf, chseq, keys, nmodel, r465 = '', None, {}, [], [], 0, 0
    for line in gzip.open(f'{PDBDIR}/{pdb}.pdb.gz', 'rt', errors='replace'):
        if line.startswith('EXPDTA'): method = line[10:].strip()
        if line.startswith('REMARK   2 RESOLUTION.'):
            try: resol = float(line[23:30])
            except ValueError: pass
        if line.startswith('REMARK 465') and len(line) > 26 and line[19] == ch and line[15:18].strip() in AA3: r465 += 1
        if line.startswith('MODEL'): nmodel += 1
        if line.startswith('ENDMDL'): break
        if line.startswith('ATOM') and line[21] == ch and line[12:16].strip() == 'CA' and line[17:20] in AA3:
            k = (int(line[22:26]), line[26].strip())
            if k not in bf: bf[k] = float(line[60:66]); keys.append(k); chseq.append(AA3[line[17:20]])
    chs = ''.join(chseq); seq = tr[i]
    def loc(k):
        for w in (6, 4):
            lo = max(0, k - w); win = seq[lo:k + w + 1]; j = chs.find(win)
            if j >= 0 and chs.find(win, j + 1) < 0: return j + (k - lo)
        return None
    b_all = [bf[keys[o]] for o in (loc(k) for k in idx) if o is not None]
    b_far = [bf[keys[o]] for o in (loc(k) for k in far) if o is not None]
    o0, o1 = loc(int(far.min())), loc(int(far.max()))
    res.append(dict(id=i, label=r['label'], N=r['N'], ratio=round(r['ratio'], 2), shape1=round(r['shape1'], 3), rmax=round(r['rmax']),
                    far_runs=runs(far.tolist()), far_n=int(len(far)), dens_far=round(float(dens[farmask].mean()), 1),
                    dens_rest=round(float(dens[~farmask].mean()), 1), method=method, resol=resol,
                    b_far=round(float(np.mean(b_far)), 1) if b_far else None, b_all=round(float(np.mean(b_all)), 1) if b_all else None,
                    far_pdb=f'{keys[o0][0]}{keys[o0][1]}–{keys[o1][0]}{keys[o1][1]}' if o0 is not None and o1 is not None else None,
                    r465=r465, seq_head=seq[:12]))
json.dump(res, open(OUT, 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
for x in res:
    print(x['id'], x['label'], x['N'], 'ratio', x['ratio'], 's1', x['shape1'], 'rmax', x['rmax'], 'far', x['far_runs'][:4], 'n', x['far_n'],
          'dens far/rest', x['dens_far'], x['dens_rest'], x['method'][:6], x['resol'], 'B far/all', x['b_far'], x['b_all'], 'pdb', x['far_pdb'], 'R465', x['r465'], x['seq_head'])
