"""A-06 겹침 쌍을 원본 PDB와 대조: 원본 거리, 점유율·대체 위치, 근접 경고(REMARK 500), B-factor.

사용: python scripts/quality/day2_a06_verify.py <레포 경로> <작업 폴더>/pdb <작업 폴더>/hits_067.json <작업 폴더>/a06_verified.json
"""
import csv, gzip, json, sys
import numpy as np

ROOT, PDBDIR, HITS, OUT = sys.argv[1:5]
AA3 = {'ALA':'A','CYS':'C','ASP':'D','GLU':'E','PHE':'F','GLY':'G','HIS':'H','ILE':'I','LYS':'K','LEU':'L',
       'MET':'M','ASN':'N','PRO':'P','GLN':'Q','ARG':'R','SER':'S','THR':'T','VAL':'V','TRW':'W','TRP':'W','TYR':'Y'}
train = {r['id']: r['sequence'] for r in csv.DictReader(open(f'{ROOT}/data/public/train.csv', encoding='utf-8'))}
hits = json.load(open(HITS, encoding='utf-8'))['a06']

def load(pdb, chain):
    res, order, resol, method, close = {}, [], None, '', []
    in500 = False
    for line in gzip.open(f'{PDBDIR}/{pdb}.pdb.gz', 'rt', errors='replace'):
        if line.startswith('EXPDTA'): method = line[10:].strip()
        if line.startswith('REMARK   2 RESOLUTION.'):
            try: resol = float(line[23:30])
            except ValueError: pass
        if line.startswith('REMARK 500') and 'CLOSE CONTACTS' in line: in500 = True
        elif line.startswith('REMARK 500') and in500 and 'REMARK 500 M ' not in line and line[11:].strip() == '': pass
        if in500 and line.startswith('REMARK 500') and line[11:].split() and line[11:].split()[0] in ('CA', 'N', 'C', 'O', 'CB'):
            close.append(line[11:].strip())
        if line.startswith('REMARK 500') and 'GEOMETRY AND STEREOCHEMISTRY' in line and close: in500 = False
        if line.startswith('ENDMDL'): break
        if line.startswith('ATOM') and line[21] == chain and line[12:16].strip() == 'CA':
            rn = line[17:20].strip()
            if rn not in AA3: continue
            key = (int(line[22:26]), line[26].strip())
            alt, occ, bf = line[16].strip(), float(line[54:60] or 0), float(line[60:66] or 0)
            xyz = np.array([float(line[30:38]), float(line[38:46]), float(line[46:54])])
            if key not in res:
                res[key] = {'aa': AA3[rn], 'alts': []}; order.append(key)
            res[key]['alts'].append((alt, occ, bf, xyz))
    return res, order, resol, method, close

def locate(seq, chseq, k):
    for w in (6, 4, 3):
        lo = max(0, k - w); win = seq[lo:k + w + 1]
        idx = chseq.find(win)
        if idx >= 0 and chseq.find(win, idx + 1) < 0:
            return idx + (k - lo)
    return None

out = []
for h in hits:
    pdb, chain = h['dom'][:4].upper(), h['dom'][4]
    res, order, resol, method, close = load(pdb, chain)
    chseq = ''.join(res[k]['aa'] for k in order)
    seq = train[h['id']]
    i, j, d = min(h['pairs'], key=lambda x: x[2])
    oi, oj = locate(seq, chseq, i), locate(seq, chseq, j)
    r = {'id': h['id'], 'label': h['label'], 'N': h['N'], 'npairs': len(h['pairs']), 'i': i, 'j': j, 'd': d,
         'resol': resol, 'method': method, 'aa_i': seq[i], 'aa_j': seq[j]}
    if oi is None or oj is None:
        r['match'] = False
    else:
        a, b = order[oi], order[oj]
        r.update(match=True, res_i=f'{a[0]}{a[1]}', res_j=f'{b[0]}{b[1]}',
                 occ_i=[x[1] for x in res[a]['alts']], occ_j=[x[1] for x in res[b]['alts']],
                 alt_i=[x[0] for x in res[a]['alts']], alt_j=[x[0] for x in res[b]['alts']],
                 bf_i=res[a]['alts'][0][2], bf_j=res[b]['alts'][0][2],
                 d_orig=round(float(np.linalg.norm(res[a]['alts'][0][3] - res[b]['alts'][0][3])), 3))
        tag_i, tag_j = f' {a[0]}{a[1]}'.rstrip(), f' {b[0]}{b[1]}'.rstrip()
        r['remark500'] = [c for c in close if (str(a[0]) in c.split() and str(b[0]) in c.split())][:2]
    if h['npairs'] if 'npairs' in h else len(h['pairs']) > 3:
        offs = [p[1] - p[0] for p in h['pairs']]
        r['offsets'] = sorted(set(offs))[:6]
        r['seg_seq_i'] = seq[min(p[0] for p in h['pairs']):max(p[0] for p in h['pairs']) + 1]
        r['seg_seq_j'] = seq[min(p[1] for p in h['pairs']):max(p[1] for p in h['pairs']) + 1]
    out.append(r)

json.dump(out, open(OUT, 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
for r in sorted(out, key=lambda r: r['d']):
    print(r['id'], r['label'], 'pairs', r['npairs'], 'd', r['d'], r['aa_i'] + r['aa_j'], r.get('res_i'), r.get('res_j'),
          'occ', r.get('occ_i'), r.get('occ_j'), 'alt', r.get('alt_i'), r.get('alt_j'), 'B', r.get('bf_i'), r.get('bf_j'),
          'res', r['resol'], r['method'][:6], 'R500', len(r.get('remark500', [])), '' if r['match'] else 'NOMATCH')
