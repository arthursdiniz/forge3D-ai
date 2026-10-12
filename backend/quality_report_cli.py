"""CPU geometry/character report for a preserved canonical scene."""
import argparse,json,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))

def main():
    parser=argparse.ArgumentParser();parser.add_argument('--input',required=True);parser.add_argument('--output',required=True);parser.add_argument('--references');parser.add_argument('--interpretation');parser.add_argument('--candidate-pose');parser.add_argument('--front-axis',default='negative_y');parser.add_argument('--up-axis',choices=['Y','Z'],default='Y');parser.add_argument('--surface-probes',action='store_true');args=parser.parse_args()
    import trimesh
    from PIL import Image
    from backend.character_quality import analyze_character
    from backend.config import atomic_json
    references={}
    if args.references:
        manifest=json.loads(Path(args.references).read_text())
        for view,item in manifest['views'].items():
            file=Path(item.get('masked_path',item['path']))
            references[view]=Image.open(file).convert('RGBA')
    interpretation=json.loads(Path(args.interpretation).read_text()) if args.interpretation else None
    pose=json.loads(Path(args.candidate_pose).read_text()) if args.candidate_pose else None
    scene=trimesh.load(args.input,force='scene',process=False)
    if args.up_axis=='Z':
        from backend.geometry_operations import canonical_matrix
        scene.apply_transform(canonical_matrix('Z','negative_y'))
    report=analyze_character(scene,interpretation,pose,references,args.front_axis,args.surface_probes)
    atomic_json(Path(args.output),report)
    print(json.dumps({'passed':True,'components':report['integrity']['connected_components'],'winding_edges':report['integrity']['inconsistent_winding_edges'],'surface_probes':args.surface_probes}),flush=True)
if __name__=='__main__':main()
