"""Actual corrected-normal regional CLI trial with process RAM and sampled GPU."""
import json
import subprocess
import time
from pathlib import Path
import psutil
ROOT=Path(__file__).resolve().parents[1];qa=ROOT/'data/texture-fidelity-20261013';folder=qa/'hinata-regional-trial5-reference-only';folder.mkdir(exist_ok=False)
options=json.loads((qa/'hinata-regional-trial2-cache/options.json').read_text());detection=json.loads((qa/'global-image/face_detection.json').read_text());options['target_box']=detection['faces'][0]['box']
options['provider']='reference_region'
options['cached_views']=False
(folder/'options.json').write_text(json.dumps(options,indent=2));reference=folder/'references/front';reference.mkdir(parents=True)
import shutil
shutil.copy2(ROOT/'data/test-inputs/hinata-shoyo-reference-20261011.png',reference/'source.png');(folder/'texture_references.json').write_text(json.dumps({'views':{'front':{'path':'references/front/source.png'}}}))
started=time.monotonic();ram_peak=0;rss_peak=0;gpu=[];last_gpu=-10;process_peaks={}
with (folder/'trial.log').open('w',encoding='utf-8') as log:
    child=subprocess.Popen([str(ROOT/'.venv-ai/Scripts/python.exe'),str(ROOT/'backend/texture_engine/cli.py'),'--input',str(qa/'global-image/model.glb'),'--output',str(folder),'--options',str(folder/'options.json')],stdout=log,stderr=subprocess.STDOUT,cwd=ROOT)
    process=psutil.Process(child.pid)
    while child.poll() is None:
        try:
            total=0
            for member in [process,*process.children(recursive=True)]:
                try:
                    memory=member.memory_info();total+=memory.rss;process_peaks[member.pid]=max(process_peaks.get(member.pid,0),getattr(memory,'peak_wset',memory.rss))
                except psutil.Error:pass
            ram_peak=max(ram_peak,max(process_peaks.values(),default=0));rss_peak=max(rss_peak,total)
        except psutil.Error:pass
        elapsed=time.monotonic()-started
        if elapsed-last_gpu>=2:
            result=subprocess.run(['nvidia-smi','--query-gpu=memory.used,memory.total','--format=csv,noheader,nounits'],capture_output=True,text=True,timeout=5)
            if result.returncode==0:
                used,total=map(int,result.stdout.strip().split(','));gpu.append({'seconds':round(elapsed,2),'used_mib':used,'total_mib':total})
            last_gpu=elapsed
        time.sleep(.15)
assert child.returncode==0,'See regional trial.log'
report=json.loads((folder/'texture.json').read_text());assert report['geometry']['equivalent'] and report['regional']['outside_unchanged']
resources={'wall_seconds':round(time.monotonic()-started,3),'process_peak_working_set_mib':round(ram_peak/1024**2,2),'sampled_process_tree_rss_peak_mib':round(rss_peak/1024**2,2),'kernel_peak_by_process_mib':{str(pid):round(value/1024**2,2) for pid,value in process_peaks.items()},'gpu_samples':gpu,'sampled_gpu_total_peak_mib':max(item['used_mib'] for item in gpu),'scope':'Maximum workload process Windows peak working set; sampled RSS sum includes venv launcher and its owned children. NVIDIA sampled whole GPU includes desktop/browser. No new neural inference.'}
(folder/'resources.json').write_text(json.dumps(resources,indent=2));print(json.dumps({'regional':report['regional'],'resources':resources},indent=2)[:2800])
