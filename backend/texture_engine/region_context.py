"""Bounded offline CPU helper for actual reference and surface selection previews."""
import argparse
import json
import socket
import sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2];sys.path.insert(0,str(ROOT));sys.path.append(str(ROOT/'.venv/Lib/site-packages'))
def blocked(*args,**kwargs):raise RuntimeError('Regional preparation is offline.')
socket.socket.connect=blocked;socket.create_connection=blocked

def main():
    parser=argparse.ArgumentParser();parser.add_argument('--directory',required=True);parser.add_argument('--axis',default='negative_y');parser.add_argument('--style',default='anime');args=parser.parse_args()
    directory=Path(args.directory)
    from PIL import Image
    import trimesh
    from backend.texture_engine.import_safety import validate_resources
    from backend.texture_engine.region_camera import RegionCamera
    from backend.texture_engine.face_detection import detect_anime
    validate_resources('model.glb',(directory/'model.glb').read_bytes(),{})
    scene=trimesh.load(directory/'model.glb',force='scene',process=False);camera=RegionCamera(scene,args.axis,1024);preview=Image.fromarray(camera.image);preview.save(directory/'model_front.png')
    reference=Image.open(directory/'source.png').convert('RGBA')
    if args.style=='anime':source=detect_anime(reference,ROOT);target=detect_anime(preview,ROOT)
    else:source=target={'status':'manual_selection','faces':[],'warnings':['Use reviewed Character Intelligence points or manual selection for this style; anime detector is not a human/object truth.']}
    materials=[]
    for index,node in enumerate(scene.graph.nodes_geometry):
        _,name=scene.graph[node];mesh=scene.geometry[name]
        material=getattr(mesh.visual,'material',None);materials.append({'name':getattr(material,'name',None) or f'Material_{index:03d}','has_albedo':getattr(material,'baseColorTexture',None) is not None})
    report={'reference_size':list(reference.size),'model_size':[1024,1024],'source_detection':source,'target_detection':target,'frame':camera.frame,'front_axis':args.axis,'materials':materials,'offline':True,'semantic_segmentation':False,'neural_inpainting':False,'requires_alignment_review':True}
    (directory/'context.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
if __name__=='__main__':main()
