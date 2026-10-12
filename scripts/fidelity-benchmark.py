"""Real v3 geometry benchmark; immutable earlier assets and baselines."""
import json,sys,subprocess,importlib.util
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];DEST=ROOT/'data/quality-upgrade/fidelity-v3'
spec=importlib.util.spec_from_file_location('bench',ROOT/'scripts/benchmark-triposg.py');bench=importlib.util.module_from_spec(spec);spec.loader.exec_module(bench)
def read(path):return json.loads(path.read_text(encoding='utf-8'))
def write(path,value):path.write_text(json.dumps(value,indent=2),encoding='utf-8')
def execute(command,directory):
    with (directory/'process.log').open('a',encoding='utf-8') as log:subprocess.run([str(x) for x in command],cwd=ROOT,stdout=log,stderr=subprocess.STDOUT,check=True,timeout=1200)
def main():
    records=[]
    for case in ['character','prop','detailed_scene']:
        baseline=DEST/'character/baseline' if case=='character' else ROOT/'data/quality-upgrade/triposg/benchmark'/case
        source=baseline/'source.png' if case=='character' else ROOT/'data/quality-upgrade/baseline'/case/'reference.png'
        params=read(baseline/'inference.json')['parameters']
        quality=DEST/case/'quality512';quality.mkdir(parents=True,exist_ok=True)
        options={**params,'quality':'balanced','seed':42,'dense_octree_depth':7,'hierarchical_octree_depth':9}
        write(quality/'options.json',options)
        if not (quality/'inference.json').exists():execute([ROOT/'.venv-sg/Scripts/python.exe',ROOT/'backend/inference_sg.py','--image',source,'--output',quality,'--options',quality/'options.json'],quality)
        if not (quality/'model.glb').exists():bench.blender(quality/'original.glb',quality,'prepare',{'raw_up':'Y','geometry_only':True,'front_axis':'negative_y'})
        previous=quality/'model.glb'
        for name,operation in [('cleaned','cleanup'),('refined','refine_silhouette')]:
            directory=DEST/case/name;directory.mkdir(parents=True,exist_ok=True)
            write(directory/'options.json',{'operation':operation});write(directory/'generation_options.json',params)
            if not (directory/'model.glb').exists():execute([ROOT/'.venv-ai/Scripts/python.exe',ROOT/'backend/refine_mesh.py','--input',previous,'--output',directory,'--options',directory/'options.json','--source',source,'--generation-options',directory/'generation_options.json'],directory)
            previous=directory/'model.glb'
        for variant,directory in [('triposg',baseline),('triposg_quality',quality),('triposg_refined',DEST/case/'refined')]:
            comparison=directory/'clay_v3';bench.blender(directory/'model.glb',comparison,'compare',{'clay':True,'front_axis':'negative_y'})
            export=directory/'export_v3'
            if not (export/'fbx_validation.json').exists():bench.blender(directory/'model.glb',export,'export',{})
            inference=read(quality/'inference.json') if variant!='triposg' else read(baseline/'inference.json')
            mesh=read(comparison/'comparison_report.json')['after']
            if variant=='triposg_refined':inference={**inference,'refinement':read(directory/'refinement.json')['refinement'],'cleanup':read(DEST/case/'cleaned/refinement.json')}
            record={'category':'character_user' if case=='character' else case,'provider':'triposg','mode':'quality' if variant!='triposg' else 'balanced','inference':inference,'mesh':mesh,'fbx':read(export/'fbx_validation.json'),'seed':42,'reference':str(source),'variant':variant}
            write(directory/'v3_record.json',record);records.append(record)
            print(json.dumps({'case':case,'variant':variant,'triangles':mesh['triangles'],'peak_vram_mb':inference['peak_vram_mb'],'fbx':record['fbx']['passed'],'iou':inference.get('refinement',{}).get('silhouette_iou_after')}),flush=True)
        write(DEST/'manifest.json',records)
    print('REAL_FIDELITY_V3_BENCHMARK_COMPLETE',flush=True)
if __name__=='__main__':main()
