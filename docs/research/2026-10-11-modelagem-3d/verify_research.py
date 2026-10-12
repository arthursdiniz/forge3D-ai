"""Verify claims/artifacts, preserving deliberately failing controls."""
import hashlib,json,math,re,tarfile
from pathlib import Path
import numpy as np
import trimesh
from PIL import Image

HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[2];OUT=ROOT/'data/research-2026-10-11'
read=lambda p:json.loads(p.read_text(encoding='utf-8'))
runs=sorted((OUT/'runs').glob('*/inference.json'))
assert len(runs)==10
for path in runs:
    info=read(path)
    raw=path.with_name('original.glb')
    assert hashlib.sha256(raw.read_bytes()).hexdigest()==info['original_sha256'],path
    assert read(path.with_name('options.json'))==info['parameters'],path
    assert info['offline_network_blocked']
    source=OUT/'fixture'/('front.png' if path.parent.name.startswith('sg_front') else 'three_quarter.png')
    assert hashlib.sha256(source.read_bytes()).hexdigest()==info['image_preparation']['source_sha256'],path
metrics=read(OUT/'geometry_metrics.json')
assert len(metrics)==13
assert all(math.isfinite(v['normalized_surface_distance_percent']) and 0<=v['surface_fscore_at_2_percent']<=1 for v in metrics)
truth=trimesh.load(OUT/'fixture/ground_truth_clean.glb',force='mesh',process=False)
truth.merge_vertices(merge_tex=True,merge_norm=True,digits_vertex=6)
assert len(truth.faces)==214 and truth.is_watertight and truth.is_winding_consistent
assert np.allclose(truth.extents,[.88,1.62,.82],atol=1e-5)
tc=read(OUT/'texture_control.json')
assert tc['vertices_identical'] and tc['faces_identical'] and not tc['geometry_changed_by_texture_method']
assert hashlib.sha256((OUT/'runs/sg_front_baseline/latents.safetensors').read_bytes()).digest()==hashlib.sha256((OUT/'runs/sg_front_quality512/latents.safetensors').read_bytes()).digest()
unity=read(OUT/'unity-validation.json')
generated=[c for c in unity['cases'] if c['name'].startswith(('sg_','sr_'))]
assert len(generated)==6
assert all(c['importCompatibilityPassed'] and c['materialPassed'] for c in generated)
for c in generated:
    assert c['expectedTriangleCountMatches'] and c['expectedDimensionsMatch']
    assert len(c['renders'])==4 and all(r['passed'] for r in c['renders'])
    for r in c['renders']:
        with Image.open(r['png']) as im:assert im.size==(512,512)
controls={c['name']:c for c in unity['cases']}
assert controls['ground_truth_clean']['geometryPassed']
assert not controls['ground_truth']['importCompatibilityPassed']
assert not controls['sg_three_quarter']['surfaceCleanlinessPassed']
assert controls['sg_best_medium']['surfaceCleanlinessPassed'] and controls['sg_best_low']['surfaceCleanlinessPassed']
lod=read(OUT/'unity-results/sg_best_lod.json')
assert lod['passed']
assert [l['triangles'] for l in lod['levels']]==[319266,31926,6384]
package=Path(lod['unityPackage'])
assert package.stat().st_size==lod['unityPackageBytes']
assert hashlib.sha256(package.read_bytes()).hexdigest()==lod['unityPackageSHA256']
with tarfile.open(package,'r:gz') as archive:
    paths=[archive.extractfile(m).read().decode('utf-8') for m in archive.getmembers() if m.name.endswith('/pathname')]
assert all(p.startswith('Assets/') for p in paths)
assert sum(p.endswith('.fbx') for p in paths)==3
assert sum(p.endswith('.prefab') for p in paths)==1
assert sum(p.endswith('.mat') for p in paths)==3
report=(HERE/'RELATORIO.md').read_text(encoding='utf-8')
assert '{{' not in report
for target in re.findall(r'\]\(<([^>]+)>\)',report):assert Path(target).exists(),target
assert (OUT/'comparacao.png').exists() and (OUT/'galeria.html').stat().st_size>1000
with Image.open(OUT/'comparacao.png') as im:assert im.size==(1200,744)
result={'passed':True,'new_real_inferences':len(runs),'measured_geometry_variants':len(metrics),'generated_unity_imports':len(generated),'actual_unity_renders':sum(len(c['renders']) for c in unity['cases']),'original_raw_and_reference_hashes_preserved':True,'texture_control_geometry_identical':True,'same_latents_256_512':True,'original_procedural_control_expected_failure':True,'high_mesh_near_zero_faces_reported':True,'three_lod_unitypackage_validated':True,'source_links':read(HERE/'sources.json')['count'],'scope':'local single-chair research and editor integration; no population-level quality or player performance claim'}
(OUT/'verification.json').write_text(json.dumps(result,indent=2),encoding='utf-8')
print(json.dumps(result),flush=True)
