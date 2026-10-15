"""Objective projected agreement, never a face identity or anatomy score."""
import numpy as np

def candidate_improved(before,after,changed_pixels,outside_unchanged,reference_pixels):
    measured=before.get('status')=='measured' and after.get('status')=='measured'
    structure=before.get('ssim') is not None and after.get('ssim') is not None and after['ssim']>=before['ssim']-.005
    return measured and structure and after['rgb_mae']<before['rgb_mae']-.002 and changed_pixels>=32 and outside_unchanged and reference_pixels>=32

def image_metrics(actual,reference,mask):
    from scipy.ndimage import uniform_filter
    actual=np.asarray(actual,dtype=float)/255;reference=np.asarray(reference,dtype=float)/255;mask=np.asarray(mask,dtype=bool)
    if mask.sum()<32:return {'status':'not_measurable','pixels':int(mask.sum())}
    difference=np.abs(actual[...,:3]-reference[...,:3]);gray_a=actual[...,:3]@np.array([.2126,.7152,.0722]);gray_b=reference[...,:3]@np.array([.2126,.7152,.0722])
    mean_a=uniform_filter(gray_a,7);mean_b=uniform_filter(gray_b,7);var_a=uniform_filter(gray_a**2,7)-mean_a**2;var_b=uniform_filter(gray_b**2,7)-mean_b**2;cov=uniform_filter(gray_a*gray_b,7)-mean_a*mean_b
    ssim=((2*mean_a*mean_b+.01**2)*(2*cov+.03**2))/((mean_a**2+mean_b**2+.01**2)*(var_a+var_b+.03**2))
    interior=uniform_filter(mask.astype(float),7)>.999
    return {'status':'measured','pixels':int(mask.sum()),'rgb_mae':round(float(difference[mask].mean()),6),'ssim':round(float(ssim[interior].mean()),6) if interior.any() else None,'scope':'Reference-aligned visible RGB/structure only; not universal facial identity.'}
