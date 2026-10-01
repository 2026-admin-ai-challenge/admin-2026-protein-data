"""Download only pinned, official CATH 4.4 files; retain checksums for provenance."""
import hashlib, json
from pathlib import Path
import requests
ROOT = Path(__file__).resolve().parents[1]
BASE = "https://download.cathdb.info/cath/releases/all-releases/v4_4_0"
SOURCES = {
    "s40.fa": BASE + "/non-redundant-data-sets/cath-dataset-nonredundant-S40-v4_4_0.fa",
    "s40.atom.fa": BASE + "/non-redundant-data-sets/cath-dataset-nonredundant-S40-v4_4_0.atom.fa",
    "s40.pdb.tgz": BASE + "/non-redundant-data-sets/cath-dataset-nonredundant-S40-v4_4_0.pdb.tgz",
    "domains.txt": BASE + "/cath-classification-data/cath-domain-list-v4_4_0.txt",
}
def download(root=ROOT):
    raw = root / "data/raw"; raw.mkdir(parents=True, exist_ok=True)
    manifest = {}
    for name, url in SOURCES.items():
        path = raw / name
        if not path.exists():
            with requests.get(url, stream=True, timeout=(20, 120)) as response:
                response.raise_for_status()
                temp = path.with_suffix(".part")
                with temp.open("wb") as f:
                    for chunk in response.iter_content(1024*1024): f.write(chunk)
                temp.replace(path)
        with path.open("rb") as f:
            head = f.read(300)
            if not head or b"<html" in head.lower(): raise ValueError("Not a CATH data file")
            f.seek(0)
            digest = hashlib.file_digest(f, "sha256").hexdigest()
        manifest[name] = {"url":url, "sha256":digest, "bytes":path.stat().st_size}
    (raw / "manifest.json").write_text(json.dumps(manifest, indent=2))
    print(json.dumps(manifest, indent=2))
    return manifest
if __name__ == "__main__": download()
