"""Real API lineage/export verification following a browser-submitted generation."""
import argparse
import hashlib
import json
import time
from pathlib import Path
import httpx
ROOT=Path(__file__).resolve().parents[1]
client=httpx.Client(base_url='http://127.0.0.1:8000',timeout=30)
def wait(identifier):
    started=time.monotonic()
    while time.monotonic()-started<1200:
        value=client.get('/api/jobs/'+identifier).raise_for_status().json()
        if value['status']=='completed':return value
        if value['status'] in ['failed','cancelled']:raise RuntimeError(value['error'])
        time.sleep(0.5)
    raise TimeoutError(identifier)
def operation(parent,**options):return wait(client.post('/api/jobs/'+parent['id']+'/operations',json=options).raise_for_status().json()['id'])
def export(parent):return wait(client.post('/api/jobs/'+parent['id']+'/export',json={'pipeline':'URP'}).raise_for_status().json()['id'])
def main():
    parser=argparse.ArgumentParser();parser.add_argument('generation_id');args=parser.parse_args()
    generated=wait(args.generation_id)
    assert generated['metadata']['pipeline_version']==2
    assert generated['metadata']['texture']['method']=='neural_atlas'
    original=ROOT/'data/assets'/generated['id']/'original.glb'
    original_hash=hashlib.sha256(original.read_bytes()).hexdigest()
    reduced=operation(generated,operation='decimate',ratio=0.25)
    centered=operation(reduced,operation='center')
    scaled=operation(centered,operation='fix_scale',height=1.5)
    assert scaled['metadata']['versions']['processed_mesh']==generated['artifacts']['model']
    assert scaled['metadata']['versions']['game_optimized']==scaled['artifacts']['model']
    assert abs(scaled['metadata']['dimensions'][2]-1.5)<0.001
    assert 0<reduced['metadata']['triangles']<generated['metadata']['triangles']
    assert scaled['metadata']['uv_meshes']==1
    assert scaled['metadata']['materials'][0]['images']
    high_export=export(generated);optimized_export=export(scaled)
    assert original_hash==hashlib.sha256(original.read_bytes()).hexdigest()
    results={'browser_generation':generated,'optimized':reduced,'centered':centered,'scaled':scaled,'high_export':high_export,'optimized_export':optimized_export,'raw_preserved_sha256':original_hash,'passed':True,'unity_test':'pending'}
    path=ROOT/'data/quality-upgrade/flow-verification.json';path.write_text(json.dumps(results,indent=2),encoding='utf-8')
    print(json.dumps({'passed':True,'raw_triangles':generated['metadata']['triangles'],'optimized_triangles':scaled['metadata']['triangles'],'height_m':scaled['metadata']['dimensions'][2],'high_export':high_export['id'],'optimized_export':optimized_export['id']}),flush=True)
if __name__=='__main__':main()
