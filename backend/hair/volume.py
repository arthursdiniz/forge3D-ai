"""Anisotropic closed hair shell around a reviewable scalp anchoring surface."""
import numpy as np

def scalp_surface(scalp,theta,phi):
    center=np.asarray(scalp['center']);radii=np.asarray(scalp['radii']);return center+radii*np.array([np.sin(theta)*np.sin(phi),np.cos(theta),np.sin(theta)*np.cos(phi)])

def base_volume(scalp,attributes,rings=12,sides=32,envelope=None,baseline=None,allow_expansion=False,support=None):
    import trimesh
    center=np.asarray(scalp['center']);radii=np.asarray(scalp['radii']);volume=float(attributes.get('volume',.08));lateral=float(attributes.get('lateral_volume',volume));top=float(attributes.get('top_height',volume));back=float(attributes.get('back_volume',volume*.6))
    if np.any(radii<=0) or not np.isfinite(radii).all():raise ValueError('Unsafe scalp radii.')
    vertices=[];faces=[];tree=None
    if envelope is not None and len(envelope)>=24:
        from scipy.spatial import cKDTree
        envelope=np.asarray(envelope);tree=cKDTree(envelope[:,:3])
    def adaptive(point,direction,outer):
        if tree is None:return point
        distance,index=tree.query(direction,k=min(6,len(envelope)));weight=1/np.maximum(np.atleast_1d(distance),.005)**2
        observed=float(np.min(envelope[np.atleast_1d(index),3]));desired=float(np.linalg.norm((point-center)/radii))
        # A fused head already provides support. Keep the new base beneath it;
        # only observed guide masses project beyond that support.
        radius=max(.55,min(desired,observed-.055))
        if allow_expansion and direction[1]>.05:
            if direction[2]>=0 and support is not None and support(point):radius=max(radius,desired)
            elif direction[2]<0:radius=max(radius,min(desired,observed+.035))
        if baseline is not None:
            front=max(0,direction[2]);top=max(0,direction[1]);side=abs(direction[0]);back=max(0,-direction[2])
            delta=sum(weight*(float(attributes.get(key,baseline.get(key,0)))-float(baseline.get(key,0))) for key,weight in [('volume',front*.6),('top_height',top*.6),('lateral_volume',side*.6),('back_volume',back*.6)])
            radius+=float(np.clip(delta,-.1,.25))
        if not outer:radius=max(.50,radius-max(.012,float(attributes.get('thickness',.05))*.4))
        return center+radii*direction*radius
    for layer in [0,1]:
        for i in range(rings):
            for j in range(sides):
                phi=2*np.pi*j/sides;front=max(0,np.cos(phi));end=1.72-.62*front;theta=.06+(end-.06)*i/(rings-1);direction=np.array([np.sin(theta)*np.sin(phi),np.cos(theta),np.sin(theta)*np.cos(phi)])
                offset=np.array([lateral*(.65+.35*np.sin(phi)**2),top*(.65+.35*np.cos(theta)**2),volume*front+back*(1-front)])
                # Spatial variation represents mass rather than uniform skull scaling.
                offset*=.90+.10*np.cos(phi*3+theta*2);offset+=.008
                outer_point=center+radii*direction*(1+offset)
                vertices.append(adaptive(outer_point,direction,bool(layer)) if tree is not None else (outer_point if layer else center+radii*direction))
        pole=len(vertices);point=center+np.array([0,radii[1]*(1+top+.008),0]);vertices.append(adaptive(point,np.array([0.,1.,0.]),bool(layer)) if tree is not None else (point if layer else center+[0,radii[1],0]))
        start=layer*(rings*sides+1)
        for j in range(sides):faces.append([pole,start+(j+1)%sides,start+j] if layer==0 else [pole,start+j,start+(j+1)%sides])
        for i in range(rings-1):
            for j in range(sides):
                a=start+i*sides+j;b=start+i*sides+(j+1)%sides;c=a+sides;d=b+sides
                faces.extend([[a,b,d],[a,d,c]] if layer else [[a,d,b],[a,c,d]])
    stride=rings*sides+1
    for j in range(sides):
        a=(rings-1)*sides+j;b=(rings-1)*sides+(j+1)%sides;c=a+stride;d=b+stride;faces.extend([[a,b,d],[a,d,c]])
    mesh=trimesh.Trimesh(vertices=vertices,faces=faces,process=False);mesh.fix_normals(multibody=True)
    if mesh.volume<0:mesh.invert()
    return mesh

def scalp_guide(scalp):
    import trimesh
    mesh=trimesh.creation.icosphere(subdivisions=3,radius=1);mesh.apply_scale(scalp['radii']);mesh.apply_translation(scalp['center']);return mesh
