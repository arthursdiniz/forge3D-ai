"""Closed swept clumps with variable profile and observed directional guides."""
import numpy as np

def sweep_clump(curve,width,thickness,profile='elliptical',curvature=0,segments=12):
    import trimesh
    curve=np.asarray(curve,float)
    if curve.shape!=(3,3) or not np.isfinite(curve).all() or min(width,thickness)<=0:raise ValueError('Invalid clump curve/profile.')
    sides=3 if profile=='triangular' else 8
    vertices=[];faces=[];parameter=np.linspace(0,.94,segments)
    for i,t in enumerate(parameter):
        point=(1-t)**2*curve[0]+2*(1-t)*t*curve[1]+t*t*curve[2];tangent=2*(1-t)*(curve[1]-curve[0])+2*t*(curve[2]-curve[1]);tangent/=max(np.linalg.norm(tangent),1e-12)
        ref=np.array([0.,1,0]) if abs(tangent[1])<.9 else np.array([1.,0,0]);u=np.cross(tangent,ref);u/=max(np.linalg.norm(u),1e-12);v=np.cross(tangent,u)
        point+=u*np.sin(t*np.pi*2)*curvature*width
        radius=(.32+.90*np.sin(t*np.pi*.85))*(1-t)**.65
        for j in range(sides):
            angle=2*np.pi*j/sides;asymmetry=1+.2*np.cos(angle) if profile=='asymmetric' else 1
            vertices.append(point+u*np.cos(angle)*width*radius*asymmetry+v*np.sin(angle)*thickness*radius)
        if i:
            for j in range(sides):
                a=(i-1)*sides+j;b=(i-1)*sides+(j+1)%sides;c=i*sides+j;d=i*sides+(j+1)%sides;faces.extend([[a,b,d],[a,d,c]])
    root=len(vertices);vertices.append(curve[0]);tip=len(vertices);vertices.append(curve[2])
    for j in range(sides):faces.extend([[root,(j+1)%sides,j],[tip,(segments-1)*sides+j,(segments-1)*sides+(j+1)%sides]])
    mesh=trimesh.Trimesh(vertices=vertices,faces=faces,process=False);mesh.fix_normals(multibody=True)
    if mesh.volume<0:mesh.invert()
    return mesh
