"""Contact sheets of real Blender renders, no generated/repaired pixels."""
from pathlib import Path
from PIL import Image,ImageDraw,ImageFont
ROOT=Path(__file__).resolve().parents[1]
BASE=ROOT/'data/character-advanced-20261011/validation-evidence'
FONT=ImageFont.truetype('C:/Windows/Fonts/segoeui.ttf',18)
SMALL=ImageFont.truetype('C:/Windows/Fonts/segoeui.ttf',14)

def main():
    variants=[('baseline_triposr','TripoSR original'),('advanced42','Avançado / seed42'),('advanced43','Avançado / seed43')]
    summary=Image.new('RGB',(1020,800),'#182127');draw=ImageDraw.Draw(summary)
    draw.text((20,12),'Hinata — renders reais antes/depois',font=FONT,fill='white')
    for row,appearance in enumerate(['textured','clay']):
        for col,(name,label) in enumerate(variants):
            x=10+340*col;y=48+354*row
            draw.text((x,y),label+(' · material' if row==0 else ' · neutro'),font=FONT,fill='white')
            image=Image.open(BASE/name/appearance/'qa_front.png').convert('RGB').resize((324,324),Image.Resampling.LANCZOS)
            summary.paste(image,(x,y+24))
    draw.text((20,765),'Sem suavização/fechamento de buracos. Rosto e dedos limitados; projeção frontal, costas neutras.',font=SMALL,fill='#b6c4cf')
    summary.save(BASE/'hinata-before-after.png')
    views=[('front','Frente'),('side','Lado'),('side_opposite','Lado oposto'),('rear','Costas'),('three_quarter','3/4')]
    for appearance in ['textured','clay']:
        sheet=Image.new('RGB',(1420,1220),'#182127');draw=ImageDraw.Draw(sheet)
        rows=[('baseline_triposr','TripoSR original'),('triposg_quality42','TripoSG Quality / seed42'),('advanced42','Avançado / seed42'),('advanced43','Avançado / seed43')]
        for row,(name,label) in enumerate(rows):
            y=12+row*294;draw.text((12,y),label,font=FONT,fill='white')
            for col,(view,title) in enumerate(views):
                x=12+col*280;draw.text((x,y+24),title,font=SMALL,fill='#b6c4cf')
                image=Image.open(BASE/name/appearance/f'qa_{view}.png').convert('RGB').resize((264,264),Image.Resampling.LANCZOS)
                sheet.paste(image,(x,y+44))
        sheet.save(BASE/f'hinata-five-views-{appearance}.png')
    print('REAL_RENDER_CONTACT_SHEETS_CREATED')
if __name__=='__main__':main()
