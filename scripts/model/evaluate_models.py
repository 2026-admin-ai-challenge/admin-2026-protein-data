"""Evaluate candidate models with extended metrics on the fixed fit/validation split.

Outputs (default folder: results/eval/):
  summary.csv               one row per model: 7 required metrics + extras
  per_class/<model>.csv     all 20 classes: precision, recall, f1, support, predicted_count
  confusion/<model>.csv     confusion matrix, rows = true label, columns = predicted label
  predictions/<model>.csv   validation predictions: id, y_true, y_pred
  run_info.json             versions, seed, threads, repeats, label order, model settings, data commit

Run from the repository root with the competition environment:
    .venv-competition\\Scripts\\python.exe scripts\\evaluate_models.py
Only some models:
    .venv-competition\\Scripts\\python.exe scripts\\evaluate_models.py --models logistic_regression xgboost
Evaluate saved prediction files only (no training, e.g. a graph model in id,y_true,y_pred format):
    .venv-competition\\Scripts\\python.exe scripts\\evaluate_models.py --predictions path\\to\\graph_model.csv

Rules: same 31 features and fixed split for every model, CPU limited to 2 threads, seed 42,
same 20-label order everywhere, divisions with no samples count as 0 (zero_division=0).
Fit time = model.fit only (data loading excluded), repeated --repeats times on the same data.
"""
from importlib.metadata import version
from pathlib import Path
import argparse
import json
import pickle
import platform
import subprocess
import time

import numpy as np
import pandas as pd
from sklearn.dummy import DummyClassifier
from sklearn.ensemble import ExtraTreesClassifier, HistGradientBoostingClassifier, RandomForestClassifier
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import (accuracy_score, balanced_accuracy_score, confusion_matrix, f1_score,
                             precision_recall_fscore_support, precision_score, recall_score)
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler
from sklearn.utils.class_weight import compute_sample_weight
from threadpoolctl import threadpool_limits

import sys
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))  # scripts folder (where baseline.py is)
from baseline import default_data_dir, load_inputs

SEED = 42
THREADS = 2
PACKAGES = ["scikit-learn", "numpy", "pandas", "scipy", "xgboost", "lightgbm", "catboost"]


def candidates():
    """Name -> new, untrained model. Library defaults, no tuning.
    Only seed, thread count, class balancing and log silencing are set explicitly."""
    from catboost import CatBoostClassifier
    from lightgbm import LGBMClassifier
    from xgboost import XGBClassifier
    return {
        # existing 4 (same settings as compare_models.py)
        "dummy_most_frequent": DummyClassifier(strategy="most_frequent"),
        "logistic_regression": make_pipeline(StandardScaler(), LogisticRegression(
            max_iter=2000, C=1.0, class_weight="balanced", random_state=SEED)),  # scaler fit on fit rows only
        "random_forest": RandomForestClassifier(
            n_estimators=300, class_weight="balanced", random_state=SEED, n_jobs=THREADS),
        "hist_gradient_boosting": HistGradientBoostingClassifier(
            class_weight="balanced", random_state=SEED),
        # new 4
        "extra_trees": ExtraTreesClassifier(  # same tree count as RF for a direct comparison
            n_estimators=300, class_weight="balanced", random_state=SEED, n_jobs=THREADS),
        "xgboost": XGBClassifier(  # no class_weight option: balanced weights go in fit(sample_weight=...)
            tree_method="hist", random_state=SEED, n_jobs=THREADS),
        "lightgbm": LGBMClassifier(
            class_weight="balanced", random_state=SEED, n_jobs=THREADS, verbosity=-1),
        "catboost": CatBoostClassifier(
            auto_class_weights="Balanced", random_seed=SEED, thread_count=THREADS,
            verbose=False, allow_writing_files=False),
    }


def fit(name, model, x, y):
    if name == "xgboost":
        model.fit(x, y, sample_weight=compute_sample_weight("balanced", y))
    else:
        model.fit(x, y)
    return model


def evaluate_predictions(name, ids, y_true, y_pred, labels, out_dir):
    """Metrics + per-class table + confusion matrix + prediction file for one model."""
    y_true, y_pred = np.asarray(y_true, dtype=str), np.asarray(y_pred, dtype=str)
    kw = dict(labels=labels, zero_division=0)
    row = {
        "model": name,
        "macro_f1": f1_score(y_true, y_pred, average="macro", **kw),
        "weighted_f1": f1_score(y_true, y_pred, average="weighted", **kw),
        "accuracy": accuracy_score(y_true, y_pred),
        "balanced_accuracy": balanced_accuracy_score(y_true, y_pred),
        "macro_precision": precision_score(y_true, y_pred, average="macro", **kw),
        "macro_recall": recall_score(y_true, y_pred, average="macro", **kw),
    }
    p, r, f, s = precision_recall_fscore_support(y_true, y_pred, **kw)
    predicted = pd.Series(y_pred).value_counts().reindex(labels, fill_value=0).to_numpy()
    pd.DataFrame({"label": labels, "precision": p.round(5), "recall": r.round(5), "f1": f.round(5),
                  "support": s, "predicted_count": predicted}
                 ).to_csv(out_dir / "per_class" / f"{name}.csv", index=False)
    cm = pd.DataFrame(confusion_matrix(y_true, y_pred, labels=labels), index=labels, columns=labels)
    cm.index.name = "true\\pred"
    cm.to_csv(out_dir / "confusion" / f"{name}.csv")
    pd.DataFrame({"id": ids, "y_true": y_true, "y_pred": y_pred}
                 ).to_csv(out_dir / "predictions" / f"{name}.csv", index=False)
    return row


