"""Reference projection on actually visible surfaces; unseen areas stay neutral."""
import numpy as np

NEUTRAL=0.7353569830524495 # sRGB corresponding to linear0.5 material

def projection_frame(vertices,rgba):
    v=np.asarray(vertices);a=np.asarray(rgba)[...,3]
    rows,cols=np.nonzero(a>128)
    if not len(rows):raise ValueError('Reference has no confident foreground.')
    bbox=(int(cols.min()),int(rows.min()),int(cols.max()+1),int(rows.max()+1))
    minimum=v.min(axis=0);maximum=v.max(axis=0);height=float(maximum[1]-minimum[1])
    if height<=0:raise ValueError('Model has no vertical extent.')
    scale=(bbox[3]-bbox[1])/height
    return {'scale':scale,'center_x':float((minimum[0]+maximum[0])/2),'center_y':float((minimum[1]+maximum[1])/2),'pixel_x':(bbox[0]+bbox[2])/2,'pixel_y':(bbox[1]+bbox[3])/2,'width':rgba.shape[1],'height':rgba.shape[0],'bbox':bbox,'z_min':float(minimum[2]),'z_max':float(maximum[2])}

def image_coordinates(points,frame):
    p=np.asarray(points)
    x=(p[:,0]-frame['center_x'])*frame['scale']+frame['pixel_x']
    y=frame['pixel_y']-(p[:,1]-frame['center_y'])*frame['scale']
    return np.column_stack([x,y])

def rasterize_front(vertices,faces,frame,resolution=512):
    """Orthographic +Z camera, Y-up, depth-tested, output rows bottom-to-top."""
    import moderngl
    context=moderngl.create_standalone_context()
    try:
        xyz=np.asarray(vertices,dtype=np.float32)
        pixels=image_coordinates(xyz,frame)
        clip=np.empty_like(xyz)
        clip[:,0]=pixels[:,0]/frame['width']*2-1
        clip[:,1]=1-pixels[:,1]/frame['height']*2
        depth=max(frame['z_max']-frame['z_min'],1e-8)
        clip[:,2]=1-2*(xyz[:,2]-frame['z_min'])/depth
        program=context.program(vertex_shader='''#version330
in vec3 in_clip; in vec3 in_position; out vec3 position;
void main(){gl_Position=vec4(in_clip,1);position=in_position;}'''.replace('#version330','#version 330'),fragment_shader='''#version 330
in vec3 position; out vec4 result;
void main(){result=vec4(position,1);}''')
        positions=context.buffer(xyz.tobytes());clips=context.buffer(clip.astype('f4').tobytes());indices=context.buffer(np.asarray(faces,dtype='i4').tobytes())
        vao=context.vertex_array(program,[(clips,'3f','in_clip'),(positions,'3f','in_position')],indices)
        texture=context.texture((resolution,resolution),4,dtype='f4');z=context.depth_renderbuffer((resolution,resolution))
        framebuffer=context.framebuffer(color_attachments=[texture],depth_attachment=z);framebuffer.use();framebuffer.clear(0,0,0,0,depth=1)
        context.enable(moderngl.DEPTH_TEST);context.disable(moderngl.CULL_FACE);context.depth_func='<='
        vao.render(mode=moderngl.TRIANGLES)
        raster=np.frombuffer(texture.read(),dtype='f4').reshape(resolution,resolution,4).copy()
        vao.release();indices.release();clips.release();positions.release();framebuffer.release();z.release();texture.release();program.release()
        return raster
    finally:context.release()

def project_reference_colors(vertices,faces,positions,normals,rgba,depth_resolution=1024):
    from scipy.ndimage import map_coordinates
    frame=projection_frame(vertices,rgba);raster=rasterize_front(vertices,faces,frame,depth_resolution)
    pixels=image_coordinates(positions,frame)
    h,w=rgba.shape[:2]
    px=np.clip(pixels[:,0]-0.5,0,w-1);py=np.clip(pixels[:,1]-0.5,0,h-1)
    sample=np.column_stack([map_coordinates(rgba[...,i].astype(float),[py,px],order=1,mode='nearest') for i in range(4)])/255
    depth_x=np.clip(pixels[:,0]/w*depth_resolution-0.5,0,depth_resolution-1)
    depth_y=np.clip((1-pixels[:,1]/h)*depth_resolution-0.5,0,depth_resolution-1)
    z=map_coordinates(raster[...,2],[depth_y,depth_x],order=1,mode='nearest')
    occupied=map_coordinates(raster[...,3],[depth_y,depth_x],order=0,mode='nearest')>0.5
    n=np.asarray(normals,dtype=float);n/=np.maximum(np.linalg.norm(n,axis=1,keepdims=True),1e-12)
    # A fraction of a raster pixel in world units allows interpolation error.
    tolerance=max((frame['z_max']-frame['z_min'])/depth_resolution*2,1e-6)
    visible=occupied & (np.abs(z-np.asarray(positions)[:,2])<=tolerance)
    visible&=(pixels[:,0]>=0)&(pixels[:,0]<w)&(pixels[:,1]>=0)&(pixels[:,1]<h)
    confidence=np.clip((n[:,2]-0.15)/0.5,0,1)*sample[:,3]*visible
    confidence[sample[:,3]<0.75]=0
    rgb=sample[:,:3]*confidence[:,None]+NEUTRAL*(1-confidence[:,None])
    return rgb.astype(np.float32),confidence.astype(np.float32)
