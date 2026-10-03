"""A-05 걸린 쌍을 원본 PDB와 대조: 거리, omega 각, C-N 결합 길이, CISPEP 기록, 해상도.

사용: python scripts/quality/day2_a05_verify.py <레포 경로> <작업 폴더>/pdb <작업 폴더>/a05_hits.json
출력: <작업 폴더>/a05_hits_verified.json
"""
import csv, gzip, json, math, sys
import numpy as np

ROOT, PDBDIR, HITS = sys.argv[1], sys.argv[2], sys.argv[3]
AA3 = {'ALA':'A','CYS':'C','ASP':'D','GLU':'E','PHE':'F','GLY':'G','HIS':'H','ILE':'I','LYS':'K','LEU':'L',
       'MET':'M','ASN':'N','PRO':'P','GLN':'Q','ARG':'R','SER':'S','THR':'T','VAL':'V','TRP':'W','TYR':'Y'}
train = {r['id']: r['sequence'] for r in csv.DictReader(open(f'{ROOT}/data/public/train.csv', encoding='utf-8'))}
hits = json.load(open(HITS, encoding='utf-8'))

def dihedral(p0, p1, p2, p3):
    b0, b1, b2 = p0 - p1, p2 - p1, p3 - p2
    b1 /= np.linalg.norm(b1)
    v = b0 - np.dot(b0, b1) * b1; w = b2 - np.dot(b2, b1) * b1
    return math.degrees(math.atan2(np.dot(np.cross(b1, v), w), np.dot(v, w)))

def load(pdb, chain):
    res, order, cis, resol, method = {}, [], [], None, ''
    for line in gzip.open(f'{PDBDIR}/{pdb}.pdb.gz', 'rt', errors='replace'):
        if line.startswith('EXPDTA'): method = line[10:].strip()
        if line.startswith('REMARK   2 RESOLUTION.'):
            try: resol = float(line[23:30])
            except ValueError: pass
        if line.startswith('CISPEP'):
            cis.append(((line[15], int(line[17:21]), line[21].strip()), (line[29], int(line[31:35]), line[35].strip()), line[53:59].strip()))
        if line.startswith('ENDMDL'): break
        if line.startswith('ATOM') and line[21] == chain:
            name, rn = line[12:16].strip(), line[17:20].strip()
            if rn not in AA3: continue
            key = (int(line[22:26]), line[26].strip())
            alt = line[16].strip()
            if key not in res: res[key] = {'aa': AA3[rn], 'at': {}}; order.append(key)
            if name in ('N', 'CA', 'C') and (name not in res[key]['at'] or alt in ('', 'A')):
                res[key]['at'][name] = np.array([float(line[30:38]), float(line[38:46]), float(line[46:54])])
    return res, order, cis, resol, method

out = []
for h in hits:
    pdb, chain = h['dom'][:4].upper(), h['dom'][4]
    res, order, cis, resol, method = load(pdb, chain)
    chseq = ''.join(res[k]['aa'] for k in order)
    seq, k = train[h['id']], h['k']
    lo = max(0, k - 5); win = seq[lo:k + 7]
    j = chseq.find(win)
    if j < 0:
        out.append({**h, 'match': False}); continue
    o = j + (k - lo); a, b = order[o], order[o + 1]
    A, B = res[a]['at'], res[b]['at']
    r = {**h, 'match': True, 'pdb_res': f'{a[0]}{a[1]}→{b[0]}{b[1]}', 'resol': resol, 'method': method}
    if all(x in A for x in ('CA', 'C')) and all(x in B for x in ('N', 'CA')):
        r['ca_ca'] = round(float(np.linalg.norm(A['CA'] - B['CA'])), 3)
        r['omega'] = round(dihedral(A['CA'], A['C'], B['N'], B['CA']), 1)
        r['c_n'] = round(float(np.linalg.norm(A['C'] - B['N'])), 3)
    else:
        r['omega'] = None
    r['cispep'] = any(c[0][0] == chain and (c[0][1], c[0][2]) == a and (c[1][1], c[1][2]) == b for c in cis)
    out.append(r)

json.dump(out, open(HITS.replace('.json', '_verified.json'), 'w', encoding='utf-8'), ensure_ascii=False)
for r in sorted(out, key=lambda r: r['d']):
    print(r['id'], r['label'], r['pair'], r['d'], r.get('pdb_res'), 'omega', r.get('omega'), 'C-N', r.get('c_n'),
          'CISPEP', r.get('cispep'), 'res', r.get('resol'), r.get('method', '')[:12], '' if r['match'] else 'NOMATCH')
