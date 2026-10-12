"""Run inside the target venv after pip reconciliation and dependency checks."""
import argparse
import hashlib
import importlib
import importlib.metadata
import json
from pathlib import Path
import sys

parser = argparse.ArgumentParser()
parser.add_argument('kind', choices=['character', 'geometry'])
args = parser.parse_args()
root = Path(__file__).resolve().parents[1]
environment = root/('.venv-'+args.kind)
if Path(sys.prefix).resolve() != environment.resolve():
    raise RuntimeError('Use o Python do ambiente CPU selecionado.')
lock = root/('requirements-'+args.kind+'-lock.txt')
for requirement in lock.read_text(encoding='utf-8-sig').splitlines():
    if not requirement.strip() or requirement.startswith('#'):
        continue
    name, version = requirement.split('==')
    if importlib.metadata.version(name) != version:
        raise RuntimeError('Versão diferente do lock: '+name)
modules = ['PIL', 'numpy', 'mediapipe', 'mediapipe.tasks.python.vision.pose_landmarker'] if args.kind == 'character' else ['PIL', 'numpy', 'scipy', 'trimesh', 'skimage', 'rtree', 'pymeshlab', 'moderngl']
files = [str(Path(importlib.import_module(name).__file__).resolve()) for name in modules]
proof = {'passed': True, 'lock_sha256': hashlib.sha256(lock.read_bytes()).hexdigest(), 'python': sys.version, 'module_files': files}
target = environment/'forge3d-validation.json'
temporary = target.with_suffix('.tmp')
temporary.write_text(json.dumps(proof, indent=2), encoding='utf-8')
temporary.replace(target)
print(args.kind+' CPU imports and pinned requirements PASS')
