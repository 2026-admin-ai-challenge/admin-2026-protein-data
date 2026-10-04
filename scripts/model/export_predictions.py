"""Export validation predictions from a graph-model run as id,y_true,y_pred CSV files.

Reproduces select_model.py exactly: ensemble = w * GNN + (1 - w) * tree, argmax over classes.
Put this file in the graph code folder (next to train.py) and run it from there:
    python export_predictions.py --data <path to data/public> --run runs/main
Outputs (default runs/main/eval_predictions/):
    graph_<tree key>.csv   one file per tree model stored in tree_validation.npz
    graph_gnn.csv          GNN alone
    graph_ensemble.csv     final ensemble with the weight chosen in selection.json
"""
from pathlib import Path
import argparse
import json

import numpy as np
import pandas as pd

from train import load_data   # same loader and validation order as select_model.py

p = argparse.ArgumentParser()
p.add_argument("--data", type=Path, required=True)
p.add_argument("--run", type=Path, default=Path("runs/main"))
p.add_argument("--out", type=Path, default=None)
a = p.parse_args()
out = a.out or a.run / "eval_predictions"
out.mkdir(parents=True, exist_ok=True)

report = json.loads((a.run / "report.json").read_text())
selection = json.loads((a.run / "selection.json").read_text())
classes = np.array(report["classes"])            # class order used by the probability columns
rows, fold = load_data(a.data)
val = np.asarray(fold == "validation")
ids = rows.id[val].to_numpy()
y_true = rows.label[val].to_numpy()


def save(name, prob):
    if prob.shape != (len(ids), len(classes)):
        raise ValueError(f"{name}: expected shape {(len(ids), len(classes))}, got {prob.shape}")
    pd.DataFrame({"id": ids, "y_true": y_true, "y_pred": classes[prob.argmax(1)]}
                 ).to_csv(out / f"{name}.csv", index=False)
    print("saved", out / f"{name}.csv")


with np.load(a.run / "tree_validation.npz") as f:
    trees = {key: f[key] for key in f.files}
gnn = np.load(a.run / "gnn_validation.npy")

for key, prob in trees.items():
    save(f"graph_{key}", prob)
save("graph_gnn", gnn)

w = float(selection["gnn_weight"])
print(f"ensemble: gnn_weight={w}, tree={selection['tree']}")
save("graph_ensemble", w * gnn + (1 - w) * trees[selection["tree"]])
