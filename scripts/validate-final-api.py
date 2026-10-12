"""Real worker integration proof on the task-owned Hinata candidate; no stubs."""
import json
import time
from pathlib import Path
import httpx

root = Path(__file__).resolve().parents[1]
proof_file = root/'data/major-quality-20261012/final-api-operations.json'
proof = {'scope': 'Actual localhost API, serial worker, CPU geometry, Blender and exports', 'jobs': []}
client = httpx.Client(base_url='http://127.0.0.1:8000', timeout=20)
candidate = '4d0fd422ce9445aa804ebbc222425d10'

def run(parent, payload, export=False):
    result = client.post('/api/jobs/'+parent+('/export' if export else '/operations'), json=payload)
    result.raise_for_status()
    identifier = result.json()['id']
    started = time.perf_counter()
    print('QUEUED '+identifier+' '+json.dumps(payload), flush=True)
    while time.perf_counter()-started < 300:
        job = client.get('/api/jobs/'+identifier).json()
        if job['status'] in ['completed', 'failed', 'cancelled']:
            proof['jobs'].append({'request': payload, 'wall_seconds': round(time.perf_counter()-started, 3), 'job': job})
            proof_file.write_text(json.dumps(proof, indent=2), encoding='utf-8')
            if job['status'] != 'completed': raise RuntimeError(job.get('error') or job['status'])
            print('PASS '+identifier+' '+str(round(time.perf_counter()-started,2))+'s', flush=True)
            return identifier
        time.sleep(1)
    raise RuntimeError('Validation job timeout; inspect preserved job.')

run(candidate, {'operation': 'analyze_character'})
run(candidate, {'operation': 'symmetry', 'symmetry_mode': 'soft', 'symmetry_regions': ['torso'], 'symmetry_confirmed': True})
run(candidate, {'operation': 'sculpt_refine', 'region_bounds': [.38,.38,.62,.55], 'protected_bounds': [[.4,0,.6,.18]], 'sculpt_strength': .1})
run('c8606699b56d4aad81fdedbe69970029', {'operation': 'project_texture', 'texture_resolution': 1024, 'texture_views': 'front'})
game = run(candidate, {'operation': 'game_ready', 'target_triangles': 20000, 'texture_resolution': 4096, 'bake_normal': True})
diagnosed = run(game, {'operation': 'analyze_character'})
exported = run(diagnosed, {'pipeline': 'URP'}, export=True)
proof.update(game_ready_4k=game, diagnosed_game_ready=diagnosed, export_4k=exported, passed=True)
proof_file.write_text(json.dumps(proof, indent=2), encoding='utf-8')
for key in ['fbx','glb','obj','unity_zip']:
    url = client.get('/api/jobs/'+exported).json()['artifacts'][key]
    result = client.get(url)
    result.raise_for_status()
    print('DOWNLOAD '+key+' '+str(len(result.content)), flush=True)
