# Forge3D AI — progresso e continuidade

Atualizado: 2026-10-09. Projeto real instalado em **C:\Projetos\forge3d-ai**. Fonte também preservada no workspace desta conversa. As cinco skills customizadas existentes em .agents foram lidas e preservadas.

## Upgrade de qualidade validado
- Auditoria e baseline concluídos antes de alterar a geração: código arquivado em data/quality-upgrade/baseline-source, três referências oficiais MIT, geração/FBX em baseline, parâmetros/hashes em manifest.json. TripoSR local real, nenhum mock; gargalos confirmados em normals e texturização por vértice. Auditoria em QUALITY_AUDIT.md.
- Novo caminho TripoSR v2: normais explícitas, RAW imutável, UV xatlas, posições de superfície rasterizadas e consulta real do campo neural por texel. Materiais/UV nativos preservados pelo Blender. Fast 128³/512, Balanced 256³/1024, Quality 320³/2048, sem decimation automática. Não há mapas PBR inventados, delighting ou detalhes de subdivisão.
- Benchmark final: nove inferências reais/offline (três casos×Fast/Balanced/Quality), nove FBX reimportados com UV/escala preservados. Pico alocado Fast1866.5/Balanced2378.5/Quality3114.5 MiB; reservado2060/3052/4032. Métricas completas, tempos e observações por categoria em QUALITY_AUDIT.md. Resultados iniciais preservados em ablation/atlas-initial; baseline imutável em baseline.
- Preparação: alpha confiável preservado em auto, u2netp CPU em fundo opaco, proporção/enquadramento, presets reais de ocupação, avisos de resolução/bordas. EXIF corrigido no upload. Entrada efetiva e original acessíveis na UI.
- Comparação React no layout existente, quatro vistas e albedo sem luz do render; avaliações manuais1–5 persistidas, sem notas pré-preenchidas. 25 testes passaram, TypeScript/Vite compilou. Playwright1600×1000/390×844 verificou geração/GLB/wireframe, input original/efetivo, comparação/albedo e persistência de observação com notas vazias; sem overflow/erros de aplicação.
- Investigação oficial: SPAR3D/SF3D pesos gated 401; TripoSG MIT7.40 GiB recebeu autorização e foi baixado/testado (fase detalhada abaixo); Hunyuan2mini/mv têm licença própria, não instalada/aceita. Nenhum desses foi fingido disponível; multi-view continua desabilitado.
- Ablação UV concluída na mesma malha: 16→4 pixels de margem, 459.010→1.652.530 texels úteis/2048, 10.94%→39.40% de cobertura. Fast/RAW sRGB→COLOR_0 linear corrigido. Quatro achados da revisão independente (cor, lineage, baseline sobrescrito, concorrência) corrigidos e relidos.
- Fluxo UI/API real: 84.274→21.066 tris, centralização/altura1.5m, RAW com SHA256 idêntico, processed preservado e último optimized corretamente rotulado. Unity6/URP17.3 importou alta+otimizada+benchmark Quality2048 juntos com textura/normais/UV/escala/prefab e smoothness .35: exit0. Provas flow-verification.json, unity-validation.json e projeto descartável data/UnityQualityValidation.
- Pendências externas: acesso gated SPAR3D/SF3D e licença/teste Hunyuan. TripoSR continua default; TripoSG foi validado em execução real, sem offload. Multi-view continua desabilitado. Sem equivalência Meshy. Qualidade artística varia; veja relatório de pequenas partes soltas/triângulos quase degenerados. Sem rig/retopo/PBR separado/gameplay Unity/OOM provocado.
- Recuperação de chunk de UI antigo após rebuild implementada/testada com uma falha404 injetada; recarregamento único recuperou a comparação. Contexto novo: zero erros/warnings, três casos×quatro variantes (baseline+modos), todos os renders/FBX/integridade disponíveis. Snapshot final de código/dependências e hashes em data/quality-upgrade/final-source; prova consolidada em release-verification.json.

