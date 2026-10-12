"""Actual three-case TripoSG benchmark, serial with app GPU lock and no paint."""
import argparse
import json
import os
import subprocess
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
DEST=ROOT/'data/quality-upgrade/triposg/benchmark'
BLENDER=next((ROOT/'tools').glob('blender-*/blender.exe'))
def read(path):return json.loads(path.read_text())
def write(path,value):path.write_text(json.dumps(value,indent=2),encoding='utf-8')
def run(command,directory):
    with (directory/'process.log').open('a',encoding='utf-8') as log:
        result=subprocess.run([str(value) for value in command],cwd=ROOT,stdout=log,stderr=subprocess.STDOUT,env={**os.environ,'OMP_NUM_THREADS':'6','PYTHONUTF8':'1'},timeout=1200)
    if result.returncode:raise RuntimeError(str(directory/'process.log'))
def blender(source,directory,mode,options):
    directory.mkdir(exist_ok=True,parents=True);option_file=directory/'blender_options.json';write(option_file,options)
    run([BLENDER,'--background','--factory-startup','--disable-autoexec','--threads','6','--python-exit-code','1','--python',ROOT/'blender/pipeline.py','--','--input',source,'--output',directory,'--mode',mode,'--options',option_file],directory)
def main():
    parser=argparse.ArgumentParser();parser.add_argument('--refresh-clay',action='store_true');args=parser.parse_args()
    records=[]
    for category in ['prop','stylized_character','detailed_scene']:
        directory=DEST/category;directory.mkdir(exist_ok=True,parents=True)
        reference=ROOT/'data/quality-upgrade/baseline'/category/'reference.png'
        options={'quality':'balanced','seed':42,'background_mode':'auto','foreground_ratio':5/6,'preparation_preset':'stylized_character' if category=='stylized_character' else 'prop'}
        option_file=directory/'options.json';write(option_file,options)
        if not (directory/'inference.json').exists():run([ROOT/'.venv-sg/Scripts/python.exe',ROOT/'backend/inference_sg.py','--image',reference,'--output',directory,'--options',option_file],directory)
        inference=read(directory/'inference.json')
        if not (directory/'model.glb').exists():blender(directory/'original.glb',directory,'prepare',{'raw_up':'Y','geometry_only':True,'front_axis':'negative_y'})
        report=read(directory/'mesh_report.json')
        if not (directory/'export/fbx_validation.json').exists():blender(directory/'model.glb',directory/'export','export',{})
        for variant in ['baseline','fast','balanced','quality','triposg']:
            source=directory/'model.glb' if variant=='triposg' else ROOT/'data/quality-upgrade'/('baseline' if variant=='baseline' else 'improved')/category/('generation' if variant=='baseline' else variant)/'model.glb'
            compare=ROOT/'data/quality-upgrade/comparison'/category/(variant+'_clay')
            if args.refresh_clay or not (compare/'qa_three_quarter.png').exists():blender(source,compare,'compare',{'clay':True,'front_axis':'negative_y' if variant=='triposg' else 'x'})
        record={'category':category,'mode':'balanced','provider':'triposg','reference_sha256':inference['image_preparation']['source_sha256'],'inference':inference,'mesh':report['after'],'fbx':read(directory/'export/fbx_validation.json'),'seed':42,'seed_supported':True,'comparison_notes':'Each provider uses its own required image normalization; shared original reference. Clay views isolate geometry. TripoSG has no generated texture.'}
        write(directory/'record.json',record);records.append(record);write(DEST/'manifest.json',records)
        print(json.dumps({'category':category,'triangles':record['mesh']['triangles'],'allocated_mib':inference['peak_vram_mb'],'reserved_mib':inference['peak_reserved_mb'],'time_s':inference['total_seconds'],'fbx_passed':record['fbx']['passed']}),flush=True)
    print('REAL_TRIPOSG_BENCHMARK_COMPLETE',flush=True)
if __name__=='__main__':main()
