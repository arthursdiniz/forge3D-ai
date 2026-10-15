"""Real SDXL completion with reference-priority semantic composition and GPU samples."""
import json,subprocess,time
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];QA=ROOT/'data/semantic-upgrade-20261014';folder=QA/'neural-completion-real';folder.mkdir(exist_ok=False);analysis=QA/'A-kageyama/analysis';source=ROOT/'data/assets/323051d419ba4e47a4f421fd25e31d5f/model.glb';options={'provider':'semantic_reference','analysis_id':'a'*32,'front_axis':'negative_y','classes':['hair'],'protected_classes':['skin','face','eyes','mouth','clothes'],'reviewed_alignment':True,'intensity':1,'completion':'neural','seed':44,'style':'anime','seam_correction':True};(folder/'options.json').write_text(json.dumps(options),encoding='utf-8');samples=[];started=time.perf_counter()
with (folder/'process.log').open('w',encoding='utf-8') as log:
    process=subprocess.Popen([str(ROOT/'.venv-texture/Scripts/python.exe'),str(ROOT/'backend/texture_engine/semantic_cli.py'),'--mode','paint','--input',str(source),'--output',str(folder),'--options',str(folder/'options.json'),'--analysis',str(analysis)],cwd=ROOT,stdout=log,stderr=subprocess.STDOUT)
    while process.poll() is None:
        value=subprocess.run(['nvidia-smi','--query-gpu=memory.used,memory.total','--format=csv,noheader,nounits'],capture_output=True,text=True,timeout=10)
        if value.returncode==0:
            used,total=map(int,value.stdout.strip().split(','));samples.append({'seconds':round(time.perf_counter()-started,2),'used_mib':used,'total_mib':total})
        time.sleep(2)
    assert process.returncode==0,'See neural-completion-real/process.log'
report=json.loads((folder/'texture.json').read_text());assert report['geometry']['equivalent'] and report['semantic']['protected_pixels_equal'] and report['neural']['offline'];assert report['neural']['peak_reserved_mb']<8188
(folder/'gpu-monitor.json').write_text(json.dumps({'wall_seconds':time.perf_counter()-started,'peak_total_gpu_mib':max(s['used_mib'] for s in samples),'samples':samples,'scope':'Whole GPU incldesktop/browser; PyTorch peaks separately in texture.json'},indent=2),encoding='utf-8');print('REAL_SDXL_SEMANTIC_COMPLETION_PASS',json.dumps({'generated_texels':report['semantic']['generated_texels'],'observed_texels':report['semantic']['observed_texels'],'protected':report['semantic']['protected_pixels_equal'],'neural':report['neural'],'seconds':report['seconds']}),flush=True)
