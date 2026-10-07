"""Deterministic per-architecture group subset split, with no H-superfamily overlap."""
import numpy as np
import pandas as pd
SEED = 42

ASSIGNMENT_COLUMNS = ["domain_id", "homologous_superfamily", "architecture_label", "id", "split", "partition", "fold"]

def load_split_assignments(path):
    """Load the organizer-only, immutable assignments, including retired IDs."""
    assignments = pd.read_csv(path, dtype=str, keep_default_na=False)
    if list(assignments.columns) != ASSIGNMENT_COLUMNS or assignments.empty:
        raise ValueError("Invalid split assignment schema")
    if (assignments.eq("").any().any() or not assignments.domain_id.is_unique
            or not assignments.id.is_unique or not assignments.split.isin(["train", "test"]).all()):
        raise ValueError("Invalid or duplicate split assignments")
    train = assignments[assignments.split == "train"]
    test = assignments[assignments.split == "test"]
    if (not train.id.str.fullmatch(r"TRAIN_\d{6}").all()
            or not test.id.str.fullmatch(r"TEST_\d{6}").all()
            or not train.partition.eq("-").all() or not train.fold.isin(["fit", "validation"]).all()
            or not test.fold.eq("-").all() or not test.partition.isin(["public", "private"]).all()):
        raise ValueError("Invalid split, partition or fold assignments")
    if assignments.groupby("homologous_superfamily").split.nunique().max() != 1:
        raise ValueError("H-superfamily crosses train/test in split assignments")
    if train.groupby("homologous_superfamily").fold.nunique().max() != 1:
        raise ValueError("H-superfamily crosses fit/validation in split assignments")
    if assignments.groupby("homologous_superfamily").architecture_label.nunique().max() != 1:
        raise ValueError("Inconsistent labels in split assignments")
    return assignments

def apply_fixed_assignments(frame, assignments):
    """Filtering may retire samples; it must never move or renumber survivors."""
    if not frame.domain_id.is_unique:
        raise ValueError("Duplicate source domains")
    unknown = set(frame.domain_id) - set(assignments.domain_id)
    if unknown:
        raise ValueError(f"Unassigned source domains: {sorted(unknown)}; review the frozen split explicitly")
    source = frame.set_index("domain_id")
    retained = assignments[assignments.domain_id.isin(source.index)]
    for col in ["homologous_superfamily", "architecture_label"]:
        if not (source.loc[retained.domain_id, col].to_numpy() == retained[col].to_numpy()).all():
            raise ValueError(f"Source differs from frozen {col}")
    ordered = source.loc[retained.domain_id].reset_index()
    for col in ["id", "split", "partition", "fold"]:
        ordered[col] = retained[col].to_numpy()
    train = ordered[ordered.split == "train"].copy()
    test = ordered[ordered.split == "test"].copy()
    labels = set(assignments.architecture_label)
    if (set(train.architecture_label) != labels or set(test.architecture_label) != labels
            or set(test[test.partition == "public"].architecture_label) != labels
            or set(test[test.partition == "private"].architecture_label) != labels
            or set(train[train.fold == "fit"].architecture_label) != labels
            or set(train[train.fold == "validation"].architecture_label) != labels):
        raise ValueError("Exclusions emptied a class or a frozen partition/fold")
    if train.groupby("architecture_label").size().min() < 20 or test.groupby("architecture_label").size().min() < 10:
        raise ValueError("Exclusions violate minimum train/test class counts")
    for col in ["domain_id", "sequence", "homologous_superfamily"]:
        if set(train[col]) & set(test[col]):
            raise ValueError(f"Leakage in {col}")
    return train, test

def group_split(df, min_train_groups=1):
    test_indices = []
    for label, part in df.groupby("architecture_label", sort=True):
        rng = np.random.default_rng(SEED)
        groups = part.groupby("homologous_superfamily").size()
        if len(groups) < 2: raise ValueError(f"{label}: fewer than two H groups")
        # Subset-sum reaches the closest feasible 20% while keeping entire H groups.
        target = round(len(part) * .2)
        items = list(groups.items()); rng.shuffle(items)
        reachable = {0: ()}
        cap = min(len(part)-20, max(target*2, target+50))
        for group, size in items:
            for total, chosen in list(reachable.items()):
                new = total + int(size)
                if new <= cap and new not in reachable and len(chosen) + 1 <= len(groups) - min_train_groups: reachable[new] = (*chosen, group)
        candidates = [n for n in reachable if n >= 10 and len(part)-n >= 20]
        if not candidates: raise ValueError(f"{label}: no feasible held-out groups")
        best = min(candidates, key=lambda n: (abs(n-target), n))
        test_indices.extend(part[part.homologous_superfamily.isin(reachable[best])].index)
    test = df.loc[test_indices].copy()
    train = df.drop(test_indices).copy()
    for col in ["domain_id", "sequence", "homologous_superfamily"]:
        if set(train[col]) & set(test[col]): raise ValueError(f"Leakage in {col}")
    return train, test

def public_private_split(test):
    rng = np.random.default_rng(SEED)
    public = []
    for _, part in test.groupby("architecture_label", sort=True):
        indices = part.index.to_numpy().copy(); rng.shuffle(indices)
        n = max(1, min(len(indices)-1, round(len(indices)*.3)))
        public.extend(indices[:n])
    mask = pd.Series("private", index=test.index)
    mask.loc[public] = "public"
    return mask