## TripoSG — download autorizado e integração real
- Pesos oficiais (~7,95GB) concluídos e SHA256 dos três safetensors conferidos; código/pesos pinned. Ambiente .venv-sg isolado, sem alterar TripoSR. pip check aprovado, lock de dependências registrado.
- Três inferências reais CUDA FP16, seed42,50passos/256³: bule256.152, robô409.674 processados (RAW409.676), cadeira274.722tris. IA54–59s, pico4.225MiB alocados;3FBX com UV/escala aprovados. Sem CPUoffload ou textura gerada.
- UI/API selecionam provedor corretamente, somente Balanced/seed no SG, controles de textura desabilitados. Preparação branca/u2netpCPU, entrada efetiva224px, ocupação<=87,5%; comparação neutra em quatro vistas com luz/eixos alinhados. UV Smart Project/material neutro via Blender. RAW/latentes preservados. Relatório TRIPOSG_VALIDATION.md.
- Fluxo pelo botão Generate aprovado; repetição seed42 com SHA256 RAW idêntico ao benchmark. Low Poly256.152→51.230tris, altura1,5m, exportação real API/FBX e Unity6/URP17.3 com UV/normais/escala/prefab/textura0 aprovados. Reimportação limpa albedo antigo. Prova data/quality-upgrade/triposg/flow-verification.json.
- 30 testes aprovados, build TS/Vite, revisão independente e quatro achados corrigidos (crop encoder, material anterior, luz/flanco da comparação e disponibilidade sem vendor). UI desktop/mobile sem overflow; contexto novo sem erros/warnings.

## Fases executadas
1. Ambiente: Windows nativo, Python 3.12, dois venvs, PyTorch 2.5.1+cu124, CUDA RTX 4060, Blender portátil 4.5.3 LTS com SHA256 verificado. Sem Docker/WSL.
2. IA: TripoSR real, código 107cefdc244c39106fa830359024f6a2f1c78871; pesos 5b521936b01fbe1890f6f9baed0254ab6351c04a, checksum e weights_only=True. Quatro inferências: cadeira duas vezes, robô e teapot. Inferência com conexões bloqueadas, pesos/configuração locais. Recorte e u2netp CPU testados. Todos os presets 128/192/256 e texturas 512/1024/2048 executados. Teapot 256: 76.368 tris, pico 2378.5 MiB alocados, IA completa 19.25 s; geração com Blender 26.26 s.
3. FBX/Unity: albedo por baking, UVs, correção de eixos e FBX real reimportado. ZIP completo baixado no navegador. Unity 6000.3.0f1 real validou Built-in e URP 17.3.0, múltiplos assets, textura, prefab, normais, UVs, orientação Y-up e altura em metros.
4. UI/API: FastAPI, SQLite, React/TS/Vite/Tailwind/R3F/Drei, upload/preview/settings, viewport, inspector, biblioteca e downloads. Rodando em 127.0.0.1:8000.
5. Ferramentas: oito operações reais. Decimation corrigida: 20.432 → 4.086 tris e 2.043 vértices Blender, UV/textura preservados, FBX/Unity aprovados. Outras sete operações no robô; altura final 1.5 m. Original preservado.
6. Entrega/QA: iniciador e setup completo executados; pesos reutilizados. 12 testes passaram, TypeScript/Vite passou. Playwright desktop 1600x1000, nativo do conceito 1586x992 e mobile 390x844, sem overflow/erros de aplicação; dez trocas de assets e rotação real. Detalhes em QA.md.

## Confiabilidade
Worker serial, lock único da API, claim e cancelamento atômicos/terminais, upload publicado após gravação, recuperação de todos os jobs, independentemente dos 200 registros recentes. Original resolvido pela API e mantido selecionado fora da janela recente. Avisos de decimation persistem em versões derivadas. Viewer descarta geometrias, materiais, mapas ocultos e ImageBitmaps.

## Modelo prioritário
SF3D retornou HTTP 401 nos pesos; nenhum aceite/login foi realizado pelo usuário. TripoSR foi a alternativa autorizada. SPAR3D/Hunyuan foram comparados, não instalados. Fontes em MODELS.md.

