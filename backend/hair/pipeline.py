"""Independent rooted hair volumes with exact original geometry/material preservation."""
import copy,json
from pathlib import Path
import numpy as np

def preserved_copy(scene):
    result=scene.copy()
    for name,mesh in scene.geometry.items():result.geometry[name].vertex_normals=np.asarray(mesh.vertex_normals).copy();result.geometry[name].visual=copy.deepcopy(mesh.visual)
    return result

def hair_material(mesh,name,color):
    import trimesh,xatlas
    from PIL import Image
    mapping,faces,uv=xatlas.parametrize(np.asarray(mesh.vertices,'f4'),np.asarray(mesh.faces,'u4'))
    result=trimesh.Trimesh(vertices=mesh.vertices[mapping],faces=faces,vertex_normals=mesh.vertex_normals[mapping],visual=trimesh.visual.TextureVisuals(uv=uv,material=trimesh.visual.material.PBRMaterial(name=name,baseColorTexture=Image.new('RGBA',(64,64),tuple(color)+ (255,)),metallicFactor=0,roughnessFactor=.7)),process=False)
    return result

def reconstruct_hair(scene,analysis,options,directory):
    import trimesh
    from .volume import base_volume,scalp_guide
    from .curves import sweep_clump
    from .metrics import mesh_integrity,exported_mass_integrity
    from .scalp import scalp_sdf
    from backend.texture_engine.identity import compare_geometry
    from backend.character_quality import view_vertices
    directory=Path(directory);directory.mkdir(parents=True,exist_ok=True)
    if not options.get('reviewed'):raise ValueError('Review hair mask, head/scalp and alignment before creating geometry.')
    scalp=analysis.get('scalp',{})
    if scalp.get('status')!='reviewable':return preserved_copy(scene),{'status':'inconclusive_previous_retained','source_retained':True,'reason':scalp.get('reason','Unsafe scalp.'),'hair_meshes':[]}
    understanding=analysis['understanding'];attributes={**understanding['attributes'],**options.get('attributes',{})};preset=options.get('preset','auto');preset=understanding['preset'] if preset=='auto' else preset
    if preset=='buzz':attributes.update(volume=min(attributes.get('volume',.025),.035),lateral_volume=min(attributes.get('lateral_volume',.02),.03),top_height=min(attributes.get('top_height',.025),.035),back_volume=min(attributes.get('back_volume',.02),.03),spikes=0,fringe=0)
    elif preset=='close_short':attributes['spikes']=0;attributes['volume']=min(attributes.get('volume',.05),.06)
    support_mask=analysis.get('reference_support_mask');frame=analysis.get('camera_frame')
    def support(point):
        if support_mask is None or frame is None:return False
        size=support_mask.shape[0];u=.5+(point[0]-frame['center'][0])*frame['scale'];v=.5-(point[1]-frame['center'][1])*frame['scale'];x,y=int(u*size),int(v*size)
        return 0<=x<size and 0<=y<size and bool(support_mask[y,x])
    base=base_volume(scalp,attributes,envelope=analysis.get('existing_head_field'),baseline=understanding['attributes'],allow_expansion=understanding.get('existing_volume',{}).get('flattened_heuristic',False),support=support);masses=[base];records=[];clumps=[];center=np.asarray(scalp['center']);radii=np.asarray(scalp['radii'])
    for i,guide in enumerate(understanding.get('tips',[])[:48]):
        if preset in ['buzz','close_short']:continue
        if preset in ['short_volume','straight_medium'] and guide['zone']!='fringe' and not guide.get('pointed',True):continue
        if guide.get('already_covered') and guide['zone']!='fringe' and not options.get('attributes'):continue
        if guide['zone']!='fringe' and preset in ['anime_spiky','spiky'] and attributes.get('spikes',.5)<=0:continue
        if guide['zone']=='fringe' and attributes.get('fringe',.2)<=0:continue
        proposed_root=np.asarray(guide['root_world']);root=np.asarray(base.vertices[np.argmin(np.linalg.norm(base.vertices-proposed_root,axis=1))]).copy();tip=np.asarray(guide['tip_world']).copy()
        strength=attributes.get('fringe',.2) if guide['zone']=='fringe' else (attributes.get('spikes',.5) if preset in ['anime_spiky','spiky'] else .6)
        length_scale=attributes.get('length',.3)/max(understanding['attributes'].get('length',.3),.01)
        baseline=understanding['attributes'].get('fringe',.2) if guide['zone']=='fringe' else (understanding['attributes'].get('spikes',.5) if preset in ['anime_spiky','spiky'] else .6)
        tip=root+(tip-root)*np.clip(strength/max(baseline,.1),.2,1.8)*np.clip(length_scale,.35,2);tip[2]+=radii[2]*attributes.get('volume',.08)*.25
        length=np.linalg.norm(tip-root)
        if length<radii.min()*.08:continue
        middle=(root+tip)/2;middle[2]+=radii[2]*.15;curve=np.stack([root,middle,tip]);width=float(np.clip(guide.get('width',.08),.025,.23)*radii[0]);thickness=max(radii.min()*.008,attributes.get('thickness',.05)*radii.min())
        angular_fringe=analysis.get('options',{}).get('style')=='anime' and guide['zone']=='fringe' and preset in ['short_volume','straight_medium','fringe','long','large_clumps']
        profile='triangular' if preset in ['anime_spiky','spiky'] or angular_fringe else ('asymmetric' if attributes.get('asymmetry',0)>.1 else 'elliptical')
        mesh=sweep_clump(curve,width,thickness,profile,attributes.get('curvature',0));clumps.append(mesh);masses.append(mesh)
        records.append({'index':i,'root':root.tolist(),'tip':tip.tolist(),'curve':curve.tolist(),'width':width,'thickness':thickness,'profile':profile,'zone':guide['zone'],'root_scalp_signed_distance':float(scalp_sdf(root,scalp)),'root_base_distance':float(np.linalg.norm(base.vertices-root,axis=1).min()),'observation':guide.get('observation','front contour')})
    integrity=[mesh_integrity(mesh) for mesh in masses]
    if any(not r['finite'] or not r['watertight'] or not r['winding_consistent'] or r['degenerate_triangles'] for r in integrity):raise ValueError('Generated hair mass integrity failed; original preserved.')
    if sum(len(m.faces) for m in masses)>30000:raise ValueError('Hair triangle budget exceeded.')
    result=preserved_copy(scene);names=[];color=understanding.get('hair_color') or [90,60,35]
    for name,mesh in [('HairBaseVolume',base)]+([('HairClumps',trimesh.util.concatenate(clumps))] if clumps else []):
        if name in scene.geometry:raise ValueError('Generated hair names already exist; reconstruct from recorded base source to avoid stacking.')
        prepared=hair_material(mesh,'ForgeHair_'+name,color)
        if options.get('front_axis')=='x':
            normals=np.asarray(prepared.vertex_normals).copy()
            prepared.vertices=view_vertices(prepared.vertices,'right')
            prepared.vertex_normals=view_vertices(normals,'right')
        result.add_geometry(prepared,node_name=name,geom_name=name);names.append(name)
    protected=preserved_copy(result)
    for node in list(protected.graph.nodes_geometry):
        if protected.graph[node][1] in names:protected.delete_geometry(protected.graph[node][1])
    identity=compare_geometry(scene,protected)
    maps_preserved=all(np.array_equal(scene.geometry[n].visual.uv,result.geometry[n].visual.uv) if getattr(scene.geometry[n].visual,'uv',None) is not None else True for n in scene.geometry)
    if not identity['equivalent'] or not maps_preserved:raise ValueError('Protected source geometry/UV changed.')
    report={'status':'reviewable_candidate','source_retained':True,'fused_source_policy':'Original fused hair/head retained under independently generated volumes; no unsafe cutting or body regeneration.','protected_geometry':identity,'source_uv_preserved':maps_preserved,'hair_meshes':names,'generated_geometry_names':names,'hair_triangles':sum(r['triangles'] for r in integrity),'clumps':records,'integrity':integrity,'scalp':scalp,'attributes':attributes,'preset':preset,'source_color':color,'color_method':'Median of observed semantic hair pixels; no generated neural texture or skin colors.','mass_volume_sum':sum(r['volume'] for r in integrity),'volume_scope':'Sum of closed mass volumes, intentional overlaps counted; not exact Boolean union.','root_overlaps_intentional':True,'hidden_geometry_confidence':'low','geometry_parameters_not_neural_reconstruction':True,'limitations':['Scalp and unobserved backside are hypotheses; review lateral/back views.','Fused original geometry is retained, not retopologized or rigged.','Hair colors come from the reference but detailed strand textures are not generated.']}
    guide=scalp_guide(scalp)
    report['observed_views']=analysis.get('observed_views',['front']);report['extra_views']=analysis.get('extra_views',[]);report['relative_depth_layer_cue']=understanding.get('layers',{});report['existing_volume']=understanding.get('existing_volume',{})
    report['new_mass_volume_relative_to_estimated_scalp']=report['mass_volume_sum']/float(4*np.pi/3*np.prod(radii));report['relative_volume_scope']='Additional closed mass sum versus estimated ellipsoid; overlapping/source fused hair is not the exact total hair volume.'
    if options.get('front_axis')=='x':guide.vertices=view_vertices(guide.vertices,'right')
    guide.export(directory/'scalp.glb',include_normals=True)
    isolated=trimesh.Scene()
    for name in names:isolated.add_geometry(result.geometry[name],geom_name=name,node_name=name)
    isolated.export(directory/'hair_isolated.glb',include_normals=True)
    (directory/'hair_geometry.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
    serialized=trimesh.load(__import__('io').BytesIO(result.export(file_type='glb',include_normals=True)),file_type='glb',force='scene',process=False)
    channel_checks=[]
    for name,original in scene.geometry.items():
        current=serialized.geometry[name];normal_ok=np.allclose(original.vertex_normals,current.vertex_normals,atol=1e-6,rtol=0);uv=getattr(original.visual,'uv',None);uv_ok=uv is None or np.allclose(uv,current.visual.uv,atol=1e-6,rtol=0);a=getattr(original.visual,'material',None);b=getattr(current.visual,'material',None);maps={}
        for channel in ['baseColorTexture','normalTexture','occlusionTexture','metallicRoughnessTexture','emissiveTexture']:
            before=getattr(a,channel,None);after=getattr(b,channel,None)
            if before is not None:maps[channel]=after is not None and np.array_equal(np.asarray(before),np.asarray(after))
        channel_checks.append({'geometry':name,'normals_within_1e_6':bool(normal_ok),'uv_within_1e_6':bool(uv_ok),'original_maps_equal_pixels':maps})
    if any(not c['normals_within_1e_6'] or not c['uv_within_1e_6'] or not all(c['original_maps_equal_pixels'].values()) for c in channel_checks):raise ValueError('Original channels changed during actual GLB roundtrip.')
    report['source_channel_roundtrip']=channel_checks;report['exported_hair_topology']={name:exported_mass_integrity(serialized.geometry[name]) for name in names}
    if any(not c['uv_valid'] or not c['geometric_topology']['watertight'] or c['geometric_topology']['degenerate_triangles'] for c in report['exported_hair_topology'].values()):raise ValueError('Exported hair UV/topology failed.')
    (directory/'hair_geometry.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
    return result,report
