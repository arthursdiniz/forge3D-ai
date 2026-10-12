import json
import subprocess
from pathlib import Path
import numpy as np
import pytest
import trimesh
from PIL import Image


def test_normal_operation_orients_uv_seam_patches_without_changing_shape_or_uvs(tmp_path):
    root=Path(__file__).resolve().parents[1]
    blender=next((root/'tools').glob('blender-*/blender.exe'),None)
    if blender is None:pytest.skip('Local Blender integration test requires portable Blender.')
    sphere=trimesh.creation.icosphere(subdivisions=1)
    vertices=sphere.vertices[sphere.faces].reshape(-1,3)
    faces=np.arange(len(vertices)).reshape(-1,3)[:,::-1]
    uv=np.tile([[0,0],[1,0],[.5,1]],(len(faces),1))
    mesh=trimesh.Trimesh(vertices=vertices,faces=faces,process=False)
    mesh.visual=trimesh.visual.TextureVisuals(uv=uv,image=Image.new('RGB',(8,8),'orange'))
    source=tmp_path/'inverted-seams.glb';mesh.export(source,include_normals=True)
    target=tmp_path/'result';options=tmp_path/'options.json'
    options.write_text(json.dumps({'operation':'recalculate_normals'}))
    result=subprocess.run([str(blender),'--background','--factory-startup','--disable-autoexec','--threads','2','--python-exit-code','1','--python',str(root/'blender/pipeline.py'),'--','--input',str(source),'--output',str(target),'--mode','transform','--options',str(options)],capture_output=True,text=True,timeout=60)
    assert result.returncode==0,result.stdout[-4000:]+result.stderr
    processed=trimesh.load(target/'model.glb',force='scene',process=False).to_geometry()
    welded=trimesh.Trimesh(vertices=processed.vertices,faces=processed.faces,process=False)
    welded.merge_vertices()
    assert welded.is_watertight and welded.is_winding_consistent
    assert welded.volume>0
    # Face-corner position/UV pairs must survive face reversal unchanged.
    def corners(m):
        return sorted(tuple(sorted(tuple(np.round(np.r_[m.vertices[i],m.visual.uv[i]],6)) for i in face)) for face in m.faces)
    assert corners(mesh)==corners(processed)
    assert len(processed.faces)==len(mesh.faces)
