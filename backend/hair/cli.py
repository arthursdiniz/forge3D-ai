"""Serial isolated offline hair analysis/reconstruction, immutable inputs."""
import argparse,hashlib,json,socket,sys,time
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2];sys.path.insert(0,str(ROOT))
def blocked(*args,**kwargs):raise RuntimeError('Hair execution is offline.')
socket.socket.connect=blocked;socket.create_connection=blocked

def main():
    import trimesh,numpy as np
    from PIL import Image
    from backend.instance import InstanceLock
    from backend.texture_engine.import_safety import validate_resources
    parser=argparse.ArgumentParser();parser.add_argument('--mode',choices=['analysis','reconstruct'],required=True);parser.add_argument('--input',required=True);parser.add_argument('--output',required=True);parser.add_argument('--options',required=True);parser.add_argument('--analysis');args=parser.parse_args();started=time.perf_counter();directory=Path(args.output);directory.mkdir(parents=True,exist_ok=True);options=json.loads(Path(args.options).read_text());payload=Path(args.input).read_bytes();validate_resources('model.glb',payload,{});digest=hashlib.sha256(payload).hexdigest();scene=trimesh.load(args.input,force='scene',process=False);lock=InstanceLock(ROOT/'data/gpu.lock');lock.acquire()
    try:
        if args.mode=='analysis':
            from backend.hair.analysis import analyze_scene
            print(json.dumps({'stage':'Hair: segmentação e profundidade local'}),flush=True);analyze_scene(scene,Image.open(directory/'source.png'),ROOT,options,directory,digest)
        else:
            from backend.hair.pipeline import preserved_copy
            from backend.hair.refinement import refine_scene
            from backend.texture_engine.region_camera import RegionCamera
            from backend.hair.metrics import silhouette_metrics
            from backend.hair.views import head_view
            analysis_folder=Path(args.analysis);analysis=json.loads((analysis_folder/'hair_analysis.json').read_text());assert analysis['source_sha256']==digest and analysis['front_axis']==options['front_axis'],'Hair analysis/source/axis mismatch.'
            field=analysis_folder/'existing_head_field.npy'
            if field.is_file():analysis['existing_head_field']=np.load(field,allow_pickle=False)
            analysis['reference_support_mask']=np.asarray(Image.open(analysis_folder/'reference_aligned_mask.png'))>0
            print(json.dumps({'stage':'Hair: massas, mechas e pontas volumétricas'}),flush=True);result,report=refine_scene(scene,analysis,options,directory,analysis_folder)
            if report['status']=='reviewable_candidate':
                frame=analysis['camera_frame'];after=RegionCamera(result,options['front_axis'],1024,frame);before=RegionCamera(scene,options['front_axis'],1024,frame);Image.fromarray(before.image).save(directory/'hair_before_front.png');Image.fromarray(after.image).save(directory/'hair_after_front.png')
                owners=[i+1 for i,node in enumerate(result.graph.nodes_geometry) if result.graph[node][1] in report['hair_meshes']];generated=np.isin(after.buffers[2][...,2],owners)&(after.buffers[0][...,3]>.5)
                original_mask=np.asarray(Image.open(analysis_folder/'hair_model_mask.png'))>0;reference=np.asarray(Image.open(analysis_folder/'reference_aligned_mask.png'))>0;classes=np.asarray(Image.open(analysis_folder/'model_classes.png'));protected=np.isin(classes,[2,3,4,5])&~reference
                manual=analysis_folder/'manual_protected_mask.png'
                if manual.is_file():protected|=np.asarray(Image.open(manual))>0
                intrusion=int((generated&protected).sum());report['protected_face_occlusion_pixels']=intrusion;report['protection_scope']='Original face/skin/eyes/mouth pixels outside aligned observed hair; actual render ownership.';report['silhouette_before']=silhouette_metrics(original_mask,reference);report['silhouette_after']=silhouette_metrics(original_mask|generated,reference)
                Image.fromarray(generated.astype('u1')*255).save(directory/'generated_hair_mask.png')
                if intrusion>max(8,int(protected.sum()*.002)) or report.get('retention_required'):
                    report.update(status='inconclusive_previous_retained',reason=report.get('reason') or 'Proposed volumes occlude protected facial pixels; adjust scalp/mask/volume.');result.export(directory/'candidate.glb',include_normals=True);result=preserved_copy(scene)
                for name,angle in [('front',0),('three_quarter',35),('side',90),('back',180)]:
                    for label,current in [('before',scene),('after',after.scene)]:Image.fromarray(head_view(current,options['front_axis'],frame,analysis['target_head_box'],analysis['scalp'],768,angle)).save(directory/f'hair_{label}_{name}.png')
                for label,current in [('before',scene),('after',after.scene)]:
                    for name,angle in [('front',0),('side',90),('back',180)]:Image.fromarray(head_view(current,options['front_axis'],frame,analysis['target_head_box'],analysis['scalp'],768,angle,True)).save(directory/f'hair_{label}_clay_{name}.png')
            result.export(directory/'model.glb',include_normals=True);report['seconds']=round(time.perf_counter()-started,3);report['source_model_sha256']=digest;(directory/'hair_geometry.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
        assert hashlib.sha256(Path(args.input).read_bytes()).hexdigest()==digest
        print(json.dumps({'stage':'Hair: original preservado e diagnóstico salvo'}),flush=True)
    finally:lock.release()
if __name__=='__main__':main()
