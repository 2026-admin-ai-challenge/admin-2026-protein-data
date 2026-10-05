# Participant structure format

Task: given an observed protein-domain sequence and experimentally measured 3D coordinates, classify its CATH Architecture (`C.A`). This is structure classification, not folding prediction. Choose your own features and modeling approach.

Participant files: `train.csv` has `id,sequence,label`; `example_input.csv` has `id,sequence`. Read labels as strings. Hidden `test.csv` is stored on the organizer server only.
The sequence is the official CATH S40 **ATOM** domain sequence, not the full SEQRES sequence. Unobserved residues may be absent from that sequence. Samples whose ordered PDB ATOM residues do not exactly match it are excluded rather than heuristically aligned. Nonstandard residues are excluded; length 40–1200; at least 40 observed Cα atoms and 95% Cα coverage required.

`train_structures.zip` contains one `<anonymous_id>.npz` per training CSV row. `example_structures.zip` holds three copies of known training structures for format checks. The server-only `test_structures.zip` has the same schema. There are no original domain identifiers, labels or raw headers in these files. Load with `allow_pickle=False`.

| Key | Shape / type | Meaning |
|---|---|---|
| residue_type | `[N]` uint8 | Index in `ACDEFGHIKLMNPQRSTVWY` |
| residue_index | `[N]` int32 | 0-based index into supplied domain sequence; NOT original PDB numbering |
| segment_index | `[N]` int32 | Continuous backbone segment; breaks on missing Cα, chain change, PDB residue-number gap or reversal, or Cα step >4.5 Å. Insertion codes do not break a segment (`208 → 209A`, `21A → 22`, and `21 → 21A` are continuous). |
| pos | `[N,3]` float32 | Cα coordinates in Å, centered on observed Cα centroid |
| ca_mask | `[N]` bool | Whether coordinates exist. False rows contain zero placeholders, not physical coordinates |

Where the CATH domain PDB retains multiple Cα locations for a residue, regenerated data uses one preferred conformer across the domain, selected by total Cα occupancy (A wins ties). Blank locations are shared. Some CATH files already contain only one preselected alternate at each residue; missing alternatives cannot be recovered from that file. Structures with nonlocal Cα overlaps below 3.0 Å are excluded, including the reported mixed-location sample. The first model is used. Domain files can join discontinuous sequence segments; consecutive array rows need not be covalently bonded. Respect segment_index and ca_mask.

```python
import io, zipfile, numpy as np
with zipfile.ZipFile('train_structures.zip') as archive:
    with np.load(io.BytesIO(archive.read('TRAIN_000001.npz')), allow_pickle=False) as f:
        structure = {key: f[key] for key in f.files}
valid_positions = structure['pos'][structure['ca_mask']]
print(valid_positions.shape)
```

`structure_features.py` computes 31 basic, rotation/translation-invariant features: 20 residue fractions, log length, Cα coverage, radius of gyration, three normalized covariance eigenvalues, mean/standard deviation/25th/50th/75th percentiles of pairwise Cα distances. No fitted extractor or labels are used. StandardScaler is fitted only on the learning subset in the baseline. These features are only a starting point.

`validation_split.csv` contains TRAIN IDs and `fit`/`validation` only. Complete homologous superfamilies remain together, with no H-group overlap between folds. It is not the hidden test Public/Private partition. Select models on this fold, then retrain on all train rows.

CATH classification codes beyond training labels, original PDB/domain IDs, raw headers and test answers are absent. Anonymization cannot prevent matching public sequences or structures back to CATH. Label lookup, searches to recover labels and manual answers are prohibited; reproducibility review applies.

Source: CATH-Plus v4.4 S40, Orengo Group / UCL, https://www.cathdb.info/ · CC BY 4.0. Changes: standard-residue cleaning, exact structural matching, class selection, centered Cα extraction, anonymous IDs and H-group splits.
