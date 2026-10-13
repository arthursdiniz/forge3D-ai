"""Scientific before/after montage from actual controlled Blender renders."""
from pathlib import Path
import argparse
from PIL import Image,ImageDraw,ImageFont
ROOT=Path(__file__).resolve().parents[1]
parser=argparse.ArgumentParser();parser.add_argument('--directory',type=Path,default=ROOT/'data/texture-engine-20261012/diagnostics');directory=parser.parse_args().directory
font_path=Path('C:/Windows/Fonts/segoeui.ttf')
font=ImageFont.truetype(str(font_path),18) if font_path.is_file() else ImageFont.load_default()
def sheet(rows,views,tile,filename):
    margin=16;header=76;cell_height=tile+36;width=len(views)*(tile+margin)+margin
    figure=Image.new('RGB',(width,len(rows)*cell_height+header+margin),'white');draw=ImageDraw.Draw(figure)
    draw.text((margin,12),'Hinata · 20.000 triângulos preservados · seis vistas neurais conjuntas',font=font,fill='black')
    draw.text((margin,38),'Atlas 4K · vistas nativas 512px · câmeras e iluminação controladas',font=font,fill='black')
    for row,(folder,label) in enumerate(rows):
        for col,(view,title) in enumerate(views):
            x=margin+col*(tile+margin);y=header+row*cell_height
            draw.text((x,y),f'{label} / {title}',font=font,fill='black')
            with Image.open(directory/folder/f'qa_{view}.png') as source:
                figure.paste(source.convert('RGB').resize((tile,tile),Image.Resampling.LANCZOS),(x,y+28))
    figure.save(directory/filename)
sheet([('before','Antes'),('after','Depois')],[('front','Frente'),('side','Lado'),('rear','Costas')],400,'before-after.png')
sheet([('before','Antes'),('after','Depois'),('clay','Clay'),('unlit','Albedo sem luz')],[('front','Frente'),('side','Lado'),('rear','Costas'),('side_opposite','Outro lado'),('three_quarter','Diagonal')],320,'all-views.png')
print('ACTUAL_DIAGNOSTIC_MONTAGES_CREATED')
