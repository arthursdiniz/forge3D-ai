import numpy as np

def test_reference_refinement_improves_contour_without_changing_depth_height_or_topology():
    from backend.silhouette_refinement import refine_silhouette
    vertices=np.array([[-0.3,-1,0],[0.3,-1,0],[0.3,1,0],[-0.3,1,0]],float)
    faces=np.array([[0,1,2],[0,2,3]])
    image=np.zeros((128,128,4),np.uint8);image[16:112,52:76]=[255,150,0,255]
    output,report=refine_silhouette(vertices,faces,image,strength=1,max_displacement_ratio=0.03,resolution=128)
    assert report['silhouette_iou_after']>report['silhouette_iou_before']+0.1
    assert np.array_equal(output[:,1:],vertices[:,1:])
    assert output.shape==vertices.shape
    assert np.max(np.abs(output[:,0]-vertices[:,0]))<=0.0600001
    assert report['faces_changed']==0

def test_reference_refinement_refuses_to_bridge_separate_parts_to_match_a_single_blob():
    from backend.silhouette_refinement import refine_silhouette
    vertices=np.array([[-0.4,-1,0],[-0.1,-1,0],[-0.1,1,0],[-0.4,1,0],[0.1,-1,0],[0.4,-1,0],[0.4,1,0],[0.1,1,0]],float)
    faces=np.array([[0,1,2],[0,2,3],[4,5,6],[4,6,7]])
    image=np.zeros((128,128,4),np.uint8);image[16:112,40:88]=[255,0,0,255]
    output,report=refine_silhouette(vertices,faces,image,strength=1,resolution=128)
    assert np.array_equal(output,vertices)
    assert report['matched_scanlines']==0

def test_reference_refinement_never_accepts_a_displacement_limit_above_three_percent():
    import pytest
    from backend.silhouette_refinement import refine_silhouette
    with pytest.raises(ValueError):refine_silhouette(np.eye(3),np.array([[0,1,2]]),np.full((16,16,4),255,np.uint8),max_displacement_ratio=0.031)

def test_a_deformation_without_measurable_improvement_is_not_applied():
    from backend.silhouette_refinement import refine_silhouette
    vertices=np.array([[-0.3,-1,0],[0.3,-1,0],[0.3,1,0],[-0.3,1,0]],float)
    faces=np.array([[0,1,2],[0,2,3]])
    image=np.zeros((128,128,4),np.uint8);image[16:112,52:76]=[255,0,0,255]
    output,report=refine_silhouette(vertices,faces,image,strength=1e-6,resolution=128)
    assert report['accepted'] is False and np.array_equal(output,vertices)
