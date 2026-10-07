"""Synthetic parser edge cases; real structures are audited by test_dataset.py."""
import io
import tarfile
import numpy as np
import pandas as pd
import pytest
from scripts.structure_dataset import consecutive, parse_pdb, prepare_structures
from scripts.structure_features import structure_features, FEATURE_NAMES


def atom(i, name='CA', xyz=None, alt='', occupancy=1.0, residue='ALA', insertion='', chain='A'):
    x,y,z = xyz if xyz is not None else (i * 3.8,0,0)
    return f"ATOM  {i:5d} {name:^4s}{alt:1s}{residue:3s} {chain}{i:4d}{insertion:1s}   {x:8.3f}{y:8.3f}{z:8.3f}{occupancy:6.2f}{20.0:6.2f}"


def pdb(): return '\n'.join(atom(i) for i in range(1,43))


def test_known_coordinates_and_no_precomputed_relationships():
    g=parse_pdb(pdb(),'A'*42)
    assert set(g)=={'residue_type','residue_index','segment_index','pos','ca_mask'}
    assert np.all(g['ca_mask']) and np.all(g['segment_index']==0)
    assert np.allclose(g['pos'].mean(0),0,atol=1e-4)
    assert np.allclose(np.linalg.norm(np.diff(g['pos'],axis=0),axis=1),3.8,atol=1e-4)


def test_missing_ca_mask_and_chain_gap_are_explicit():
    lines=[atom(i,name='N' if i==10 else 'CA') for i in range(1,43)]
    g=parse_pdb('\n'.join(lines),'A'*42)
    assert not g['ca_mask'][9] and np.all(g['pos'][9]==0)
    assert g['segment_index'][10] > g['segment_index'][8]
    # Consecutive array rows with discontinuous original residue numbering.
    lines=[atom(i,xyz=(j*3.8,0,0)) for j,i in enumerate(list(range(1,22))+list(range(50,71)))]
    g=parse_pdb('\n'.join(lines),'A'*42)
    assert g['segment_index'][20]!=g['segment_index'][21]


def test_sequence_mismatch_and_low_coverage_rejected():
    with pytest.raises(ValueError,match='atom_sequence_mismatch'): parse_pdb(pdb(),'C'+'A'*41)
    lines=[atom(i,name='N' if i<10 else 'CA') for i in range(1,43)]
    with pytest.raises(ValueError,match='insufficient_ca_coverage'): parse_pdb('\n'.join(lines),'A'*42)


def test_altloc_occupancy_and_first_model():
    text=pdb()+'\n'+atom(1,alt='B',occupancy=.5,xyz=(999,0,0))+'\nENDMDL\n'+atom(1,residue='CYS')
    assert np.array_equal(parse_pdb(text,'A'*42)['pos'],parse_pdb(pdb(),'A'*42)['pos'])


def test_same_insertion_code_on_successive_numbers_is_continuous():
    text='\n'.join(atom(i,insertion='P') for i in range(1,43))
    assert np.all(parse_pdb(text,'A'*42)['segment_index']==0)


@pytest.mark.parametrize("a,b,expected", [
    (("A", 208, ""), ("A", 209, "A"), True),
    (("A", 21, "A"), ("A", 22, ""), True),
    (("A", 4, "P"), ("A", 5, "P"), True),
    (("A", 21, ""), ("A", 21, "A"), True),
    (("A", 21, "A"), ("A", 21, "B"), True),
    (("A", 21, "A"), ("A", 23, ""), False),
    (("A", 22, ""), ("A", 21, "A"), False),
    (("A", 21, "A"), ("B", 22, ""), False),
])
def test_insertion_code_boundaries(a, b, expected):
    assert consecutive(a, b) is expected


def test_altlocs_use_one_domain_wide_conformer():
    lines=[atom(i) for i in range(1,43) if i not in (1,26)]
    lines += [atom(1,alt='A',occupancy=.51,xyz=(3.8,0,0)),
              atom(1,alt='B',occupancy=.49,xyz=(95,0,0)),
              atom(26,alt='A',occupancy=.49,xyz=(98.8,0,0)),
              atom(26,alt='B',occupancy=.51,xyz=(6.4,0,0))]
    # Keep the ATOM residue order while putting both alternatives next to each other.
    lines=lines[-4:-2]+lines[:24]+lines[-2:]+lines[24:]
    g=parse_pdb('\n'.join(lines),'A'*42)
    assert np.isclose(np.linalg.norm(g['pos'][0]-g['pos'][25]),95.0)


def test_nonlocal_ca_overlap_is_rejected():
    lines=[atom(i,xyz=(2*3.8,0,0) if i==27 else None) for i in range(1,43)]
    with pytest.raises(ValueError,match='nonlocal_ca_clash'):
        parse_pdb('\n'.join(lines),'A'*42)

def test_preselected_adjacent_altloc_mixing_is_rejected_even_at_normal_distance():
    lines=[atom(i,alt='A' if i==10 else 'B' if i==11 else '') for i in range(1,43)]
    with pytest.raises(ValueError,match='adjacent_altloc_mismatch'):
        parse_pdb('\n'.join(lines),'A'*42)

def test_shared_blank_sites_and_separate_segments_do_not_force_altloc_letters():
    lines=[atom(i,alt='A' if i==10 else 'B' if i==12 else '') for i in range(1,43)]
    assert parse_pdb('\n'.join(lines),'A'*42)['ca_mask'].all()
    lines=[atom(i,alt='A' if i==10 else 'B' if i==11 else '',chain='A' if i<11 else 'B') for i in range(1,43)]
    g=parse_pdb('\n'.join(lines),'A'*42)
    assert g['segment_index'][9]!=g['segment_index'][10]

def test_cis_distance_with_coherent_altloc_is_retained():
    lines=[atom(i,alt='A' if i in (10,11) else '',xyz=((i*3.8-0.9 if i>=11 else i*3.8),0,0)) for i in range(1,43)]
    g=parse_pdb('\n'.join(lines),'A'*42)
    assert g['segment_index'][9]==g['segment_index'][10]


def test_reviewed_domain_is_excluded_before_publication(tmp_path):
    raw=tmp_path/'raw'; raw.mkdir()
    with tarfile.open(raw/'s40.pdb.tgz','w:gz') as archive:
        for domain in ('reviewed','valid'):
            content=pdb().encode('ascii')
            info=tarfile.TarInfo(domain); info.size=len(content)
            archive.addfile(info,io.BytesIO(content))
    frame=pd.DataFrame({'domain_id':['reviewed','valid'],'sequence':['A'*42]*2})
    clean,reasons=prepare_structures(raw,frame,{'reviewed'})
    assert clean.domain_id.tolist()==['valid']
    assert reasons['curated_source_quality']==1


def test_features_invariant_to_rotation_translation_and_have_no_labels():
    g=parse_pdb(pdb(),'A'*42)
    before=structure_features(g)
    g['pos']=g['pos'] @ np.array([[0,-1,0],[1,0,0],[0,0,1]],dtype=np.float32)+np.array([4,5,6],dtype=np.float32)
    assert np.allclose(before,structure_features(g),atol=1e-6)
    assert len(before)==len(FEATURE_NAMES)==31
    assert not any('label' in name or 'domain' in name for name in g)


def test_case_sensitive_domain_ids_do_not_collide_on_macos():
    from scripts.structure_dataset import cache_name
    assert cache_name("1abcA00").lower() != cache_name("1abca00").lower()
