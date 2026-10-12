import numpy as np

def srgb_to_linear(rgb):
    """glTF COLOR_0 is linear; neural RGB/PNG follow image sRGB encoding."""
    rgb=np.asarray(rgb,dtype=np.float64)
    return np.where(rgb<=0.04045,rgb/12.92,((rgb+0.055)/1.055)**2.4)
