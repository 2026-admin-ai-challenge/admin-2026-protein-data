"""Reproducible CATH S40 cleaning and homology-aware dataset publication."""
import json, re, hashlib, zipfile
from pathlib import Path
import pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
try:
    from .download_cath import download, ROOT
    from .split_dataset import load_split_assignments, apply_fixed_assignments, SEED
except ImportError:
    from download_cath import download, ROOT
    from split_dataset import load_split_assignments, apply_fixed_assignments, SEED
try:
    from .structure_dataset import prepare_structures, publish_structures
except ImportError:
    from structure_dataset import prepare_structures, publish_structures
AA = set("ACDEFGHIKLMNPQRSTVWY")

def public_distribution_stats(train):
    """Only public training rows may contribute to published distributions."""
    lengths = train.sequence.str.len()
    return {"distribution_scope": "train",
            "samples_per_class": {k: int(v) for k, v in train.architecture_label.value_counts().items()},
            "sequence_length": {"mean": float(lengths.mean()), "median": float(lengths.median()),
                                "min": int(lengths.min()), "max": int(lengths.max())}}

def write_public_distribution_plots(train, public):
    lengths = train.sequence.str.len()
    for filename, values, kind in [("class_distribution.png", train.architecture_label.value_counts(), "bar"),
                                  ("sequence_length_distribution.png", lengths, "hist")]:
        fig, ax = plt.subplots(figsize=(10, 4))
        values.plot(kind=kind, ax=ax, color="#5156df")
        ax.set_title(filename.replace("_", " ").replace(".png", "") + " (training only)")
        fig.tight_layout(); fig.savefig(public / filename, dpi=150); plt.close(fig)

def read_fasta(path):
    records=[]; header=None; sequence=[]
    def add():
        if header is not None:
            # Official headers: >cath|4_4_0|1abcA01/segments (or >1abcA01).
            hits=re.findall(r"(?<![A-Za-z0-9])([0-9][A-Za-z0-9]{3}[A-Za-z0-9][0-9]{2})(?=[/\s|]|$)", header)
            if len(hits)!=1: raise ValueError(f"Unrecognized domain header: {header}")
            records.append((hits[0], "".join(sequence).upper()))
    for line in Path(path).read_text().splitlines():
        if line.startswith(">"):
            add(); header=line[1:]; sequence=[]
        else: sequence.append(line.strip())
    add()
    return pd.DataFrame(records, columns=["domain_id","sequence"])

def clean(seqs, metadata):
    df=seqs.merge(metadata, on="domain_id", validate="many_to_one")
    df["sequence_length"]=df.sequence.str.len()
    df=df[df.sequence_length.between(40,1200) & df.sequence.map(lambda s:set(s)<=AA)]
    df=df.sort_values("domain_id").drop_duplicates("domain_id").drop_duplicates("sequence")
    df["architecture_label"]=df["class"]+"."+df.architecture
    df["homologous_superfamily"]=df[["class","architecture","topology","superfamily"]].agg(".".join,axis=1)
    return df.reset_index(drop=True)

def load_quality_exclusions(path=ROOT / "data/private/quality_exclusions.csv"):
    """Load manually reviewed source-domain exclusions from the organizer file."""
    exclusions = pd.read_csv(path, dtype=str)
    if list(exclusions.columns) != ["domain_id", "reference_sample_id", "reason"]:
        raise ValueError("Invalid quality exclusion columns")
    if (exclusions.isna().any().any() or not exclusions.domain_id.is_unique
            or not exclusions.reference_sample_id.is_unique
            or not exclusions.reference_sample_id.str.fullmatch(r"(?:TRAIN|TEST)_\d{6}").all()):
        raise ValueError("Invalid or duplicate quality exclusions")
    if not set(exclusions.reason) <= {"A-02", "A-05", "A-06", "X-01", "X-02", "P-30"}:
        raise ValueError("Unexpected quality exclusion reason")
    return set(exclusions.domain_id)

