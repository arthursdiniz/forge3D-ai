"""Isolated serial offline semantic analysis/painting on immutable source files."""
import argparse,hashlib,json,socket,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2];sys.path.insert(0,str(ROOT));sys.path.append(str(ROOT/'.venv/Lib/site-packages'))
def offline(*args,**kwargs):raise RuntimeError('Semantic processing is offline.')
socket.socket.connect=offline;socket.create_connection=offline

def main():
    import trimesh
    from backend.instance import InstanceLock
    from .semantic_contracts import SemanticAnalysisOptions,SemanticPaintOptions
    from .import_safety import validate_resources
    parser=argparse.ArgumentParser();parser.add_argument('--mode',choices=['analysis','paint'],required=True);parser.add_argument('--input',required=True);parser.add_argument('--output',required=True);parser.add_argument('--options',required=True);parser.add_argument('--analysis');args=parser.parse_args();source=Path(args.input);payload=source.read_bytes();digest=hashlib.sha256(payload).hexdigest();validate_resources('model.glb',payload,{});scene=trimesh.load(source,force='scene',process=False);settings=json.loads(Path(args.options).read_text());directory=Path(args.output);lock=InstanceLock(ROOT/'data/gpu.lock');lock.acquire()
    try:
        if args.mode=='analysis':
            from backend.texture_engine.semantic_analysis import analyze_semantics
            settings=SemanticAnalysisOptions.model_validate(settings).model_dump();print(json.dumps({'stage':'Semantics: segmentação real e correspondência de superfície'}),flush=True);analyze_semantics(scene,ROOT,settings,directory,digest)
        else:
            from backend.texture_engine.semantic_paint import paint_semantic
            settings=SemanticPaintOptions.model_validate(settings).model_dump();folder=Path(args.analysis);record=json.loads((folder/'semantic_analysis.json').read_text());assert record['source_sha256']==digest and record['front_axis']==settings['front_axis'] and record['status']=='reviewable','Semantic source/camera/review mismatch.'
            for name,view in record['views'].items():
                for relative,expected in view.get('file_sha256',{}).items():assert hashlib.sha256((folder/'views'/name/relative).read_bytes()).hexdigest()==expected,'Semantic reference/mask changed.'
            record['directory']=str(folder);print(json.dumps({'stage':'Semantics: Reference Fidelity e proteção de texels'}),flush=True);paint_semantic(scene,record,settings,directory,ROOT)
        assert hashlib.sha256(source.read_bytes()).hexdigest()==digest
        print(json.dumps({'stage':'Semantics: original preservado'}),flush=True)
    finally:lock.release()

if __name__=='__main__':
    __package__='backend.texture_engine';main()
