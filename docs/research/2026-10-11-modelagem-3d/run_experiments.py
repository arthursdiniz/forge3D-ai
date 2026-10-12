"""Research only. Uses installed offline models; outputs stay in this workspace."""
import argparse
import importlib.util
import json
import os
import subprocess
import sys
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
INSTALL = Path('C:/Projetos/forge3d-ai')
OUT = ROOT/'data/research-2026-10-11'
BLENDER = next((ROOT/'tools').glob('blender-*/blender.exe'))

def write(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2), encoding='utf-8')

def child(provider, image, dest, options, vertex_ablation=False):
    # The existing GPU lock is opened read-only: no installation files modified.
    import msvcrt
    sys.path.insert(0, str(INSTALL))
    lock = (INSTALL/'data/gpu.lock').open('rb')
    try:
        msvcrt.locking(lock.fileno(), msvcrt.LK_NBLCK, 1)
        name = 'inference_sg' if provider == 'triposg' else 'inference_v2'
        spec = importlib.util.spec_from_file_location('research_inference', INSTALL/'backend'/f'{name}.py')
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        sys.argv = [str(INSTALL/'backend'/f'{name}.py'), '--image', str(image), '--output', str(dest), '--options', str(options)]
        if vertex_ablation:
            sys.argv += ['--ablation-resolution', '256']
        module.main()
    finally:
        lock.close()

def execute(command, directory, timeout=1200):
    directory.mkdir(parents=True, exist_ok=True)
    # Numba/rembg probes a temporary file in its cache during import. Keep that
    # cache writable instead of probing the read-only installed environment.
    local_cache=OUT/'runtime-cache'
    temporary=local_cache/'tmp'
    temporary.mkdir(parents=True,exist_ok=True)
    numba=local_cache/'numba';numba.mkdir(exist_ok=True)
    child_env={**os.environ,'OMP_NUM_THREADS':'6','PYTHONUTF8':'1','NUMBA_CACHE_DIR':str(numba),'TEMP':str(temporary),'TMP':str(temporary)}
    with (directory/'process.log').open('a', encoding='utf-8') as log:
        result = subprocess.run([str(x) for x in command], cwd=ROOT, stdout=log, stderr=subprocess.STDOUT, timeout=timeout, env=child_env)
    if result.returncode:
        raise RuntimeError(f'{result.returncode}: {directory / "process.log"}')

def pipeline(source, directory, mode, options):
    write(directory/'blender-options.json', options)
    execute([BLENDER, '--background', '--factory-startup', '--disable-autoexec', '--threads', '6', '--python-exit-code', '1', '--python', HERE/'blender_safe_pipeline.py', '--', '--input', source, '--output', directory, '--mode', mode, '--options', directory/'blender-options.json'], directory)

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--child', action='store_true')
    parser.add_argument('--provider')
    parser.add_argument('--image')
    parser.add_argument('--output')
    parser.add_argument('--options')
    parser.add_argument('--vertex-ablation', action='store_true')
    args = parser.parse_args()
    if args.child:
        child(args.provider, Path(args.image), Path(args.output), Path(args.options), args.vertex_ablation)
        return
    fixture = OUT/'fixture'
    if not (fixture/'fixture.json').exists():
        execute([BLENDER, '--background', '--factory-startup', '--disable-autoexec', '--threads', '6', '--python-exit-code', '1', '--python', HERE/'create_fixture.py', '--', fixture], fixture)
    print('FIXTURE_READY', flush=True)
    standard = {'quality':'balanced', 'seed':42, 'background_mode':'preserve_alpha', 'foreground_ratio':5/6, 'preparation_preset':'prop'}
    cases = [
        ('sg_front_baseline', 'triposg', 'front', standard),
        ('sg_front_small', 'triposg', 'front', {**standard,'foreground_ratio':.65}),
        ('sg_front_large', 'triposg', 'front', {**standard,'foreground_ratio':.875}),
        ('sg_front_seed7', 'triposg', 'front', {**standard,'seed':7}),
        ('sg_front_steps25', 'triposg', 'front', {**standard,'num_inference_steps':25}),
        ('sg_front_quality512', 'triposg', 'front', {**standard,'quality':'quality'}),
        ('sg_three_quarter', 'triposg', 'three_quarter', standard),
        ('sr_three_quarter_neural', 'triposr', 'three_quarter', {'quality':'balanced','background_mode':'preserve_alpha','foreground_ratio':.85,'preparation_preset':'prop'}),
        ('sr_three_quarter_vertex', 'triposr', 'three_quarter', {'quality':'fast','background_mode':'preserve_alpha','foreground_ratio':.85,'preparation_preset':'prop'}),
    ]
    records = []
    for name, provider, view, options in cases:
        dest = OUT/'runs'/name
        write(dest/'options.json', options)
        image = fixture/(view+'.png')
        started = time.perf_counter()
        if not (dest/'inference.json').exists():
            env_python = INSTALL/('.venv-sg' if provider=='triposg' else '.venv-ai')/'Scripts/python.exe'
            command = [env_python, HERE/'run_experiments.py','--child','--provider',provider,'--image',image,'--output',dest,'--options',dest/'options.json']
            if name.endswith('_vertex'):
                command.append('--vertex-ablation')
            execute(command, dest)
        if not (dest/'model.glb').exists():
            pipeline(dest/'original.glb', dest, 'prepare', {'raw_up':'Y' if provider=='triposg' else 'Z','geometry_only':provider=='triposg','front_axis':'negative_y' if provider=='triposg' else 'x','texture_resolution':512 if name.endswith('_vertex') else 1024})
        inference = json.loads((dest/'inference.json').read_text())
        record = {'name':name,'provider':provider,'input_view':view,'options':options,'inference':inference,'mesh':json.loads((dest/'mesh_report.json').read_text()),'driver_elapsed_seconds':round(time.perf_counter()-started,2),'model':str(dest/'model.glb')}
        records.append(record)
        write(OUT/'manifest.json', records)
        print(json.dumps({'case':name,'triangles':inference['triangles'],'time_s':inference['total_seconds'],'vram_mib':inference['peak_vram_mb']}), flush=True)
    print('NINE_REAL_INFERENCES_COMPLETE', flush=True)

if __name__ == '__main__':
    main()
