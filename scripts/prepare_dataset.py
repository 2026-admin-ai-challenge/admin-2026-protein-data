"""Reproducible CATH S40 cleaning and homology-aware dataset publication."""
import json, re, hashlib, zipfile
from pathlib import Path
import pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
try:
    from .download_cath import download, ROOT
    from .split_dataset import group_split, public_private_split, SEED
except ImportError:
    from download_cath import download, ROOT
    from split_dataset import group_split, public_private_split, SEED
try:
    from .structure_dataset import prepare_structures, publish_structures
except ImportError:
    from structure_dataset import prepare_structures, publish_structures
AA = set("ACDEFGHIKLMNPQRSTVWY")

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

def prepare(root=ROOT):
    raw=root/"data/raw"; public=root/"data/public"; private=root/"data/private"
    public.mkdir(parents=True,exist_ok=True); private.mkdir(parents=True,exist_ok=True)
    if any(p.name != ".gitkeep" for p in public.iterdir()) or any(p.name != ".gitignore" for p in private.iterdir()):
        raise RuntimeError("Output directory is not empty. Use a fresh staging root; do not mix old public test files with a new dataset.")
    manifest=download(root)
    rows=[line.split()[:5] for line in (raw/"domains.txt").read_text().splitlines() if line.strip() and not line.startswith("#")]
    metadata=pd.DataFrame(rows,columns=["domain_id","class","architecture","topology","superfamily"])
    df=clean(read_fasta(raw/"s40.atom.fa"),metadata)
    df,structure_exclusions=prepare_structures(raw,df)
    counts=df.groupby("architecture_label").size().sort_values(ascending=False)
    eligible=[]; rejected={}
    for label,n in counts.items():
        if n<50: rejected[label]="fewer than 50 cleaned samples"; continue
        try:
            fit,_=group_split(df[df.architecture_label==label],min_train_groups=2)
            group_split(fit)
        except ValueError as e: rejected[label]=str(e); continue
        eligible.append(label)
    if len(eligible)<15: raise ValueError(f"Only {len(eligible)} eligible classes; review class-selection policy")
    selected=eligible[:20]
    df=df[df.architecture_label.isin(selected)].copy()
    train,test=group_split(df,min_train_groups=2)
    train=train.sample(frac=1,random_state=SEED).copy()
    test=test.sample(frac=1,random_state=SEED).copy()
    train["id"]=[f"TRAIN_{i:06d}" for i in range(1,len(train)+1)]
    test["id"]=[f"TEST_{i:06d}" for i in range(1,len(test)+1)]
    test["partition"]=public_private_split(test)
    train.rename(columns={"architecture_label":"label"})[["id","sequence","label"]].to_csv(public/"train.csv",index=False)
    # Hidden evaluation inputs and answers belong together under organizer-only storage.
    test[["id","sequence"]].to_csv(private/"test.csv",index=False)
    test.rename(columns={"architecture_label":"label"})[["id","label","partition"]].to_csv(private/"labels.csv",index=False)
    pd.concat([train,test])[["id","domain_id","homologous_superfamily"]].to_csv(private/"id_mapping.csv",index=False)
    publish_structures(train,raw,public,"train")
    publish_structures(test,raw,private,"test")
    # Participant validation fold is opaque, training-only, and preserves complete H groups.
    _,validation=group_split(train.reset_index(drop=True))
    validation_ids=set(validation.id)
    pd.DataFrame({"id":train.id,"fold":["validation" if i in validation_ids else "fit" for i in train.id]}).to_csv(public/"validation_split.csv",index=False)
    make_example(public)
    make_starter(public)
    lengths=df.sequence_length
    stats={"total":len(df),"classes":len(selected),"train":len(train),"test":len(test),"samples_per_class":{k:int(v) for k,v in df.architecture_label.value_counts().items()},"sequence_length":{"mean":float(lengths.mean()),"median":float(lengths.median()),"min":int(lengths.min()),"max":int(lengths.max())}}
    result={"schema_version":2,"input":"sequence + observed C-alpha coordinates","structure":{"min_ca_coverage":0.95,"residue_sequence":"ATOM domain sequence; exact PDB residue match","exclusions":structure_exclusions},"source":"CATH","version":"4.4","subset":"S40","target":"architecture","seed":SEED,"labels":sorted(selected),"split":{"train":.8,"test":.2,"public_test":.3,"private_test":.7},"actual_train_fraction":len(train)/len(df),"stats":stats,"sources":manifest,"excluded_architectures":rejected,"policy":"Exact ATOM sequence/structure correspondence, >=95% CA coverage, >=40 observed CA. Remove all non-standard amino acids; >=50 samples and feasible H-group split. Up to top 20 eligible classes.","files":{}}
    for name in ["train.csv","train_features.csv","validation_split.csv","example_input.csv","example_features.csv","example_output.csv"]:
        p=public/name; frame=pd.read_csv(p,dtype=str)
        result["files"][name]={"rows":len(frame),"columns":list(frame.columns),"bytes":p.stat().st_size,"sha256":hashlib.sha256(p.read_bytes()).hexdigest()}
    for name in ["train_structures.zip","example_structures.zip","starter_kit.zip","baseline_code.zip"]:
        p=public/name
        with p.open("rb") as f: digest=hashlib.file_digest(f,"sha256").hexdigest()
        result["files"][name]={"bytes":p.stat().st_size,"sha256":digest,"description":"Participant archive; anonymized data only"}
    (public/"metadata.json").write_text(json.dumps(result,indent=2))
    private_files={}
    for name in ["test.csv","test_features.csv","test_structures.zip","labels.csv","id_mapping.csv"]:
        p=private/name
        with p.open("rb") as f: digest=hashlib.file_digest(f,"sha256").hexdigest()
        private_files[name]={"bytes":p.stat().st_size,"sha256":digest}
    (private/"manifest.json").write_text(json.dumps({"schema_version":2,"files":private_files},indent=2))
    for filename,values,kind in [("class_distribution.png",df.architecture_label.value_counts(),"bar"),("sequence_length_distribution.png",lengths,"hist")]:
        fig,ax=plt.subplots(figsize=(10,4));values.plot(kind=kind,ax=ax,color="#5156df")
        ax.set_title(filename.replace("_"," ").replace(".png",""));fig.tight_layout();fig.savefig(public/filename,dpi=150);plt.close(fig)
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
                target.writestr(name,source.read(name))
