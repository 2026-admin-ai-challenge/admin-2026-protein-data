"""비정상 값 후보 A-01~A-08의 분포를 계산한다 (학습 데이터만, 읽기 전용). 시각자료와 기준 후보에 쓴 값.

사용: python scripts/quality/day2_abnormal_stats.py <레포 경로> <작업 폴더>/abn.json
"""
import csv, io, json, sys, zipfile, collections
import numpy as np
from scipy.spatial.distance import pdist, squareform

ROOT = sys.argv[1]
OUT = sys.argv[2]
AA = "ACDEFGHIKLMNPQRSTVWY"
z = zipfile.ZipFile(f"{ROOT}/data/public/train_structures.zip")
train = {r["id"]: r for r in csv.DictReader(open(f"{ROOT}/data/public/train.csv", encoding="utf-8"))}
feat = {r["id"]: r for r in csv.DictReader(open(f"{ROOT}/data/public/train_features.csv", encoding="utf-8"))}

rec = []
consec_all = []
for n in z.namelist():
    i = n[:-4]
    f = np.load(io.BytesIO(z.read(n)), allow_pickle=False)
    pos, m, seg = f["pos"].astype(float), f["ca_mask"], f["segment_index"]
    N = len(m)
    seq = train[i]["sequence"]; lab = train[i]["label"]
    cnt = collections.Counter(seq); top_aa, top_n = cnt.most_common(1)[0]
    P = pos[m]
    rg = float(np.sqrt(((P - P.mean(0)) ** 2).sum(1).mean()))
    rmax = float(np.sqrt(((P - P.mean(0)) ** 2).sum(1)).max())
    d = np.linalg.norm(np.diff(pos, axis=0), axis=1)
    same = (seg[1:] == seg[:-1]) & m[:-1] & m[1:]
    cd = d[same]
    consec_all.append(cd)
    cmin = float(cd.min()) if len(cd) else None
    cmin_k = int(np.where(same)[0][np.argmin(cd)]) if len(cd) else None
    # non-bonded clash: pairs |i-j|>=3 among observed
    idx = np.where(m)[0]
    D = squareform(pdist(pos[idx]))
    sep = np.abs(idx[:, None] - idx[None, :])
    D[sep < 3] = np.inf
    a, b = np.unravel_index(np.argmin(D), D.shape)
    nb = float(D[a, b])
    rec.append(dict(id=i, label=lab, N=N, top_aa=top_aa, top_frac=top_n / N, rg=rg, rmax=rmax,
                    shape1=float(feat[i]["shape_1"]), cmin=cmin, cmin_k=cmin_k,
                    nb=nb, nb_i=int(idx[a]), nb_j=int(idx[b]), nseg=int(len(np.unique(seg)))))

consec = np.concatenate(consec_all)
L = np.array([r["N"] for r in rec]); RG = np.array([r["rg"] for r in rec])
lb, la = np.polyfit(np.log(L), np.log(RG), 1)
for r in rec:
    r["rg_ratio"] = r["rg"] / (np.exp(la) * r["N"] ** lb)

def hist(vals, edges):
    h, _ = np.histogram(vals, edges); return h.tolist()

def top(key, k=5, rev=True):
    s = sorted(rec, key=lambda r: (r[key] is None, -r[key] if rev else r[key]))
    return [{kk: r[kk] for kk in ("id", "label", "N", key)} for r in s[:k]]

out = {}
out["n"] = len(rec)
out["fit"] = {"a": float(np.exp(la)), "b": float(lb)}
lengths = L
out["A01"] = {"edges": list(range(0, 1101, 50)), "hist": hist(lengths, list(range(0, 1101, 50))),
              "mean": float(lengths.mean()), "median": float(np.median(lengths)),
              "q": {str(q): float(np.percentile(lengths, q)) for q in (90, 95, 99, 99.9)},
              "top": top("N"),
              "class_median": {c: float(np.median([r["N"] for r in rec if r["label"] == c])) for c in sorted({r["label"] for r in rec})}}
tf = np.array([r["top_frac"] for r in rec])
e = [round(x, 2) for x in np.arange(0.05, 0.56, 0.025)]
out["A02"] = {"edges": e, "hist": hist(tf, e), "q": {str(q): float(np.percentile(tf, q)) for q in (90, 99, 99.9)},
              "top": [{"id": r["id"], "label": r["label"], "N": r["N"], "aa": r["top_aa"], "frac": r["top_frac"]}
                      for r in sorted(rec, key=lambda r: -r["top_frac"])[:5]],
              "max": float(tf.max())}
