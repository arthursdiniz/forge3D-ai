"""Real render/export evidence; leaves inference and original models untouched."""
import hashlib
import json
import shutil
import struct
import subprocess
from pathlib import Path
import sys
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from backend.quality_settings import generation_settings
from backend.hunyuan_provider import MODEL_REV,CODE_REV

BASE=ROOT/'data/character-advanced-20261011'
PROOF=BASE/'validation-evidence'
BLENDER=next((ROOT/'tools').glob('blender-*/blender.exe'))

def read(path):return json.loads(path.read_text(encoding='utf-8'))
def digest(path):return hashlib.sha256(path.read_bytes()).hexdigest()

def attributes(path):
    import numpy as np
    data=path.read_bytes();assert data[:4]==b'glTF'
    size,kind=struct.unpack_from('<II',data,12);assert kind==0x4e4f534a
    doc=json.loads(data[20:20+size]);offset=20+size
    size,kind=struct.unpack_from('<II',data,offset);assert kind==0x004e4942
    binary=data[offset+8:offset+8+size]
    report=[]
    for mesh in doc['meshes']:
        for primitive in mesh['primitives']:
            result={}
            for name in ['POSITION','NORMAL','TEXCOORD_0']:
                accessor=doc['accessors'][primitive['attributes'][name]]
                view=doc['bufferViews'][accessor['bufferView']]
                assert accessor['componentType']==5126
                channels={'VEC2':2,'VEC3':3}[accessor['type']]
                start=view.get('byteOffset',0)+accessor.get('byteOffset',0)
                values=np.ndarray((accessor['count'],channels),dtype='<f4',buffer=binary,offset=start,strides=(view.get('byteStride',channels*4),4))
                assert np.isfinite(values).all()
                result[name]={'count':len(values),'finite':True}
                if name=='NORMAL':
                    lengths=np.linalg.norm(values,axis=1)
                    result[name].update(zero_normals=int((lengths<1e-6).sum()),min_length=float(lengths.min()))
                    assert (lengths>.5).all()
                if name=='TEXCOORD_0':assert (values>=-1e-5).all() and (values<=1.00001).all()
            report.append(result)
    return report

def blender(source,target,mode,options):
    target.mkdir(parents=True,exist_ok=True)
    settings=target/'options.json';settings.write_text(json.dumps(options),encoding='utf-8')
    with (target/'blender.log').open('w',encoding='utf-8') as log:
        subprocess.run([str(BLENDER),'--background','--factory-startup','--disable-autoexec','--threads','6','--python-exit-code','1','--python',str(ROOT/'blender/pipeline.py'),'--','--input',str(source),'--output',str(target),'--mode',mode,'--options',str(settings)],cwd=ROOT,stdout=log,stderr=subprocess.STDOUT,check=True,timeout=300,creationflags=subprocess.CREATE_NO_WINDOW)

def main():
    if PROOF.exists():raise RuntimeError('Preserve prior evidence; this validation directory already exists.')
    PROOF.mkdir()
    paths={'baseline_triposr':BASE/'baseline-triposr-quality','triposr_corrected':BASE/'triposr-corrected','triposg_quality42':BASE/'triposg-quality42','advanced42':BASE/'advanced-validated-prototype/candidates/0','advanced43':BASE/'advanced-validated-prototype/candidates/1'}
    proof={'input_sha256':digest(ROOT/'data/test-inputs/hinata-shoyo-reference-20261011.png'),'variants':{},'scope':'Five matching directions, original materials and neutral clay. No geometry smoothing or hole filling. Blender renders double sided; browser culling checked separately.'}
    for name,directory in paths.items():
        source=directory/'model.glb';unchanged=digest(source)
        record={'model_sha256':unchanged,'renders':{}}
        for appearance in ['textured','clay']:
            target=PROOF/name/appearance
            blender(source,target,'compare',{'front_axis':'x' if 'triposr' in name else 'negative_y','clay':appearance=='clay','opposite_side':True,'render_resolution':768})
            views=['front','side','side_opposite','rear','three_quarter']
            assert all((target/f'qa_{view}.png').is_file() for view in views)
            record['renders'][appearance]={view:str((target/f'qa_{view}.png').relative_to(BASE)) for view in views}
            if appearance=='textured':record['integrity']=read(target/'comparison_report.json')['after']['integrity']
        assert digest(source)==unchanged
        proof['variants'][name]=record
        print('REAL_FIVE_VIEWS_TEXTURE_AND_CLAY '+name,flush=True)
    exports={}
    for name,directory in {'balanced':BASE/'hunyuan-mini256-seed42','quality':BASE/'hunyuan-mini384-seed42','advanced42':paths['advanced42'],'advanced43':paths['advanced43']}.items():
        source=directory/'model.glb';target=PROOF/name/'export'
        validation=attributes(source)
        blender(source,target,'export',{'pipeline':'URP'})
        report=read(target/'fbx_validation.json');assert report['passed']
        exports[name]={'validation':report,'glb_attributes':validation,'model_sha256':digest(source)}
        print('REAL_FBX_ROUNDTRIP '+name,flush=True)
    # Experimental profiles used the same official weights and native processor.
    for name,resolution in [('balanced',256),('quality',384)]:
        source=BASE/f'hunyuan-mini{resolution}-seed42'
        metadata=read(source/'inference.json')
        for key,value in [('mc_resolution',resolution),('num_inference_steps',50),('guidance_scale',5),('model_cpu_offload',False),('encoder_resolution',518),('dtype','float16')]:assert metadata[key]==value
        assert metadata['source_sha256']==proof['input_sha256']
    advanced=read(BASE/'advanced-validated-prototype/inference.json')
    assert advanced['effective_settings']==generation_settings('advanced','hunyuan_mini')
    assert advanced['advanced']['candidate_count']==2 and advanced['advanced']['generation_wall_seconds']<300
    # Restore prototype previews in the intended directory after relative-path bug.
    for index,name in enumerate(['advanced42','advanced43']):
        directory=paths[name]
        for image in (PROOF/name/'textured').glob('qa_*.png'):shutil.copy2(image,directory/image.name)
        if index==0:
            for image in directory.glob('qa_*.png'):shutil.copy2(image,BASE/'advanced-validated-prototype'/image.name)
    proof.update(exports=exports,passed=True)
    (PROOF/'evidence.json').write_text(json.dumps(proof,indent=2),encoding='utf-8')
    marker={'passed':True,'weight_revision':MODEL_REV,'code_revision':CODE_REV,'profiles':{name:generation_settings(name,'hunyuan_mini') for name in ['balanced','quality','advanced']},'evidence':str((PROOF/'evidence.json').relative_to(ROOT)),'scope':'Real native CUDA FP16 inference, five-view inspection and FBX roundtrip; technical/visual limits retained. Unity product flow follows separately.'}
    (ROOT/'models/hunyuan-mini/validation.json').write_text(json.dumps(marker,indent=2),encoding='utf-8')
    print('CHARACTER_RENDER_EXPORT_LOCAL_VALIDATION_PASS',flush=True)

if __name__=='__main__':main()
