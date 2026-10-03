"""Day1 결측·중복·불일치 점검 (C-01~C-14), 학습 데이터 대상. 원본은 읽기만 한다.

사용: python scripts/quality/day1_check.py <레포 경로>
출력: 항목별 결과 JSON을 화면에 출력
"""
import csv, io, json, sys, zipfile, collections
from pathlib import Path
import numpy as np
from scipy.spatial.distance import pdist

ROOT = Path(sys.argv[1])
PUB, PRIV = ROOT / "data/public", ROOT / "data/private"
AA = "ACDEFGHIKLMNPQRSTVWY"
FEATS = [f"aa_{a}" for a in AA] + ["log_length", "ca_coverage", "radius_gyration", "shape_1", "shape_2", "shape_3",
         "distance_mean", "distance_std", "distance_q25", "distance_q50", "distance_q75"]
KEYS = {"residue_type", "residue_index", "segment_index", "pos", "ca_mask"}
R = {}

def rows(p):
    with open(p, newline="", encoding="utf-8") as f:
        r = csv.reader(f); h = next(r); return h, list(r)

def feats(g):
    aa, m = g["residue_type"], g["ca_mask"]; pos = g["pos"][m].astype(np.float64)
    c = pos - pos.mean(0); ev = np.maximum(np.linalg.eigvalsh(c.T @ c / len(pos)), 0)[::-1]
    d = pdist(pos)
    return np.asarray([*[np.mean(aa == i) for i in range(20)], np.log1p(len(aa)), np.mean(m), np.sqrt(ev.sum()),
                       *(ev / max(ev.sum(), 1e-12)), d.mean(), d.std(), *np.quantile(d, [.25, .5, .75])])

# C-01
NULLS = {"", "nan", "null", "none", "na"}
csvs = sorted(PUB.glob("*.csv")); bad = {}
for p in csvs:
    h, rs = rows(p)
    bad[p.name] = sum(1 for r in rs for v in r if v.strip().lower() in NULLS) + sum(1 for r in rs if len(r) != len(h))
R["C-01"] = {"files": [p.name for p in csvs], "bad": bad}

h_t, train = rows(PUB / "train.csv")
h_f, ftab = rows(PUB / "train_features.csv")
h_v, split = rows(PUB / "validation_split.csv")
ids_t = [r[0] for r in train]; ids_f = [r[0] for r in ftab]; ids_v = [r[0] for r in split]
seq = {r[0]: r[1] for r in train}; lab = {r[0]: r[2] for r in train}
fval = {r[0]: np.array([float(x) for x in r[1:]]) for r in ftab}
z = zipfile.ZipFile(PUB / "train_structures.zip"); names = z.namelist(); ids_z = [n[:-4] for n in names]

# C-03, C-04, C-07
S = {"train.csv": set(ids_t), "train_features.csv": set(ids_f), "validation_split.csv": set(ids_v), "train_structures.zip": set(ids_z)}
R["C-03"] = {"counts": {"train.csv": len(ids_t), "train_features.csv": len(ids_f), "validation_split.csv": len(ids_v), "train_structures.zip": len(names)},
             "missing_vs_train": {k: len(S["train.csv"] - v) for k, v in S.items()}, "extra_vs_train": {k: len(v - S["train.csv"]) for k, v in S.items()},
             "non_npz": sum(1 for n in names if not n.endswith(".npz"))}
R["C-04"] = {k: len(v) - len(set(v)) for k, v in {"train.csv": ids_t, "train_features.csv": ids_f, "validation_split.csv": ids_v}.items()}
R["C-07"] = {"dup_names": len(names) - len(set(names))}

# C-05
sq = list(seq.values()); R["C-05"] = {"dup_seq": len(sq) - len(set(sq))}

# C-06
_, test = rows(PRIV / "test.csv"); _, mp = rows(PRIV / "id_mapping.csv")
dom = {r[0]: r[1] for r in mp}; hs = {r[0]: r[2] for r in mp}
tid = [r[0] for r in test]; tseq = [r[1] for r in test]
R["C-06"] = {"id": len(set(ids_t) & set(tid)), "seq": len(set(sq) & set(tseq)),
             "domain": len({dom[i] for i in ids_t} & {dom[i] for i in tid}), "H": len({hs[i] for i in ids_t} & {hs[i] for i in tid}),
             "test_n": len(tid)}

