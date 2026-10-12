"""Only parameters implemented by each real provider. No quality scores."""
MODES={
    'fast':{'mc_resolution':128,'texture_resolution':512,'texture_method':'vertex_bake','auto_decimate':False},
    'balanced':{'mc_resolution':256,'texture_resolution':1024,'texture_method':'neural_atlas','auto_decimate':False},
    'quality':{'mc_resolution':320,'texture_resolution':2048,'texture_method':'neural_atlas','auto_decimate':False},
}
PREPARATION_PRESETS={
    'character':{'foreground_ratio':0.9,'background_mode':'auto'},
    'stylized_character':{'foreground_ratio':0.85,'background_mode':'auto'},
    'prop':{'foreground_ratio':0.85,'background_mode':'auto'},
    'hard_surface':{'foreground_ratio':0.9,'background_mode':'auto'},
    'organic':{'foreground_ratio':0.85,'background_mode':'auto'},
}
TRIPOSG_BALANCED={'num_inference_steps':50,'guidance_scale':7.0,'num_tokens':2048,'dense_octree_depth':7,'hierarchical_octree_depth':8,'mc_resolution':256,'decoder_chunk':8192,'model_cpu_offload':False,'texture_resolution':None,'texture_method':'none','auto_decimate':False}
TRIPOSG_QUALITY={**TRIPOSG_BALANCED,'hierarchical_octree_depth':9,'mc_resolution':512}
HUNYUAN_BALANCED={'num_inference_steps':50,'guidance_scale':5.0,'mc_resolution':256,'num_chunks':8000,'model_cpu_offload':False,'texture_resolution':None,'texture_method':'none','auto_decimate':False,'candidate_count':1,'dtype':'float16','encoder_resolution':518}
HUNYUAN_QUALITY={**HUNYUAN_BALANCED,'mc_resolution':384}
HUNYUAN_ADVANCED={**HUNYUAN_QUALITY,'candidate_count':2}

def generation_settings(mode,provider='triposr'):
    mode={'draft':'fast','high':'quality'}.get(mode,mode)
    if provider=='character_base_mesh':
        if mode!='balanced':raise ValueError('Template assistido usa somente Balanced CPU.')
        return {'mc_resolution':128,'texture_resolution':None,'neural_generation':False}
    if provider=='hunyuan_mv':
        if mode!='balanced':raise ValueError('Hunyuan multiview: somente Balanced256 validado nesta GPU.')
        return dict(HUNYUAN_BALANCED)
    if provider=='hunyuan_mini':
        if mode not in ['balanced','quality','advanced']:raise ValueError('Hunyuan-mini: Balanced/Quality/Avançado; Fast não implementado.')
        return dict({'balanced':HUNYUAN_BALANCED,'quality':HUNYUAN_QUALITY,'advanced':HUNYUAN_ADVANCED}[mode])
    if provider=='triposg':
        if mode not in ['balanced','quality']:raise ValueError('TripoSG: somente Balanced/Quality implementados; Fast não suportado.')
        return dict(TRIPOSG_QUALITY if mode=='quality' else TRIPOSG_BALANCED)
    if provider!='triposr':
        raise ValueError('Parâmetros deste provedor ainda não validados.')
    if mode not in MODES:
        raise ValueError('Modo de geração inválido.')
    return dict(MODES[mode])

def validate_provider_options(provider,options):
    generation_settings(options.quality,provider)
    if provider=='character_base_mesh' and options.texture_resolution is not None:raise ValueError('Template gera geometria sem textura; use projeção/baking depois de selecionar a forma.')
    if provider=='hunyuan_mv' and options.texture_resolution is not None and not (options.quality_mode and options.reference_texture=='front'):raise ValueError('Multiview gera geometria; resolução de textura exige projeção em Quality Mode.')
    if provider=='character_base_mesh' and (options.strategy!='base_mesh' or not options.character_mode or options.seed is not None or options.candidate_count not in [None,1] or options.reference_texture!='none' or options.refine_reference):raise ValueError('Template próprio exige estratégia base_mesh e pontos revisados, sem seeds/lotes neurais ou projeção automática.')
    if (options.reference_texture!='none' or options.refine_reference) and (provider not in ['hunyuan_mini','triposg','hunyuan_mv'] or (options.quality!='advanced' and not options.quality_mode)):raise ValueError('Textura por referência/refinamento integrado exige Quality Mode ou Avançado compatível.')
    if options.quality_mode and provider=='triposr' and options.candidate_count not in [None,1]:raise ValueError('TripoSR não suporta múltiplos candidatos por seed.')
    if provider=='triposr' and options.seed is not None:raise ValueError('TripoSR não suporta seed de geração.')
    if provider=='triposg' and options.texture_resolution is not None and not (options.quality_mode and options.reference_texture=='front'):raise ValueError('TripoSG gera geometria; resolução de textura exige projeção em Quality Mode.')
    if provider=='triposg' and options.foreground_ratio is not None and options.foreground_ratio>0.875:raise ValueError('TripoSG: ocupação máxima 87,5%; valores maiores cortam o objeto no encoder 224/256.')
    if provider=='hunyuan_mini' and options.texture_resolution is not None and ((options.quality!='advanced' and not options.quality_mode) or options.reference_texture!='front'):raise ValueError('Hunyuan-mini gera forma; resolução de textura exige projeção frontal no modo Avançado/Quality Mode.')
    if provider=='triposr' and options.texture_resolution==4096:raise ValueError('TripoSR neural suporta até2K neste perfil;4K disponível no baking/projeção por referência.')
