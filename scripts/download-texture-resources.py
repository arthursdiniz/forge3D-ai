"""Explicit, user-authorized public downloads. Never called during inference."""
import argparse
import hashlib
import json
import os
import time
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
RESOURCES = {
    'sdxl': ('stabilityai/stable-diffusion-xl-base-1.0', '462165984030d82259a11f4367a4eed129e94a7b', 'CreativeML Open RAIL++-M'),
    'adapter': ('huanngzh/mv-adapter', '6de4033df6b53366f3c009d22f5ec434bb55e59f', 'Apache-2.0'),
}

def sha256(path):
    digest = hashlib.sha256()
    with path.open('rb') as stream:
        while chunk := stream.read(8 * 1024 * 1024): digest.update(chunk)
    return digest.hexdigest()

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--authorized-local-test', action='store_true', required=True)
    args = parser.parse_args()
    root = ROOT / 'models/texture'
    root.mkdir(parents=True, exist_ok=True)
    for key, (repo, revision, license_name) in RESOURCES.items():
        with urllib.request.urlopen(f'https://huggingface.co/api/models/{repo}/revision/{revision}?blobs=true', timeout=60) as response:
            metadata = json.load(response)
        if metadata.get('gated'): raise RuntimeError('Restricted resources require a separate authorized setup.')
        files = []
        for entry in metadata['siblings']:
            name = entry['rfilename']
            if key == 'sdxl':
                selected = name in ['LICENSE.md', 'README.md', 'model_index.json'] or (name.startswith(('scheduler/', 'tokenizer/', 'tokenizer_2/', 'text_encoder/', 'text_encoder_2/', 'unet/', 'vae/')) and (name.endswith(('.json', '.txt')) or name.endswith('.fp16.safetensors')))
            else:
                selected = name in ['README.md', 'LICENSE', 'LICENSE.md', 'mvadapter_ig2mv_sdxl.safetensors', 'mvadapter_tg2mv_sdxl.safetensors']
            if not selected: continue
            path = root / key / name
            path.parent.mkdir(parents=True, exist_ok=True)
            size = entry.get('size')
            expected = entry.get('lfs', {}).get('sha256')
            url = f'https://huggingface.co/{repo}/resolve/{revision}/{name}'
            if path.exists() and (size is None or path.stat().st_size == size) and (expected is None or sha256(path) == expected):
                digest = sha256(path)
            else:
                temporary = path.with_name(path.name + '.part')
                count = 0; digestor = hashlib.sha256(); last = time.monotonic()
                with urllib.request.urlopen(url, timeout=120) as source, temporary.open('wb') as target:
                    while chunk := source.read(8 * 1024 * 1024):
                        count += len(chunk); digestor.update(chunk); target.write(chunk)
                        if time.monotonic() - last > 30:
                            print(json.dumps({'file': name, 'bytes': count, 'total': size}), flush=True); last = time.monotonic()
                digest = digestor.hexdigest()
                if size is not None and count != size: raise RuntimeError(f'Size mismatch: {name}')
                if expected and digest != expected: raise RuntimeError(f'SHA256 mismatch: {name}')
                os.replace(temporary, path)
            files.append({'path': name, 'bytes': path.stat().st_size, 'sha256': digest, 'source': url})
            print(json.dumps({'verified': key + '/' + name, 'bytes': path.stat().st_size}), flush=True)
        manifest = {'download_complete': True, 'repo': repo, 'revision': revision, 'license': license_name, 'authorization': 'User explicitly authorized public downloads and personal local tests on 2026-10-12.', 'files': files}
        (root / key / 'download_manifest.json').write_text(json.dumps(manifest, indent=2), encoding='utf-8')
    print('TEXTURE_RESOURCE_DOWNLOAD_VERIFIED', flush=True)

if __name__ == '__main__': main()
