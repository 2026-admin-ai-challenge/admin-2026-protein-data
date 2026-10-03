"""C-12 의심 지점을 원본 PDB 번호와 대조해 원인별로 분류한다.

사용: python scripts/quality/c12_classify.py <작업 폴더>
입력: <작업 폴더>/suspects.json (c12_suspects.py), <작업 폴더>/pdb/ (fetch_pdb.py)
출력: <작업 폴더>/c12_result.json
"""
import gzip, json, sys, collections
from pathlib import Path

S = Path(sys.argv[1])
AA = {'ALA':'A','CYS':'C','ASP':'D','GLU':'E','PHE':'F','GLY':'G','HIS':'H','ILE':'I','LYS':'K','LEU':'L','MET':'M',
      'ASN':'N','PRO':'P','GLN':'Q','ARG':'R','SER':'S','THR':'T','VAL':'V','TRP':'W','TYR':'Y'}

def chain_pdb(text, chain):
    res, seen = [], set()
    for l in text.splitlines():
        if l.startswith('ENDMDL'): break
        if not l.startswith('ATOM  ') or l[21] != chain: continue
        aa = AA.get(l[17:20].strip())
        if aa is None: continue
        k = (l[21], int(l[22:26]), l[26].strip())
        if k not in seen: seen.add(k); res.append((k, aa))
    return res

def chain_cif(text, chain):
    lines = text.splitlines(); cols = []; res = []; seen = set(); i = 0; model = None
    while i < len(lines):
        if lines[i].startswith('_atom_site.'):
            while lines[i].startswith('_atom_site.'): cols.append(lines[i].split('.')[1].strip()); i += 1
            ix = {c: n for n, c in enumerate(cols)}
            while i < len(lines) and (lines[i].startswith('ATOM') or lines[i].startswith('HETATM')):
                t = lines[i].split()
                if t[ix['group_PDB']] == 'ATOM' and t[ix['auth_asym_id']] == chain:
                    mdl = t[ix['pdbx_PDB_model_num']]
                    if model is None: model = mdl
                    if mdl != model: break
                    aa = AA.get(t[ix['label_comp_id']])
                    if aa:
                        ic = t[ix['pdbx_PDB_ins_code']]; ic = '' if ic in '?.' else ic
                        k = (chain, int(t[ix['auth_seq_id']]), ic)
                        if k not in seen: seen.add(k); res.append((k, aa))
                i += 1
            break
        i += 1
    return res

def load(pdb, chain):
    p = S / 'pdb' / f'{pdb}.pdb.gz'
    if p.exists(): return chain_pdb(gzip.open(p, 'rt').read(), chain)
    p = S / 'pdb' / f'{pdb}.cif.gz'
    if p.exists(): return chain_cif(gzip.open(p, 'rt').read(), chain)
    return None

def fmt(k): return f"{k[1]}{k[2]}"

def classify(a, b):
    (ca, na, ia), (cb, nb, ib) = a, b
    if ca != cb: return '사슬 변경'
    if nb == na + 1 and ib and ia == ib: return '삽입코드 고정 (버그)'
    if nb == na + 1 and ib: return '삽입코드 경계'
    if nb == na + 1 and not ib: return '연속인데 끊김 (설명 불가)'
    if nb == na:
        exp = chr(ord(ia) + 1) if ia else 'A'
        if ib == exp: return '연속인데 끊김 (설명 불가)'
        if not ib: return '삽입코드 역순'
        return '삽입코드 건너뜀'
    if nb > na + 1: return '번호 건너뜀'
    return '번호 역행'

sus = json.load(open(S / 'suspects.json'))
rows = []; per = {}
for o in sus:
    pdb, chain = o['domain'][:4].upper(), o['domain'][4]
    res = load(pdb, chain)
    cats = []
    for i, d in zip(o['breaks'], o['dist']):
        seq = o['seq']
        if res is None: cats.append(('원본 없음', '', '', d)); continue
        cs = ''.join(a for _, a in res)
        # 1) 앞뒤 6글자 창: 원본 사슬에서 바로 이웃이면 그 쌍, 떨어져 있으면 "사이에 다른 잔기"
        left = seq[max(0, i - 5):i + 1]; right = seq[i + 1:i + 7]
        A = [p + len(left) - 1 for p in range(len(cs)) if cs.startswith(left, p)]
        B = [p for p in range(len(cs)) if cs.startswith(right, p)]
        pair = next(((x, x + 1) for x in A if x + 1 in B), None)
        if pair is None:
            pair2 = next(((x, y) for x in A for y in B if y > x), None)
            if pair2 is not None:
                x, y = pair2; cats.append(('사이에 다른 잔기', fmt(res[x][0]), fmt(res[y][0]), d)); continue
        # 2) 6글자 창으로 못 찾으면 3→2글자 창으로 줄여, 바로 이웃한 위치가 하나뿐일 때만 채택
        if pair is None:
            for lw in (3, 2):
                l2 = seq[max(0, i - lw + 1):i + 1]; r2 = seq[i + 1:i + 1 + lw]
                cand = [(p + len(l2) - 1, p + len(l2)) for p in range(len(cs)) if cs.startswith(l2, p) and cs.startswith(r2, p + len(l2))]
                if len(cand) == 1: pair = cand[0]; break
        # 3) 끊긴 뒤 칸이 혼자 떨어진 잔기 1개인 경우(바로 다음에 또 끊김): 뒤 창을 그 잔기 하나로 줄임
        if pair is None:
            cand = [(x, x + 1) for x in A if x + 1 < len(cs) and cs[x + 1] == seq[i + 1]]
            if len(cand) == 1: pair = cand[0]
        if pair is None:
            cats.append(('대응 실패', '', '', d)); continue
        x, y = pair; ka, kb = res[x][0], res[y][0]
        cats.append((classify(ka, kb), fmt(ka), fmt(kb), d))
    per[o['id']] = {'label': o['label'], 'n_break': len(cats), 'cats': dict(collections.Counter(c[0] for c in cats)),
                    'examples': [f"{c[1]}→{c[2]} ({c[3]}Å) {c[0]}" for c in cats[:4]]}
    rows += [(o['id'], o['label'], *c) for c in cats]

tot = collections.Counter(r[2] for r in rows)
sc = collections.Counter()
for i, v in per.items():
    sc['버그 포함' if v['cats'].get('삽입코드 고정 (버그)') else ('설명 불가 포함' if any(k.startswith('연속인데') or k in ('대응 실패','원본 없음','삽입코드 역순','번호 역행') for k in v['cats']) else '정상 처리만')] += 1
json.dump({'by_point': dict(tot), 'by_struct': dict(sc), 'per': per, 'rows': rows}, open(S / 'c12_result.json', 'w', encoding='utf-8'), ensure_ascii=False)
print('points', dict(tot)); print('structs', dict(sc))
for i, v in per.items():
    if not set(v['cats']) <= {'번호 건너뜀', '사슬 변경'}: print(i, v['label'], v['n_break'], v['cats'], v['examples'][:2])
