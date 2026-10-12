# Verificação real — 2026-10-09

## Upgrade de qualidade
Auditoria/benchmark final em QUALITY_AUDIT.md. Nove inferências reais (três casos×Fast/Balanced/Quality), nove FBX aprovados; baseline v1 e ablações preservados. 25 testes passaram, build TypeScript/Vite passou. API e benchmark compartilham lock GPU; nenhum fallback simulado. Revisão independente relida após quatro correções de integração.

Unity 6000.3/URP17.3 no projeto descartável data/UnityQualityValidation: modelo da UI 84.274 tris/1024, otimizado 21.066 tris/1024/1.5m e benchmark Quality 120.508 tris/2048; BaseMap, UV/normais, posições/UV finitas, contagem, escala/prefab e smoothness .35 aprovados juntos. unity-validation.json e logs/unity-quality-final.log registram exit0. Teste batchmode/nographics, sem render/gameplay.

Playwright (Browser plugin not available): http://127.0.0.1:8000, viewport1600×1000/390×844. Título/conteúdo/ausência de overlay, zero erros de aplicação, screenshot e interação verificados. Upload→Generate→GLB carregado→wireframe; original/entrada; comparação esquerda/direita, quatro vistas/albedo; observação manual salva e preservada no reload com sete notas vazias; sem overflow horizontal. Screenshots no diretório de visualizações da conversa. Inspector/página com scroll por conteúdo; aviso Vite sobre chunk Three.js lazy é conhecido.

Atualização com aba aberta revelou um chunk antigo de comparação removido pelo rebuild (404/tela vazia). lazyModule.ts recarrega uma vez para obter o entry point atual, com limite para não entrar em loop. Teste de falha injetou exatamente um 404 e comprovou recuperação automática; contexto novo terminou com zero erros/warnings. Os erros intencionais/de reinício foram distinguidos dos checks finais. Validação Unity foi repetida após exigir as três fixtures, exit0.

Windows, RTX 4060 8188 MiB, driver 595.97; Python 3.12.10, Torch 2.5.1+cu124, Blender 4.5.3 LTS, Unity 6000.3.0f1, URP 17.3.0. Nenhuma geração falsa/mocada foi considerada sucesso. Testes de API com worker desativado verificam infraestrutura; inferências abaixo são subprocessos CUDA reais.

## Fluxo obrigatório
| Etapa | Resultado | Evidência |
|---|---|---|
| Iniciar localmente | PASS | start.ps1, server-error.log, /api/health |
| Upload na interface | PASS | chair.png enviado no Playwright, preview real |
| IA real | PASS | inference.json identifica RTX 4060, pesos e tempos |
| Geometria | PASS | cadeira 20.432 e robô 82.888 tris |
| Viewer | PASS | data-model-loaded=true, screenshots, rotação pixel a pixel |
| UV/textura | PASS | GLB embutido com 1 textura, inspector GLB/Blender |
| FBX | PASS | arquivo binário real e fbx_validation.json |
| Reimportar FBX | PASS | tris, UVs, escala e posições finitas preservados |
| ZIP Unity | PASS | Models/Textures/Editor/README/manifest, zip.testzip sem erro |
| Download | PASS | download event: Forge3D_Unity.zip |
| Unity | PASS | Built-in/URP, textura, prefab, normais/UV e altura em metros |

## Benchmarks
| Entrada | Extração | Triângulos | Pico alocado | Inferência | Processo IA completo |
|---|---:|---:|---:|---:|---:|
| chair isolado | 128 | 20.432 | 1866.5 MiB | 3.05 s | 12.30 s |
| chair no browser | 128 | 20.432 | 1866.5 MiB | 3.17 s | 12.97 s |
| robot com recorte/fundo | 192 | 82.888 | 1937.5 MiB | registrado em inference.json | 13.85 s |
| teapot, textura 2048 | 256 | 76.368 | 2378.5 MiB | 5.64 s | 19.25 s |