def data_commit():
    try:
        return subprocess.run(["git", "rev-parse", "HEAD"], capture_output=True, text=True, check=True).stdout.strip()
    except Exception:
        return "unknown"


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--data-dir", type=Path, default=default_data_dir())
    parser.add_argument("--output-dir", type=Path, default=Path("results/eval"))
    parser.add_argument("--repeats", type=int, default=3, help="fit-time repeats per model (3-5)")
    parser.add_argument("--models", nargs="*", help="subset of model names (default: all)")
    parser.add_argument("--predictions", nargs="*", help="evaluate id,y_true,y_pred files instead of training")
    args = parser.parse_args()

    train, _, x, _, fold = load_inputs(args.data_dir)       # same loader/checks as baseline.py
    fit_rows, val_rows = fold == "fit", fold == "validation"
    labels = sorted(train.label.unique())                   # one fixed 20-label order for everything
    code = {label: i for i, label in enumerate(labels)}
    y = train.label.map(code).to_numpy()                    # integer codes (XGBoost needs them); decoded back later
    x_fit, y_fit, x_val = x.iloc[fit_rows], y[fit_rows], x.iloc[val_rows]
    ids_val = train.id[val_rows].to_numpy()
    y_val = train.label[val_rows].to_numpy()

    out = args.output_dir
    for sub in ("per_class", "confusion", "predictions"):
        (out / sub).mkdir(parents=True, exist_ok=True)
    print(f"Python {platform.python_version()}, " + ", ".join(f"{p} {version(p)}" for p in PACKAGES))
    print(f"fit {fit_rows.sum()} / validation {val_rows.sum()} samples, {len(labels)} classes, data commit {data_commit()[:7]}")

    rows, settings = [], {}
    if args.predictions:                                    # evaluation only, e.g. graph model output
        for path in args.predictions:
            pred = pd.read_csv(path, dtype=str)
            if not pred.id.is_unique or set(pred.id) != set(ids_val):
                raise ValueError(f"{path}: ids must be exactly the {len(ids_val)} validation ids")
            rows.append(evaluate_predictions(Path(path).stem, pred.id, pred.y_true, pred.y_pred, labels, out))
        summary_name = "summary_predictions.csv"
    else:
        selected = args.models or list(candidates())
        with threadpool_limits(limits=THREADS):
            for name in selected:
                print(f"running {name} ({args.repeats} fits) ...", flush=True)
                fit_times = []
                for _ in range(args.repeats):               # fresh untrained model each time, same data
                    model = candidates()[name]
                    started = time.perf_counter()
                    fit(name, model, x_fit, y_fit)
                    fit_times.append(time.perf_counter() - started)
                started = time.perf_counter()
                codes = np.asarray(model.predict(x_val)).ravel().astype(int)
                predict_seconds = time.perf_counter() - started
                row = evaluate_predictions(name, ids_val, y_val, np.array(labels)[codes], labels, out)
                row.update(
                    fit_seconds_mean=float(np.mean(fit_times)),
                    fit_seconds_std=float(np.std(fit_times, ddof=1)) if len(fit_times) > 1 else 0.0,
                    predict_ms_per_sample=predict_seconds / len(x_val) * 1000,
                    model_size_mb=len(pickle.dumps(model)) / 2**20,
                )
                rows.append(row)
                settings[name] = {k: repr(v) for k, v in model.get_params(deep=False).items()}
        summary_name = "summary.csv"

    table = pd.DataFrame(rows).round(5)
    print()
    print(table.to_string(index=False))
    table.to_csv(out / summary_name, index=False)

    info = {
        "python": platform.python_version(),
        "packages": {p: version(p) for p in PACKAGES},
        "data_commit": data_commit(),
        "n_fit": int(fit_rows.sum()), "n_validation": int(val_rows.sum()),
        "label_order": labels, "seed": SEED, "threads": THREADS, "fit_repeats": args.repeats,
        "rules": {"zero_division": 0, "fit_time": "model.fit only, data loading excluded",
                  "xgboost_class_balance": "compute_sample_weight('balanced') passed to fit"},
        "model_settings": settings,
    }
    (out / ("run_info.json" if not args.predictions else "run_info_predictions.json")).write_text(
        json.dumps(info, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"\nSaved results to {out}")


if __name__ == "__main__":
    main()
