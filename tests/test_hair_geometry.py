import numpy as np
import trimesh
import pytest
from PIL import Image

SCALP={'status':'reviewable','center':[0,.7,0],'radii':[.14,.18,.13]}

def test_curved_variable_profile_is_closed_and_has_a_real_tip():
    from backend.hair.curves import sweep_clump
    from backend.hair.metrics import mesh_integrity
    curve=np.array([[0,.82,.10],[.04,.90,.15],[.11,1.03,.10]])
    mesh=sweep_clump(curve,.045,.023,profile='triangular',curvature=.08)
    report=mesh_integrity(mesh)
    assert report['watertight'] and report['winding_consistent'] and report['degenerate_triangles']==0
    assert report['volume']>0 and np.isfinite(mesh.vertex_normals).all()
    assert np.any(np.all(np.isclose(mesh.vertices,curve[-1],atol=1e-8),axis=1))

def test_hair_base_volume_is_nonuniform_and_buzz_is_conservative():
    from backend.hair.volume import base_volume
    scalp=SCALP
    short=base_volume(scalp,{'volume':.025,'lateral_volume':.015,'top_height':.015,'back_volume':.015})
    fluffy=base_volume(scalp,{'volume':.20,'lateral_volume':.25,'top_height':.30,'back_volume':.15})
    assert short.is_watertight and fluffy.is_watertight and fluffy.volume>short.volume
    assert fluffy.extents[0]>short.extents[0] and fluffy.extents[1]>short.extents[1]

def test_reconstruction_preserves_original_geometry_uv_normals_and_maps(tmp_path):
    from backend.hair.pipeline import reconstruct_hair
    original=trimesh.creation.icosphere(subdivisions=2,radius=.14);original.apply_translation([0,.7,0]);uv=np.column_stack([np.linspace(0,1,len(original.vertices)),np.linspace(1,0,len(original.vertices))]);original.visual=trimesh.visual.TextureVisuals(uv=uv,material=trimesh.visual.material.PBRMaterial(name='Original',baseColorTexture=Image.new('RGBA',(8,8),'orange'),normalTexture=Image.new('RGB',(8,8),(128,128,255))))
    original.vertex_normals=np.asarray(original.vertex_normals).copy();scene=trimesh.Scene(original)
    analysis={'scalp':SCALP,'understanding':{'preset':'anime_spiky','hair_color':[225,115,30],'attributes':{'volume':.12,'lateral_volume':.12,'top_height':.15,'back_volume':.08,'spikes':.8,'thickness':.06,'fringe':.2,'length':.3,'curvature':.02},'tips':[{'tip_world':[.13,1.03,.12],'root_world':[.04,.83,.12],'width':.08,'zone':'top'}]}}
    result,report=reconstruct_hair(scene,analysis,{'reviewed':True,'front_axis':'negative_y'},tmp_path)
    assert report['protected_geometry']['equivalent'] and report['source_retained'] and report['hair_meshes']
    assert all(c['root_base_distance']<1e-8 for c in report['clumps'])
    name=next(iter(scene.geometry));before=scene.geometry[name];after=result.geometry[name]
    assert np.array_equal(before.vertices,after.vertices) and np.array_equal(before.faces,after.faces)
    assert np.array_equal(before.visual.uv,after.visual.uv) and np.array_equal(before.vertex_normals,after.vertex_normals)
    assert np.array_equal(np.asarray(before.visual.material.normalTexture),np.asarray(after.visual.material.normalTexture))
    assert all(c['normals_within_1e_6'] and c['uv_within_1e_6'] and all(c['original_maps_equal_pixels'].values()) for c in report['source_channel_roundtrip'])
    assert all(c['uv_valid'] and c['geometric_topology']['watertight'] for c in report['exported_hair_topology'].values())

def test_uncertain_scalp_or_unreviewed_mask_cannot_publish_hair(tmp_path):
    from backend.hair.pipeline import reconstruct_hair
    import pytest
    scene=trimesh.Scene(trimesh.creation.icosphere(radius=.2))
    with pytest.raises(ValueError):reconstruct_hair(scene,{'scalp':SCALP},{'reviewed':False},tmp_path)
    result,report=reconstruct_hair(scene,{'scalp':{'status':'unsafe_original_retained'}},{'reviewed':True},tmp_path)
    assert report['status']=='inconclusive_previous_retained' and len(result.geometry)==len(scene.geometry)

def test_adaptive_shell_follows_existing_volume_without_flat_overlays():
    from backend.hair.volume import base_volume
    directions=trimesh.creation.icosphere(subdivisions=3).vertices
    envelope=np.column_stack([directions,np.full(len(directions),1.3)])
    mesh=base_volume(SCALP,{'volume':.04,'top_height':.04},envelope=envelope)
    radii=np.linalg.norm((mesh.vertices-np.array(SCALP['center']))/np.array(SCALP['radii']),axis=1)
    assert radii.min()>1.0 and radii.max()<1.1
    assert mesh.is_watertight and mesh.volume>0

