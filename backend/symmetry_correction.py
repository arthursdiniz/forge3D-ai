"""Selective bilateral corrections; no automatic mirroring of uncertain poses."""
import numpy as np
from scipy.spatial import cKDTree


def reflection(points,normal,offset):
    points=np.asarray(points)
    return points-2*(points@normal-offset)[:,None]*normal


def estimate_plane(vertices,selected=None,yaw_limit=15):
    points=np.asarray(vertices,dtype=float)
    if selected is not None:points=points[np.asarray(selected,bool)]
    if len(points)<8:raise ValueError('Pouca geometria selecionada para estimar plano local.')
    points=np.unique(np.round(points,7),axis=0)
    if len(points)>2000:points=points[np.linspace(0,len(points)-1,2000,dtype=int)]
    tree=cKDTree(points);height=max(np.ptp(points,axis=0)[1],1e-8)
    best=None
    for angle in np.linspace(-yaw_limit,yaw_limit,13):
        radians=np.deg2rad(angle);normal=np.array([np.cos(radians),0,np.sin(radians)])
        for offset in np.linspace(float(np.median(points@normal))-height*.04,float(np.median(points@normal))+height*.04,9):
            distance,_=tree.query(reflection(points,normal,offset))
            score=float(np.mean(np.sort(distance)[:max(1,int(len(distance)*.8))]))
            if best is None or score<best['sampled_distance']:best={'yaw_degrees':float(angle),'offset':float(offset),'normal':normal.tolist(),'sampled_distance':score,'method':'bounded local-plane reflection distance, trimmed80%','confidence':None,'requires_user_confirmation':True}
    return best


def correct_symmetry(vertices,selected=None,mode='off',strength=.2,plane_yaw_degrees=0,plane_offset=0,max_displacement_ratio=.003,match_distance_ratio=.04,normals=None):
    points=np.asarray(vertices,dtype=np.float64);result=points.copy()
    if mode not in ['off','soft','strong','custom']:raise ValueError('Modo de simetria inválido.')
    if not 0<=strength<=1 or not 0<=max_displacement_ratio<=.03:raise ValueError('Intensidade/deslocamento inválidos.')
    angle=np.deg2rad(plane_yaw_degrees);normal=np.array([np.cos(angle),0,np.sin(angle)])
    report={'mode':mode,'accepted':False,'plane':{'normal':normal.tolist(),'offset':float(plane_offset),'coordinate_system':'object canonical Y-up/front+Z'},'paired_vertices':0,'max_displacement':0.,'geometry_topology_changed':False,'metric_scope':'Corresponding selected surface-point distances; not anatomical accuracy.'}
    if mode=='off':report['reason']='Preservar assimetria original.';return result,report
    selection=np.ones(len(points),bool) if selected is None else np.asarray(selected,bool)
    indices=np.flatnonzero(selection)
    if len(indices)<4:report['reason']='Pouca geometria selecionada.';return result,report
    unique,representatives,inverse=np.unique(np.round(points[indices],7),axis=0,return_index=True,return_inverse=True)
    originals=points[indices[representatives]];tree=cKDTree(originals)
    mirrored=reflection(originals,normal,plane_offset);distance,neighbor=tree.query(mirrored)
    height=max(float(np.ptp(points,axis=0)[1]),float(np.ptp(points,axis=0).max()),1e-8)
    mutual=neighbor[neighbor]==np.arange(len(originals))
    mutual&=neighbor!=np.arange(len(originals));mutual&=distance<=height*match_distance_ratio
    if normals is not None:
        vectors=np.asarray(normals,dtype=float)[indices[representatives]]
        reflected_normals=vectors-2*(vectors@normal)[:,None]*normal
        dots=np.einsum('ij,ij->i',reflected_normals,vectors[neighbor]);mutual&=dots>.5
    if mutual.sum()<4:
        report['reason']='Correspondências bilaterais insuficientes; pose/partes assimétricas não foram forçadas.';return result,report
    before=float(distance[mutual].mean())
    if before<height*1e-6:report.update(reason='Superfície selecionada já bilateral neste plano.',paired_vertices=int(mutual.sum()),pair_distance_before=before,pair_distance_after=before);return result,report
    effective_strength=max(strength,.6) if mode=='strong' else strength
    target=(originals+reflection(originals[neighbor],normal,plane_offset))/2
    delta=(target-originals)*effective_strength;delta[~mutual]=0
    length=np.linalg.norm(delta,axis=1);limit=height*max_displacement_ratio
    delta*=np.minimum(1,limit/np.maximum(length,1e-15))[:,None]
    edited=originals+delta
    after=float(np.linalg.norm(reflection(edited,normal,plane_offset)-edited[neighbor],axis=1)[mutual].mean())
    if after>before+1e-12:report['reason']='Correção não melhorou correspondências; original conservado.';return result,report
    result[indices]+=delta[inverse]
    report.update(accepted=True,effective_strength=effective_strength,paired_vertices=int(mutual.sum()),pair_distance_before=before,pair_distance_after=after,max_displacement=float(np.linalg.norm(delta,axis=1).max()),selected_vertices=len(indices),reason='Correção limitada nas regiões confirmadas pelo usuário.')
    return result,report


class SymmetryCorrection:
    estimate_plane=staticmethod(estimate_plane)
    correct=staticmethod(correct_symmetry)
