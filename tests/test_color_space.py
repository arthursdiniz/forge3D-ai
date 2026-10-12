import numpy as np
from backend.color_space import srgb_to_linear

def test_vertex_color_transfer_is_linear_once():
    result=srgb_to_linear(np.array([0,0.04045,0.5,1]))
    assert np.allclose(result,[0,0.0031308,0.21404114,1],atol=1e-7)
    recovered=np.where(result<=0.0031308,result*12.92,1.055*result**(1/2.4)-0.055)
    assert np.allclose(recovered,[0,0.04045,0.5,1],atol=1e-6)
