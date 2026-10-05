from pathlib import Path
import pandas as pd
from scripts.prepare_dataset import clean,read_fasta,load_quality_exclusions
from scripts.verify_dataset import verify,ROOT
from scripts.split_dataset import group_split,public_private_split

def test_real_cath_dataset_and_no_leakage(): verify()
def test_actual_group_split_reproducible():
    mapping=pd.read_csv(ROOT/"data/private/id_mapping.csv",dtype=str)
    train=pd.read_csv(ROOT/"data/public/train.csv",dtype=str)
    test=pd.read_csv(ROOT/"data/private/test.csv",dtype=str)
    labels=pd.read_csv(ROOT/"data/private/labels.csv",dtype=str)
    full=pd.concat([train,test.merge(labels[["id","label"]],on="id")],ignore_index=True)
    subset=full.merge(mapping,on="id").rename(columns={"label":"architecture_label"})
    a,b=group_split(subset);c,d=group_split(subset)
    assert list(b.id)==list(d.id)
    assert not set(a.homologous_superfamily)&set(b.homologous_superfamily)
    mask=public_private_split(b)
    assert set(b[mask=="public"].id).isdisjoint(set(b[mask=="private"].id))
    assert set(mask)=={"public","private"}
def test_cleaning_excludes_ambiguous_duplicates_and_lengths():
    # Small unit fixture only; competition data is exclusively official CATH.
    seq=pd.DataFrame({"domain_id":["a","b","c","d","e"],"sequence":["A"*40,"A"*40,"X"*40,"A"*39,"C"*1201]})
    meta=pd.DataFrame({"domain_id":seq.domain_id,"class":"1","architecture":"10","topology":"8","superfamily":"2"})
    result=clean(seq,meta)
    assert len(result)==1 and result.iloc[0].architecture_label=="1.10"
    assert result.iloc[0].homologous_superfamily=="1.10.8.2"


def test_curated_source_exclusions_match_quality_reviews():
    reviewed=pd.read_csv(ROOT/"docs/quality/day2-abnormal-samples.csv",dtype=str)
    exclusions=pd.read_csv(ROOT/"data/private/quality_exclusions.csv",dtype=str)
    bad=set(reviewed.loc[reviewed["판정"]=="오류 (원본 구조)","샘플 ID"])
    day3={
        "TRAIN_006196", "TRAIN_003522", "TRAIN_019154", "TEST_001746",
        "TEST_000447", "TEST_001110", "TEST_002261", "TEST_002855",
        "TEST_003365", "TEST_003807", "TEST_003982", "TEST_004963",
    }
    assert len(bad)==21 and len(exclusions)==33
    assert set(exclusions.reference_sample_id)==bad|day3
    assert exclusions.domain_id.is_unique
    assert exclusions.reason.value_counts().to_dict()=={
        "A-02":2, "A-05":3, "A-06":16, "X-01":1, "X-02":3, "P-30":8,
    }
    assert load_quality_exclusions()==set(exclusions.domain_id)
    mapping=pd.read_csv(ROOT/"data/private/id_mapping.csv",dtype=str)
    assert not set(exclusions.domain_id)&set(mapping.domain_id)
