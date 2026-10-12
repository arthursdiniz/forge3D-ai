"""Persistent local settings; generated artifacts cannot overwrite originals."""
import json
import os
from pathlib import Path


def atomic_json(path,value):
    path=Path(path);path.parent.mkdir(parents=True,exist_ok=True)
    temporary=path.with_name(path.name+'.tmp')
    temporary.write_text(json.dumps(value,indent=2,ensure_ascii=False),encoding='utf-8')
    os.replace(temporary,path)


def load_config(root):
    path=Path(root)/'data/config.json'
    try:return json.loads(path.read_text(encoding='utf-8'))
    except (OSError,ValueError):return {'blender_executable':None,'max_concurrent_heavy_jobs':1}


def configure_blender(root,value):
    path=Path(value).expanduser()
    if not path.is_absolute() or path.name.lower()!='blender.exe' or not path.is_file():
        raise ValueError('Informe o caminho absoluto de um blender.exe existente.')
    settings={**load_config(root),'blender_executable':str(path.resolve()),'max_concurrent_heavy_jobs':1}
    atomic_json(Path(root)/'data/config.json',settings)
    return settings


def resolve_blender(root):
    selected=load_config(root).get('blender_executable')
    if selected:
        path=Path(selected)
        if path.is_file() and path.name.lower()=='blender.exe':return path
        return None
    paths=sorted((Path(root)/'tools').glob('blender-*/blender.exe'),reverse=True)
    return paths[0] if paths else None
