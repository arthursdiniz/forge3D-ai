"""Controlled real Blender renders and labeled evidence; no appearance retouching."""
import json,subprocess,sys
from pathlib import Path
from PIL import Image,ImageDraw,ImageFont
ROOT=Path(__file__).resolve().parents[1];qa=ROOT/'data/texture-fidelity-20261013';directory=qa/'diagnostics-final';directory.mkdir(exist_ok=True)
cases=[('historical',ROOT/'data/assets/3b09436697594d489cc9ace821a00f9b/model.glb',False),('before',qa/'global-image/model.glb',False),('after',qa/'hinata-regional-final-footprint/model.glb',False),('clay',qa/'hinata-regional-final-footprint/model.glb',True)]
for name,source,clay in cases:
    if '--sheets-only' in sys.argv:continue
    folder=directory/name;folder.mkdir(exist_ok=True);options={'front_axis':'negative_y','unlit':not clay,'clay':clay,'normalize_light':True,'render_resolution':384,'opposite_side':True};(folder/'options-384.json').write_text(json.dumps(options))
    with (folder/'render-384.log').open('w') as log:
        subprocess.run([str(ROOT/'tools/blender-4.5.3-windows-x64/blender.exe'),'--background','--factory-startup','--disable-autoexec','--threads','6','--python-exit-code','1','--python',str(ROOT/'blender/pipeline.py'),'--','--input',str(source),'--output',str(folder),'--mode','compare','--options',str(folder/'options-384.json')],cwd=ROOT,stdout=log,stderr=subprocess.STDOUT,check=True)
font=ImageFont.truetype('C:/Windows/Fonts/segoeui.ttf',20)
views=[('front','Frente'),('three_quarter','3/4'),('side','Lado'),('rear','Costas'),('side_opposite','Outro lado')]
tile=320;margin=14;canvas=Image.new('RGB',(5*(tile+margin)+margin,4*(tile+35)+90),'white');draw=ImageDraw.Draw(canvas)
draw.text((margin,10),'Hinata / 20.000 triângulos / mesmas câmeras / albedo sem iluminação nas três primeiras linhas',font=font,fill='black')
for row,(case,label) in enumerate([('historical','Histórico'),('before','Global corrigido'),('after','Refino regional'),('clay','Geometria / clay')]):
    for col,(view,title) in enumerate(views):
        x=margin+col*(tile+margin);y=70+row*(tile+35);draw.text((x,y),label+' / '+title,font=font,fill='black')
        with Image.open(directory/case/f'qa_{view}.png') as source:canvas.paste(source.convert('RGB').resize((tile,tile),Image.Resampling.LANCZOS),(x,y+30))
canvas.save(directory/'all-views.png')
folder=qa/'hinata-regional-final-footprint';size=360;canvas=Image.new('RGB',(3*(size+margin)+margin,3*(size+38)+86),'#edf0f4');draw=ImageDraw.Draw(canvas)
draw.text((margin,10),'Refino regional / pixels reais da referência / defeitos restantes visíveis',font=font,fill='black')
for row,(view,title) in enumerate(views[:3]):
    for col,(filename,label) in enumerate([('face_reference_core.png','Referência frontal'),(f'face_before_{view}.png','Antes / '+title),(f'face_after_{view}.png','Depois / '+title)]):
        x=margin+col*(size+margin);y=64+row*(size+38);draw.text((x,y),label,font=font,fill='black')
        with Image.open(folder/filename) as source:
            rgba=source.convert('RGBA');scale=min(size/rgba.width,size/rgba.height);rgba=rgba.resize((round(rgba.width*scale),round(rgba.height*scale)),Image.Resampling.NEAREST if scale>1 else Image.Resampling.LANCZOS);background=Image.new('RGB',(size,size),'#202632');background.paste(rgba,((size-rgba.width)//2,(size-rgba.height)//2),rgba.getchannel('A'));canvas.paste(background,(x,y+30))
canvas.save(directory/'face-before-after.png')
print('FIDELITY_ACTUAL_CONTROLLED_SHEETS_PASS',flush=True)
