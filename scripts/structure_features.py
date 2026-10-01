"""Label-free, rotation/translation invariant features from public C-alpha coordinates."""
import numpy as np
from scipy.spatial.distance import pdist

AMINO_ACIDS = "ACDEFGHIKLMNPQRSTVWY"
FEATURE_NAMES = ([f"aa_{aa}" for aa in AMINO_ACIDS] +
    ["log_length", "ca_coverage", "radius_gyration", "shape_1", "shape_2", "shape_3",
     "distance_mean", "distance_std", "distance_q25", "distance_q50", "distance_q75"])

def structure_features(structure):
    aa = structure["residue_type"]
    mask = structure["ca_mask"]
    pos = structure["pos"][mask].astype(np.float64)
    centered = pos - pos.mean(axis=0)
    eigenvalues = np.maximum(np.linalg.eigvalsh(centered.T @ centered / len(pos)), 0)[::-1]
    shape = eigenvalues / max(eigenvalues.sum(), 1e-12)
    distances = pdist(pos)
    return np.asarray([
        *[np.mean(aa == i) for i in range(20)], np.log1p(len(aa)), np.mean(mask),
        np.sqrt(eigenvalues.sum()), *shape,
        distances.mean(), distances.std(), *np.quantile(distances, [.25, .5, .75]),
    ], dtype=np.float64)
