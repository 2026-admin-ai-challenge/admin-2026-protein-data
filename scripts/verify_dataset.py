import json,hashlib
from pathlib import Path
import pandas as pd
ROOT=Path(__file__).resolve().parents[1]
def verify(root=ROOT):
    pub=root/"data/public"; priv=root/"data/private"
    train=pd.read_csv(pub/"train.csv",dtype=str);test=pd.read_csv(pub/"test.csv",dtype=str)
    sample=pd.read_csv(pub/"sample_submission.csv",dtype=str)
    labels=pd.read_csv(priv/"labels.csv",dtype=str);mapping=pd.read_csv(priv/"id_mapping.csv",dtype=str)
    meta=json.loads((pub/"metadata.json").read_text())
    assert meta["schema_version"] == 2
    for filename,info in meta["files"].items():
        with (pub/filename).open("rb") as f:
            assert hashlib.file_digest(f,"sha256").hexdigest()==info["sha256"]
    assert list(train.columns)==["id","sequence","label"]
    assert list(test.columns)==["id","sequence"]
    assert list(sample.columns)==["id","label"]
    assert not set(train.id)&set(test.id)
    assert not set(train.sequence)&set(test.sequence)
    assert train.sequence.is_unique and test.sequence.is_unique
    assert mapping.id.is_unique and mapping.domain_id.is_unique
    a=mapping[mapping.id.isin(train.id)];b=mapping[mapping.id.isin(test.id)]
    assert not set(a.domain_id)&set(b.domain_id)
    assert not set(a.homologous_superfamily)&set(b.homologous_superfamily)
    assert labels.id.is_unique and set(labels.id)==set(test.id)==set(sample.id)
    public=set(labels[labels.partition=="public"].id);private=set(labels[labels.partition=="private"].id)
    assert public and private and not public&private and public|private==set(test.id)
    assert set(train.label)==set(labels.label)==set(labels[labels.partition=="public"].label)==set(labels[labels.partition=="private"].label)
    assert not train.isna().any().any() and not test.isna().any().any()
    try:
        from .verify_structures import verify_structures
    except ImportError:
        from verify_structures import verify_structures
    verify_structures(root)
    print("PASS: schemas, anonymized IDs, class coverage, sequence/domain/H leakage, public/private disjointness")
if __name__=="__main__":
    import argparse
    parser=argparse.ArgumentParser();parser.add_argument("--root",type=Path,default=ROOT)
    verify(parser.parse_args().root)
