"""Reconnect only unique, opposed UV boundary edge pairs at exact positions."""
import numpy as np


def reconnect_uv_seams(vertices, faces, normals, materials):
    vertices=np.asarray(vertices);faces=np.asarray(faces);normals=np.asarray(normals);materials=np.asarray(materials)
    edges=np.concatenate([faces[:,[0,1]],faces[:,[1,2]],faces[:,[2,0]]])
    owners=np.tile(np.arange(len(faces)),3)
    _,edge_ids,counts=np.unique(np.sort(edges,axis=1),axis=0,return_inverse=True,return_counts=True)
    boundary=np.flatnonzero(counts[edge_ids]==1)
    _,positions=np.unique(vertices,axis=0,return_inverse=True)
    groups={}
    for index in boundary:
        a,b=edges[index];key=tuple(sorted((int(positions[a]),int(positions[b]))))
        if key[0]!=key[1]:groups.setdefault(key,[]).append(int(index))
    parent=np.arange(len(vertices))
    def find(a):
        while parent[a]!=a:parent[a]=parent[parent[a]];a=parent[a]
        return a
    def merge(a,b):
        a,b=find(a),find(b)
        if a!=b:parent[max(a,b)]=min(a,b)
    accepted=0
    for pair in groups.values():
        if len(pair)!=2:continue # ambiguous overlapping shells, never merge them
        i,j=pair;a,b=edges[i];c,d=edges[j]
        if positions[a]!=positions[d] or positions[b]!=positions[c] or materials[owners[i]]!=materials[owners[j]]:continue
        if np.dot(normals[a],normals[d])<.99999 or np.dot(normals[b],normals[c])<.99999:continue
        merge(a,d);merge(b,c);accepted+=1
    roots=np.array([find(i) for i in range(len(vertices))]);unique,index=np.unique(roots,return_inverse=True)
    report={'edge_pairs_reconnected':accepted,'vertices_reconnected':len(vertices)-len(unique),'method':'Unique opposite boundary edges; exact coordinates, matching imported normals and material; no tolerance weld, smoothing, filling or position changes','high_poly_unchanged':True}
    return vertices[unique].copy(),index[faces],normals[unique].copy(),report


def small_component_faces(faces, max_faces=100):
    faces=np.asarray(faces);parents=np.arange(int(faces.max())+1)
    def find(a):
        while parents[a]!=a:parents[a]=parents[parents[a]];a=parents[a]
        return a
    for a,b,c in faces:
        for u,v in [(a,b),(b,c)]:
            u,v=find(u),find(v)
            if u!=v:parents[max(u,v)]=min(u,v)
    labels=np.array([find(face[0]) for face in faces]);_,inverse,counts=np.unique(labels,return_inverse=True,return_counts=True)
    return counts[inverse]<=max_faces
