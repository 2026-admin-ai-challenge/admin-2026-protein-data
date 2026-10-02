"""Check the version contract of the competition CPU inference environment."""
import importlib.metadata
from pathlib import Path
import platform
import sys
import argparse

ROOT = Path(__file__).resolve().parent
parser = argparse.ArgumentParser()
parser.add_argument('--competition', action='store_true', help='Check expanded competition package set')
args = parser.parse_args()
expected_python = (ROOT / 'python-version.txt').read_text().strip()
errors = []
if platform.python_implementation() != 'CPython':
    errors.append('CPython is required')
if platform.python_version() != expected_python:
    errors.append(f'Python: expected {expected_python}, got {platform.python_version()}')
lock_name = 'requirements-competition.lock.txt' if args.competition else 'requirements-inference.lock.txt'
for line in (ROOT / lock_name).read_text().splitlines():
    if not line.strip() or line.startswith('#'):
        continue
    name, expected = line.split('==')
    try:
        actual = importlib.metadata.version(name)
    except importlib.metadata.PackageNotFoundError:
        errors.append(f'{name}: not installed')
        continue
    if actual != expected:
        errors.append(f'{name}: expected {expected}, got {actual}')
if errors:
    print('\n'.join(errors))
    sys.exit(1)
print(f'PASS: CPU inference environment v1 / CPython {expected_python} / pinned package versions')
print(f'Host: {platform.system()} {platform.machine()}')