# C-11
meta = json.loads((PUB / "metadata.json").read_text(encoding="utf-8"))
labs = set(lab.values())
R["C-11"] = {"n": len(labs), "eq_meta": labs == set(meta["labels"]), "meta_n": len(meta["labels"]),
             "float_changes": sum(1 for l in labs if str(float(l)) != l)}

# C-13
L = [len(s) for s in sq]; R["C-13"] = {"min": min(L), "max": max(L), "out": sum(1 for x in L if not 40 <= x <= 1200)}

# C-14
fold = dict((r[0], r[1]) for r in split)
H = collections.defaultdict(set); LB = collections.defaultdict(set)
for i, f in fold.items(): H[f].add(hs[i]); LB[f].add(lab[i])
R["C-14"] = {"cols": h_v, "folds": dict(collections.Counter(fold.values())), "H_overlap": len(H["fit"] & H["validation"]),
             "labels": {k: len(v) for k, v in LB.items()}}

# per-structure: C-02, C-08, C-09, C-10, C-12
c = collections.Counter(); minc = 1.0; miss_s = miss_r = 0; maxdiff = 0.0
odd_total = odd_files = 0; runs = collections.Counter()
R["C-10_cols"] = h_f[1:] == FEATS
for n in names:
    i = n[:-4]
    with np.load(io.BytesIO(z.read(n)), allow_pickle=False) as f:
        if set(f.files) != KEYS: c["C08_keys"] += 1; continue
        g = {k: f[k] for k in f.files}
    s = seq[i]; N = len(s); m = g["ca_mask"]; pos = g["pos"]; seg = g["segment_index"]
    # C-08
    if not all(len(g[k]) == N for k in KEYS): c["C08_len"] += 1
    if pos.shape != (N, 3): c["C08_shape"] += 1
    if not np.array_equal(g["residue_index"], np.arange(N)): c["C08_ridx"] += 1
    # C-09
    if not set(s) <= set(AA): c["C09_nonstd"] += 1
    if "".join(AA[int(a)] for a in g["residue_type"]) != s: c["C09_decode"] += 1
    # C-02
    if m.sum() < 40: c["C02_ca40"] += 1
    if m.mean() < .95: c["C02_cov"] += 1
    if not np.all(pos[~m] == 0): c["C02_zero"] += 1
    if not np.isfinite(pos).all(): c["C02_finite"] += 1
    if (~m).any(): miss_s += 1; miss_r += int((~m).sum())
    minc = min(minc, float(m.mean()))
    # C-10
    v = fval[i]
    if not np.isfinite(v).all(): c["C10_finite"] += 1
    rf = feats(g)
    if not np.allclose(v, rf, rtol=1e-6, atol=1e-7): c["C10_mismatch"] += 1
    maxdiff = max(maxdiff, float(np.max(np.abs(v - rf))))
    # C-12
    if seg[0] != 0: c["C12_start"] += 1
    if not set(np.diff(seg).tolist()) <= {0, 1}: c["C12_step"] += 1
    d = np.linalg.norm(np.diff(pos, axis=0), axis=1); same = np.diff(seg) == 0
    if not (m[:-1][same] & m[1:][same]).all() or not (d[same] <= 4.5 + 1e-5).all(): c["C12_cont"] += 1
    odd = m[:-1] & m[1:] & ~same & (d <= 4.5)
    if odd.any():
        odd_total += int(odd.sum()); odd_files += 1
        best = cur = 0
        for x in odd: cur = cur + 1 if x else 0; best = max(best, cur)
        runs["5+" if best >= 5 else "2-4" if best >= 2 else "1"] += 1

R["struct"] = {"counts": dict(c), "missing_structs": miss_s, "missing_res": miss_r, "min_cov": minc, "feat_maxdiff": maxdiff,
               "odd_total": odd_total, "odd_files": odd_files, "runs": dict(runs), "n": len(names)}
print(json.dumps(R, ensure_ascii=False, indent=1))
