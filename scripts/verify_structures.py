"""Audit every published structure, feature table and participant starter-kit member."""
import io
import zipfile
import numpy as np
import pandas as pd
try:
    from .structure_dataset import STRUCTURE_KEYS
    from .structure_features import AMINO_ACIDS, FEATURE_NAMES, structure_features
except ImportError:
    from structure_dataset import STRUCTURE_KEYS
    from structure_features import AMINO_ACIDS, FEATURE_NAMES, structure_features


def verify_structures(root):
    public = root / "data/public"
    train = pd.read_csv(public / "train.csv", dtype=str)
    mapping = pd.read_csv(root / "data/private/id_mapping.csv", dtype=str)
    folds = pd.read_csv(public / "validation_split.csv", dtype=str)
    assert list(folds.columns) == ["id", "fold"] and folds.id.is_unique
    assert set(folds.id) == set(train.id) and set(folds.fold) == {"fit", "validation"}
    grouped = folds.merge(mapping, on="id", validate="one_to_one").merge(train[["id", "label"]], on="id")
    fit, validation = grouped[grouped.fold == "fit"], grouped[grouped.fold == "validation"]
    assert not set(fit.homologous_superfamily) & set(validation.homologous_superfamily)
    assert set(fit.label) == set(validation.label) == set(train.label)
    for split in ["train", "test"]:
        directory = public if split == "train" else root / "data/private"
        frame = pd.read_csv(directory / f"{split}.csv", dtype=str)
        features = pd.read_csv(directory / f"{split}_features.csv").set_index("id")
        assert features.index.is_unique and set(features.index) == set(frame.id)
        assert list(features.columns) == FEATURE_NAMES
        assert np.isfinite(features.to_numpy()).all()
        with zipfile.ZipFile(directory / f"{split}_structures.zip") as archive:
            assert len(archive.namelist()) == len(frame)
            assert set(archive.namelist()) == {f"{i}.npz" for i in frame.id}
            for index, row in enumerate(frame.itertuples()):
                with np.load(io.BytesIO(archive.read(f"{row.id}.npz")), allow_pickle=False) as f:
                    assert set(f.files) == STRUCTURE_KEYS
                    g = {k: f[k] for k in f.files}
                n = len(row.sequence)
                assert ''.join(AMINO_ACIDS[int(a)] for a in g['residue_type']) == row.sequence
                assert np.array_equal(g['residue_index'], np.arange(n))
                assert g['pos'].shape == (n, 3) and g['pos'].dtype == np.float32
                mask = g['ca_mask']
                assert mask.shape == (n,) and mask.dtype == bool and mask.sum() >= 40 and mask.mean() >= .95
                assert np.isfinite(g['pos']).all() and np.all(g['pos'][~mask] == 0)
                assert np.allclose(g['pos'][mask].mean(0), 0, atol=1e-3)
                segments = g['segment_index']
                assert segments.shape == (n,) and segments[0] == 0
                assert set(np.diff(segments).tolist()) <= {0, 1}
                continuous = np.diff(segments) == 0
                assert (mask[:-1][continuous] & mask[1:][continuous]).all()
                assert (np.linalg.norm(np.diff(g['pos'],axis=0)[continuous],axis=1) <= 4.5 + 1e-5).all()
                assert np.allclose(features.loc[row.id].to_numpy(), structure_features(g), rtol=1e-6, atol=1e-7)
                if index and index % 5000 == 0: print(f"Verified {split}: {index} structures", flush=True)
    example = pd.read_csv(public / 'example_input.csv', dtype=str)
    example_features = pd.read_csv(public / 'example_features.csv').set_index('id')
    assert set(example_features.index) == set(example.id)
    with zipfile.ZipFile(public / 'example_structures.zip') as archive:
        assert set(archive.namelist()) == {f'{value}.npz' for value in example.id}
        with zipfile.ZipFile(public / 'train_structures.zip') as train_archive:
            for value in example.id:
                assert archive.read(f'{value}.npz') == train_archive.read(f'{value}.npz')
    allowed = {'train.csv','train_features.csv','validation_split.csv',
               'example_input.csv','example_features.csv','example_output.csv','example_structures.zip',
               'baseline.py','structure_features.py','baseline.ipynb','README.md','structure-format.md','requirements.txt'}
    with zipfile.ZipFile(public / "starter_kit.zip") as archive:
        assert len(archive.namelist()) == len(allowed) and set(archive.namelist()) == allowed
        for name in allowed:
            if name.endswith(('.csv', '.zip')): assert archive.read(name) == (public / name).read_bytes()
    code_only = {'baseline.py','structure_features.py','baseline.ipynb','README.md','structure-format.md','requirements.txt'}
    with zipfile.ZipFile(public / "baseline_code.zip") as archive:
        assert len(archive.namelist()) == len(code_only) and set(archive.namelist()) == code_only
        import json
        notebook = json.loads(archive.read('baseline.ipynb'))
        assert all(not cell.get('outputs') for cell in notebook['cells'])
    print("PASS: all coordinate/sequence mappings, masks, segments, invariant features, H-group validation and starter allowlist")
