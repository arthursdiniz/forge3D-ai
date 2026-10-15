from fastapi import HTTPException
from ..providers import provider_statuses
from ..texture_engine.providers import provider_statuses as texture_statuses


def capabilities(root):
    return {'model': provider_statuses(root), 'texture': texture_statuses(root),
            'quality_note': 'Qualidade ajusta apenas os perfis locais validados. Não garante reconstrução fiel.'}


def model_plan(root, settings):
    available = {p['id']: p for p in provider_statuses(root) if p['available']}
    # Prefer a seed-capable geometry provider. This is compatibility selection,
    # not a claim that one model is visually superior for every reference.
    provider = settings.provider
    if provider == 'auto':
        order = ['triposr', 'hunyuan_mini', 'triposg'] if settings.quality == 'fast' else ['hunyuan_mini', 'triposg', 'triposr']
        provider = next((p for p in order if p in available), None)
    if provider not in available:
        raise HTTPException(409, 'O modelo de IA selecionado não está disponível. Confira as configurações locais.')
    health = available[provider]
    quality = settings.quality
    warnings = []
    presets = health.get('presets') or (['fast', 'balanced', 'quality'] if provider == 'triposr' else ['balanced'])
    if quality not in presets:
        quality = 'balanced' if 'balanced' in presets else presets[0]
        warnings.append(f'O perfil solicitado não foi validado para {provider}; será usado {quality}.')
    return provider, {'quality': quality, 'texture_output': 'geometry_only',
        'preparation_preset': {'character': 'character', 'anime': 'stylized_character', 'object': 'prop'}[settings.category],
        'background_mode': settings.background_mode,
        'seed': None if provider == 'triposr' else settings.seed,
        'reference_texture': 'none', 'refine_reference': False, 'character_mode': False}, warnings


def texture_plan(root, settings, parent):
    available = {p['id']: p for p in texture_statuses(root) if p['available']}
    provider = settings.provider
    if provider == 'auto':
        provider = next((p for p in ['neural_multiview', 'reference_projection'] if p in available), None)
    if provider not in available:
        raise HTTPException(409, 'Não há provedor de textura validado para esta opção. Confira Configurações.')
    warnings = []
    if provider == 'reference_projection':
        if settings.goal != 'reference' or settings.prompt:
            raise HTTPException(422, 'Este objetivo precisa da IA multiview. A projeção local apenas copia a aparência visível da referência.')
        warnings.append('Projeção de referências: áreas sem observação não são reconstruídas por IA e podem permanecer neutras.')
    options = {'provider': provider, 'resolution': {'fast': 1024, 'balanced': 2048, 'quality': 4096}[settings.quality],
        'uv_mode': 'auto', 'front_axis': settings.front_axis or parent['metadata'].get('render_front_axis', 'negative_y'),
        'background_mode': settings.background_mode, 'use_saved_references': settings.use_saved_references}
    if provider == 'neural_multiview':
        options.update(seed=settings.seed, style='free' if settings.goal == 'reference' else settings.goal,
                       prompt=settings.prompt, fidelity=1.0)
    return options, warnings