Métricas são do processo IA, não VRAM total; desktop/browser também consomem memória. Processo encerra após geração. Socket.connect/create_connection bloqueados, HF/Transformers em modo offline e DINO/u2netp locais. Inferência offline validada nesses casos. Instalação inicial exige internet; não foi alterado firewall nem desconectada toda a máquina.

Todos os presets de extração (128,192,256) e textura (512,1024,2048) foram executados. Teapot 256/2048 apareceu no viewer e passou por FBX reimportado; geração total 26.26 s. Original em data/assets/10ad0f21ca5f4aaf90bdb2f6ae05b02e. Pico reservado CUDA 3052 MiB; alocado 2378.5 MiB.

## Unity e exportação
- Built-in: 20.432 tris, 1 textura, Standard, Prefab.
- URP múltiplos: cadeira 20.432 tris e robô 82.888 tris juntos, sem conflito C#, Universal Render Pipeline/Lit, _BaseMap preenchido. Override somente em QualitySettings também testado.
- Low Poly: 4.086 tris, 1 textura, URP, Prefab.
- Normais/UVs em todos os vértices. Alturas Unity Y-up: 1.076947 m (cadeira), 1.5 m (robô), 1.077479 m (Low Poly); comparação ao Z-up Blender com tolerância 1%.
- Relatórios em data/UnityValidation/Assets/Forge3D_Asset e data/UnityValidationURP/Assets/{AssetA,AssetB,Forge3D_Asset}/unity_import_report.json.
- Reimportação Blender não reassociou automaticamente a textura. PNG externo preservado; importer Unity fez a associação, comprovada no editor. Não se presume PBR completo no FBX.

## Regressões
12/12 testes em test_core.py: uploads/opções, fonte/centro, persistência/restart, operações limitadas, cancelamento fila/terminal/atômico, jobs além do histórico, upload não publicado, origem externa, lock único e cadeia Original. RED observado antes das implementações; logs/tests-release.log registra o resultado final.

Revisão independente motivou: publicação de upload, claim/cancel atômicos, recuperação sem corte de 200, lock da API, pesos/configuração fixados/hash, descarte de mapa oculto/ImageBitmap, URP ativo, importer/menu únicos e instruções. Nenhum achado Important conhecido pendente.

Decimation: versão inicial deixava 44.872 vértices para 4.086 tris e faces desconectadas por normais/UVs do GLB. Diagnóstico confirmou. Correção reconecta posições antes de colapsar arestas; 2.043 vértices Blender, GLB sem warnings do inspector, 4.086 tris, UV/1 textura, FBX/Unity aprovados. Original não sobrescrito.

## Interface e fidelidade
Browser plugin/skill não disponível; Playwright usado. URL/título corretos, conteúdo real, sem overlay, zero erros/warnings de aplicação. Desktop 1600x1000, nativo 1586x992 e mobile 390x844, sem overflow horizontal. Upload → Generate → viewer → Export to Unity → download, wireframe/texturas/enquadrar, Low Poly/Original, dez trocas/reload e Girar com pixels diferentes exercitados.

Referência docs/interface-concept.png (ImageGen integrado, somente UI). Screenshots finais fora do repo: C:\Users\arthu\.codex\visualizations\2026\10\09\01a12269-3152-7493-9717-857cf9de86b5. Conceito e screenshot final inspecionados com view_image na mesma passagem.

| Comparação | Resultado |
|---|---|
| Três painéis, canvas, faixa da biblioteca | Preservados; mobile empilha |
| Carvão/laranja, borda e raios | Tokens CSS consistentes |
| Diamante, títulos/controles/tipografia | Hierarquia legível preservada |
| Upload/Generate/Export | Copy e posição principais, handlers reais |
| Grid/enquadramento | Bounds vazio, orientação e piso corrigidos |
| Resultado | Geometria, imagens, medidas e histórico reais |

