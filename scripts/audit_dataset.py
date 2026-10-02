"""Audit all published CSVs and coordinate coverage; save an organizer report."""
import io
import json
from pathlib import Path
import zipfile
import numpy as np
import pandas as pd
from scripts.verify_dataset import verify, ROOT
from scripts.prepare_dataset import read_fasta


def audit():
    verify(ROOT)
    tables = {}
    for directory in ['public', 'private']:
        for path in sorted((ROOT / 'data' / directory).glob('*.csv')):
            frame = pd.read_csv(path, dtype=str, keep_default_na=False)
            missing = {name: int(frame[name].str.strip().eq('').sum()) for name in frame}
            na_tokens = {name: int(frame[name].str.lower().isin(['nan','null','none','na','n/a']).sum()) for name in frame}
            assert not any(missing.values()) and not any(na_tokens.values()), str(path)
            tables[str(path.relative_to(ROOT))] = {'rows': len(frame), 'columns': list(frame),
                'empty_cells': sum(missing.values()), 'missing_tokens': sum(na_tokens.values())}
    train = pd.read_csv(ROOT/'data/public/train.csv', dtype=str)
    test = pd.read_csv(ROOT/'data/private/test.csv', dtype=str)
    labels = pd.read_csv(ROOT/'data/private/labels.csv', dtype=str)
    mapping = pd.read_csv(ROOT/'data/private/id_mapping.csv', dtype=str)
    full = pd.concat([train, test.merge(labels, on='id', validate='one_to_one')])
    assert full.id.is_unique and full.sequence.is_unique
    assert full.sequence.str.fullmatch('[ACDEFGHIKLMNPQRSTVWY]+').all()
    assert full.sequence.str.len().between(40,1200).all()
    source = read_fasta(ROOT/'data/raw/s40.atom.fa')
    linked = full.merge(mapping, on='id', validate='one_to_one').merge(source, on='domain_id', suffixes=('', '_source'), validate='one_to_one')
    assert len(linked) == len(full) and (linked.sequence == linked.sequence_source).all()
    rows = [line.split()[:5] for line in (ROOT/'data/raw/domains.txt').read_text().splitlines() if line.strip() and not line.startswith('#')]
    meta = pd.DataFrame(rows, columns=['domain_id','class','architecture','topology','superfamily'])
    linked = linked.merge(meta, on='domain_id', validate='many_to_one')
    assert (linked.label == linked['class']+'.'+linked.architecture).all()
    assert (linked.homologous_superfamily == linked[['class','architecture','topology','superfamily']].agg('.'.join,axis=1)).all()
    coords = {}
    for split, directory in [('train','public'), ('test','private')]:
        missing_residues = structures_with_gaps = total_residues = 0
        minimum_coverage = 1.0
        with zipfile.ZipFile(ROOT/f'data/{directory}/{split}_structures.zip') as archive:
            for name in archive.namelist():
                with np.load(io.BytesIO(archive.read(name)), allow_pickle=False) as g:
                    mask = g['ca_mask']
                    absent = int((~mask).sum())
                    missing_residues += absent
                    structures_with_gaps += int(absent > 0)
                    total_residues += len(mask)
                    minimum_coverage = min(minimum_coverage, float(mask.mean()))
        coords[split] = {'residues': total_residues, 'missing_ca_residues': missing_residues,
            'structures_with_missing_ca': structures_with_gaps, 'minimum_ca_coverage': minimum_coverage}
    classes = []
    for label in sorted(full.label.unique()):
        counts = labels[labels.label == label].partition.value_counts()
        classes.append({'label':label,'train':int((train.label==label).sum()),
            'test':int((labels.label==label).sum()), 'public':int(counts.get('public',0)), 'private':int(counts.get('private',0))})
    result = {'status':'PASS','csv_tables':tables, 'total':len(full), 'classes':classes,
        'split':{'train':len(train),'test':len(test), 'public':int((labels.partition=='public').sum()),'private':int((labels.partition=='private').sum())},
        'length':{'min':int(full.sequence.str.len().min()),'max':int(full.sequence.str.len().max())},
        'source_sequence_and_label_match':True, 'coordinates':coords,
        'note':'Missing C-alpha coordinates are allowed up to 5%, explicitly masked; all feature values and CSV fields must be complete.'}
    path = ROOT/'docs/dataset-audit.json'
    path.write_text(json.dumps(result, indent=2), encoding='utf-8')
    print(json.dumps({k:v for k,v in result.items() if k not in ['csv_tables','classes']},indent=2))
    print('CSV tables:',len(tables),'empty/missing-token cells: 0')


if __name__ == '__main__':
    audit()
