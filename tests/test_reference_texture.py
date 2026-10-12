import numpy as np

def test_projection_preserves_image_orientation_and_does_not_paint_occluded_surfaces():
    from backend.reference_texture import project_reference_colors
    # Front (+Z) and rear overlapping planes. Red top / blue bottom in photo.
    vertices=np.array([[-1,-1,1],[1,-1,1],[1,1,1],[-1,1,1],[-1,-1,0],[1,-1,0],[1,1,0],[-1,1,0]],np.float32)
    faces=np.array([[0,1,2],[0,2,3],[4,5,6],[4,6,7]],np.int32)
    image=np.zeros((64,64,4),np.uint8);image[:32]=[255,0,0,255];image[32:]=[0,0,255,255]
    positions=np.array([[0,0.6,1],[0,-0.6,1],[0,0.6,0]],np.float32)
    normals=np.tile([0,0,1],(3,1))
    rgb,confidence=project_reference_colors(vertices,faces,positions,normals,image,depth_resolution=128)
    assert np.allclose(rgb[0],[1,0,0],atol=0.01)
    assert np.allclose(rgb[1],[0,0,1],atol=0.01)
    assert confidence[2]==0
    assert np.allclose(rgb[2],[0.735357,0.735357,0.735357],atol=0.001)

def test_projection_rejects_background_pixels_and_surfaces_facing_away():
    from backend.reference_texture import project_reference_colors
    vertices=np.array([[-1,-1,0],[1,-1,0],[1,1,0],[-1,1,0]],np.float32)
    faces=np.array([[0,1,2],[0,2,3]],np.int32)
    image=np.full((32,32,4),255,np.uint8);image[14:18,14:18,3]=0
    rgb,confidence=project_reference_colors(vertices,faces,np.array([[0,0,0],[0.6,0.6,0]]),np.array([[0,0,1],[0,0,-1]]),image,depth_resolution=64)
    assert np.array_equal(confidence,[0,0])
