"""Freeze an existing reviewed dataset before changing source-quality filters.

Run once on the reference version; never regenerate this policy from filtered data.
The output contains hidden labels and original domains and is organizer-only.
"""
import argparse
import hashlib
import json
from pathlib import Path
import pandas as pd
from scripts.split_dataset import ASSIGNMENT_COLUMNS, load_split_assignments

def freeze(root, output, reference):
    output = Path(output)
    if output.exists() or output.with_suffix(".json").exists():
        raise FileExistsError("Frozen split already exists; do not overwrite reference assignments")
    mapping = pd.read_csv(root / "data/private/id_mapping.csv", dtype=str)
    train = pd.read_csv(root / "data/public/train.csv", dtype=str)
    labels = pd.read_csv(root / "data/private/labels.csv", dtype=str)
    folds = pd.read_csv(root / "data/public/validation_split.csv", dtype=str)
    train = train[["id", "label"]].merge(folds, on="id", validate="one_to_one")
    train["split"], train["partition"] = "train", "-"
    labels["split"], labels["fold"] = "test", "-"
    assignments = pd.concat([train, labels], ignore_index=True).merge(mapping, on="id", validate="one_to_one")
    assignments = assignments.rename(columns={"label": "architecture_label"})[ASSIGNMENT_COLUMNS]
    if len(assignments) != len(mapping):
        raise ValueError("Reference mapping is not fully covered")
    output.parent.mkdir(parents=True, exist_ok=True)
    assignments.to_csv(output, index=False)
    load_split_assignments(output)
    paths = ["data/public/train.csv", "data/private/id_mapping.csv", "data/private/labels.csv", "data/public/validation_split.csv"]
    output.with_suffix(".json").write_text(json.dumps({"schema_version": 1, "reference_commit": reference,
        "rows": len(assignments), "sha256": hashlib.sha256(output.read_bytes()).hexdigest(),
        "source_sha256": {name: info["sha256"] for name, info in json.loads((root/"data/public/metadata.json").read_text())["sources"].items()},
        "reference_files": {p: hashlib.sha256((root / p).read_bytes()).hexdigest() for p in paths}}, indent=2) + "\n")

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--reference", required=True, help="Reviewed reference commit")
    args = parser.parse_args()
    freeze(args.root, args.output, args.reference)
