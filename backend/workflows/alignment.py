"""Conservative automatic correspondence, explicitly distinct from user review."""
import numpy as np


def automatic_registration(source_faces, target_faces):
    result = {'accepted': False, 'method': 'automatic_landmark_gate', 'human_reviewed': False,
              'reason': 'Não foi encontrado um rosto único e compatível nas duas imagens.'}
    if len(source_faces) != 1 or len(target_faces) != 1:
        return result
    source, target = source_faces[0], target_faces[0]
    if min(source.get('raw_detection_score', 0), target.get('raw_detection_score', 0)) < .9:
        return result
    a = {p['index']: p for p in source['landmarks'] if p['raw_score'] >= .8}
    b = {p['index']: p for p in target['landmarks'] if p['raw_score'] >= .8}
    common = sorted(a.keys() & b.keys())
    if len(common) < 18:
        return result
    src = np.array([[a[i]['x'], a[i]['y']] for i in common])
    dst = np.array([[b[i]['x'], b[i]['y']] for i in common])
    if not np.isfinite(src).all() or not np.isfinite(dst).all() or min(src.min(), dst.min()) < 0 or max(src.max(), dst.max()) > 1:
        return result
    design = np.column_stack([dst, np.ones(len(dst))])
    transform = np.linalg.lstsq(design, src, rcond=None)[0]
    extent = np.ptp(src, axis=0)
    residual = np.linalg.norm((design @ transform - src) / np.maximum(extent, .01), axis=1)
    singular = np.linalg.svd(transform[:2], compute_uv=False)
    result.update(points=len(common), maximum_normalized_residual=float(residual.max()),
                  normalized_rmse=float(np.sqrt(np.mean(residual ** 2))))
    if np.linalg.matrix_rank(design) != 3 or np.linalg.det(transform[:2]) <= 0 or singular.min() < .2 or singular.max() > 5 or singular.max() / singular.min() > 1.4 or residual.max() > .10 or result['normalized_rmse'] > .045:
        result['reason'] = 'Pose, proporções ou landmarks incompatíveis; detalhes locais serão preservados.'
        return result
    result.update(accepted=True, reason=None, registration={'source_box': source['box'], 'target_box': target['box'],
        'source_points': src.tolist(), 'target_points': dst.tolist(), 'minimum_cosine': .8,
        'accept_unknown_target': False, 'protected': []})
    return result


def validate_automatic_evidence(analysis, evidence):
    if not evidence or evidence.get('method') != 'automatic_landmark_gate' or evidence.get('human_reviewed') is not False or not evidence.get('views'):
        raise ValueError('Automatic correspondence evidence missing.')
    if set(evidence['views']) != set(analysis['views']):
        raise ValueError('Every automatic painting view needs its own correspondence evidence.')
    for view, record in evidence['views'].items():
        recalculated = automatic_registration(record['source_faces'], record['target_faces'])
        if not recalculated['accepted'] or analysis['views'][view]['registration'] != recalculated['registration']:
            raise ValueError('Automatic correspondence does not match this view.')
