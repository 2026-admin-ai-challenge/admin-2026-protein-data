"""Download pinned official CATH 4.4 S40 sequence, structure, and labels."""
import argparse
import hashlib
import json
from pathlib import Path
from urllib.request import urlopen
ROOT = Path(__file__).resolve().parents[1]
BASE = "https://download.cathdb.info/cath/releases/all-releases/v4_4_0"
SOURCES = {
    "s40.fa": BASE + "/non-redundant-data-sets/cath-dataset-nonredundant-S40-v4_4_0.fa",
    "s40.atom.fa": BASE + "/non-redundant-data-sets/cath-dataset-nonredundant-S40-v4_4_0.atom.fa",
    "s40.pdb.tgz": BASE + "/non-redundant-data-sets/cath-dataset-nonredundant-S40-v4_4_0.pdb.tgz",
    "domains.txt": BASE + "/cath-classification-data/cath-domain-list-v4_4_0.txt",
}
def download(root=ROOT):
    root = Path(root)
    raw = root / "data/raw"; raw.mkdir(parents=True, exist_ok=True)
    manifest = {}
    for name, url in SOURCES.items():
        path = raw / name
        if not path.exists():
            temp = path.with_suffix(path.suffix + ".part")
            print(f"Downloading {name} from {url}", flush=True)
            try:
                with urlopen(url, timeout=120) as response:
                    expected = int(response.headers.get("Content-Length", "0"))
                    received = 0
                    next_report = 64 * 1024 * 1024
                    with temp.open("wb") as output:
                        while True:
                            chunk = response.read(1024 * 1024)
                            if not chunk:
                                break
                            output.write(chunk)
                            received += len(chunk)
                            if received >= next_report:
                                print(f"  {name}: {received / 1024**2:.0f} MiB", flush=True)
                                next_report += 64 * 1024 * 1024
                    if expected and received != expected:
                        raise IOError(f"Incomplete download of {name}: {received}/{expected} bytes")
                temp.replace(path)
            except Exception:
                temp.unlink(missing_ok=True)
                raise
        else:
            print(f"Using existing {path}", flush=True)
        with path.open("rb") as f:
            head = f.read(300)
            if not head or b"<html" in head.lower(): raise ValueError("Not a CATH data file")
            f.seek(0)
            digest = hashlib.file_digest(f, "sha256").hexdigest()
        manifest[name] = {"url":url, "sha256":digest, "bytes":path.stat().st_size}
    (raw / "manifest.json").write_text(json.dumps(manifest, indent=2))
    print(json.dumps(manifest, indent=2))
    return manifest
if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Download official CATH v4.4 S40 raw data")
    parser.add_argument("--root", type=Path, default=ROOT,
                        help="Dataset workspace (files go into data/raw)")
    download(parser.parse_args().root)
