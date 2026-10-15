import importlib.util
import numpy as np
import pytest
import trimesh
from PIL import Image

def engine_module(name):
    assert importlib.util.find_spec('backend.texture_engine') is not None, 'Independent Texture Engine is missing'
    return __import__('backend.texture_engine.' + name, fromlist=[name])

def plane(z=.5, material=None):
    return trimesh.Trimesh(vertices=[[-.5,-.5,z],[.5,-.5,z],[.5,.5,z],[-.5,.5,z]], faces=[[0,1,2],[0,2,3]], vertex_normals=[[0,0,1]]*4, visual=trimesh.visual.TextureVisuals(uv=[[0,0],[1,0],[1,1],[0,1]],material=material), process=False)

def test_identity_accounts_for_world_instances_and_uv_seams():
    identity = engine_module('identity')
    scene = trimesh.Scene()
    mesh = plane()
    scene.add_geometry(mesh, geom_name='shared', node_name='one')
    scene.graph.update(frame_to='two', geometry='shared', matrix=trimesh.transformations.translation_matrix([2,0,0]))
    result = scene.copy()
    # UV seams may duplicate all three corners without changing triangles.
    duplicate = trimesh.Trimesh(vertices=mesh.vertices[mesh.faces].reshape(-1,3),faces=np.arange(6).reshape(-1,3),process=False)
    result.geometry['shared'] = duplicate
    assert identity.compare_geometry(scene,result)['equivalent']
    result.graph.update(frame_to='two', geometry='shared', matrix=trimesh.transformations.translation_matrix([2.01,0,0]))
    assert not identity.compare_geometry(scene,result)['equivalent']

def test_identity_rejects_reversed_winding_and_missing_instance():
    identity=engine_module('identity')
    scene=trimesh.Scene(plane()); changed=scene.copy()
    next(iter(changed.geometry.values())).faces=next(iter(changed.geometry.values())).faces[:,::-1]
    assert not identity.compare_geometry(scene,changed)['equivalent']
    changed=scene.copy();changed.graph.update(frame_to='extra',geometry=next(iter(changed.geometry)),matrix=np.eye(4))
    assert not identity.compare_geometry(scene,changed)['equivalent']

def test_texture_contract_rejects_effectless_projection_options():
    contracts=engine_module('contracts')
    assert contracts.TextureOptions().provider=='reference_projection'
    for value in [{'provider':'reference_projection','prompt':'anime'}, {'provider':'reference_projection','seed':1}, {'resolution':512}, {'unused':1}]:
        with pytest.raises(ValueError):contracts.TextureOptions(**value)
    settings=contracts.TextureOptions(provider='neural_multiview',prompt='orange uniform',style='anime',seed=44)
    assert settings.prompt=='orange uniform'

def test_uv_creation_preserves_triangles_and_data_maps_prevent_rewrap():
    uv=engine_module('uv');identity=engine_module('identity')
    mesh=trimesh.creation.box();before=trimesh.Scene(mesh)
    after,report=uv.prepare_uv(before,'auto',1024)
    assert identity.compare_geometry(before,after)['equivalent']
    assert report[0]['created'] and report[0]['valid'] and report[0]['overlap_percent']<1
    mesh=plane(material=trimesh.visual.material.PBRMaterial(normalTexture=Image.new('RGB',(8,8),(128,128,255))))
    with pytest.raises(ValueError,match='rebake'):uv.prepare_uv(trimesh.Scene(mesh),'new',1024)
    after,report=uv.prepare_uv(trimesh.Scene(mesh),'preserve',1024)
    assert np.array_equal(next(iter(after.geometry.values())).visual.uv,mesh.visual.uv)

def test_uv_copy_preserves_imported_authored_normals_instead_of_recomputing_them():
    uv=engine_module('uv')
    mesh=plane();mesh.vertex_normals=np.tile([.4,0,np.sqrt(.84)],(len(mesh.vertices),1))
    normals=mesh.vertex_normals.copy();result,_=uv.prepare_uv(trimesh.Scene(mesh),'preserve',1024)
    assert np.allclose(next(iter(result.geometry.values())).vertex_normals,normals,atol=1e-7)

def test_uv_retexturing_geometry_names_cannot_overwrite_a_later_source_instance():
    uv=engine_module('uv');identity=engine_module('identity')
    scene=trimesh.Scene();scene.add_geometry(plane(),geom_name='texture_001',node_name='first')
    scene.add_geometry(plane(-.5),geom_name='texture_000',node_name='second')
    result,_=uv.prepare_uv(scene,'preserve',1024)
    assert identity.compare_geometry(scene,result)['equivalent']

def test_uv_overlap_detected_instead_of_silently_overwritten():
    uv=engine_module('uv')
    mesh=plane(); mesh.faces=np.vstack([mesh.faces,mesh.faces])
    report=uv.inspect_uv(mesh,128)
    assert report['overlap_percent']>95
    with pytest.raises(ValueError,match='overlap'):uv.prepare_uv(trimesh.Scene(mesh),'preserve',1024)

def test_new_uv_cannot_silently_discard_source_alpha():
    uv=engine_module('uv')
    mesh=plane(material=trimesh.visual.material.PBRMaterial(baseColorTexture=Image.new('RGBA',(8,8),(255,0,0,50)),alphaMode='MASK'))
    with pytest.raises(ValueError,match='rebake'):uv.prepare_uv(trimesh.Scene(mesh),'new',1024)

