"""Provenance from reviewed source pixels to the cropped, masked reference."""
import copy
import hashlib
import json
from pathlib import Path


def reference_transform(size, crop=None):
    width, height = size
    box = [round(v * (width if i % 2 == 0 else height)) for i, v in enumerate(crop)] if crop else [0, 0, width, height]
    if box[2] <= box[0] or box[3] <= box[1]:
        raise ValueError('Recorte não contém pixels suficientes.')
    return {'source_size': list(size), 'crop_pixels': box, 'effective_size': [box[2]-box[0], box[3]-box[1]],
            'coordinate_space': 'effective cropped image before encoder framing'}


def cropped_interpretation(original, crop=None):
    from .character_understanding import summarize_character
    result = copy.deepcopy(original)
    transform = reference_transform(original['image_size'], crop)
    result['reference_transform'] = transform
    if not crop:
        return result
    width, height = transform['source_size']
    left, top, right, bottom = transform['crop_pixels']
    ew, eh = transform['effective_size']
    points = {}
    excluded = []
    for name, point in original.get('landmarks', {}).items():
        x, y = point['x']*width, point['y']*height
        if not (left <= x <= right and top <= y <= bottom):
            excluded.append(name)
            continue
        points[name] = {**point, 'x': (x-left)/ew, 'y': (y-top)/eh}
    # Recompute projected ratios in pixels; never clamp out-of-crop joints onto a border.
    summary = summarize_character(points, [ew, eh], original.get('category', 'humanoid'), original.get('pose', 'unknown'), original.get('view', 'unknown'))
    result.update(summary)
    regions = copy.deepcopy(original.get('regions', {}))
    for region in regions.values():
        box = region.get('bounds')
        if not box:
            continue
        a, b, c, d = box[0]*width, box[1]*height, box[2]*width, box[3]*height
        a, b, c, d = max(a,left), max(b,top), min(c,right), min(d,bottom)
        region['bounds'] = [(a-left)/ew, (b-top)/eh, (c-left)/ew, (d-top)/eh] if a < c and b < d else None
        region['coordinate_space'] = transform['coordinate_space']
    result.update(regions=regions, image_size=[ew, eh], excluded_by_crop=excluded)
    result['warnings'] = list(dict.fromkeys(original.get('warnings', []) + result['warnings'] + ['Landmarks e regiões foram transformados para o recorte em pixels; pontos fora dele foram excluídos.']))
    return result


def record_effective_reference(directory, options):
    """Runs for every generation, including ordinary modes without diagnostics."""
    from PIL import Image
    from .config import atomic_json
    directory = Path(directory)
    refs = directory/'references.json'
    if not refs.is_file():
        return
    bundle = json.loads(refs.read_text(encoding='utf-8'))
    front = bundle.get('views', {}).get('front')
    masked = directory/'prepared_masked.png'
    if front and masked.is_file():
        with Image.open(front['path']) as source:
            transform = reference_transform(source.size, options.get('crop'))
        with Image.open(masked) as effective:
            if list(effective.size) != transform['effective_size']:
                raise ValueError('Máscara efetiva e recorte têm espaços de coordenadas incompatíveis.')
        front.update(masked_path=str(masked.resolve()), masked_sha256=hashlib.sha256(masked.read_bytes()).hexdigest(),
                     coordinate_space=transform['coordinate_space'], reference_transform=transform)
        atomic_json(refs, bundle)