## Arquivos e continuidade
- Abrir C:\Projetos\forge3d-ai\Start-Forge3D.bat. Início normal não baixa ou reinstala nada.
- Modelos: data\assets\<id>; SQLite: data\forge3d.sqlite3. Pesos: models\triposr, models\dino, models\rembg.
- Prova do fluxo: data\flow_verification.json, data\verified-Unity.zip. Logs de instalação, IA, API, build e Unity em logs.
- Projetos de QA: data\UnityValidation e data\UnityValidationURP; relatórios de importação dentro de Assets.
- scripts/sync-source.ps1 copia a fonte do workspace da conversa ao destino, preservando data, modelos, ambientes e .agents. Reiniciar API após mudanças backend. Blender/IA são processos novos por job.
- Não executar pip simultaneamente no mesmo venv: isso causou conflito NumPy na instalação inicial e foi corrigido com reinstalação sequencial.

## Limitações
Qualidade artística varia e lados invisíveis são estimados. Albedo de cores neurais, sem mapas PBR separados. Sem rig/retopologia de animação. Decimation pode afetar detalhes/UVs. OOM/timeout tratados, mas OOM não foi provocado deliberadamente. UI mostra 200 registros recentes; banco e arquivos preservam histórico. Unity foi testado em batchmode/nographics, sem gameplay/render final de uma cena. Exemplos oficiais foram usados para QA. Consultar QA.md antes de assumir testes adicionais.

## Fidelidade v3 — 2026-10-10

Preferência recebida: forma e proporções. Entregues Quality TripoSG512³ validado, limpeza conservadora e refinamento frontal limitado a 3% da altura, sempre em novas versões. Sem pesos novos, textura SG, rig ou suposto treinamento. Encoder448 testado sem benefício claro; padrão224 mantido.

Benchmark real: personagem do usuário/bule/cadeira, nove variantes e quatro vistas neutras/FBX; contorno Quality limpo→refinado: 87,60→93,33%, 91,43→96,23% e 68,26→75,35% respectivamente. Valores representam sobreposição2D, não notas de fidelidade3D. Referências e versões anteriores preservadas.

51 testes, build, UI desktop/mobile e UnityURP real passaram. Fluxo pelo botão Quality471.304→limpeza470.284→silhueta470.284→LowPoly94.054→altura1,5m→ZIP/FBX/URP/prefab. RAW e pais conferidos por hash; medição de contorno removida nas versões posteriores que alteram a malha. Provas em data/quality-upgrade/fidelity-v3 e data/UnityFidelityV3Validation. Relatório e limites em FIDELITY_V3_VALIDATION.md.

## Personagens avançados — 11/10/2026

Hunyuan2mini público autorizado sob licençaTencent, isolado em.venv-hy; sem pintura neural/offload. Novo modo384³×2/seeds42,43, refinamento limitado e projeção frontal opcionais; seleção humana preserva RAWs. TripoSR extração/normais em costurasUV corrigidos sem mudar posições/UVs. Originais e modos anteriores preservados.

Hinata exato: lote UI260,60s,alocado4644,1MiB,reservado5160MiB,totalGPU7305MiB; mesmosRAWs do protótipo214,39s.50renders768/fiveviews/clay+textura e4FBXroundtrips; cinco vistas extras da versão otimizada. Candidato2→52330triângulos→altura1,5m→ZIP realmente baixado→Unity6000.3URP17.3/normais+UV+textura1024+material+prefab passaram.0degenerados/bordas/não manifold na versão reduzida; dois componentes preservados.

71testes/1depreciaçãoAnyIO; build6,32s/warningViewer932KB. QA Playwright desktop1600×1000/mobile390×844 sem overflow, wireframe/neutro/textura e cinco vistas×dois materiais carregadas. Revisão única: Original/linhagem e publicação atômica/cancelamento corrigidos RED→GREEN; testeBlender real de UVs/normais também. Sem alegar anatomia exata, costas observadas, rig ou gameplay.

Provas em data/character-advanced-20261011/validation-evidence,ui-flow-verification.json,release-verification.json; Unity isolado em data/UnityCharacterAdvancedValidation. Detalhes/limites/decisões em CHARACTER_ADVANCED_VALIDATION.md. App ativo no workspace desta conversa; instalação antiga C:/Projetos preservada.
