"""A successful raw reconstruction may survive a failed postprocessing attempt."""
import hashlib
import json
import shutil
import struct
from pathlib import Path

from ..config import atomic_json


def digest(path):
    value = hashlib.sha256()
    with path.open('rb') as stream:
        for chunk in iter(lambda: stream.read(4 * 1024 * 1024), b''):
            value.update(chunk)
    return value.hexdigest()


def identity(root, directory, job):
    providers = {
        'triposr': (['triposr', 'dino'], 'TripoSR'),
        'triposg': (['triposg'], 'TripoSG'),
        'hunyuan_mini': (['hunyuan-mini'], 'Hunyuan3D-2'),
        'hunyuan_mv': (['hunyuan-mv'], 'Hunyuan3D-2'),
        'character_base_mesh': (['character'], None),
    }
    folders, vendor = providers[job['provider']]
    files = {p.relative_to(root).as_posix(): digest(p) for p in (root / 'backend').rglob('*.py')}
    if vendor:
        files.update({p.relative_to(root).as_posix(): digest(p) for p in (root / 'vendor' / vendor).rglob('*.py')})
    for folder in folders + ['rembg']:
        for p in (root / 'models' / folder).rglob('*'):
            if p.is_file() and p.suffix.lower() in ['.ckpt', '.safetensors', '.bin', '.pth', '.pt', '.onnx', '.json', '.yaml', '.yml'] and 'validation' not in p.name:
                files[p.relative_to(root).as_posix()] = digest(p)
    inputs = {name: digest(directory / name) for name in ['source.png', 'character_interpretation.json'] if (directory / name).is_file()}
    refs = directory / 'references.json'
    if refs.is_file():
        for view, reference in json.loads(refs.read_text(encoding='utf-8')).get('views', {}).items():
            inputs['view:' + view] = digest(Path(reference['path']))
    return hashlib.sha256(json.dumps({'provider': job['provider'], 'options': job['options'], 'inputs': inputs, 'dependencies': files}, sort_keys=True).encode()).hexdigest()


REQUIRED = {'original.glb', 'raw_generation.glb', 'inference.json', 'preparation.json', 'prepared.png'}


def valid_stage(stage, key):
    try:
        record = json.loads((stage / 'checkpoint.json').read_text(encoding='utf-8'))
        if record['key'] != key or not REQUIRED.issubset(record['files']):
            return False
        for name, expected in record['files'].items():
            path = stage / name
            if not path.resolve().is_relative_to(stage.resolve()) or digest(path) != expected:
                return False
        metadata = json.loads((stage / 'inference.json').read_text(encoding='utf-8'))
        if not isinstance(metadata.get('effective_settings'), dict):
            return False
        for name in ['original.glb', 'raw_generation.glb']:
            data = (stage / name).read_bytes()
            if len(data) < 20 or struct.unpack('<4sII', data[:12]) != (b'glTF', 2, len(data)):
                return False
        return True
    except (OSError, ValueError, KeyError, TypeError, struct.error):
        return False


def reconstruction(worker, job, directory, options_file, provider, health):
    # The legacy candidate pipeline remains unchanged. The basic workflow emits one raw mesh.
    if job['kind'] != 'model_workflow':
        return False, None
    key = identity(worker.root, directory, job)
    workflow = json.loads((directory / 'workflow.json').read_text(encoding='utf-8'))
    retry = workflow.get('retry_of')
    previous = worker.store.directory(retry) / 'inference-stage' if retry else None
    reused = bool(previous and valid_stage(previous, key))
    if reused:
        stage = directory / 'inference-stage'
        shutil.copytree(previous, stage)
        record = json.loads((stage / 'checkpoint.json').read_text(encoding='utf-8'))
        for name in record['files']:
            shutil.copy2(stage / name, directory / name)
        worker.record_stage(job['id'], 'Reconstrução validada recuperada; retomando pós-processamento')
    workflow.update(inference_cache_reused=reused, inference_source_job=retry if reused else job['id'])
    atomic_json(directory / 'workflow.json', workflow)
    current = worker.store.get(job['id'])
    worker.store.update(job['id'], metadata={**current['metadata'], 'workflow': workflow})
    return reused, key


def checkpoint(directory, key):
    stage = directory / 'inference-stage'; stage.mkdir()
    names = REQUIRED | {p.name for p in directory.glob('prepared*.png')}
    if (directory / 'gpu_monitor.json').is_file():
        names.add('gpu_monitor.json')
    for name in names:
        shutil.copy2(directory / name, stage / name)
    atomic_json(stage / 'checkpoint.json', {'key': key, 'files': {name: digest(stage / name) for name in names}})
    if not valid_stage(stage, key):
        raise RuntimeError('A reconstrução não produziu um checkpoint íntegro; arquivos preservados para diagnóstico.')