@pytest.mark.parametrize('preset',['anime_spiky','short_volume','buzz','anime_fluffy','fringe','long'])
def test_six_controlled_geometry_cases_are_closed_rooted_and_preserve_body(tmp_path,preset):
    from backend.hair.pipeline import reconstruct_hair
    from backend.hair.understanding import analyze_hair
    from tests.test_hair_understanding import mask_image
    understanding=analyze_hair(mask_image('buzz' if preset=='buzz' else 'spiky'),[.3,.32,.72,.78],preset=preset)
    understanding['tips']=[{'tip_world':[.12,.97,.15],'root_world':[.04,.83,.10],'width':.16,'zone':'top'}, {'tip_world':[.04,.65,.19],'root_world':[.025,.82,.13],'width':.2,'zone':'fringe'}]
    head=trimesh.creation.icosphere(subdivisions=2,radius=.14);head.apply_translation(SCALP['center']);body=trimesh.creation.box([.4,.7,.2]);scene=trimesh.Scene();scene.add_geometry(head,geom_name='FusedHead');scene.add_geometry(body,geom_name='Body')
    result,report=reconstruct_hair(scene,{'scalp':SCALP,'understanding':understanding},{'reviewed':True,'front_axis':'negative_y'},tmp_path)
    assert report['protected_geometry']['equivalent'] and all(m['watertight'] and m['degenerate_triangles']==0 for m in report['integrity'])
    assert np.array_equal(result.geometry['Body'].vertices,body.vertices)
    if preset in ['buzz','close_short']:assert not report['clumps'] and report['attributes']['volume']<=.035
    else:assert report['clumps'] and all(c['root_base_distance']<1e-8 for c in report['clumps'])

def test_anime_fringe_uses_a_sharp_profile_and_realistic_uses_elliptical(tmp_path):
    from backend.hair.pipeline import reconstruct_hair
    scene=trimesh.Scene(trimesh.creation.icosphere(radius=.14).apply_translation(SCALP['center']))
    context={'scalp':SCALP,'understanding':{'preset':'short_volume','attributes':{'volume':.08,'fringe':.5,'thickness':.05},'tips':[{'root_world':[0,.82,.10],'tip_world':[.04,.70,.18],'zone':'fringe','width':.16}]}}
    profiles=[]
    for style in ['anime','realistic']:
        _,report=reconstruct_hair(scene,{**context,'options':{'style':style}},{'reviewed':True},tmp_path/style);profiles.append(report['clumps'][0]['profile'])
    assert profiles==['triangular','elliptical']

def test_flat_hair_base_expands_only_inside_observed_cranial_support():
    from backend.hair.volume import base_volume
    directions=trimesh.creation.icosphere(subdivisions=3).vertices;field=np.column_stack([directions,np.ones(len(directions))]);attrs={'volume':.2,'top_height':.3,'lateral_volume':.2,'back_volume':.05}
    supported=base_volume(SCALP,attrs,envelope=field,allow_expansion=True,support=lambda point:point[1]>.75)
    conservative=base_volume(SCALP,attrs,envelope=field,allow_expansion=False)
    assert supported.is_watertight and supported.volume>conservative.volume and supported.bounds[1,1]>conservative.bounds[1,1]
    # Even a flat source keeps unobserved rear growth very small.
    assert supported.bounds[0,2]>=-.145

def test_x_front_export_rotates_authored_hair_normals_once(tmp_path):
    import io
    from backend.hair.pipeline import reconstruct_hair
    scene=trimesh.Scene(trimesh.creation.icosphere(radius=.14).apply_translation(SCALP['center']))
    analysis={'scalp':SCALP,'understanding':{'preset':'short_volume','attributes':{'volume':.08,'fringe':.5},'tips':[{'root_world':[0,.82,.10],'tip_world':[.04,.70,.18],'zone':'fringe','width':.16}]}}
    canonical,_=reconstruct_hair(scene,analysis,{'reviewed':True,'front_axis':'negative_y'},tmp_path/'canonical')
    rotated,report=reconstruct_hair(scene,analysis,{'reviewed':True,'front_axis':'x'},tmp_path/'x')
    exported=trimesh.load(io.BytesIO(rotated.export(file_type='glb',include_normals=True)),file_type='glb',force='scene',process=False)
    for name in report['hair_meshes']:
        # Right-view transform is [z,y,-x], independently derived from the axis mapping.
        original=canonical.geometry[name].vertex_normals
        expected=np.column_stack([original[:,2],original[:,1],-original[:,0]])
        assert np.allclose(rotated.geometry[name].vertex_normals,expected,atol=1e-6,rtol=0)
        assert np.allclose(exported.geometry[name].vertex_normals,expected,atol=1e-6,rtol=0)