def prepare(root=ROOT, assignments_path=ROOT / "data/private/split_assignments.csv"):
    raw=root/"data/raw"; public=root/"data/public"; private=root/"data/private"
    public.mkdir(parents=True,exist_ok=True); private.mkdir(parents=True,exist_ok=True)
    if any(p.name != ".gitkeep" for p in public.iterdir()) or any(p.name != ".gitignore" for p in private.iterdir()):
        raise RuntimeError("Output directory is not empty. Use a fresh staging root; do not mix old public test files with a new dataset.")
    assignments_path = Path(assignments_path)
    assignments = load_split_assignments(assignments_path)
    split_reference = json.loads(assignments_path.with_suffix(".json").read_text())
    assignment_digest = hashlib.sha256(assignments_path.read_bytes()).hexdigest()
    if assignment_digest != split_reference["sha256"] or len(assignments) != split_reference["rows"]:
        raise ValueError("Frozen split reference hash/count mismatch")
    manifest=download(root)
    if {name: info["sha256"] for name, info in manifest.items()} != split_reference["source_sha256"]:
        raise ValueError("CATH sources differ from the frozen reference version")
    rows=[line.split()[:5] for line in (raw/"domains.txt").read_text().splitlines() if line.strip() and not line.startswith("#")]
    metadata=pd.DataFrame(rows,columns=["domain_id","class","architecture","topology","superfamily"])
    df=clean(read_fasta(raw/"s40.atom.fa"),metadata)
    curated_exclusions=load_quality_exclusions()
    df,structure_exclusions=prepare_structures(raw,df,curated_exclusions)
    selected=sorted(assignments.architecture_label.unique())
    rejected={label: "outside frozen reference classes" for label in sorted(set(df.architecture_label) - set(selected))}
    df=df[df.architecture_label.isin(selected)].copy()
    train,test=apply_fixed_assignments(df,assignments)
    train.rename(columns={"architecture_label":"label"})[["id","sequence","label"]].to_csv(public/"train.csv",index=False)
    # Hidden evaluation inputs and answers belong together under organizer-only storage.
    test[["id","sequence"]].to_csv(private/"test.csv",index=False)
    test.rename(columns={"architecture_label":"label"})[["id","label","partition"]].to_csv(private/"labels.csv",index=False)
    pd.concat([train,test])[["id","domain_id","homologous_superfamily"]].to_csv(private/"id_mapping.csv",index=False)
    publish_structures(train,raw,public,"train")
    publish_structures(test,raw,private,"test")
    # Frozen folds preserve H groups and survive exclusions without reshuffling.
    train[["id", "fold"]].to_csv(public/"validation_split.csv",index=False)
    make_example(public)
    make_starter(public)
    stats={"total":len(df),"classes":len(selected),"train":len(train),"test":len(test),**public_distribution_stats(train)}
    result={"schema_version":2,"input":"sequence + observed C-alpha coordinates","structure":{"min_ca_coverage":0.95,"min_nonlocal_ca_distance":3.0,"residue_sequence":"ATOM domain sequence; exact PDB residue match","curated_source_exclusions":len(curated_exclusions),"curated_exclusions_sha256":hashlib.sha256((ROOT/"data/private/quality_exclusions.csv").read_bytes()).hexdigest(),"exclusions":structure_exclusions},"source":"CATH","version":"4.4","subset":"S40","target":"architecture","seed":SEED,"labels":sorted(selected),"split":{"train":.8,"test":.2,"public_test":.3,"private_test":.7},"actual_train_fraction":len(train)/len(df),"stats":stats,"sources":manifest,"excluded_architectures":rejected,"policy":f"Exact ATOM sequence/structure correspondence, >=95% CA coverage, >=40 observed CA, no nonlocal CA clashes <3.0 A, and {len(curated_exclusions)} curated source exclusions. Remove all non-standard amino acids; >=50 samples and feasible H-group split. Up to top 20 eligible classes.","files":{}}
    result["split_policy"] = {"mode": "frozen", "reference_commit": split_reference["reference_commit"],
                              "assignments_sha256": assignment_digest, "retired_ids_are_not_reused": True}
    result["structure"]["reject_adjacent_altloc_mismatch"] = True
    result["policy"] = f"Exact ATOM sequence/structure correspondence, >=95% CA coverage, >=40 observed CA, no nonlocal CA clashes <3.0 A, coherent alternate-location selection, and {len(curated_exclusions)} curated source exclusions. Frozen reference classes, IDs, H-group train/test assignments, Public/Private partitions and fit/validation folds; exclusions never rebalance splits."
    for name in ["train.csv","train_features.csv","validation_split.csv","example_input.csv","example_features.csv","example_output.csv"]:
        p=public/name; frame=pd.read_csv(p,dtype=str)
        result["files"][name]={"rows":len(frame),"columns":list(frame.columns),"bytes":p.stat().st_size,"sha256":hashlib.sha256(p.read_bytes()).hexdigest()}
    for name in ["train_structures.zip","example_structures.zip","starter_kit.zip","baseline_code.zip"]:
        p=public/name
        with p.open("rb") as f: digest=hashlib.file_digest(f,"sha256").hexdigest()
        result["files"][name]={"bytes":p.stat().st_size,"sha256":digest,"description":"Participant archive; anonymized data only"}
    (public/"metadata.json").write_text(json.dumps(result,indent=2))
    # Organizer policy files must not enter participant archives.
    (private/"split_assignments.csv").write_bytes(assignments_path.read_bytes())
    (private/"split_assignments.json").write_bytes(assignments_path.with_suffix(".json").read_bytes())
    (private/"quality_exclusions.csv").write_bytes((ROOT/"data/private/quality_exclusions.csv").read_bytes())
    (private/"structure_rejections.csv").write_bytes((raw/"structure-rejections.csv").read_bytes())
    private_files={}
    for name in ["test.csv","test_features.csv","test_structures.zip","labels.csv","id_mapping.csv",
                 "split_assignments.csv", "split_assignments.json", "quality_exclusions.csv", "structure_rejections.csv"]:
        p=private/name
        with p.open("rb") as f: digest=hashlib.file_digest(f,"sha256").hexdigest()
        private_files[name]={"bytes":p.stat().st_size,"sha256":digest}
    (private/"manifest.json").write_text(json.dumps({"schema_version":2,"files":private_files},indent=2))
    write_public_distribution_plots(train, public)
    try:
        from .make_data_version import write_checksums, main as make_version
    except ImportError:
        from make_data_version import write_checksums, main as make_version
    write_checksums(root)
    make_version(root)
    print(json.dumps(stats,indent=2))
