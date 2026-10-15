import hashlib,json
from pathlib import Path

def verify_resources(root):
    root=Path(root).resolve();folder=root/'models/hair'
    try:
        manifest=json.loads((folder/'manifest.json').read_text())
        if not manifest['weights'] or not manifest['source_sha256'] or not set(manifest['licenses']).issubset({'MIT','Apache-2.0'}):raise ValueError('Unverified resource license/manifest.')
        for record in manifest['weights']:
            path=(folder/record['path']).resolve()
            if not path.is_relative_to(folder) or path.stat().st_size!=record['bytes'] or hashlib.sha256(path.read_bytes()).hexdigest()!=record['sha256']:raise ValueError('Hair checkpoint SHA/size mismatch.')
        for relative,digest in manifest['source_sha256'].items():
            path=(root/relative).resolve()
            if not path.is_relative_to(root) or hashlib.sha256(path.read_bytes()).hexdigest()!=digest:raise ValueError('Hair model source SHA mismatch.')
        return {'ready':True,'manifest':manifest,'offline_only':True}
    except (OSError,ValueError,KeyError) as error:return {'ready':False,'reason':str(error)[-500:],'offline_only':True}

def hair_status(root):
    root=Path(root);resources=verify_resources(root);validated=False
    try:
        proof=json.loads((root/'models/hair/validation.json').read_text())
        validated=proof.get('neural_executed') is True and proof.get('geometry_protected') is True and all(proof.get('exports',{}).get(name) is True for name in ['glb','fbx','obj'])
        validated&=bool(proof.get('source_sha256')) and all(hashlib.sha256((root/name).read_bytes()).hexdigest()==value for name,value in proof['source_sha256'].items())
    except (OSError,ValueError,KeyError):pass
    runtime=(root/'.venv-hair/Scripts/python.exe').is_file()
    return {'installed':resources['ready'],'available':resources['ready'] and validated and runtime,'runtime':runtime,'models':['Anime semantic UNet/MobileNet','Depth Anything V2 Small'],'notes':'Local reviewed hair geometry; hidden regions are hypotheses, no rig or universal identity score.'}
