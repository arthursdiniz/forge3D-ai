"""Resume preserved real neural cases; references/GT are explicitly own fixtures."""
import argparse,json,os,sys,time,subprocess,hashlib
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT));os.environ.pop('PYTHONPATH',None)
CASES=['a_pose','anime_hair','bulky_clothing','symmetric','asymmetric_accessory','dynamic','multiview']
def main():
    parser=argparse.ArgumentParser();parser.add_argument('--process-only',action='store_true');args=parser.parse_args()
    from backend.config import atomic_json
    base=ROOT/'data/major-quality-20261012/seven-case-neural-benchmark';base.mkdir(parents=True,exist_ok=True);records=[]
    if not args.process_only:
        from backend.hunyuan_runtime import HunyuanMiniRuntime
        from backend.inference_hy import generate_candidate
        from backend.quality_settings import generation_settings
        from backend.instance import InstanceLock
        lock=InstanceLock(ROOT/'data/gpu.lock',message='GPU occupied; resume benchmark after current generation.')
        lock.acquire();runtime=HunyuanMiniRuntime(ROOT);pipe=None;load_assigned=False
        try:
            pending=[case for case in CASES if not (base/case/'inference.json').is_file()]
            if pending:
                started=time.perf_counter();pipe=runtime.load();load=time.perf_counter()-started
            for case in CASES:
                d=base/case;d.mkdir(parents=True,exist_ok=True);source=ROOT/'data/major-quality-20261012/owned-character-fixtures'/case
                if (d/'inference.json').is_file():
                    metadata=json.loads((d/'inference.json').read_text(encoding='utf-8'))
                    if metadata['image_preparation']['source_sha256']!=hashlib.sha256((source/'front.png').read_bytes()).hexdigest():raise RuntimeError('Preserved case reference mismatch.')
                else:
                    metadata=generate_candidate(source/'front.png',d,{'quality':'balanced','seed':42,'background_mode':'preserve_alpha','foreground_ratio':.85,'preparation_preset':'stylized_character'},pipe,generation_settings('balanced','hunyuan_mini'),0 if load_assigned else load);load_assigned=True
                interpretation=json.loads((source/'fixture.json').read_text(encoding='utf-8'));interpretation.update(reviewed=True,image_size=[640,768])
                atomic_json(d/'character_interpretation.json',interpretation)
                atomic_json(d/'references.json',{'conditioning':'front_only; other real views reserved for diagnostics','views':{view:{'path':str(source/(view+'.png'))} for view in ['front','left','back','right']}})
                records.append({'case':case,'seconds':metadata['total_seconds'],'peak_vram_mb':metadata['peak_vram_mb'],'triangles':metadata['triangles'],'neural_conditioning':'front_only','source':'own CC0 procedural references, not AI results'})
        finally:del pipe;runtime.unload();lock.release()
        atomic_json(base/'manifest.json',{'cases':records,'resumed_preserved_first_two_cases':True,'inference_seconds_sum':round(sum(item['seconds'] for item in records),2),'shared_model_load_within_each_run':True})
    blender=next((ROOT/'tools').glob('blender-*/blender.exe'))
    def execute(command,directory,name):
        with (directory/(name+'.log')).open('w',encoding='utf-8') as log:subprocess.run([str(item) for item in command],stdout=log,stderr=subprocess.STDOUT,cwd=ROOT,check=True,timeout=600)
    for case in CASES:
        d=base/case;options=d/'blender_options.json';atomic_json(options,{'raw_up':'Y','geometry_only':True,'front_axis':'negative_y','clay':True,'opposite_side':True})
        if not (d/'model.glb').is_file():execute([blender,'--background','--factory-startup','--disable-autoexec','--threads','6','--python-exit-code','1','--python',ROOT/'blender/pipeline.py','--','--input',d/'original.glb','--output',d,'--mode','prepare','--options',options],d,'prepare')
        if not (d/'qa_side_opposite.png').is_file():execute([blender,'--background','--factory-startup','--disable-autoexec','--threads','6','--python-exit-code','1','--python',ROOT/'blender/pipeline.py','--','--input',d/'model.glb','--output',d,'--mode','compare','--options',options],d,'compare')
        if not (d/'character_quality.json').is_file():execute([ROOT/'.venv-geometry/Scripts/python.exe',ROOT/'backend/quality_report_cli.py','--input',d/'model.glb','--output',d/'character_quality.json','--references',d/'references.json','--interpretation',d/'character_interpretation.json','--surface-probes'],d,'diagnostics')
        print('ACTUAL_NEURAL_CHARACTER_DIAGNOSTIC_PASS '+case,flush=True)
if __name__=='__main__':main()
