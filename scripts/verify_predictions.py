"""Validate a participant prediction file against the submission contract.

Thin entry point; the judgement lives in scripts/prediction_validator/.
See docs/prediction-contract.md for the contract and docs/prediction-errors.md
for the error codes.
"""
import sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))   # allow `python scripts/verify_predictions.py` from the repo root
from scripts.prediction_validator.cli import main

if __name__ == "__main__":
    raise SystemExit(main())
