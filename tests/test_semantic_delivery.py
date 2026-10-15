import json
import numpy as np
import pytest
from PIL import Image
import trimesh
from tests.test_region_refinement import plane

def test_analysis_reports_atlas_failure_as_actionable_reason(tmp_path,monkeypatch):
    import backend.texture_engine.semantic_analysis as module
    folder=tmp_path/'views/front';folder.mkdir(parents=True);Image.new('RGBA',(32,32),'red').save(folder/'source.png')
    monkeypatch.setattr(module,'segment_image',lambda image,*args:(np.full((image.height,image.width),4,'u1'),np.ones((image.height,image.width),'u1'),{'provider':'fixture'}))
    def missing(*args):raise ValueError('Existing UV and albedo required')
    monkeypatch.setattr(module,'write_analysis_atlas',missing)
    report=module.analyze_semantics(trimesh.Scene(plane()),tmp_path,{'front_axis':'negative_y','views':{'front':{'registration':{}}}},tmp_path,'abc')
    assert report['status']=='manual_required' and 'UV and albedo' in report['reason']

def test_semantic_neural_preflight_checks_measured_free_vram(tmp_path,monkeypatch):
    from backend.texture_engine.providers import TextureProvider
    import backend.gpu_manager as gpu
    monkeypatch.setattr(TextureProvider,'health_check',lambda self:{'available':True})
    monkeypatch.setattr(gpu,'probe_gpu',lambda:{'fixture':'gpu'})
    calls=[];monkeypatch.setattr(gpu,'validate_vram',lambda device,required:calls.append(required))
    TextureProvider(tmp_path,'semantic_reference').preflight({'completion':'preserve'})
    assert calls==[]
    TextureProvider(tmp_path,'semantic_reference').preflight({'completion':'neural'})
    assert calls==[5500]

def test_semantic_ui_report_contains_actual_uv_diagnostics(tmp_path):
    from tests.test_semantic_paint import context
    from backend.texture_engine.semantic_paint import paint_semantic
    scene=trimesh.Scene(plane());report=paint_semantic(scene,context(tmp_path,scene),{'classes':['hair'],'protected_classes':['face'],'reviewed_alignment':True,'seam_correction':False},tmp_path/'result',tmp_path)
    assert report['uv'][0]['valid'] and 'overlap_percent' in report['uv'][0]
