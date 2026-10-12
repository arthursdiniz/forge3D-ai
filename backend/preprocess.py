from pathlib import Path
from PIL import Image, ImageOps

def prepare_image(source: Path, destination: Path, foreground_ratio=None, crop=None, remove_background=False, model_dir=None, background_mode=None, preparation_preset='prop',background_color=(128,128,128),save_alpha=False,save_masked_source=False):
    import hashlib
    from .quality_settings import PREPARATION_PRESETS
    preset=PREPARATION_PRESETS.get(preparation_preset)
    if preset is None:
        raise ValueError('Preset de preparação inválido.')
    if foreground_ratio is None:
        foreground_ratio=preset['foreground_ratio']
    if not 0.5<=foreground_ratio<=0.95:
        raise ValueError('Ocupação deve estar entre 50% e 95%.')
    if len(background_color)!=3 or any(not isinstance(value,int) or not 0<=value<=255 for value in background_color):
        raise ValueError('Cor de fundo RGB inválida.')
    image = ImageOps.exif_transpose(Image.open(source)).convert('RGBA')
    source_size=list(image.size)
    warning_codes=[]
    warnings=[]
    if min(image.size)<256:
        warning_codes.append('low_resolution')
        warnings.append('Referência de baixa resolução; ampliar para 512 não cria detalhe novo.')
    if crop:
        left, top, right, bottom = crop
        if not (0 <= left < right <= 1 and 0 <= top < bottom <= 1):
            raise ValueError('Recorte inválido: use coordenadas de 0 a 1.')
        image = image.crop((round(left*image.width),round(top*image.height),round(right*image.width),round(bottom*image.height)))
    alpha=image.getchannel('A')
    # Respect every supplied alpha mask, including interior holes/opaque corners.
    has_cutout=alpha.getextrema()[0]<255
    mode=background_mode or ('auto' if remove_background else 'keep')
    if mode not in ['auto','keep','remove','preserve_alpha']:
        raise ValueError('Modo de fundo inválido.')
    background_action='preserved_alpha' if has_cutout else 'kept'
    if mode=='remove' or (mode=='auto' and not has_cutout):
        import os
        import rembg
        os.environ['U2NET_HOME'] = str(model_dir)
        if not (Path(model_dir) / 'u2netp.onnx').exists():
            raise RuntimeError('Pesos de remoção de fundo ausentes. Execute Setup-Forge3D.')
        image = rembg.remove(image, session=rembg.new_session('u2netp', providers=['CPUExecutionProvider']))
        background_action='u2netp_cpu'
    if save_masked_source:image.save(Path(destination).with_name(Path(destination).stem+'_masked.png'))
    if image.getextrema()[3][0] < 255:
        bounds = image.getchannel('A').getbbox()
        if bounds is None:
            raise ValueError('A imagem está totalmente transparente.')
        if bounds[0]<=1 or bounds[1]<=1 or bounds[2]>=image.width-1 or bounds[3]>=image.height-1:
            warning_codes.append('touches_border')
            warnings.append('O objeto toca a borda: confira possíveis partes cortadas na referência.')
        image = image.crop(bounds)
    else:
        bounds=(0,0,image.width,image.height)
        if mode in ['keep','preserve_alpha']:
            warnings.append('Fundo opaco mantido; objetos sobrepostos/fundo complexo podem prejudicar a reconstrução.')
    side = max(image.size)
    canvas = Image.new('RGBA',(side,side),(0,0,0,0))
    canvas.alpha_composite(image,((side-image.width)//2,(side-image.height)//2))
    inner = round(512*foreground_ratio)
    canvas = canvas.resize((inner,inner),Image.Resampling.LANCZOS)
    if save_alpha:
        alpha_canvas=Image.new('RGBA',(512,512),(0,0,0,0))
        alpha_canvas.alpha_composite(canvas,((512-inner)//2,(512-inner)//2))
        alpha_canvas.save(Path(destination).with_name(Path(destination).stem+'_alpha.png'))
    output = Image.new('RGBA',(512,512),(*background_color,255))
    output.alpha_composite(canvas,((512-inner)//2,(512-inner)//2))
    output.convert('RGB').save(destination)
    return {'source_size':source_size,'effective_size':[512,512],'background_action':background_action,'background_color':list(background_color),'has_existing_alpha':has_cutout,'foreground_bbox':list(bounds),'foreground_ratio':foreground_ratio,'preparation_preset':preparation_preset,'normalization':f'RGB + alpha sobre RGB{tuple(background_color)}; encoder normaliza internamente','warnings':warnings,'warning_codes':warning_codes,'upscale_adds_detail':False,'occlusion_assessment':'unknown_single_view','source_sha256':hashlib.sha256(Path(source).read_bytes()).hexdigest(),'effective_sha256':hashlib.sha256(Path(destination).read_bytes()).hexdigest()}
