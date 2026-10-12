"""CPU marching cubes with the upstream density/axis convention."""
def cpu_marching_cubes(level,threshold):
    import numpy as np
    import torch
    from skimage.measure import marching_cubes
    # MarchingCubeHelper passes density-threshold (positive inside). The
    # adapter swaps axes here and upstream swaps them back. With this
    # convention, ascent gives exterior faces; descent produces an inside-out
    # closed shell. Do not hide that error by enabling double-sided materials.
    vertices,faces,_,_=marching_cubes(level.detach().cpu().numpy(),level=threshold,gradient_direction='ascent')
    return torch.from_numpy(vertices[:,[2,1,0]].copy()),torch.from_numpy(faces.copy().astype(np.int64))
