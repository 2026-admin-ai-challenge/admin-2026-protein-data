"""Read official domain PDBs without extracting archive paths; publish safe numeric coordinate arrays."""
import io
import json
import tarfile
import zipfile
from collections import Counter
from pathlib import Path
import numpy as np
try:
    from .structure_features import AMINO_ACIDS, FEATURE_NAMES, structure_features
except ImportError:
    from structure_features import AMINO_ACIDS, FEATURE_NAMES, structure_features

RESIDUES = dict(zip(
    "ALA CYS ASP GLU PHE GLY HIS ILE LYS LEU MET ASN PRO GLN ARG SER THR VAL TRP TYR".split(),
    AMINO_ACIDS))
STRUCTURE_KEYS = {"residue_type", "residue_index", "segment_index", "pos", "ca_mask"}

def cache_name(domain):
    # PDB chain IDs are case-sensitive, macOS default filesystems are not.
    return domain.encode("ascii").hex() + ".npz"

def consecutive(a, b):
    # PDB residue numbers are used only here and are never published.
    chain_a, number_a, insertion_a = a
    chain_b, number_b, insertion_b = b
    if chain_a != chain_b:
        return False
    return ((number_b == number_a + 1 and not insertion_b) or
            (number_b == number_a and insertion_b and
             ord(insertion_b) == (ord(insertion_a) + 1 if insertion_a else ord("A"))))

def parse_pdb(text, expected_sequence):
    residues = {}
    model_seen = False
    for line in text.splitlines():
        if line.startswith("MODEL"):
            if model_seen: break
            model_seen = True
        if line.startswith("ENDMDL"): break
        if not line.startswith("ATOM  "): continue
        key = (line[21:22], int(line[22:26]), line[26:27].strip())
        aa = RESIDUES.get(line[17:20].strip())
        if aa is None: raise ValueError("nonstandard_structure_residue")
        entry = residues.setdefault(key, {"aa": aa, "ca": None, "priority": None})
        if entry["aa"] != aa: raise ValueError("ambiguous_residue_identity")
        if line[12:16].strip() != "CA": continue
        occupancy = float(line[54:60].strip() or 0)
        alt = line[16:17].strip()
        priority = (-occupancy, alt != "", alt != "A", alt)
        xyz = np.array([float(line[30:38]), float(line[38:46]), float(line[46:54])])
        if not np.isfinite(xyz).all(): raise ValueError("nonfinite_coordinates")
        if entry["priority"] is None or priority < entry["priority"]:
            entry.update(ca=xyz, priority=priority)
    sequence = "".join(r["aa"] for r in residues.values())
    # No heuristic alignment: reject disagreements instead of assigning coordinates to the wrong residue.
    if sequence != expected_sequence: raise ValueError("atom_sequence_mismatch")
    keys = list(residues)
    mask = np.array([r["ca"] is not None for r in residues.values()], dtype=bool)
    if mask.sum() < 40 or mask.mean() < .95: raise ValueError("insufficient_ca_coverage")
    pos = np.zeros((len(sequence), 3), dtype=np.float32)
    pos[mask] = np.array([r["ca"] for r in residues.values() if r["ca"] is not None], dtype=np.float32)
    pos[mask] -= pos[mask].mean(axis=0)
    segments = np.zeros(len(sequence), dtype=np.int32)
    for i in range(1, len(sequence)):
        linked = (consecutive(keys[i-1], keys[i]) and mask[i-1] and mask[i]
                  and 0 < np.linalg.norm(pos[i] - pos[i-1]) <= 4.5)
        segments[i] = segments[i-1] + int(not linked)
    return {"residue_type": np.array([AMINO_ACIDS.index(a) for a in sequence], dtype=np.uint8),
            "residue_index": np.arange(len(sequence), dtype=np.int32), "segment_index": segments,
            "pos": pos, "ca_mask": mask}

def prepare_structures(raw, frame):
    cache = raw / "ca-structures-v1"
    cache.mkdir(exist_ok=True)
    wanted = dict(zip(frame.domain_id, frame.sequence))
    accepted = set()
    rejected = Counter()
    with tarfile.open(raw / "s40.pdb.tgz", "r|gz") as archive:
        for member in archive:
            domain = Path(member.name).name
            if not member.isfile() or domain not in wanted: continue
            if domain in accepted: raise ValueError("duplicate structure in official archive")
            try:
                structure = parse_pdb(archive.extractfile(member).read().decode("ascii"), wanted[domain])
            except ValueError as error:
                rejected[str(error)] += 1
                continue
            np.savez(cache / cache_name(domain), **structure)
            accepted.add(domain)
            if len(accepted) % 5000 == 0: print(f"Parsed {len(accepted)} structures", flush=True)
    rejected["missing_or_rejected_structure"] = len(wanted) - len(accepted)
    (raw / "structure-audit.json").write_text(json.dumps({"accepted": len(accepted), "exclusions": dict(rejected)}, indent=2))
    return frame[frame.domain_id.isin(accepted)].reset_index(drop=True), dict(rejected)

def publish_structures(frame, raw, public, split):
    import pandas as pd
    features = []
    with zipfile.ZipFile(public / f"{split}_structures.zip", "w", compression=zipfile.ZIP_DEFLATED, compresslevel=6) as archive:
        for row in frame.itertuples():
            with np.load(raw / "ca-structures-v1" / cache_name(row.domain_id), allow_pickle=False) as loaded:
                structure = {k: loaded[k] for k in loaded.files}
            buffer = io.BytesIO()
            np.savez(buffer, **structure)
            info = zipfile.ZipInfo(f"{row.id}.npz", date_time=(2026, 1, 1, 0, 0, 0))
            info.compress_type = zipfile.ZIP_DEFLATED
            archive.writestr(info, buffer.getvalue())
            features.append([row.id, *structure_features(structure)])
    pd.DataFrame(features, columns=["id", *FEATURE_NAMES]).to_csv(public / f"{split}_features.csv", index=False)
