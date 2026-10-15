"""Orthographic material-aware inspection and depth projection, no mesh edits."""
import numpy as np
from ..character_quality import canonical_vertices
from .identity import world_triangles

class RegionCamera:
    def __init__(self,scene,axis='negative_y',size=1024,frame=None,yaw=0):
        self.scene=scene;self.axis=axis;self.size=size;self.yaw=yaw
        vertices=self.rotate(canonical_vertices(world_triangles(scene).reshape(-1,3),axis))
        low=vertices.min(axis=0);high=vertices.max(axis=0);span=max(np.ptp(vertices[:,:2],axis=0).max(),1e-8)
        self.frame=dict(frame) if frame else {'center':((low+high)/2).tolist(),'scale':.9/span}
        self.frame.update(z_min=float(low[2]),z_max=float(high[2]))
        self.buffers=self.render(scene,size);self.image=np.rint(np.clip(self.buffers[3],0,1)*255).astype('u1')

    def rotate(self,points):
        angle=np.deg2rad(self.yaw);c=np.cos(angle);s=np.sin(angle)
        return np.asarray(points)@np.array([[c,0,s],[0,1,0],[-s,0,c]])

    def coordinates(self,points):
        points=self.rotate(np.asarray(points));center=np.asarray(self.frame['center']);scale=self.frame['scale']
        return np.column_stack([.5+(points[:,0]-center[0])*scale,.5-(points[:,1]-center[1])*scale])

    def visibility(self,points,normals,owner=None,triangles=None):
        from scipy.ndimage import map_coordinates
        xy=self.coordinates(points);xy_pixels=xy*self.size-.5;raster=self.buffers[0]
        rotated=self.rotate(points);visible=np.zeros(len(points),bool)
        # A nearest pixel can belong to the adjacent triangle on a curved face.
        # Search its one-pixel footprint only when the exact source primitive
        # is known. Other layers/materials never qualify through a depth window.
        offsets=[(0,0)] if triangles is None else [(dx,dy) for dx in [-1,0,1] for dy in [-1,0,1]]
        tolerance=2e-6/self.frame['scale']
        for dx,dy in offsets:
            sample=[xy_pixels[:,1]+dy,xy_pixels[:,0]+dx]
            surface=np.column_stack([map_coordinates(raster[...,i],sample,order=0,mode='nearest') for i in range(3)])
            geometric_normal=np.column_stack([map_coordinates(self.buffers[4][...,i],sample,order=0,mode='nearest') for i in range(3)])
            occupied=map_coordinates(raster[...,3],sample,order=0,mode='nearest')>.5
            distance=np.abs(np.sum((rotated-surface)*geometric_normal,axis=1))
            matched=occupied&(distance<=tolerance)&(np.linalg.norm(geometric_normal,axis=1)>.9)
            if owner is not None:matched&=map_coordinates(self.buffers[2][...,2],sample,order=0,mode='nearest')==owner
            if triangles is not None:matched&=map_coordinates(self.buffers[2][...,3],sample,order=0,mode='nearest')==triangles
            visible|=matched
        visible&=(xy.min(axis=1)>=0)&(xy.max(axis=1)<1)
        normals=self.rotate(normals);normals=normals/np.maximum(np.linalg.norm(normals,axis=1,keepdims=True),1e-12)
        return visible*np.clip(normals[:,2],0,1)

    def render(self,scene,size):
        import moderngl
        import trimesh
        from PIL import Image
        ctx=moderngl.create_standalone_context();attachments=[]
        try:
            program=ctx.program(vertex_shader='#version 330\nuniform mat4 mvp;in vec3 point;in vec3 normal;in vec2 uv;out vec3 p;out vec3 n;out vec2 t;void main(){p=point;n=normal;t=uv;gl_Position=mvp*vec4(point,1);}',fragment_shader='#version 330\nin vec3 p;in vec3 n;in vec2 t;uniform sampler2D albedo;uniform vec4 factor;uniform float index;uniform float cutoff;uniform float opaque;layout(location=0)out vec4 position;layout(location=1)out vec4 normal;layout(location=2)out vec4 texel;layout(location=3)out vec4 color;layout(location=4)out vec4 plane;void main(){vec4 tex=texture(albedo,t);vec3 lin=mix(tex.rgb/12.92,pow((tex.rgb+.055)/1.055,vec3(2.4)),step(vec3(.04045),tex.rgb))*factor.rgb;vec3 enc=mix(lin*12.92,1.055*pow(lin,vec3(1./2.4))-.055,step(vec3(.0031308),lin));vec4 rgb=vec4(enc,tex.a*factor.a);if(rgb.a<cutoff)discard;if(opaque>.5)rgb.a=1.;position=vec4(p,1);normal=vec4(normalize(n),1);texel=vec4(t,index,float(gl_PrimitiveID+1));color=rgb;plane=vec4(normalize(cross(dFdx(p),dFdy(p))),1);}')
            frame=self.frame;center=frame['center'];scale=frame['scale'];depth=max(frame['z_max']-frame['z_min'],1e-8)
            mvp=np.eye(4);mvp[0,0]=mvp[1,1]=2*scale;mvp[0,3]=-2*scale*center[0];mvp[1,3]=-2*scale*center[1];mvp[2,2]=-2/depth;mvp[2,3]=(frame['z_max']+frame['z_min'])/depth
            program['mvp'].write(np.asarray(mvp.T,dtype='f4').tobytes());program['albedo'].value=0
            attachments=[ctx.texture((size,size),4,dtype='f4') for _ in range(5)];z=ctx.depth_renderbuffer((size,size));target=ctx.framebuffer(attachments,z);target.use();target.clear(0,0,0,0,depth=1)
            ctx.enable(moderngl.DEPTH_TEST);ctx.disable(moderngl.CULL_FACE);ctx.depth_func='<='
            for index,node in enumerate(scene.graph.nodes_geometry):
                matrix,name=scene.graph[node];mesh=scene.geometry[name];visual=mesh.visual;material=getattr(visual,'material',None)
                points=self.rotate(canonical_vertices(trimesh.transform_points(mesh.vertices,matrix),self.axis))
                normals=self.rotate(canonical_vertices(np.asarray(mesh.vertex_normals)@np.linalg.inv(matrix[:3,:3]),self.axis))
                uv=getattr(visual,'uv',None);uv=np.zeros((len(points),2)) if uv is None else uv
                buffer=ctx.buffer(np.column_stack([points,normals,uv]).astype('f4').tobytes());indices=ctx.buffer(np.asarray(mesh.faces,dtype='i4').tobytes());vao=ctx.vertex_array(program,[(buffer,'3f 3f 2f','point','normal','uv')],indices)
                image=getattr(material,'baseColorTexture',None) or Image.new('RGBA',(1,1),'white');pixels=np.asarray(image.convert('RGBA'))[::-1].copy();texture=ctx.texture(image.size,4,pixels.tobytes());texture.filter=(moderngl.LINEAR,moderngl.LINEAR);texture.repeat_x=False;texture.repeat_y=False;texture.use()
                factor=getattr(material,'baseColorFactor',None);program['factor'].value=tuple(np.asarray(factor)/255) if factor is not None else (1,1,1,1);program['index'].value=float(index+1)
                cutoff=getattr(material,'alphaCutoff',None);program['cutoff'].value=float(cutoff if cutoff is not None else .5) if getattr(material,'alphaMode',None)=='MASK' else (0. if getattr(material,'alphaMode',None)!='BLEND' else .01);program['opaque'].value=0. if getattr(material,'alphaMode',None)=='BLEND' else 1.
                vao.render(moderngl.TRIANGLES);vao.release();indices.release();buffer.release();texture.release()
            arrays=[np.frombuffer(t.read(),dtype='f4').reshape(size,size,4)[::-1].copy() for t in attachments]
            target.release();z.release();program.release()
            for t in attachments:t.release()
            return arrays
        finally:ctx.release()

    def zoom(self,box,size=512,yaw=0):
        l,t,r,b=box;frame=dict(self.frame);center=np.array(frame['center']);scale=frame['scale']
        center[0]+=((l+r)/2-.5)/scale;center[1]+=(.5-(t+b)/2)/scale
        if yaw:
            points=self.buffers[0][..., :3];selected=self.buffers[0][...,3]>.5
            rows,cols=np.indices(selected.shape);selected&=(cols/self.size>=l)&(cols/self.size<r)&(rows/self.size>=t)&(rows/self.size<b)
            if selected.any():center[2]=np.median(points[selected,2])
            angle=np.deg2rad(yaw);center=center@np.array([[np.cos(angle),0,np.sin(angle)],[0,1,0],[-np.sin(angle),0,np.cos(angle)]])
        frame.update(center=center.tolist(),scale=scale/max(r-l,b-t))
        return RegionCamera(self.scene,self.axis,size,frame,yaw).image