Diferenças intencionais: chrome de janela omitido, resoluções na qualidade, ocupação real 85%, luz/validar/material/cancelar/status/downloads exigidos pelo escopo. Inspector scroll para ações extras. Copy principal comparada; extensões em UI-DESIGN.md. Sem desvio visual material conhecido no fluxo testado. Fidelidade verificada junto à funcionalidade, sem alegar qualidade artística uniforme.

## Limites
Unity batchmode/nographics comprova importação/material/UV/normais/escala/prefab; gameplay/renderização final não testados. Não há rig, animação, retopologia, OOM provocado nem teste de toda imagem/navegador. Baking/decimation podem gerar seams/distorções; examine os assets.

## TripoSG autorizado e verificado
Download oficial/hashes,4inferências concluídas (uma smoke128 +três casos256) e repetição real pelo botão Generate/seed42. FBX×3, fluxo256.152→51.230/1,5m, UnityURP geometry-only com mapa antigo removido,30 testes e QA desktop/mobile passaram. Sem CPUoffload, multi-view, texture/PBR SG ou OOM provocado. Resultados detalhados em TRIPOSG_VALIDATION.md; provas separadas em data/quality-upgrade/triposg, preservando a validação TripoSR anterior.

## Fidelidade v3

Quality512³ real na RTX4060, três casos/nove variantes/FBX, máscaras e refinamento conservador,51 testes e build passaram. Playwright: Quality pelo botão→limpeza→silhueta→LowPoly→1,5m→export e ZIP3.603.981bytes; métricas desatualizadas ausentes após decimation. Desktop1600×1000/mobile390×844 sem overflow, quatro vistas×três casos carregadas, zero erros/warnings de aplicação nas verificações finais. Browser plugin indisponível; Playwright usado.

Unity6000.3.0f1/URP17.3 aprovou o FBX realmente exportado:94.054triângulos,altura1,4999999m,UV/posições/normais finitas e normais não nulas,shaderLit/materialneutro/smoothness0,35,prefab,remoção de textura antiga. Batchmode/nographics; gameplay/renderização de cena não testados. Continuidade de normais em costurasUV e preservação de arestas duras também cobertas por regressões. Detalhes, métricas2D e limitações em FIDELITY_V3_VALIDATION.md; provas isoladas em data/quality-upgrade/fidelity-v3/flow-verification.json e release-verification.json.

## Personagens avançados — 11/10/2026

Hunyuan2mini público autorizado sob licençaTencent, isolado em.venv-hy; sem pintura neural/offload. Novo modo384³×2/seeds42,43, refinamento limitado e projeção frontal opcionais; seleção humana preserva RAWs. TripoSR extração/normais em costurasUV corrigidos sem mudar posições/UVs. Originais e modos anteriores preservados.

Hinata exato: lote UI260,60s,alocado4644,1MiB,reservado5160MiB,totalGPU7305MiB; mesmosRAWs do protótipo214,39s.50renders768/fiveviews/clay+textura e4FBXroundtrips; cinco vistas extras da versão otimizada. Candidato2→52330triângulos→altura1,5m→ZIP realmente baixado→Unity6000.3URP17.3/normais+UV+textura1024+material+prefab passaram.0degenerados/bordas/não manifold na versão reduzida; dois componentes preservados.

71testes/1depreciaçãoAnyIO; build6,32s/warningViewer932KB. QA Playwright desktop1600×1000/mobile390×844 sem overflow, wireframe/neutro/textura e cinco vistas×dois materiais carregadas. Revisão única: Original/linhagem e publicação atômica/cancelamento corrigidos RED→GREEN; testeBlender real de UVs/normais também. Sem alegar anatomia exata, costas observadas, rig ou gameplay.

Provas em data/character-advanced-20261011/validation-evidence,ui-flow-verification.json,release-verification.json; Unity isolado em data/UnityCharacterAdvancedValidation. Detalhes/limites/decisões em CHARACTER_ADVANCED_VALIDATION.md. App ativo no workspace desta conversa; instalação antiga C:/Projetos preservada.
