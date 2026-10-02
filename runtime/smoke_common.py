"""Offline checks for the main competition package families."""
import importlib
import json
from pathlib import Path
import tempfile

modules = ['torch', 'torchvision', 'torchaudio', 'xgboost', 'lightgbm', 'catboost',
           'transformers', 'datasets', 'accelerate', 'safetensors', 'tokenizers',
           'huggingface_hub', 'Bio', 'networkx', 'tqdm', 'yaml', 'requests',
           'h5py', 'einops', 'optuna']
for name in modules:
    importlib.import_module(name)
    print('PASS import:', name, flush=True)

import numpy as np
import torch
from safetensors.torch import save_file, load_file
from Bio.Seq import Seq
from xgboost import XGBClassifier
from lightgbm import LGBMClassifier
from catboost import CatBoostClassifier
from transformers import BertConfig, BertModel

x = np.array([[0,0], [0,1], [1,0], [1,1]] * 5, dtype=np.float32)
y = np.array([0,0,1,1] * 5)
for model in [XGBClassifier(n_estimators=2, n_jobs=1),
              LGBMClassifier(n_estimators=2, n_jobs=1, verbosity=-1, min_child_samples=1),
              CatBoostClassifier(iterations=2, thread_count=1, verbose=False, allow_writing_files=False)]:
    model.fit(x, y)
    assert model.predict(x).shape[0] == len(y)
    print('PASS fit/predict:', type(model).__name__, flush=True)

torch.set_num_threads(1)
model = BertModel(BertConfig(vocab_size=24, hidden_size=16, num_hidden_layers=1,
                            num_attention_heads=2, intermediate_size=32))
with torch.no_grad():
    assert model(torch.tensor([[1,2,3]])).last_hidden_state.shape == (1,3,16)
with tempfile.TemporaryDirectory() as directory:
    path = str(Path(directory) / 'model.safetensors')
    save_file({'weights': torch.ones(2,3)}, path)
    assert torch.equal(load_file(path)['weights'], torch.ones(2,3))
assert str(Seq('ACDEFG')) == 'ACDEFG'
print('PASS: offline Transformer forward, tensor serialization, protein sequence', flush=True)
