from pathlib import Path
import pandas as pd
from scripts.prepare_dataset import clean,read_fasta,load_quality_exclusions,public_distribution_stats,write_public_distribution_plots
from scripts.verify_dataset import verify,ROOT
from scripts.split_dataset import group_split,public_private_split,apply_fixed_assignments,load_split_assignments
import pytest

def test_real_cath_dataset_and_no_leakage(): verify()

def test_public_distributions_exclude_hidden_evaluation(tmp_path, monkeypatch):
    train = pd.DataFrame({"sequence": ["A" * 40, "C" * 60, "D" * 80],
                          "architecture_label": ["1.10", "1.10", "2.20"]})
    assert public_distribution_stats(train) == {
        "distribution_scope": "train", "samples_per_class": {"1.10": 2, "2.20": 1},
        "sequence_length": {"mean": 60.0, "median": 60.0, "min": 40, "max": 80}}
    plotted = []
    original = pd.Series.plot
    # Capture the actual values handed to the public chart renderer.
    def record_plot(series, *args, **kwargs):
        plotted.append(series.to_dict())
        return original(series)(*args, **kwargs)
    monkeypatch.setattr(pd.Series, "plot", record_plot)
    write_public_distribution_plots(train, tmp_path)
    assert plotted == [{"1.10": 2, "2.20": 1}, {0: 40, 1: 60, 2: 80}]
    assert {p.name for p in tmp_path.iterdir()} == {"class_distribution.png", "sequence_length_distribution.png"}

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

def frozen_fixture():
    records=[]
    for j in range(42):
        train=j<30
        records.append({"domain_id":f"d{j}", "homologous_superfamily":f"1.10.1.{1 if j<20 else 2 if train else 3}",
            "architecture_label":"1.10", "id":f'{"TRAIN" if train else "TEST"}_{j+1:06d}',
            "split":"train" if train else "test", "partition":"-" if train else "public" if j<34 else "private",
            "fold":"fit" if j<20 else "validation" if train else "-"})
    assignments=pd.DataFrame(records)
    frame=assignments[["domain_id","homologous_superfamily","architecture_label"]].copy()
    frame["sequence"]=["A"*(40+j) for j in range(len(frame))]
    return frame,assignments

def test_exclusions_preserve_all_frozen_assignments_and_ids(tmp_path):
    frame,assignments=frozen_fixture()
    path=tmp_path/"assignments.csv"; assignments.to_csv(path,index=False)
    loaded=load_split_assignments(path)
    before=pd.concat(apply_fixed_assignments(frame,loaded)).set_index("domain_id")
    filtered=frame[~frame.domain_id.isin(["d0","d20","d35"])].sample(frac=1,random_state=7)
    after=pd.concat(apply_fixed_assignments(filtered,loaded)).set_index("domain_id")
    for col in ["id","split","partition","fold"]:
        assert after[col].to_dict()==before.loc[after.index,col].to_dict()
    assert len(loaded)==42  # Retired samples stay in the policy; IDs cannot be reused.

def test_frozen_split_rejects_unknown_or_reclassified_domains():
    frame,assignments=frozen_fixture()
    unknown=frame.copy();unknown.loc[0,"domain_id"]="new-domain"
    with pytest.raises(ValueError,match="Unassigned source domains"):
        apply_fixed_assignments(unknown,assignments)
    changed=frame.copy();changed.loc[0,"homologous_superfamily"]="different-H"
    with pytest.raises(ValueError,match="frozen homologous_superfamily"):
        apply_fixed_assignments(changed,assignments)

def test_frozen_split_rejects_h_group_overlap_and_empty_partition(tmp_path):
    frame,assignments=frozen_fixture()
    assignments.loc[30,"homologous_superfamily"]=assignments.loc[0,"homologous_superfamily"]
    path=tmp_path/"assignments.csv";assignments.to_csv(path,index=False)
    with pytest.raises(ValueError,match="crosses train/test"):
        load_split_assignments(path)
    frame,assignments=frozen_fixture()
    with pytest.raises(ValueError,match="emptied a class"):
        apply_fixed_assignments(frame[~frame.domain_id.isin([f"d{j}" for j in range(30,34)])],assignments)
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
    day4={
        "TRAIN_000408", "TRAIN_001985", "TRAIN_002034", "TRAIN_002934", "TRAIN_003511",
        "TRAIN_004484", "TRAIN_004721", "TRAIN_005228", "TRAIN_006145", "TRAIN_008557",
        "TRAIN_009517", "TRAIN_009706", "TRAIN_009935", "TRAIN_010977", "TRAIN_012477",
        "TRAIN_012679", "TRAIN_014047", "TRAIN_015174", "TRAIN_015596", "TRAIN_015756",
        "TRAIN_015759", "TRAIN_017325", "TRAIN_017661", "TRAIN_017945", "TRAIN_018402",
        "TRAIN_018441", "TRAIN_019167", "TRAIN_019420", "TRAIN_019787", "TRAIN_020215",
        "TRAIN_021176", "TRAIN_021526", "TEST_001374",
    }
    assert len(bad)==21 and len(exclusions)==66
    assert set(exclusions.reference_sample_id)==bad|day3|day4
    assert exclusions.domain_id.is_unique
    assert exclusions.reason.value_counts().to_dict()=={
        "A-02":2, "A-05":3, "A-06":16, "X-01":1, "X-02":3, "P-30":41,
    }
    assert load_quality_exclusions()==set(exclusions.domain_id)
    mapping=pd.read_csv(ROOT/"data/private/id_mapping.csv",dtype=str)
    assert not set(exclusions.domain_id)&set(mapping.domain_id)
