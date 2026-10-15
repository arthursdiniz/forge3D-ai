"""Unmodified diagnostic montage and normal-lit clay evidence; no cosmetic edits."""
import json
from pathlib import Path
import numpy as np
from PIL import Image,ImageDraw
import trimesh
from backend.texture_engine.region_camera import RegionCamera
ROOT=Path(__file__).resolve().parents[1];QA=ROOT/'data/semantic-upgrade-20261014';out=QA/'comparisons';out.mkdir(exist_ok=True)
cases=[('Kageyama',QA/'A-kageyama/result',ROOT/'data/assets/323051d419ba4e47a4f421fd25e31d5f/model.glb'),('Hinata',QA/'B-hinata-head/result',ROOT/'data/assets/3c2829b70fe046328b86d2a1141736d4/model.glb'),('Stylized',QA/'C-stylized-naruto/result',QA/'C-stylized-baseline/model.glb'),('Uniform',QA/'B-uniform-real-multiview/result3',ROOT/'data/assets/323051d419ba4e47a4f421fd25e31d5f/model.glb')]
clay={}
for name,folder,source in cases:
    sheet=Image.new('RGB',(1024,4*540),(24,29,34));draw=ImageDraw.Draw(sheet)
    for row,view in enumerate(['front','left','right','back']):
        for column,when in enumerate(['before','after']):
            im=Image.open(folder/f'semantic_{when}_{view}.png').convert('RGBA');im.thumbnail((512,512));sheet.paste(im,(column*512,row*540+28),im);draw.text((column*512+12,row*540+8),f'{name} {view} {when} | actual unlit render',fill='white')
    sheet.save(out/(name+'-before-after.png'))
    before=trimesh.load(source,force='scene',process=False);after=trimesh.load(folder/'model.glb',force='scene',process=False);checks=[]
    for view,yaw in [('front',0),('left',90),('right',-90),('back',180)]:
        images=[]
        for label,scene in [('before',before),('after',after)]:
            c=RegionCamera(scene,'negative_y',512,yaw=yaw);normals=c.buffers[1][...,:3];light=np.array([-.4,.6,1]);light/=np.linalg.norm(light);brightness=.25+.75*np.maximum(0,normals@light);visible=c.buffers[0][...,3]>.5;im=np.zeros((512,512,4),'u1');im[...,:3]=np.rint(brightness[...,None]*190).astype('u1');im[...,3]=visible.astype('u1')*255;images.append(im);Image.fromarray(im).save(out/f'{name}-clay-{label}-{view}.png')
        checks.append({'view':view,'maximum_channel_difference':int(np.max(np.abs(images[0].astype(int)-images[1].astype(int)))),'silhouette_identical':bool(np.array_equal(images[0][...,3],images[1][...,3]))})
    clay[name]=checks
(out/'clay-checks.json').write_text(json.dumps(clay,indent=2))
print('SEMANTIC_REAL_VIEWS_AND_CLAY_RECORDED',flush=True)
