"""Install-time downloads only. Inference never calls this script."""
import hashlib
import json
import urllib.request
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

def read_json(url):
    request = urllib.request.Request(url, headers={'User-Agent':'Mozilla/5.0 Forge3D/1.0'})
    with urllib.request.urlopen(request, timeout=60) as response:
        return json.load(response)

def sha256(path):
    digest = hashlib.sha256()
    with path.open('rb') as stream:
        for block in iter(lambda: stream.read(4 * 1024 * 1024), b''):
            digest.update(block)
    return digest.hexdigest()

def download(url, path, expected=None):
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.exists() and (expected is None or sha256(path) == expected):
        print(f'Cached: {path}', flush=True)
        return
    temporary = path.with_suffix(path.suffix + '.download')
    print(f'Downloading {url}', flush=True)
    request = urllib.request.Request(url, headers={'User-Agent':'Mozilla/5.0 Forge3D/1.0'})
    with urllib.request.urlopen(request, timeout=120) as response, temporary.open('wb') as stream:
        while block := response.read(4 * 1024 * 1024):
            stream.write(block)
    if expected and sha256(temporary) != expected:
        raise RuntimeError(f'Checksum mismatch: {path}')
    temporary.replace(path)
    print(f'OK: {path.stat().st_size:,} bytes', flush=True)

def main():
    pinned_revision = '5b521936b01fbe1890f6f9baed0254ab6351c04a'
    info = read_json(f'https://huggingface.co/api/models/stabilityai/TripoSR/revision/{pinned_revision}?blobs=true')
    revision = info['sha']
    records = []
    for name in ['config.yaml', 'model.ckpt', 'README.md']:
        entry = next(s for s in info['siblings'] if s['rfilename'] == name)
        expected = entry.get('lfs', {}).get('sha256') or {'config.yaml':'74ca708ce086bf68e97709ea6b3d91f14717921c04691e84043f0eb8fcc68e62','README.md':'5c12ef5b850c6ee2aa7454b1a264f6f8dfa95164384dbb1ab374acd917aa558b'}[name]
        path = ROOT / 'models' / 'triposr' / name
        download(f'https://huggingface.co/stabilityai/TripoSR/resolve/{revision}/{name}', path, expected)
        records.append({'name': name, 'sha256': sha256(path), 'bytes': path.stat().st_size})
    dino = read_json('https://huggingface.co/api/models/facebook/dino-vitb16/revision/f205d5d8e640a89a2b8ef0369670dfc37cc07fc2')
    download(f"https://huggingface.co/facebook/dino-vitb16/resolve/{dino['sha']}/config.json", ROOT / 'models/dino/config.json')
    download('https://github.com/danielgatis/rembg/releases/download/v0.0.0/u2netp.onnx', ROOT / 'models/rembg/u2netp.onnx')
    (ROOT / 'models/manifest.json').write_text(json.dumps({'provider':'triposr','weight_revision':revision,'dino_revision':dino['sha'],'files':records}, indent=2))
    version = '4.5.3'
    filename = f'blender-{version}-windows-x64.zip'
    base = 'https://download.blender.org/release/Blender4.5/'
    checksum_file = ROOT / 'tools' / f'blender-{version}.sha256'
    download(base + f'blender-{version}.sha256', checksum_file)
    expected = next(line.split()[0] for line in checksum_file.read_text().splitlines() if filename in line)
    archive = ROOT / 'tools' / filename
    download(base + filename, archive, expected)
    executable = ROOT / 'tools' / f'blender-{version}-windows-x64' / 'blender.exe'
    if not executable.exists():
        with zipfile.ZipFile(archive) as package:
            for member in package.infolist():
                resolved = (ROOT / 'tools' / member.filename).resolve()
                if not resolved.is_relative_to((ROOT / 'tools').resolve()):
                    raise RuntimeError('Unsafe archive path')
            package.extractall(ROOT / 'tools')
    print(f'Blender ready: {executable}', flush=True)

if __name__ == '__main__':
    main()
