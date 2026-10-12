"""Reproducible sequential neural benchmark. Does not modify baseline assets."""
import argparse
import hashlib
import json
import os
import subprocess
import time
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
AI=ROOT/'.venv-ai/Scripts/python.exe'
BLENDER=next((ROOT/'tools').glob('blender-*/blender.exe'))
BASE=ROOT/'data/quality-upgrade/baseline'
RESULTS=ROOT/'data/quality-upgrade/improved'
CASES={'prop':'teapot.png','stylized_character':'robot.png','detailed_scene':'chair.png'}

def read(path):return json.loads(path.read_text(encoding='utf-8'))
def write(path,value):path.write_text(json.dumps(value,indent=2),encoding='utf-8')
def run(command,directory):
    with (directory/'benchmark.log').open('a',encoding='utf-8') as log:
        result=subprocess.run([str(part) for part in command],cwd=ROOT,stdout=log,stderr=subprocess.STDOUT,env={**os.environ,'OMP_NUM_THREADS':'6','PYTHONUTF8':'1'})
    if result.returncode:raise RuntimeError(f'Failed: {directory}/benchmark.log')
def blender(source,directory,mode,options):
    directory.mkdir(parents=True,exist_ok=True)
    option_file=directory/'blender_options.json';write(option_file,options)
    run([BLENDER,'--background','--factory-startup','--disable-autoexec','--threads','6','--python-exit-code','1','--python',ROOT/'blender/pipeline.py','--','--input',source,'--output',directory,'--mode',mode,'--options',option_file],directory)

def main():
    parser=argparse.ArgumentParser();parser.add_argument('--modes',nargs='+',default=['balanced','quality']);parser.add_argument('--refresh-renders',action='store_true');args=parser.parse_args()
    records=[]
    for category,reference in CASES.items():
        reference_path=BASE/category/'reference.png'
        old=read(BASE/category/'record.json')
        baseline_model=BASE/category/'generation/model.glb'
        for unlit in [False,True]:
            directory=ROOT/'data/quality-upgrade/comparison'/category/('baseline_albedo' if unlit else 'baseline')
            if args.refresh_renders or not (directory/'qa_three_quarter.png').exists():blender(baseline_model,directory,'compare',{'unlit':unlit})
        for mode in args.modes:
            directory=RESULTS/category/mode;directory.mkdir(parents=True,exist_ok=True)
            # Preparation kept equal to baseline to isolate reconstruction/material changes.
            options={'quality':mode,'foreground_ratio':0.85,'remove_background':False,'background_mode':'keep','preparation_preset':category if category=='stylized_character' else 'prop'}
            option_file=directory/'options.json';write(option_file,options)
            started=time.perf_counter()
            if not (directory/'inference.json').exists():run([AI,ROOT/'backend/inference_v2.py','--image',reference_path,'--output',directory,'--options',option_file],directory)
            inference=read(directory/'inference.json')
            if not (directory/'model.glb').exists():blender(directory/'textured_generation.glb' if (directory/'textured_generation.glb').exists() else directory/'original.glb',directory,'prepare',{'texture_resolution':inference['effective_settings']['texture_resolution']})
            report=read(directory/'mesh_report.json')
            if not (directory/'export/fbx_validation.json').exists():blender(directory/'model.glb',directory/'export','export',{})
            for unlit in [False,True]:
                comparison=ROOT/'data/quality-upgrade/comparison'/category/(mode+'_albedo' if unlit else mode)
                if args.refresh_renders or not (comparison/'qa_three_quarter.png').exists():blender(directory/'model.glb',comparison,'compare',{'unlit':unlit})
                if not unlit:report['after']['integrity']=read(comparison/'comparison_report.json')['after']['integrity']
            record={'category':category,'mode':mode,'provider':'triposr','reference':reference,'reference_sha256':hashlib.sha256(reference_path.read_bytes()).hexdigest(),'inference':inference,'mesh':report['after'],'fbx':read(directory/'export/fbx_validation.json'),'pipeline_seconds':round(time.perf_counter()-started,2),'seed':None,'seed_supported':False,'baseline_generation_id':old['generation']['id']}
            write(directory/'record.json',record);records.append(record)
            write(RESULTS/'manifest.json',records)
            print(json.dumps({'completed':category,'mode':mode,'triangles':report['after']['triangles'],'vram_mb':inference['peak_vram_mb'],'fbx':record['fbx']['passed']}),flush=True)
    print('REAL_QUALITY_BENCHMARK_COMPLETE',flush=True)
if __name__=='__main__':main()
