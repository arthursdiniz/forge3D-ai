"""Unit tests of texture math using an analytic field, NOT generation benchmarks."""
import numpy as np

def test_position_raster_matches_surface_coordinates():
    from backend.neural_texture import rasterize_positions
    vertices=np.array([[0,0,0],[1,0,0],[0,1,0]],dtype=np.float32)
    uv=np.array([[0.1,0.1],[0.9,0.1],[0.1,0.9]],dtype=np.float32)
    positions=rasterize_positions(vertices,np.array([[0,1,2]],dtype=np.int32),uv,32)
    assert positions[8,8,3]==1
    expected=((8.5/32)-0.1)/0.8
    # Hardware rasterizers quantize screen coordinates at subpixel precision.
    assert np.allclose(positions[8,8,:2],expected,atol=1e-4)
    assert positions[31,31,3]==0

def test_padding_extends_edge_color_without_black_seams():
    from backend.neural_texture import pad_texture
    rgb=np.zeros((12,12,3),dtype=np.float32)
    mask=np.zeros((12,12),dtype=bool)
    mask[5:7,5:7]=True
    rgb[mask]=[0.8,0.2,0.1]
    padded=pad_texture(rgb,mask,2)
    assert np.allclose(padded[5,3],[0.8,0.2,0.1])
    assert np.allclose(padded[0,0],[0.5,0.5,0.5])