def make_starter(public):
    # Public before the event: code/docs ONLY. Never add data-dependent files here.
    with zipfile.ZipFile(public/"baseline_code.zip","w",compression=zipfile.ZIP_DEFLATED) as archive:
        for source,name in [(ROOT/"scripts/baseline.py","baseline.py"),(ROOT/"scripts/structure_features.py","structure_features.py"),(ROOT/"notebooks/baseline.ipynb","baseline.ipynb"),(ROOT/"docs/baseline-preview.md","README.md"),(ROOT/"docs/structure-format.md","structure-format.md"),(ROOT/"notebooks/requirements.txt","requirements.txt")]:
            archive.write(source,name)
    # Event-only allowlist: never package raw sources, private labels, or generator code.
    with zipfile.ZipFile(public/"starter_kit.zip","w",compression=zipfile.ZIP_DEFLATED) as archive:
        for name in ["train.csv","train_features.csv","validation_split.csv","example_input.csv","example_features.csv","example_output.csv","example_structures.zip"]:
            archive.write(public/name,name)
        for source,name in [(ROOT/"scripts/baseline.py","baseline.py"),(ROOT/"scripts/structure_features.py","structure_features.py"),(ROOT/"notebooks/baseline.ipynb","baseline.ipynb"),(ROOT/"docs/starter-guide.md","README.md"),(ROOT/"docs/structure-format.md","structure-format.md"),(ROOT/"notebooks/requirements.txt","requirements.txt")]:
            archive.write(source,name)

if __name__=="__main__":
    import argparse
    parser=argparse.ArgumentParser()
    parser.add_argument("--root",type=Path,default=ROOT,help="Separate staging directory for a new, unpublished dataset")
    prepare(parser.parse_args().root)
