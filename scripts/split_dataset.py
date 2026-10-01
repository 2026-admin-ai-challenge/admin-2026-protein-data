"""Deterministic per-architecture group subset split, with no H-superfamily overlap."""
import numpy as np
import pandas as pd
SEED = 42

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