rr = np.array([r["rg_ratio"] for r in rec])
rng = np.random.default_rng(0)
samp = rng.choice(len(rec), 1500, replace=False)
pts = sorted(set(samp.tolist()) | set(np.argsort(-rr)[:40].tolist()))
out["A03"] = {"scatter": [[rec[k]["N"], round(rec[k]["rg"], 2), round(rec[k]["rg_ratio"], 3)] for k in pts],
              "ratio_edges": [round(x, 2) for x in np.arange(0.6, 3.01, 0.1)],
              "ratio_hist": hist(rr, [round(x, 2) for x in np.arange(0.6, 3.01, 0.1)]),
              "q": {str(q): float(np.percentile(rr, q)) for q in (1, 99, 99.9)},
              "top": [{"id": r["id"], "label": r["label"], "N": r["N"], "rg": r["rg"], "ratio": r["rg_ratio"]}
                      for r in sorted(rec, key=lambda r: -r["rg_ratio"])[:5]]}
s1 = np.array([r["shape1"] for r in rec])
e = [round(x, 2) for x in np.arange(0.3, 1.001, 0.025)]
out["A04"] = {"edges": e, "hist": hist(s1, e), "q": {str(q): float(np.percentile(s1, q)) for q in (50, 99, 99.9)},
              "top": top("shape1"), "count_ge": {str(t): int((s1 >= t).sum()) for t in (0.8, 0.9, 0.95, 0.98)}}
e = [round(x, 2) for x in np.arange(2.5, 4.51, 0.1)]
cm = np.array([r["cmin"] for r in rec if r["cmin"] is not None])
out["A05"] = {"edges": e, "hist_all": hist(consec, e), "n_pairs": int(len(consec)),
              "min": float(consec.min()), "below": {str(t): int((consec < t).sum()) for t in (2.5, 2.8, 3.0, 3.2, 3.5)},
              "struct_below": {str(t): int((cm < t).sum()) for t in (2.5, 2.8, 3.0, 3.2, 3.5)},
              "top": [{"id": r["id"], "label": r["label"], "N": r["N"], "cmin": r["cmin"], "k": r["cmin_k"]}
                      for r in sorted([r for r in rec if r["cmin"] is not None], key=lambda r: r["cmin"])[:5]]}
nbv = np.array([r["nb"] for r in rec])
e = [round(x, 2) for x in np.arange(2.0, 5.01, 0.1)]
out["A06"] = {"edges": e, "hist": hist(nbv, e), "below": {str(t): int((nbv < t).sum()) for t in (2.5, 3.0, 3.5, 3.8, 4.0)},
              "top": [{"id": r["id"], "label": r["label"], "N": r["N"], "nb": r["nb"], "i": r["nb_i"], "j": r["nb_j"]}
                      for r in sorted(rec, key=lambda r: r["nb"])[:6]], "median": float(np.median(nbv))}
RM = np.array([r["rmax"] for r in rec])
out["A07"] = {"scatter": [[rec[k]["N"], round(rec[k]["rmax"], 1)] for k in pts],
              "q": {str(q): float(np.percentile(RM, q)) for q in (50, 99, 99.9)}, "max": float(RM.max()),
              "top": top("rmax")}
NS = np.array([r["nseg"] for r in rec])
e = list(range(1, 22))
out["A08"] = {"edges": e, "hist": hist(NS, e + [1000]), "q": {str(q): float(np.percentile(NS, q)) for q in (50, 99, 99.9)},
              "top": top("nseg", 8)}
def vc(vals, nd):
    c = collections.Counter(round(float(np.floor(v * 10**nd) / 10**nd), nd) for v in vals)
    return sorted([[k, n] for k, n in c.items()])
out["vc"] = {"A01": vc(L, 0), "A02": vc(tf, 3), "A03": vc(rr, 3), "A04": vc(s1, 4),
             "A05": vc(consec[consec < 3.6], 3), "A05s": vc(cm, 3), "A06": vc(nbv, 3), "A07": vc(RM, 1), "A08": vc(NS, 0)}
out["A05"]["n_struct"] = int(len(cm))
out["class_rg"] = {}
for c in sorted({r["label"] for r in rec}):
    xs = [r["rg_ratio"] for r in rec if r["label"] == c]
    out["class_rg"][c] = [float(np.median(xs)), int(sum(x >= 2 for x in xs)), len(xs)]
json.dump(out, open(OUT, "w", encoding="utf-8"), ensure_ascii=False)
print(json.dumps({k: (v if k in ("n", "fit") else {kk: vv for kk, vv in v.items() if kk not in ("scatter", "hist", "hist_all", "edges", "ratio_hist", "ratio_edges", "class_median")}) for k, v in out.items()}, ensure_ascii=False, indent=1, default=str)[:6000])