def test_provider_lifecycle_releases_scene_and_uses_real_projection(tmp_path):
    providers=engine_module('providers')
    provider=providers.TextureProvider(tmp_path,'reference_projection');image=np.zeros((32,32,4),np.uint8);image[1:-1,1:-1]=[0,255,0,255]
    provider.prepare(trimesh.Scene(plane()),{'front':image},{'provider':'reference_projection','resolution':1024,'uv_mode':'preserve'},tmp_path)
    provider.generate();report=provider.finalize();provider.release()
    assert report['geometry']['equivalent'] and report['copied_percent']>90 and provider.session is None

def test_texture_errors_distinguish_resources_geometry_and_vram():
    errors=engine_module('errors')
    for message,code in [('UV replacement requires rebake','UV_REBAKE_REQUIRED'),('Geometry identity failed after GLB reimport','GEOMETRY_IDENTITY_FAILED'),('SHA256 mismatch','LOCAL_RESOURCES_INVALID'),('CUDA out of memory','CUDA_OOM'),('Static meshes only','IMPORT_INVALID')]:
        assert errors.classify_texture_failure(message)['code']==code

def test_fusion_preserves_normal_and_full_scene_occlusion(tmp_path):
    pipeline=engine_module('pipeline');identity=engine_module('identity')
    normal=Image.new('RGB',(8,8),(128,128,255))
    scene=trimesh.Scene()
    scene.add_geometry(plane(.5,trimesh.visual.material.PBRMaterial(name='front',normalTexture=normal)),node_name='front')
    scene.add_geometry(plane(-.5,trimesh.visual.material.PBRMaterial(name='occluded')),node_name='occluded')
    rgba=np.zeros((64,64,4),np.uint8);rgba[2:-2,2:-2]=[255,0,0,255]
    report=pipeline.texture_scene(scene,{'front':rgba},tmp_path,{'provider':'reference_projection','resolution':1024,'uv_mode':'preserve','front_axis':'negative_y'})
    restored=trimesh.load(tmp_path/'model.glb',force='scene',process=False)
    assert identity.compare_geometry(scene,restored)['equivalent']
    assert report['geometry']['equivalent'] and report['synthesized_percent']==0
    materials=[g.visual.material for g in restored.geometry.values()]
    front=next(m for m in materials if m.name=='front');hidden=next(m for m in materials if m.name=='occluded')
    assert np.asarray(front.baseColorTexture)[512,512,0]>240
    assert np.allclose(np.asarray(hidden.baseColorTexture)[512,512,:3],[188,188,188],atol=1)
    assert np.array_equal(np.asarray(front.normalTexture),np.asarray(normal))

def test_pbr_packing_uses_linear_channels_and_factors():
    materials=engine_module('materials')
    packed=np.array([[[0,64,128,255],[0,255,0,255]]],dtype=np.uint8)
    result=materials.unity_metallic_smoothness(packed,metallic_factor=.5,roughness_factor=.8)
    assert np.array_equal(result[...,0],[[64,0]])
    assert np.array_equal(result[...,3],[[204,51]])
    assert np.all(result[...,1:3]==0)

def test_native_controls_match_front_top_orientation_and_projection():
    native=engine_module('native')
    mesh=plane();scene=trimesh.Scene(mesh)
    renderer=native.NativeControls(scene,'negative_y',128)
    assert renderer.controls.shape==(6,6,128,128)
    # A +Y point must appear near the top of a generated front view.
    points=np.array([[0,.3,.5],[0,-.3,.5]])
    image=np.zeros((128,128,4),np.uint8);image[:64]=[255,0,0,255];image[64:]=[0,0,255,255]
    colors,weight=renderer.project('front',points,np.array([[0,0,1]]*2),image)
    assert weight.min()>.5 and colors[0,0]>.95 and colors[1,2]>.95
    assert np.allclose(renderer.controls[:, :3,:, :][...,0,0],.5)

def test_export_material_records_keep_distinct_pbr_slots_and_source_alpha(tmp_path):
    export=engine_module('export_materials')
    packed=Image.fromarray(np.array([[[0,64,128,255]]]*4,np.uint8))
    first=trimesh.visual.material.PBRMaterial(name='Fabric',baseColorTexture=Image.new('RGBA',(8,8),(255,0,0,180)),baseColorFactor=[255,255,255,128],metallicRoughnessTexture=packed,occlusionTexture=Image.new('RGB',(8,8),(220,32,16)),metallicFactor=.5,roughnessFactor=.8,alphaMode='BLEND')
    second=trimesh.visual.material.PBRMaterial(name='Steel',metallicFactor=.9,roughnessFactor=.2)
    scene=trimesh.Scene();scene.add_geometry(plane(material=first));scene.add_geometry(plane(-.5,second))
    records=export.export_materials(scene,tmp_path)
    assert [r['name'] for r in records]==['Fabric','Steel']
    assert records[0]['alpha_mode']=='BLEND' and abs(records[0]['color'][3]-128/255)<1e-6
    pixels=np.asarray(Image.open(tmp_path/records[0]['metallic_smoothness']))
    assert pixels[0,0,0]==64 and pixels[0,0,3]==204
    assert records[1]['metallic']==pytest.approx(.9) and records[1]['roughness']==pytest.approx(.2)
    assert np.asarray(Image.open(tmp_path/records[0]['unity_occlusion']))[0,0,1]==220
