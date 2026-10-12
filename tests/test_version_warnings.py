def test_current_mesh_counts_replace_ancestor_counts_but_keep_operation_warnings():
    from backend.worker import version_warnings
    old=['126 componentes desconectados; confira partes soltas nas vistas.','61 triângulos de área quase zero. RAW preservado; limpeza não aplicada automaticamente.','Decimation pode alterar detalhes e distorcer UVs.','O objeto toca a borda.']
    new=['54 componentes desconectados; confira partes soltas nas vistas.']
    result=version_warnings(old,new)
    assert old[0] not in result and old[1] not in result
    assert old[2] in result and old[3] in result and new[0] in result

def test_a_descendant_does_not_present_the_parents_iou_as_its_own_measurement():
    from backend.worker import version_metadata
    parent={'triangles':100,'refinement':{'silhouette_iou_after':0.93},'mesh_refinement':{'operation':'refine_silhouette'}}
    result=version_metadata(parent,'transform')
    assert 'refinement' not in result and 'mesh_refinement' not in result
    assert result['triangles']==100
    assert parent['refinement']['silhouette_iou_after']==0.93
    assert version_metadata(parent,'export')['refinement']['silhouette_iou_after']==0.93
