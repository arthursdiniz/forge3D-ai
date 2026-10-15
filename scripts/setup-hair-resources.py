"""Download only pinned public MIT semantic + Apache2 Small resources to own folders."""
import hashlib,json,urllib.request
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];folder=ROOT/'models/hair';folder.mkdir(exist_ok=True)
SEG='7107bfc64610cec5b9e64a2c16a4f011b5f513e5';DEPTH='a561b849ebae10a6f5ef49e26c83cbbcd36c71bf';MODEL='03876f8651c73a60fe4c2c48294e09fcb6838fcf'
headers={'User-Agent':'Forge3D-Local-Hair-Setup'}
def fetch(url):return urllib.request.urlopen(urllib.request.Request(url,headers=headers),timeout=60).read()
def save(path,data):
    path.parent.mkdir(parents=True,exist_ok=True)
    if path.exists() and path.read_bytes()!=data:raise RuntimeError('Existing resource differs; preserve it: '+str(path))
    path.write_bytes(data)
segroot=ROOT/'vendor/anime-hair-segmentation'
for name in ['network.py','util.py','README.md','LICENSE']:
    data=fetch(f'https://raw.githubusercontent.com/siyeong0/Anime-Face-Segmentation/{SEG}/{name}')
    if name=='network.py':
        original=data;data=data.replace(b'weights=MobileNet_V2_Weights.IMAGENET1K_V1',b'weights=None')
        assert data!=original;save(segroot/'network.upstream.txt',original)
    save(segroot/name,data)
weight=fetch(f'https://raw.githubusercontent.com/siyeong0/Anime-Face-Segmentation/{SEG}/model/UNet.pth');assert len(weight)==6428741
assert hashlib.sha1(b'blob '+str(len(weight)).encode()+b'\0'+weight).hexdigest()=='e4a938d4aff61a1a639f55bc559f7fe1c9237f1a';save(folder/'anime-unet.pth',weight)
tree=json.loads(fetch(f'https://api.github.com/repos/DepthAnything/Depth-Anything-V2/git/trees/{DEPTH}?recursive=1'))['tree'];depthroot=ROOT/'vendor/Depth-Anything-V2'
for item in tree:
    name=item['path']
    if item['type']=='blob' and ((name.startswith('depth_anything_v2/') and name.endswith('.py')) or name in ['LICENSE','README.md','requirements.txt']):save(depthroot/name,fetch(f'https://raw.githubusercontent.com/DepthAnything/Depth-Anything-V2/{DEPTH}/{name}'))
weight=fetch(f'https://huggingface.co/depth-anything/Depth-Anything-V2-Small/resolve/{MODEL}/depth_anything_v2_vits.pth');assert len(weight)==99218434 and hashlib.sha256(weight).hexdigest()=='715fade13be8f229f8a70cc02066f656f2423a59effd0579197bbf57860e1378';save(folder/'depth-small.pth',weight)
digest=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
manifest={'licenses':['MIT','Apache-2.0'],'semantic':{'repo':'siyeong0/Anime-Face-Segmentation','revision':SEG,'license':'MIT','adaptation':'MobileNet weights=None; full trained state_dict contains encoder; prevents implicit pretrained download.'},'depth':{'repo':'DepthAnything/Depth-Anything-V2','code_revision':DEPTH,'model_revision':MODEL,'license':'Apache-2.0','model':'Small only; no larger noncommercial checkpoints'},'weights':[{'path':name,'bytes':(folder/name).stat().st_size,'sha256':digest(folder/name)} for name in ['anime-unet.pth','depth-small.pth']],'source_sha256':{p.relative_to(ROOT).as_posix():digest(p) for base in [segroot,depthroot] for p in base.rglob('*') if p.is_file() and p.suffix=='.py'}}
save(folder/'manifest.json',json.dumps(manifest,indent=2).encode());print('PINNED_PUBLIC_HAIR_RESOURCES_READY',sum(w['bytes'] for w in manifest['weights']),flush=True)
