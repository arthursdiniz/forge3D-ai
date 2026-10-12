"""Reject measured structural regressions instead of hiding them with a bake."""
def validate_reduction(before, after):
    source=before['integrity'];target=after['integrity'];failures=[]
    for key in ['boundary_edges','nonmanifold_edges','duplicate_faces','inconsistent_winding_edges','connected_components']:
        if target.get(key,0)>source.get(key,0):failures.append(key)
    a=source.get('checks',{}).get('intersections',{}).get('selected_faces')
    b=target.get('checks',{}).get('intersections',{}).get('selected_faces')
    if a is not None and b is not None and b>a:failures.append('new_self_intersections')
    volume=abs(source.get('signed_volume',0))
    if source.get('watertight') and volume>1e-9 and abs(abs(target.get('signed_volume',0))/volume-1)>.01:failures.append('volume_change_above_1_percent')
    for name,reference in before.get('silhouettes',{}).items():
        low=after.get('silhouettes',{}).get(name,{})
        if reference.get('iou') is not None and low.get('iou') is not None and low['iou']<reference['iou']-.01:failures.append('silhouette_regression_'+name)
    if failures:raise ValueError('Game Ready recusado: '+', '.join(failures)+'. Origem e diagnóstico preservados; aumente o orçamento ou faça retopologia manual.')
    return {'passed':True,'method':'Actual source/low geometry probes; no new holes/nonmanifold/winding/duplicates/intersections/components, <=1% closed volume and measured silhouette loss','intersections_measured':a is not None and b is not None,'source_components':source['connected_components'],'low_components':target['connected_components'],'automatic_hole_filling':False}
