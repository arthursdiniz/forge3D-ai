"""Optional automatic portrait refinement. Never simulates a human review."""
import argparse
import hashlib
import json
import socket
import sys
from pathlib import Path
ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
sys.path.append(str(ROOT / '.venv/Lib/site-packages'))


def offline(*args, **kwargs):
    raise RuntimeError('Automatic texture refinement is offline.')


socket.socket.connect = offline
socket.create_connection = offline


def refine(source, directory, references, axis, goal):
    import trimesh
    from PIL import Image
    from backend.texture_engine.face_detection import detect_anime
    from backend.texture_engine.region_camera import RegionCamera
    from backend.texture_engine.semantic_atlas import YAW
    from backend.workflows.alignment import automatic_registration
    from backend.hair.resources import verify_resources
    report = {'accepted': False, 'human_reviewed': False, 'views': {}, 'segmentation': {}, 'warnings': [],
              'scope': 'Portrait parser only; no automatic full-body semantics or anatomy correction.'}
    if goal not in ['reference', 'anime', 'stylized'] or not verify_resources(ROOT)['ready']:
        report['warnings'].append('Refinamento de retrato omitido: estilo ou recursos locais incompatíveis. A textura base foi mantida.')
        return report
    scene = trimesh.load(source, force='scene', process=False)
    settings = {'front_axis': axis, 'views': {}}
    evidence = {'method': 'automatic_landmark_gate', 'human_reviewed': False, 'views': {}}
    analysis_dir = directory / 'analysis'; analysis_dir.mkdir()
    from backend.hair.analysis import expand_head
    for name in ['front', 'back', 'left', 'right']:
        path = references / (name + '.png')
        if not path.is_file():
            continue
        image = Image.open(path).convert('RGBA')
        camera = RegionCamera(scene, axis, 512, yaw=YAW[name])
        detected_source = detect_anime(image, ROOT)
        detected_target = detect_anime(Image.fromarray(camera.image), ROOT)
        from backend.texture_engine.semantic_inference import segment_image
        segmentation = {}
        for role, picture, detected in [('source', image, detected_source), ('target', Image.fromarray(camera.image), detected_target)]:
            if len(detected['faces']) == 1:
                print(json.dumps({'stage': 'Segmentando retrato observado: ' + name + ' / ' + role}), flush=True)
                _, _, segmentation[role] = segment_image(picture, ROOT, expand_head(detected['faces'][0]['box']), 'anime', directory / 'masks' / name / role)
        report['segmentation'][name] = segmentation
        gate = automatic_registration(detected_source['faces'], detected_target['faces'])
        report['views'][name] = gate
        if not gate['accepted']:
            report['warnings'].append('Vista ' + name + ' omitida do refinamento local: ' + gate.get('reason', 'correspondência insegura') + ' A aparência dessa vista permanece estimada pela base.')
            continue
        # A style objective must retain the base's interpretation rather than paste raw appearance over it.
        if goal != 'reference':
            continue
        folder = analysis_dir / 'views' / name; folder.mkdir(parents=True)
        image.save(folder / 'source.png')
        evidence['views'][name] = {'source_faces': detected_source['faces'], 'target_faces': detected_target['faces']}
        settings['views'][name] = {'profile': 'anime', 'source_crop': expand_head(detected_source['faces'][0]['box']),
            'target_crop': expand_head(detected_target['faces'][0]['box']), 'registration': gate['registration']}
    if not settings['views']:
        report['warnings'].append('Não houve correspondência segura para transferir detalhes locais; base preservada. Ajustes de rosto, máscaras e vistas estão nas opções avançadas.')
        return report
    from backend.texture_engine.semantic_analysis import analyze_semantics
    print(json.dumps({'stage': 'Segmentando retratos compatíveis e protegendo classes'}), flush=True)
    analysis = analyze_semantics(scene, ROOT, settings, analysis_dir, hashlib.sha256(source.read_bytes()).hexdigest())
    report['registered_segmentation'] = {name: {'source': view['source'], 'target': view['target']} for name, view in analysis['views'].items()}
    if analysis['status'] != 'reviewable':
        report['warnings'].append('As máscaras automáticas não têm evidência suficiente; base de textura preservada.')
        return report
    analysis['directory'] = str(analysis_dir)
    from backend.texture_engine.semantic_paint import paint_semantic
    options = {'classes': ['hair', 'face', 'eyes', 'mouth'], 'protected_classes': [], 'reviewed_alignment': False,
               'intensity': .65, 'completion': 'preserve', 'surface_fill': False, 'seam_correction': False, 'feather_pixels': 2}
    print(json.dumps({'stage': 'Refinando apenas detalhes observados e compatíveis'}), flush=True)
    result = paint_semantic(scene, analysis, options, directory / 'refined', ROOT, automatic_evidence=evidence)
    from backend.texture_engine.texture_metrics import candidate_improved
    semantic = result['semantic']
    improved = all(candidate_improved(m['before'], m['after'], semantic['changed_pixels'],
                   semantic['protected_pixels_equal'], m['after'].get('pixels', 0)) for m in semantic['metrics'].values())
    report.update(accepted=improved, refinement=semantic, geometry=result['geometry'])
    if not improved:
        report['warnings'].append('O refinamento local não passou na comparação objetiva; base preservada e candidato mantido para inspeção.')
    return report


def main():
    parser = argparse.ArgumentParser()
    for name in ['input', 'output', 'references', 'axis', 'goal']:
        parser.add_argument('--' + name, required=True)
    args = parser.parse_args(); directory = Path(args.output)
    from backend.instance import InstanceLock
    lock = InstanceLock(ROOT / 'data/gpu.lock'); lock.acquire()
    try:
        try:
            report = refine(Path(args.input), directory, Path(args.references), args.axis, args.goal)
        except Exception as error:
            # Only this optional stage may fall back. Base generation and identity validation never do.
            report = {'accepted': False, 'human_reviewed': False, 'warnings': ['Refinamento opcional indisponível; a base validada foi mantida.'],
                      'detail': str(error)[-1500:]}
        (directory / 'automatic.json').write_text(json.dumps(report, indent=2), encoding='utf-8')
    finally:
        lock.release()


if __name__ == '__main__':
    main()
