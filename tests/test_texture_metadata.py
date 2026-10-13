def test_texture_metrics_do_not_report_parent_geometry_gpu_peak():
    from backend.texture_engine.jobs import texture_metadata
    parent={'peak_vram_mb':7000,'inference_seconds':900,'seed':12,'provider':'hunyuan_mini','triangles':20000}
    texture={'provider':'neural_multiview','neural':{'peak_allocated_mb':3800,'peak_reserved_mb':5000,'inference_seconds':64,'seed':44,'offline':True}}
    result=texture_metadata(parent,texture,{'front_axis':'negative_y'},'source-hash')
    assert result['peak_vram_mb']==3800 and result['inference_seconds']==64 and result['seed']==44
    assert result['geometry_generation_metrics']['peak_vram_mb']==7000 and parent['peak_vram_mb']==7000
    projection=texture_metadata(parent,{'provider':'reference_projection'},{'front_axis':'x'},'source-hash')
    assert 'peak_vram_mb' not in projection and 'inference_seconds' not in projection
