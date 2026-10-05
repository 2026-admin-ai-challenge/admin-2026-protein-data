"""Write data/DATA_VERSION.json: one file tying the data version to counts and checksum files."""
import hashlib, json
from pathlib import Path
import pandas as pd
ROOT = Path(__file__).resolve().parents[1]


def sha256(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main(root=ROOT):
    pub, priv = root / "data/public", root / "data/private"
    meta = json.loads((pub / "metadata.json").read_text())
    labels = pd.read_csv(priv / "labels.csv", dtype=str)
    version = {
        "schema_version": 1,
        "source": f"CATH v{meta['version']} {meta['subset']}",
        "seed": meta["seed"],
        "counts": {
            "train": meta["stats"]["train"],
            "test": meta["stats"]["test"],
            "public": int((labels.partition == "public").sum()),
            "private": int((labels.partition == "private").sum()),
            "classes": meta["stats"]["classes"],
        },
        "metadata_sha256": sha256(pub / "metadata.json"),
        "checksums_sha256": sha256(root / "data/DATASET_CHECKSUMS.json"),
    }
    (root / "data/DATA_VERSION.json").write_text(json.dumps(version, indent=2) + "\n")
    print("wrote data/DATA_VERSION.json")


if __name__ == "__main__":
    main()
