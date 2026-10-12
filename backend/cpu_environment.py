"""A Python executable alone is not evidence of a complete CPU runtime."""
import hashlib
import json
from pathlib import Path


def cpu_environment_ready(root, kind):
    root = Path(root)
    environment = root/('.venv-'+kind)
    lock = root/('requirements-'+kind+'-lock.txt')
    try:
        proof = json.loads((environment/'forge3d-validation.json').read_text(encoding='utf-8'))
        return (environment/'Scripts/python.exe').is_file() and proof.get('passed') is True and proof.get('lock_sha256') == hashlib.sha256(lock.read_bytes()).hexdigest() and bool(proof.get('module_files')) and all(Path(path).is_relative_to(environment.resolve()) and Path(path).is_file() for path in proof['module_files'])
    except (OSError, ValueError, KeyError):
        return False
