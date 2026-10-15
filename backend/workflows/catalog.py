TECHNICAL = {'export', 'semantic_analysis', 'hair_analysis'}


def catalog(store):
    all_jobs = store.list(limit=None)
    lookup = {j['id']: j for j in all_jobs}
    groups = {}
    for job in reversed(all_jobs):
        if job['kind'] in TECHNICAL:
            continue
        # Failed/in-flight model attempts belong in task progress, not asset cards.
        if job['status'] != 'completed' or 'model' not in job['artifacts']:
            continue
        ancestor = job
        visited = set()
        while ancestor.get('parent') in lookup and ancestor['id'] not in visited:
            visited.add(ancestor['id'])
            parent = lookup[ancestor['parent']]
            if parent['kind'] in TECHNICAL:
                break
            ancestor = parent
        root_id = ancestor['id']
        legacy_category = {'stylized_character': 'anime', 'character': 'character'}.get(ancestor.get('options', {}).get('preparation_preset'), 'object')
        group = groups.setdefault(root_id, {'id': root_id, 'name': ancestor['name'], 'versions': [],
                    'category': (ancestor['metadata'].get('workflow') or {}).get('settings', {}).get('category', legacy_category)})
        textured = any(m.get('images') for m in job['metadata'].get('materials', []))
        # A geometry-only model can still have an embedded neutral material.
        if job['kind'] == 'model_workflow' or job.get('options', {}).get('texture_output') == 'geometry_only':
            textured = False
        # Candidates share a batch card, but each generated candidate starts its own geometry lineage.
        original = job
        seen = set()
        while original.get('parent') in lookup and original['kind'] != 'generate' and original['id'] not in seen:
            seen.add(original['id'])
            original = lookup[original['parent']]
        group['versions'].append({'id': job['id'], 'name': job['name'], 'kind': job['kind'],
            'created_at': job['created_at'], 'preview': job['artifacts'].get('preview'), 'has_texture': textured,
            'original_id': original['id'], 'candidate_index': original['metadata'].get('candidate_index')})
        group.update(latest_id=job['id'], preview=job['artifacts'].get('preview'), has_texture=textured,
                     updated_at=job['updated_at'], warnings=len(job['metadata'].get('warnings', [])), status=job['status'])
    return sorted(groups.values(), key=lambda g: g['updated_at'], reverse=True)