def make_example(public):
    """Give participants a tiny inference example copied from known training rows."""
    train=pd.read_csv(public/"train.csv",dtype=str).head(3)
    train[["id","sequence"]].to_csv(public/"example_input.csv",index=False)
    train[["id","label"]].to_csv(public/"example_output.csv",index=False)
    features=pd.read_csv(public/"train_features.csv").set_index("id")
    features.loc[train.id].reset_index().to_csv(public/"example_features.csv",index=False)
    with zipfile.ZipFile(public/"train_structures.zip") as source:
        with zipfile.ZipFile(public/"example_structures.zip","w",compression=zipfile.ZIP_DEFLATED) as target:
            for sample_id in train.id:
                name=f"{sample_id}.npz"
                info = zipfile.ZipInfo(name, date_time=(2026, 1, 1, 0, 0, 0))
                info.compress_type = zipfile.ZIP_DEFLATED
                target.writestr(info,source.read(name))

def archive_file(archive, source, name):
    """Keep package hashes stable across regeneration times and file mtimes."""
    info = zipfile.ZipInfo(name, date_time=(2026, 1, 1, 0, 0, 0))
    info.compress_type = zipfile.ZIP_DEFLATED
    archive.writestr(info, Path(source).read_bytes())

def make_starter(public):
    # Public before the event: code/docs ONLY. Never add data-dependent files here.
    with zipfile.ZipFile(public/"baseline_code.zip","w",compression=zipfile.ZIP_DEFLATED) as archive:
        for source,name in [(ROOT/"scripts/baseline.py","baseline.py"),(ROOT/"scripts/structure_features.py","structure_features.py"),(ROOT/"notebooks/baseline.ipynb","baseline.ipynb"),(ROOT/"docs/baseline-preview.md","README.md"),(ROOT/"docs/structure-format.md","structure-format.md"),(ROOT/"notebooks/requirements.txt","requirements.txt")]:
            archive_file(archive,source,name)
    # Event-only allowlist: never package raw sources, private labels, or generator code.
    with zipfile.ZipFile(public/"starter_kit.zip","w",compression=zipfile.ZIP_DEFLATED) as archive:
        for name in ["train.csv","train_features.csv","validation_split.csv","example_input.csv","example_features.csv","example_output.csv","example_structures.zip"]:
            archive_file(archive,public/name,name)
        for source,name in [(ROOT/"scripts/baseline.py","baseline.py"),(ROOT/"scripts/structure_features.py","structure_features.py"),(ROOT/"notebooks/baseline.ipynb","baseline.ipynb"),(ROOT/"docs/starter-guide.md","README.md"),(ROOT/"docs/structure-format.md","structure-format.md"),(ROOT/"notebooks/requirements.txt","requirements.txt")]:
            archive_file(archive,source,name)

if __name__=="__main__":
    import argparse
    parser=argparse.ArgumentParser()
    parser.add_argument("--root",type=Path,default=ROOT,help="Separate staging directory for a new, unpublished dataset")
    parser.add_argument("--split-assignments", type=Path, default=ROOT/"data/private/split_assignments.csv")
    args = parser.parse_args()
    prepare(args.root, args.split_assignments)
