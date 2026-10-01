from pathlib import Path
import pandas as pd
from scripts.prepare_dataset import clean,read_fasta
from scripts.verify_dataset import verify,ROOT
from scripts.split_dataset import group_split,public_private_split

def test_real_cath_dataset_and_no_leakage(): verify()
def test_actual_group_split_reproducible():
    mapping=pd.read_csv(ROOT/"data/private/id_mapping.csv",dtype=str)
    train=pd.read_csv(ROOT/"data/public/train.csv",dtype=str)
    test=pd.read_csv(ROOT/"data/public/test.csv",dtype=str)
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
