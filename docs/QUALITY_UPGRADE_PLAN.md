# Upgrade de qualidade — 2026-10-09

Escopo autorizado: melhorar geração e artefatos reais no projeto existente, preservar originais/funcionalidades, comparar antes/depois e candidatos locais. Sem equivalência presumida a Meshy, pontuações artificiais, novos serviços pagos, rig ou redesign.

1. Auditar código e salvar baseline imutável de código, três referências e gerações/FBX reais. Arquivos em data/quality-upgrade/baseline-source e baseline. Registrar QUALITY_AUDIT.md.
2. Avaliar SPAR3D primeiro, SF3D, TripoSG, Hunyuan2/mini/mv. Pesos gated 401 não permitem inferência; não aceitar termos pelo usuário. TripoSG (~8 GB, MIT, 8 GB GPU limítrofe) requer autorização de download, solicitada de forma assíncrona.
3. Hipóteses isoladas: texturização densa do campo neural/xatlas versus cores de vértices+Smart UV; preparação com alpha preservado/avisos/enquadramento; reconstrução com presets reais e memória monitorada; preservar RAW, processado, otimizado e export.
4. TDD para parâmetros/capabilities/preparação/preservação de materiais. Teste real CUDA e Blender para textura/UV, render comparável em quatro vistas e métricas de integridade. Não tratar número de tris como pontuação de qualidade.
5. Se autorizado e viável: ambiente TripoSG isolado, pesos safetensors fixados, inferência real sem baixar modelos auxiliares de licença diferente. Comparar geometria, tratar falta de texturas explicitamente. Nenhum novo default sem evidência.
6. Validar exportação/reimportação Blender e Unity URP de amostras melhoradas. Só depois adicionar Fast/Balanced/Quality, input efetivo, capabilities e página lado a lado/rubrica manual. Não substituir layout existente.
7. Benchmark completo nas três categorias, registros reais (parâmetros/seed quando suportado/tempo/VRAM/UV/textura/FBX), revisão independente, PROGRESS atualizado e limitações pendentes.

O pedido fornece escopo e determina execução autônoma entre fases; planejamento é registrado sem inserir aprovações técnicas triviais. Aprovação não trivial de download grande e acesso/licença permanece respeitada.
