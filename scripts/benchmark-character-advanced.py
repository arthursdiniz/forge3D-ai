"""Isolated real Hinata ablations; every source and candidate is preserved."""
import json
import os
import shutil
import subprocess
import time
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
DEST=ROOT/'data/character-advanced-20261011'
REFERENCE=ROOT/'data/test-inputs/hinata-shoyo-reference-20261011.png'
BLENDER=next((ROOT/'tools').glob('blender-*/blender.exe'))

def read(path):return json.loads(path.read_text(encoding='utf-8'))
def write(path,value):path.write_text(json.dumps(value,indent=2),encoding='utf-8')

def run(command,directory):
    start=time.perf_counter();samples=[]
    with (directory/'process.log').open('a',encoding='utf-8') as log:
        process=subprocess.Popen([str(value) for value in command],cwd=ROOT,stdout=log,stderr=subprocess.STDOUT,env={**os.environ,'PYTHONUTF8':'1','OMP_NUM_THREADS':'6'},creationflags=subprocess.CREATE_NO_WINDOW)
        while process.poll() is None:
            try:
                result=subprocess.run(['nvidia-smi','--query-gpu=memory.used','--format=csv,noheader,nounits'],capture_output=True,text=True,timeout=5)
                samples.append({'seconds':round(time.perf_counter()-start,2),'gpu_used_mib':int(result.stdout.strip())})
            except (OSError,ValueError,subprocess.TimeoutExpired):pass
            if time.perf_counter()-start>1200:process.kill();raise TimeoutError(str(directory))
            time.sleep(1)
        if process.returncode:raise RuntimeError(str(directory/'process.log'))
    return {'wall_seconds':round(time.perf_counter()-start,2),'total_gpu_peak_mib':max((x['gpu_used_mib'] for x in samples),default=None),'gpu_samples':samples}

def blender(source,directory,mode,options):
    directory.mkdir(exist_ok=True,parents=True)
    write(directory/'blender_options.json',options)
    return run([BLENDER,'--background','--factory-startup','--disable-autoexec','--threads','6','--python-exit-code','1','--python',ROOT/'blender/pipeline.py','--','--input',source,'--output',directory,'--mode',mode,'--options',directory/'blender_options.json'],directory)

def main():
    DEST.mkdir(parents=True,exist_ok=True)
    baseline=DEST/'baseline-triposr-quality'
    if not baseline.exists():shutil.copytree(ROOT/'data/assets/51764b49c97743508f5391760330dc1f',baseline)
    common={'quality':'quality','background_mode':'preserve_alpha','preparation_preset':'stylized_character','foreground_ratio':0.85}
    trials=[('triposr-corrected','triposr',common),('triposr-character','triposr',{**common,'foreground_ratio':.9,'preparation_preset':'character'})]
    sg={**common,'foreground_ratio':5/6,'seed':42}
    trials += [('triposg-balanced42','triposg',{**sg,'quality':'balanced'}),('triposg-quality42','triposg',sg),('triposg-quality7','triposg',{**sg,'seed':7}),('triposg-quality1234','triposg',{**sg,'seed':1234}),('triposg-guidance4','triposg',{**sg,'guidance_scale':4})]
    records=[]
    for name,provider,options in trials:
        directory=DEST/name;directory.mkdir(exist_ok=True)
        write(directory/'options.json',options)
        if not (directory/'inference.json').exists():
            timing=run([ROOT/('.venv-ai/Scripts/python.exe' if provider=='triposr' else '.venv-sg/Scripts/python.exe'),ROOT/('backend/inference_v2.py' if provider=='triposr' else 'backend/inference_sg.py'),'--image',REFERENCE,'--output',directory,'--options',directory/'options.json'],directory)
            write(directory/'runtime.json',timing)
        inference=read(directory/'inference.json')
        if not (directory/'model.glb').exists():
            timing=blender(directory/('textured_generation.glb' if provider=='triposr' else 'original.glb'),directory,'prepare',{'raw_up':'Z' if provider=='triposr' else 'Y','geometry_only':provider=='triposg','front_axis':'x' if provider=='triposr' else 'negative_y','texture_resolution':2048})
            write(directory/'blender_runtime.json',timing)
        clay=directory/'clay'
        if not (clay/'qa_rear.png').exists():blender(directory/'model.glb',clay,'compare',{'clay':True,'front_axis':'x' if provider=='triposr' else 'negative_y'})
        record={'name':name,'provider':provider,'inference':inference,'mesh':read(directory/'mesh_report.json')['after'],'runtime':read(directory/'runtime.json'),'blender_runtime':read(directory/'blender_runtime.json')}
        record['generation_wall_seconds']=round(record['runtime']['wall_seconds']+record['blender_runtime']['wall_seconds'],2)
        write(directory/'record.json',record);records.append(record);write(DEST/'ablation-manifest.json',records)
        print(json.dumps({'name':name,'triangles':record['mesh']['triangles'],'wall_seconds':record['generation_wall_seconds'],'allocated_mib':inference['peak_vram_mb'],'total_gpu_peak':record['runtime']['total_gpu_peak_mib']}),flush=True)
    print('REAL_HINATA_ABLATIONS_COMPLETE',flush=True)

if __name__=='__main__':main()
