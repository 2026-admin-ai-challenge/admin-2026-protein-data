import json,hashlib
from pathlib import Path
import pandas as pd
ROOT=Path(__file__).resolve().parents[1]
def verify(root=ROOT):
    pub=root/"data/public"; priv=root/"data/private"
    train=pd.read_csv(pub/"train.csv",dtype=str);test=pd.read_csv(priv/"test.csv",dtype=str)
    labels=pd.read_csv(priv/"labels.csv",dtype=str);mapping=pd.read_csv(priv/"id_mapping.csv",dtype=str)
    meta=json.loads((pub/"metadata.json").read_text())
    assert meta["schema_version"] == 2
    for filename,info in meta["files"].items():
        with (pub/filename).open("rb") as f:
            assert hashlib.file_digest(f,"sha256").hexdigest()==info["sha256"]
    assert list(train.columns)==["id","sequence","label"]
    assert list(test.columns)==["id","sequence"]
    assert not any((pub/name).exists() for name in ["test.csv","test_features.csv","test_structures.zip","sample_submission.csv"])
    assert not set(train.id)&set(test.id)
    assert not set(train.sequence)&set(test.sequence)
    assert train.sequence.is_unique and test.sequence.is_unique
    assert mapping.id.is_unique and mapping.domain_id.is_unique
    a=mapping[mapping.id.isin(train.id)];b=mapping[mapping.id.isin(test.id)]
    assert not set(a.domain_id)&set(b.domain_id)
    assert not set(a.homologous_superfamily)&set(b.homologous_superfamily)
    assert labels.id.is_unique and set(labels.id)==set(test.id)
    public=set(labels[labels.partition=="public"].id);private=set(labels[labels.partition=="private"].id)
    assert public and private and not public&private and public|private==set(test.id)
    assert set(train.label)==set(labels.label)==set(labels[labels.partition=="public"].label)==set(labels[labels.partition=="private"].label)
    assert not train.isna().any().any() and not test.isna().any().any()
    example=pd.read_csv(pub/"example_input.csv",dtype=str)
    example_output=pd.read_csv(pub/"example_output.csv",dtype=str)
    assert list(example.columns)==["id","sequence"]
    assert list(example_output.columns)==["id","label"]
    assert set(example.id).issubset(set(train.id)) and not set(example.id)&set(test.id)
    assert example.merge(train,on=["id","sequence"])["id"].tolist()==example.id.tolist()
    assert example_output.merge(train,on=["id","label"])["id"].tolist()==example.id.tolist()
    private_manifest=json.loads((priv/"manifest.json").read_text())
    for filename,info in private_manifest["files"].items():
        with (priv/filename).open("rb") as f:
            assert hashlib.file_digest(f,"sha256").hexdigest()==info["sha256"]
    stats=meta["stats"]
    assert len(train)==stats["train"] and len(test)==stats["test"]
    assert stats["train"]+stats["test"]==stats["total"]
    assert train.label.nunique()==stats["classes"]
    assert pd.concat([train.label,labels.label]).value_counts().to_dict()==stats["samples_per_class"]
    checksums_path=root/"data/DATASET_CHECKSUMS.json"
    if checksums_path.exists():
        for relative,info in json.loads(checksums_path.read_text()).items():
            path=root/relative
            assert path.stat().st_size==info["bytes"],relative
            with path.open("rb") as f:
                assert hashlib.file_digest(f,"sha256").hexdigest()==info["sha256"],relative
    version_path=root/"data/DATA_VERSION.json"
    if version_path.exists():
        version=json.loads(version_path.read_text())
        assert version["counts"]=={"train":len(train),"test":len(test),"public":len(public),"private":len(private),"classes":train.label.nunique()}
        assert version["metadata_sha256"]==hashlib.sha256((pub/"metadata.json").read_bytes()).hexdigest()
        assert version["checksums_sha256"]==hashlib.sha256(checksums_path.read_bytes()).hexdigest()
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
