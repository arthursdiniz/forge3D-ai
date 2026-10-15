import json
import numpy as np
import pytest
from PIL import Image

@pytest.mark.parametrize('reverse',[False,True])
def test_protected_class_evidence_blocks_all_views_independent_of_order(monkeypatch,reverse):
    import backend.texture_engine.semantic_atlas as atlas
    def observation(camera,*args):
        target=4 if camera=='front' else 5
        return {'rgb':np.ones((1,3),'f4'),'weight':np.ones(1),'gradient':np.zeros(1),'source_class':np.array([4]),'target_class':np.array([target]),'target_visible':np.array([True]),'visible':np.array([True]),'origin':np.array([2]),'protected':np.array([False]),'conflict':np.array([False])}
    monkeypatch.setattr(atlas,'project_semantic',observation)
    views=[{'camera':name,'rgba':None,'source_labels':None,'target_labels':None,'registration':{},'source_origin':None} for name in ['front','manual_side']]
    result=atlas.atlas_observations({'points':np.zeros((1,3)),'normals':np.ones((1,3)),'faces':np.ones(1)},views[::-1] if reverse else views,1,['hair'],['eyes'])
    assert result['protected'].tolist()==[True] and result['weight'].tolist()==[0]

@pytest.mark.parametrize('operation,label,expected,provenance',[('paint',16,16,2),('erase',0,0,2),('restore',0,3,1)])
def test_saved_polygon_mask_agrees_with_later_brush_and_neural_restore(tmp_path,monkeypatch,operation,label,expected,provenance):
    import backend.texture_engine.semantic_analysis as module
    class Camera:
        def __init__(self,*args,**kwargs):self.image=np.full((64,64,4),255,'u1');self.frame={}
    monkeypatch.setattr(module,'RegionCamera',Camera)
    monkeypatch.setattr(module,'segment_image',lambda image,*args:(np.full((64,64),3,'u1'),np.ones((64,64),'u1'),{'provider':'unit fixture, not neural proof'}))
    monkeypatch.setattr(module,'write_analysis_atlas',lambda *args:[])
    folder=tmp_path/'views/front';folder.mkdir(parents=True);Image.new('RGBA',(64,64),'red').save(folder/'source.png')
    settings={'front_axis':'negative_y','views':{'front':{'registration':{},'source_polygons':[{'label':4,'points':[[.1,.1],[.9,.1],[.9,.9],[.1,.9]]}],'source_strokes':[{'operation':operation,'label':label,'radius':.04,'points':[[.5,.5]]}]}}}
    module.analyze_semantics(None,tmp_path,settings,tmp_path,'hash')
    saved=np.asarray(Image.open(folder/'source_labels.png'));origin=np.asarray(Image.open(folder/'source_origin.png'))
    assert saved[32,32]==expected and origin[32,32]==provenance
    assert saved[16,16]==4 and origin[16,16]==2

def test_semantic_neural_license_lineage_survives_preserve_edit_and_packaging(tmp_path):
    from backend.texture_engine.jobs import texture_metadata
    from backend.worker import Worker
    neural={'peak_allocated_mb':3800,'peak_reserved_mb':5300,'inference_seconds':65,'seed':44,'offline':True}
    generated=texture_metadata({}, {'provider':'semantic_reference','semantic':{},'neural':neural},{'front_axis':'negative_y'},'first')
    edited=texture_metadata(generated,{'provider':'semantic_reference','semantic':{},'neural':None},{'front_axis':'negative_y'},'second')
    for name,value in [('unity/Forge3DImporter.cs','public static class Forge3DImporter {}'),('unity/README_IMPORT.md','test'),('models/texture/sdxl/LICENSE.md','SDXL test notice'),('vendor/MV-Adapter/LICENSE','Adapter test notice'),('vendor/anime-hair-segmentation/LICENSE','Portrait test notice')]:
        path=tmp_path/name;path.parent.mkdir(parents=True,exist_ok=True);path.write_text(value)
    folder=tmp_path/'output';(folder/'Forge3D_Asset/Textures').mkdir(parents=True);(folder/'fbx_validation.json').write_text('{}')
    Worker(tmp_path,None).package({'id':'a'*32,'provider':'imported','name':'fixture','parent':None,'options':{}},folder,edited)
    assert (folder/'Forge3D_Asset/SDXL_LICENSE.md').is_file() and (folder/'Forge3D_Asset/MV_ADAPTER_LICENSE.txt').is_file()
    manifest=json.loads((folder/'Forge3D_Asset/asset_manifest.json').read_text());assert set(manifest['inference']['texture_resource_history'])>={'sdxl','mv_adapter'}
