"""Controlled geometric comparison. Alignment is optimistic; not an art score."""
import hashlib
import json
from pathlib import Path
import numpy as np
import trimesh
from scipy.spatial import cKDTree

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
OUT = ROOT/'data/research-2026-10-11'

def load(path):
    return trimesh.load(path, force='mesh', process=False)

def normalize(mesh):
    value = mesh.copy()
    value.vertices = (value.vertices-value.bounds.mean(axis=0))/max(value.extents)
    return value

def rotate(points, angle):
    theta = np.deg2rad(angle)
    matrix = np.array([[np.cos(theta),0,np.sin(theta)],[0,1,0],[-np.sin(theta),0,np.cos(theta)]])
    return points@matrix.T

def samples(mesh, count, seed):
    np.random.seed(seed)
    return trimesh.sample.sample_surface(mesh, count)[0]

def score(a, b):
    ab = cKDTree(b).query(a, workers=1)[0]
    ba = cKDTree(a).query(b, workers=1)[0]
    return float((ab.mean()+ba.mean())/2), ab, ba

def geometry_hash(mesh):
    points = np.rint(mesh.vertices[mesh.faces].reshape(-1,3)*1e6).astype(np.int64)
    points = np.unique(points, axis=0)
    return hashlib.sha256(points.tobytes()).hexdigest()

def evaluate(path, truth):
    mesh = normalize(load(path))
    ref = samples(truth, 8000, 43)
    pred = samples(mesh, 8000, 42)
    trials = [(score(rotate(pred, angle), ref)[0], angle) for angle in range(0,360,15)]
    _, angle = min(trials)
    trials = [(score(rotate(pred, value), ref)[0], value) for value in np.arange(angle-14,angle+15,1)]
    _, angle = min(trials)
    # Denser independent samples for reported metrics; coarse points only align.
    ref = samples(truth, 25000, 43)
    pred = samples(mesh, 25000, 42)
    distance, ab, ba = score(rotate(pred, angle), ref)
    precision = float((ab<.02).mean())
    recall = float((ba<.02).mean())
    aligned = mesh.copy()
    aligned.vertices = rotate(mesh.vertices, angle)
    result = {'triangles':len(mesh.faces),'vertices':len(mesh.vertices),'normalized_surface_distance_percent':round(distance*100,4),'surface_fscore_at_2_percent':round(2*precision*recall/max(precision+recall,1e-9),4),'surface_precision_at_2_percent':round(precision,4),'surface_recall_at_2_percent':round(recall,4),'best_upright_yaw_degrees':float(angle%360),'relative_dimensions':aligned.extents.tolist(),'truth_relative_dimensions':truth.extents.tolist(),'sample_count_each':25000,'sampling_seed_prediction':42,'sampling_seed_groundtruth':43,'alignment':'bbox center + longest dimension=1 + best upright yaw (oracle, favorable to generator)','metric_scope':'one known mesh, approximate surface samples; not perceptual quality, topology for animation, UV or material accuracy'}
    return result, aligned

def main():
    gt = OUT/'fixture/ground_truth_clean.glb'
    if not gt.exists():gt=OUT/'fixture/ground_truth.glb'
    truth = normalize(load(gt))
    distance,a,b=score(samples(truth,25000,42),samples(truth,25000,43))
    calibration={'same_surface_independent_samples_distance_percent':round(distance*100,4),'sample_count_each':25000,'seeds':[42,43],'note':'Sampling floor, not correction to subtract from model errors; scalar scores do not certify visual/topological quality.'}
    (OUT/'metric_calibration.json').write_text(json.dumps(calibration,indent=2),encoding='utf-8')
    aligned_dir = OUT/'aligned'
    aligned_dir.mkdir(parents=True,exist_ok=True)
    truth.export(aligned_dir/'ground_truth.glb')
    records = []
    sources = [(p.parent.name,p) for p in sorted((OUT/'runs').glob('*/model.glb'))]
    sources += [(p.parent.name,p) for p in sorted((OUT/'optimized').glob('*/model.glb'))]
    for name,path in sources:
        result,aligned = evaluate(path, truth)
        result.update(name=name,model=str(path),glb_bytes=path.stat().st_size)
        raw = path.with_name('original.glb')
        if raw.exists():
            result['raw_unique_position_sha256'] = geometry_hash(load(raw))
        aligned.export(aligned_dir/(name+'.glb'))
        records.append(result)
        (OUT/'geometry_metrics.json').write_text(json.dumps(records,indent=2),encoding='utf-8')
        print(json.dumps({k:result[k] for k in ['name','triangles','normalized_surface_distance_percent','surface_fscore_at_2_percent','best_upright_yaw_degrees']}),flush=True)
    print('GEOMETRY_EVALUATION_COMPLETE',flush=True)

if __name__ == '__main__':
    main()
