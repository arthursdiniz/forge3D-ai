"""Measure UV surface coverage on the SAME preserved neural geometry."""
import json
import sys
import time
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
import numpy as np
import trimesh
import xatlas
from backend.neural_texture import rasterize_positions
mesh=trimesh.load(ROOT/'data/quality-upgrade/improved/stylized_character/quality/original.glb',force='mesh',process=False)
results=[]
for padding in [16,4]:
    started=time.perf_counter();atlas=xatlas.Atlas()
    atlas.add_mesh(np.asarray(mesh.vertices,dtype=np.float32),np.asarray(mesh.faces,dtype=np.uint32))
    options=xatlas.PackOptions();options.resolution=2048;options.padding=padding;options.bilinear=True
    atlas.generate(pack_options=options)
    mapping,indices,uv=atlas[0]
    raster=rasterize_positions(mesh.vertices[mapping],indices,uv,2048)
    result={'padding':padding,'atlas_size':[atlas.width,atlas.height],'charts':atlas.chart_count,'surface_texels':int((raster[...,3]>0.5).sum()),'coverage_percent':round(float((raster[...,3]>0.5).mean()*100),2),'seconds':round(time.perf_counter()-started,2)}
    print(json.dumps(result),flush=True);results.append(result)
(ROOT/'data/quality-upgrade/atlas-ablation.json').write_text(json.dumps(results,indent=2))
