"""Geometry proof from actual GLB/OBJ and Blender FBX reimport, not file presence."""
import argparse
import json
import sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[2]))

def main():
    import trimesh
    from backend.texture_engine.identity import compare_geometry
    parser=argparse.ArgumentParser();parser.add_argument('--source',required=True);parser.add_argument('--directory',required=True);args=parser.parse_args()
    directory=Path(args.directory);source=trimesh.load(args.source,force='scene',process=False);reports={}
    for name,path in [('fbx',directory/'fbx_reimport.glb'),('glb',directory/'Forge3D_Asset/Models/Model.glb'),('obj',directory/'Forge3D_Asset/Models/Model.obj')]:
        if not path.is_file():
            if name=='fbx':raise ValueError('Actual FBX reimport is missing.')
            continue
        report=compare_geometry(source,trimesh.load(path,force='scene',process=False));reports[name]=report
        if not report['equivalent']:raise ValueError('Export world geometry mismatch: '+name)
    (directory/'geometry_export_validation.json').write_text(json.dumps(reports,indent=2),encoding='utf-8')
    print('WORLD_GEOMETRY_EXPORT_PASS',flush=True)
if __name__=='__main__':main()
