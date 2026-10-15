"""MV-Adapter's six native Z-up cameras, OpenGL instead of nvdiffrast/CV-CUDA.

Only temporary control/projection coordinates rotate; published meshes stay Y-up.
Negative projection Y matches the official renderer's top-first image buffers.
"""
import numpy as np

class NativeControls:
    views=['front','left','back','right','top','bottom']
    def __init__(self,scene,front_axis,resolution=512):
        import trimesh
        from ..character_quality import canonical_vertices
        arrays=[];normals=[]
        for node in scene.graph.nodes_geometry:
            matrix,name=scene.graph[node];mesh=scene.geometry[name]
            world=trimesh.transform_points(mesh.vertices,matrix)
            arrays.append(canonical_vertices(world[mesh.faces].reshape(-1,3),front_axis))
            normal=mesh.vertex_normals@np.linalg.inv(matrix[:3,:3])
            normals.append(canonical_vertices(normal[mesh.faces].reshape(-1,3),front_axis))
        points=np.concatenate(arrays);vectors=np.concatenate(normals)
        self.center=(points.max(axis=0)+points.min(axis=0))/2
        self.scale=float(np.abs(points-self.center).max())*2
        if self.scale<=1e-8:raise ValueError('Empty control geometry.')
        points=self.native((points-self.center)/self.scale);vectors=self.native(vectors)
        vectors/=np.maximum(np.linalg.norm(vectors,axis=1,keepdims=True),1e-12)
        self.resolution=resolution;self.rasters={};self.cameras={};controls=[]
        for view,azimuth,elevation in zip(self.views,[-90,0,90,180,90,90],[0,0,0,0,89.99,-89.99]):
            a,e=np.deg2rad([azimuth,elevation]);position=1.8*np.array([np.cos(e)*np.cos(a),np.cos(e)*np.sin(a),np.sin(e)])
            look=-position/np.linalg.norm(position);right=np.cross(look,[0,0,1]);right/=np.linalg.norm(right);up=np.cross(right,look)
            c2w=np.eye(4);c2w[:3,:3]=np.column_stack([right,up,-look]);c2w[:3,3]=position
            projection=np.diag([2/1.1,-2/1.1,-2/(100-.1),1]);projection[2,3]=-(100+.1)/(100-.1)
            mvp=projection@np.linalg.inv(c2w)
            raster=self.raster(points,vectors,mvp,resolution)
            self.rasters[view]=raster;self.cameras[view]=(mvp,position)
            encoded=np.concatenate([np.clip(raster[...,:3]+.5,0,1),np.clip(raster[...,4:7]/2+.5,0,1)],axis=-1)
            controls.append(encoded.transpose(2,0,1))
        self.controls=np.stack(controls).astype('f4')

    @staticmethod
    def native(points):return np.asarray(points,dtype=float)[:,[0,2,1]]*np.array([1,-1,1])

    @staticmethod
    def raster(points,normals,mvp,resolution):
        import moderngl
        context=moderngl.create_standalone_context()
        try:
            program=context.program(vertex_shader='#version 330\nuniform mat4 mvp;in vec3 point;in vec3 normal;out vec3 p;out vec3 n;void main(){p=point;n=normal;gl_Position=mvp*vec4(point,1);}',fragment_shader='#version 330\nin vec3 p;in vec3 n;layout(location=0)out vec4 position;layout(location=1)out vec4 normal;void main(){position=vec4(p,1);normal=vec4(normalize(n),1);}')
            program['mvp'].write(np.asarray(mvp.T,dtype='f4').tobytes())
            buffer=context.buffer(np.column_stack([points,normals]).astype('f4').tobytes());vao=context.vertex_array(program,[(buffer,'3f 3f','point','normal')])
            textures=[context.texture((resolution,resolution),4,dtype='f4') for _ in range(2)];depth=context.depth_renderbuffer((resolution,resolution));target=context.framebuffer(textures,depth)
            target.use();target.clear(0,0,0,0,depth=1);context.enable(moderngl.DEPTH_TEST);context.disable(moderngl.CULL_FACE);context.depth_func='<='
            vao.render(moderngl.TRIANGLES)
            result=np.concatenate([np.frombuffer(t.read(),dtype='f4').reshape(resolution,resolution,4).copy() for t in textures],axis=-1)
            vao.release();buffer.release();target.release();depth.release()
            for t in textures:t.release()
            program.release();return result
        finally:context.release()

    def project(self,view,points,normals,rgba):
        from scipy.ndimage import map_coordinates
        from ..reference_texture import NEUTRAL
        native=self.native((points-self.center)/self.scale);normals=self.native(normals)
        normals/=np.maximum(np.linalg.norm(normals,axis=1,keepdims=True),1e-12)
        mvp,camera=self.cameras[view];clip=np.column_stack([native,np.ones(len(native))])@mvp.T
        uv=clip[:,:2]/2+.5;h,w=rgba.shape[:2]
        x=uv[:,0]*w-.5;y=uv[:,1]*h-.5
        sample=np.column_stack([map_coordinates(rgba[...,i].astype(float),[y,x],order=1,mode='nearest') for i in range(4)])/255.
        raster=self.rasters[view];size=self.resolution;rx=uv[:,0]*size-.5;ry=uv[:,1]*size-.5
        depth=np.column_stack([map_coordinates(raster[...,i],[ry,rx],order=1,mode='nearest') for i in range(3)])
        occupied=map_coordinates(raster[...,3],[ry,rx],order=0,mode='nearest')>.5
        direction=camera/np.linalg.norm(camera)
        visible=occupied&(np.abs((depth-native)@direction)<=2/size)&(uv[:,0]>=0)&(uv[:,0]<1)&(uv[:,1]>=0)&(uv[:,1]<1)
        weight=np.clip((normals@direction-.15)/.6,0,1)*sample[:,3]*visible
        weight[sample[:,3]<.75]=0
        colors=sample[:,:3]
        colors[weight<=0]=NEUTRAL
        return colors.astype('f4'),weight.astype('f4')
