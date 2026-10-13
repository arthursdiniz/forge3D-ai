"""Regressions reproduced by the independent final review."""
import json
import subprocess
from pathlib import Path
import numpy as np
import pytest
import trimesh
from PIL import Image
from backend.texture_engine.import_safety import validate_resources
from backend.texture_engine.jobs import texture_metadata

ROOT=Path(__file__).resolve().parents[1]

@pytest.mark.parametrize('content,sidecars',[
    (b'mtllib\t../outside.mtl\nv 0 0 0',{}),
    (b'mtllib local.mtl',{'local.mtl':b'newmtl M\ndisp\t../outside.png'}),
])
def test_obj_whitespace_cannot_bypass_sidecar_path_validation(content,sidecars):
    with pytest.raises(ValueError):validate_resources('mesh.obj',content,sidecars)

@pytest.mark.parametrize('field,value',[
    ('normalTexture',{'index':0,'scale':.25}),
    ('occlusionTexture',{'index':0,'strength':.2}),
])
def test_unsupported_gltf_material_factors_are_rejected_before_loss(field,value):
    document={'asset':{'version':'2.0'},'materials':[{field:value}]}
    with pytest.raises(ValueError,match='material|factor'):
        validate_resources('model.gltf',json.dumps(document).encode(),{})

def test_retexturing_preserves_geometry_metrics_and_clears_projection_seed():
    parent={'geometry_generation_metrics':{'peak_vram_mb':7000,'inference_seconds':900},'texture_provider':'neural_multiview','peak_vram_mb':3800,'inference_seconds':64,'seed':44,'seed_supported':True,'offline_network_blocked':True}
    projection=texture_metadata(parent,{'provider':'reference_projection'},{'front_axis':'x'},'source-hash')
    assert projection['geometry_generation_metrics']==parent['geometry_generation_metrics']
    assert projection.get('seed') is None and projection.get('seed_supported') is False
    assert 'peak_vram_mb' not in projection and 'offline_network_blocked' not in projection

def blender_command(script,*arguments):
    executable=next((ROOT/'tools').glob('blender-*/blender.exe'),None)
    if executable is None:pytest.skip('Portable Blender required for integration proof.')
    result=subprocess.run([str(executable),'--background','--factory-startup','--disable-autoexec','--threads','2','--python-exit-code','1','--python',str(script),'--',*[str(value) for value in arguments]],capture_output=True,text=True,timeout=90)
    return result

def test_exported_obj_mtl_maps_resolve_inside_the_actual_package(tmp_path):
    mesh=trimesh.creation.box()
    mesh.visual=trimesh.visual.TextureVisuals(uv=np.zeros((len(mesh.vertices),2)),material=trimesh.visual.material.PBRMaterial(name='Red',baseColorTexture=Image.new('RGBA',(8,8),(220,40,20,255))))
    source=tmp_path/'source.glb';trimesh.Scene(mesh).export(source,include_normals=True)
    target=tmp_path/'export';target.mkdir();options=tmp_path/'options.json';options.write_text('{}')
    result=blender_command(ROOT/'blender/pipeline.py','--input',source,'--output',target,'--mode','export','--options',options)
    assert result.returncode==0,result.stdout+result.stderr
    package=target/'Forge3D_Asset';mtl=package/'Models/Model.mtl'
    maps=[line.split()[-1] for line in mtl.read_text().splitlines() if line.lstrip().startswith('map_')]
    assert maps,'Real exported OBJ must contain albedo map.'
    for uri in maps:
        path=(mtl.parent/uri).resolve()
        assert path.is_relative_to(package.resolve()) and path.is_file(),uri

def test_static_fbx_embedded_texture_import_needs_no_external_sidecar(tmp_path):
    fixture=tmp_path/'embedded.fbx'
    result=blender_command(ROOT/'tests/texture_embedded_fbx_fixture.py',fixture)
    assert result.returncode==0,result.stdout+result.stderr
    assert not list(tmp_path.glob('*.png'))
    target=tmp_path/'import';target.mkdir()
    result=blender_command(ROOT/'blender/import_static.py','--input',fixture,'--output',target)
    assert result.returncode==0,result.stdout+result.stderr
    scene=trimesh.load(target/'model.glb',force='scene',process=False)
    image=next(iter(scene.geometry.values())).visual.material.baseColorTexture
    assert image is not None and np.array_equal(np.asarray(image)[0,0,:3],[210,40,20])
