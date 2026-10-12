"""Opt-in local micro refinement with boundary/sharp-feature protection."""
import numpy as np
from scipy.sparse import coo_matrix
from .geometry_integrity import welded_topology


def refine_surface(vertices,faces,selected,strength=.1,iterations=2,max_displacement_ratio=.001,sharp_degrees=35):
    original=np.asarray(vertices,dtype=float);faces=np.asarray(faces,dtype=int)
    report={'level':'micro','method':'selected bounded two-pass Laplacian/Taubin-style update','accepted':False,'faces_changed':0,'learned_anatomy':False}
    if not 0<=strength<=.25 or not 1<=iterations<=5:raise ValueError('Refinamento deve usar intensidade≤0.25 e1–5iterações.')
    keys=np.round(original,7);points,indices,inverse=np.unique(keys,axis=0,return_index=True,return_inverse=True)
    points=original[indices].copy();triangles=inverse[faces]
    selection=np.zeros(len(points),bool);np.logical_or.at(selection,inverse,np.asarray(selected,bool))
    edges=np.concatenate([triangles[:,[0,1]],triangles[:,[1,2]],triangles[:,[2,0]]]);edge_faces=np.tile(np.arange(len(triangles)),3)
    canonical=np.sort(edges,axis=1);unique,edge_index,counts=np.unique(canonical,axis=0,return_inverse=True,return_counts=True)
    protected=np.zeros(len(points),bool);protected[np.unique(unique[counts!=2])]=True
    corners=points[triangles];normals=np.cross(corners[:,1]-corners[:,0],corners[:,2]-corners[:,0]);length=np.linalg.norm(normals,axis=1);normals/=np.maximum(length[:,None],1e-15)
    order=np.argsort(edge_index,kind='stable');starts=np.r_[0,np.cumsum(counts)[:-1]];manifold=np.flatnonzero(counts==2)
    a=edge_faces[order[starts[manifold]]];b=edge_faces[order[starts[manifold]+1]]
    sharp=np.einsum('ij,ij->i',normals[a],normals[b])<np.cos(np.deg2rad(sharp_degrees))
    if sharp.any():protected[np.unique(unique[manifold[sharp]])]=True
    protected[np.unique(triangles[length<1e-12])]=True
    neighbors=np.vstack([unique,unique[:,::-1]])
    adjacency=coo_matrix((np.ones(len(neighbors)),(neighbors[:,0],neighbors[:,1])),shape=(len(points),len(points))).tocsr()
    degree=np.maximum(np.asarray(adjacency.sum(axis=1)).ravel(),1)
    movable=selection&~protected
    if movable.sum()<3:report['reason']='Região sem vértices interiores seguros; bordas/detalhes conservados.';return original.copy(),report
    def laplacian(value):return adjacency@value/degree[:,None]-value
    before=float(np.linalg.norm(laplacian(points)[movable],axis=1).mean())
    result=points.copy();height=max(float(np.ptp(original,axis=0)[1]),1e-8);limit=height*max_displacement_ratio
    for _ in range(iterations):
        result[movable]+=.35*strength*laplacian(result)[movable]
        result[movable]-=.36*strength*laplacian(result)[movable]
        delta=result-points;length=np.linalg.norm(delta,axis=1)
        result=points+delta*np.minimum(1,limit/np.maximum(length,1e-15))[:,None]
    after=float(np.linalg.norm(laplacian(result)[movable],axis=1).mean())
    if after>=before:report.update(reason='A métrica local não melhorou; original preservado.',local_laplacian_before=before,local_laplacian_after=after);return original.copy(),report
    # Surface points at seams move together while indices and UV corners remain.
    edited=original+(result-points)[inverse]
    report.update(accepted=True,local_laplacian_before=before,local_laplacian_after=after,max_displacement=float(np.linalg.norm(edited-original,axis=1).max()),protected_vertices=int(protected.sum()),moved_vertices=int(np.count_nonzero(np.linalg.norm(edited-original,axis=1)>1e-12)),scope='Local irregularity only; macro proportions/face/fingers are not reconstructed.')
    return edited,report


class SculptRefinement:
    micro=staticmethod(refine_surface)
