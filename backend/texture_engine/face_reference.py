"""Original pixels, explicit crop resolution and safe immutable ancestry."""
import hashlib
import json
from PIL import Image

def crop_reference(image,box,margin=.15):
    width,height=image.size;l,t,r,b=box
    if not 0<=l<r<=1 or not 0<=t<b<=1:raise ValueError('Invalid reference crop.')
    dx=(r-l)*margin;dy=(b-t)*margin
    pixels=(max(0,int((l-dx)*width)),max(0,int((t-dy)*height)),min(width,int((r+dx)*width+.999)),min(height,int((b+dy)*height+.999)))
    crop=image.crop(pixels);enlarged=crop.copy();enlarged.thumbnail((768,768),Image.Resampling.LANCZOS)
    if max(enlarged.size)<512:enlarged=enlarged.resize(tuple(max(1,round(v*512/max(enlarged.size))) for v in enlarged.size),Image.Resampling.NEAREST)
    detail=min((r-l)*width,(b-t)*height)
    return {'source_crop':crop,'enlarged':enlarged,'pixel_box':pixels,'original_size':[width,height],'face_min_pixels':round(detail,1),'warnings':['Reference region has fewer than64 original pixels across; enlargement does not create detail.'] if detail<64 else [],'upscale_adds_detail':False}

def best_reference(store,parent):
    candidates=[];visited=set();job=parent
    while job:
        if job['id'] in visited:raise ValueError('Invalid source ancestry.')
        visited.add(job['id']);folder=store.directory(job['id'])
        explicit=False
        if job.get('options',{}).get('provider')=='reference_region':
            try:explicit=json.loads((folder/'texture_references.json').read_text()).get('views',{}).get('front',{}).get('explicit_regional_upload') is True
            except (OSError,ValueError):pass
        for relative in ['references/front/source.png','source.png','prepared_masked.png']:
            path=folder/relative
            if path.is_file() and path.resolve().is_relative_to(store.root.resolve()):
                try:
                    with Image.open(path) as image:
                        if image.width*image.height<=25_000_000:candidates.append((image.width*image.height,len(visited),job['id'],relative,image.size,explicit and relative=='references/front/source.png'))
                except OSError:pass
        job=store.get(job['parent']) if job.get('parent') else None
    if not candidates:return None
    _,_,identifier,relative,size,_=max(candidates,key=lambda c:(c[5],c[0],-c[1]));path=store.directory(identifier)/relative
    return {'asset':identifier,'relative':relative,'url':f'/api/files/{identifier}/{relative}','width':size[0],'height':size[1],'sha256':hashlib.sha256(path.read_bytes()).hexdigest()}

def character_context(store,parent,reference_sha,reference_image=None):
    import json
    visited=set();job=parent
    while job:
        if job['id'] in visited:raise ValueError('Invalid source ancestry.')
        visited.add(job['id']);path=store.directory(job['id'])/'character_interpretation.json'
        if path.is_file() and path.resolve().is_relative_to(store.root.resolve()):
            try:
                record=json.loads(path.read_text())
                matching_pixels=reference_image is not None and record.get('image_size')==list(reference_image.size) and record.get('effective_image_sha256')==hashlib.sha256(reference_image.convert('RGBA').tobytes()).hexdigest()
                if record.get('source_upload_sha256')==reference_sha or matching_pixels:return {'source_asset':job['id'],'landmarks':record.get('landmarks',{}),'regions':record.get('regions',{}),'scope':'Existing reviewable Character Intelligence suggestions; no anatomy/identity truth.'}
            except (OSError,ValueError):pass
        job=store.get(job['parent']) if job.get('parent') else None
    return None
