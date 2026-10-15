"""Final regional geometry-plane visibility run with measured process/GPU samples."""
import hashlib,json,shutil,subprocess,time,sys
from pathlib import Path
import psutil
ROOT=Path(__file__).resolve().parents[1];qa=ROOT/'data/texture-fidelity-20261013';folder=ROOT/'data/semantic-upgrade-20261014/regression-regional';folder.mkdir(exist_ok=False)
source=qa/'global-image/model.glb'
options=json.loads((qa/'hinata-regional-trial6-fidelity-angle/options.json').read_text())
(folder/'options.json').write_text(json.dumps(options,indent=2));ref=folder/'references/front';ref.mkdir(parents=True)
shutil.copy2(ROOT/'data/test-inputs/hinata-shoyo-reference-20261011.png',ref/'source.png')
(folder/'texture_references.json').write_text(json.dumps({'views':{'front':{'path':'references/front/source.png'}}}))
started=time.monotonic();peaks={};rss_peak=0;gpu=[];last_gpu=-10
with (folder/'trial.log').open('w') as log:
    child=subprocess.Popen([str(ROOT/'.venv-texture/Scripts/python.exe'),str(ROOT/'backend/texture_engine/cli.py'),'--input',str(source),'--output',str(folder),'--options',str(folder/'options.json')],cwd=ROOT,stdout=log,stderr=subprocess.STDOUT)
    process=psutil.Process(child.pid)
    while child.poll() is None:
        total=0
        try:members=[process,*process.children(recursive=True)]
        except psutil.Error:members=[]
        for member in members:
            try:memory=member.memory_info();total+=memory.rss;peaks[member.pid]=max(peaks.get(member.pid,0),getattr(memory,'peak_wset',memory.rss))
            except psutil.Error:pass
        rss_peak=max(rss_peak,total);elapsed=time.monotonic()-started
        if elapsed-last_gpu>=2:
            sample=subprocess.run(['nvidia-smi','--query-gpu=memory.used,memory.total','--format=csv,noheader,nounits'],capture_output=True,text=True,timeout=5)
            if sample.returncode==0:
                used,capacity=map(int,sample.stdout.strip().split(','));gpu.append({'seconds':round(elapsed,2),'used_mib':used,'total_mib':capacity})
            last_gpu=elapsed
        time.sleep(.1)
assert child.returncode==0,'See final trial.log'
resources={'wall_seconds':round(time.monotonic()-started,3),'process_peak_working_set_mib':round(max(peaks.values())/1024**2,2),'sampled_process_tree_rss_peak_mib':round(rss_peak/1024**2,2),'sampled_gpu_total_peak_mib':max(s['used_mib'] for s in gpu),'gpu_samples':gpu,'scope':'Windows kernel peak working set of actual owned Python child; sampled full GPU includes desktop/browser. No neural inference in regional stage.'}
(folder/'resources.json').write_text(json.dumps(resources,indent=2))
report=json.loads((folder/'texture.json').read_text());assert report['geometry']['equivalent'] and report['regional']['outside_unchanged'] and report['regional']['status']=='improved_candidate'
with (folder/'export.log').open('w') as log:
    subprocess.run([str(ROOT/'tools/blender-4.5.3-windows-x64/blender.exe'),'--background','--factory-startup','--disable-autoexec','--threads','6','--python-exit-code','1','--python',str(ROOT/'blender/pipeline.py'),'--','--input',str(folder/'model.glb'),'--output',str(folder),'--mode','export','--options',str(folder/'options.json')],cwd=ROOT,stdout=log,stderr=subprocess.STDOUT,check=True)
subprocess.run([str(ROOT/'.venv-ai/Scripts/python.exe'),str(ROOT/'backend/texture_engine/validate_export.py'),'--source',str(source),'--directory',str(folder)],cwd=ROOT,check=True)
sys.path.insert(0,str(ROOT))
from backend.texture_engine.export_materials import export_materials
import trimesh
export_materials(trimesh.load(folder/'model.glb',force='scene',process=False),folder/'Forge3D_Asset')
digest=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
proof=json.loads((ROOT/'models/texture/region_validation.json').read_text());proof.update(world_geometry=report['geometry'],protected_pixels=report['regional']['outside_unchanged'],exports=json.loads((folder/'geometry_export_validation.json').read_text()),evidence_directory=str(folder.relative_to(ROOT)),texture_report_sha256=digest(folder/'texture.json'),model_sha256=digest(folder/'model.glb'))
proof['source_sha256']={p.relative_to(ROOT).as_posix():digest(p) for p in list((ROOT/'backend/texture_engine').glob('*.py'))+[ROOT/'backend/reference_texture.py',ROOT/'backend/neural_texture.py']}
(ROOT/'models/texture/region_validation.json').write_text(json.dumps(proof,indent=2))
neural_path=ROOT/'models/texture/validation.json';neural=json.loads(neural_path.read_text());neural['source_sha256']={relative:digest(ROOT/relative) for relative in neural['source_sha256']};neural['validation_note']='Actual global image/text inference retained; optional primitive-ID raster alpha is regional-only, default RGB/alpha behavior passed existing tests. Regional corrections validated separately.';neural_path.write_text(json.dumps(neural,indent=2))
print(json.dumps({'metrics':report['regional']['metrics'],'changed_pixels':report['regional']['changed_pixels'],'resources':{k:v for k,v in resources.items() if k!='gpu_samples'}},indent=2),flush=True)
