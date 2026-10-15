import json,hashlib
from pathlib import Path

def semantic_status(root):
    from backend.hair.resources import verify_resources
    root=Path(root);installed=verify_resources(root)['ready'] and (root/'.venv-hair/Scripts/python.exe').is_file();valid=False
    try:
        proof=json.loads((root/'models/texture/semantic_validation.json').read_text());valid=proof.get('passed') is True and proof.get('neural_masks_executed') is True and proof.get('protected_pixels') is True and proof.get('geometry_equivalent') is True and all(proof.get('exports',{}).get(name) is True for name in ['glb','fbx','obj'])
        valid&=bool(proof.get('source_sha256')) and all((root/path).resolve().is_relative_to(root.resolve()) and hashlib.sha256((root/path).read_bytes()).hexdigest()==value for path,value in proof['source_sha256'].items())
    except (OSError,ValueError,KeyError):pass
    return {'installed':installed,'available':bool(installed and valid),'profile':'Verified seven-class anime portrait; manual whole-body categories','unknown_preserved':True,'no_calibrated_confidence':True}
