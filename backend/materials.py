"""Actual exported channel paths; no fabricated PBR maps."""
from pathlib import Path

def texture_channels(directory):
    files=sorted(Path(directory).glob('*.png'))
    def find(prefix):return next(('Textures/'+file.name for file in files if file.name.lower().startswith(prefix)),None)
    base=find('basecolor') or next(('Textures/'+file.name for file in files if not file.name.lower().startswith(('normal','roughness','metallic'))),None)
    return {'base_color':base,'normal':find('normal'),'roughness':find('roughness'),'metallic':find('metallic')}
