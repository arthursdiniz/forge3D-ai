# Forge3D — qualidade e Character Intelligence, 12/10/2026

Implementação local com preservação dos modos e dos originais. A RTX 4060 foi confirmada: 8.188 MiB, driver595.97; i5-12400F,31,82GiB de RAM, Windows11/Python3.12.10. Os runtimes neurais usam Torch2.5.1+cu124. Nenhum serviço pago, peso gated, novo driver ou toolkit CUDA foi instalado.

## Resultado demonstrado e limite

O novo Quality Mode oferece1/3/5 candidatos por seeds reais em TripoSG/Hunyuan, com carga compartilhada e execução sequencial. O Avançado antigo continua com2. TripoSR continua determinístico/1. Candidatos preservam RAW, latentes, malha, UVs, vistas e relatórios. A escolha é humana; não existe nota automática de anatomia.

Hunyuan3D2mv passou com2/3/4 imagens realmente distintas e nomeadas, em256³/50passos/FP16, sem offload. No caso próprio multiview, o IoU lateral estimado passou de0,648(single-image) para0,867(native4views), enquanto o frontal passou de0,921 para0,900. É uma melhora lateral com uma perda frontal mensurável; não prova fidelidade anatômica universal. Nenhuma colagem foi usada como condicionamento.

O Hinata agora pode ser analisado, revisado, comparado em três alternativas e convertido para20mil triângulos com bake real de normal. Ainda existem diferenças de proporção: na seed44, landmarks2D indicam quadril~19,8% mais estreito e canelas~9,8–13,7% mais curtas em relação ao torso. A câmera e o detector afetam esses valores. O rosto, dedos, cabelo e verso de uma única imagem continuam estimados. **Não foi demonstrada paridade Meshy, anatomia perfeita ou prontidão para rig.** Para melhorar substancialmente a identidade/verso, a alternativa prática é fornecer frente, lados e costas do mesmo personagem na mesma pose, usar o multiview validado e fazer acabamento/retopologia manual no Blender.

## Uso

1. Envie a referência, selecione o motor e, para personagens, ative Character Intelligence.
2. Selecione categoria/pose/vista. Analise em CPU, confira/arraste/adicone/remova os pontos e marque cabelo/roupas/acessórios que precisam de proteção. Salve a interpretação. A geração verifica o vínculo pelos pixels da imagem; interpretação de outra imagem é rejeitada.
3. Ative Quality Mode e escolha1/3/5. Comece por Balanced256 para o orçamento de3–5min. Quality512 do SG/384 do mini é mais lento e não garante anatomia superior. Compare clay/frente/lados/costas e selecione um candidato.
4. Opcionalmente aplique simetria/regiões ou refinamento micro. Simetria começa Off; exige pose frontal neutra/A-pose/T-pose e confirmação. Pose dinâmica é recusada. Não há fechamento automático de buracos ou remesh global.
5. Projete textura só depois de escolher a forma. Alpha e visibilidade são necessários; áreas não observadas ficam neutras.1K/2K/4K são atlas/baking reais, sem alegar criação de detalhe ausente. Normal maps existentes são preservados na projeção.
6. Crie Game Ready com5k/10k/20k/40k/custom. O high poly permanece na origem. Decimation não equivale a retopologia para animação. Baking CPU transfere cor e normal tangente high→low; roughness.65 e metallic0 são constantes declaradas.
7. Exporte o pacote Unity/FBX/GLB/OBJ. O importador configura UVs, normais, escala, URP/Standard, normal map e prefab. A validação Unity é de importação, não de gameplay/rig.

O corpo assistido é uma estratégia experimental opcional e explicitamente **não neural**: template procedural próprio CC0, com volume extraído de primitivas e proporções de landmarks revisados. Exige head_top/chin e articulações confiáveis. Não contém identidade facial, cabelo, roupas, dedos detalhados ou rig e não substitui silenciosamente um candidato de IA. Categorias não humanas exigem outro template.

## Medições reais

| Caso | Tempo | Pico PyTorch MiB | Escopo |
|---|---:|---:|---|
| Hinata3, navegador→API→GPU→Blender→diagnósticos |159,406s|4182,2|Pico total NVIDIA amostrado5665MiB;67amostras aproximadamente2s|
| TripoSG5, referência própria anime |273,92s|4225,0|Lote real de seeds42–46, carga compartilhada|
| HunyuanMV2 |128,08s|5432,9|Inferência/preparo/carga; Blender à parte|
| HunyuanMV3 |157,18s|5558,2|Adaptador oficial reproduziu144728triângulos|
| HunyuanMV4 |178,00s|5686,7|Inferência real, sem offload|
| Hinata115506→20000, cor+normal4K |39,16s|CPU|Fluxo final API, bake, renders e diagnóstico; bake/decimation24,25s|
| Corpo assistido próprio |2,80s|0|CPU,14932triângulos, volume fechado|

Reservas PyTorch e uso total da GPU são métricas distintas; tempos de inferência não incluem necessariamente rendering/exportação. Os arquivos JSON contêm os parâmetros, amostras e escopos. O preflight usa estimativas com margem e mantém erro CUDA OOM explícito; não troca modelo ou perfil silenciosamente. Um processo pesado por vez e lock global; offload não foi necessário e permanece desativado nos motores validados.

## Evidências

- `data/major-quality-20261012/actual-api-quality-flow.json`: lote gerado pela UI e monitor NVIDIA;root2cfcab0c06da451e893218e326260e7b;seed44=4d0fd422ce9445aa804ebbc222425d10.
- `data/major-quality-20261012/hinata-quality-three-preserved`: três RAWs/latentes e cinco vistas de cada candidato. O primeiro processamento encontrou uma cópia do modelo sobre ele mesmo no Windows; os RAWs foram preservados, a causa ganhou teste e o processamento retomou em uma cópia.151,39s nesse ensaio mede inferência ativa+processamento, excluindo a interrupção; o fluxo posterior pela UI mediu159,406s contínuos.
- `data/major-quality-20261012/sg-quality-five-anime-fixture`: cinco gerações TripoSG verdadeiras.
- `data/major-quality-20261012/mv-adapter-2-views`, `mv-adapter-three-views`, `mv-adapter-4-views`: inferência, parâmetros, referências, máscaras, latentes, clay e FBX reimportado. Os GTs próprios nunca foram usados como malhas de saída da IA.
- `data/major-quality-20261012/owned-character-fixtures`: sete referências/GTs procedurais CC0: A-pose, anime/hair, roupas volumosas, simétrico, acessório assimétrico, dinâmica e multiview. Estes arquivos são fixtures de teste, não modelos gerados por IA.
- `data/major-quality-20261012/seven-case-neural-benchmark`: sete reconstruções neurais reais, cinco vistas, máscaras e diagnóstico; todas tiveram1componente,0duplicatas,0arestas com winding inconsistente e0faces selecionadas por auto-interseção MeshLab. Isso não prova anatomia correta. IoUs frontais0,872–0,921 e laterais0,620–0,771 mostram a incerteza da vista única.
- `refinement-measured-results.json`: correções seletivas com métricas antes/depois,13operações aceitas, simetria dinâmica recusada. Micro mede irregularidade local; simetria mede distância de pares. Não alegam reconstrução anatômica aprendida.
- `data/major-quality-20261012/final-safe-game-ready.json`: versão final d50d2f098559482ca796bb59672b7289 e export5756523892ef4bbc88bdf8ec1157e135;20mil triângulos, cor/normal4K,14componentes preservados,0bordas abertas,0não manifold e0faces selecionadas por auto-interseção. Variação de volume0,1002%. Cinco vistas clay/textured em `final-game-ready-views/`. Os testes iniciais2K/4K anteriores à correção de costuras preservam evidência histórica, mas foram superados por esta versão.
- `data/UnityFinalSafe4KValidation`: Unity6000.3.0f1, URP17.3/Standard,20mil triângulos, cor e normal carregadas em4096×4096, normal map/keyword/prefab/UVs/normais/vértices finitos. O teste anterior reproduziu a redução silenciosa para2048; o importador corrigido preserva os tamanhos dos arquivos. O projeto `UnityMajorQualityValidation` também demonstrou geometry-only com0texturas. Licença Unity exigiu execução fora do sandbox; nenhum software de sistema foi reinstalado.
- Capturas `ui-mobile-character.png`(390×844,sem overflow) e `ui-hinata-three-candidates-desktop.png`(1600×1000).

## Integridade e preservação

GeometryIntegrity mede topologia temporariamente soldada somente para inspeção: shells, faces duplicadas, winding, volume por shell, normais/UVs e, quando solicitados, auto-interseções MeshLab e64raios interiores. Raios não são medição exaustiva da espessura. Partes abertas/interseções podem ser intencionais; relatórios não fecham/fundem automaticamente.

Correções preservam índices/cantos UV e materiais, protegem bordas/detalhes e limitam deslocamento. Rejeitam piora de duplicatas, winding, bordas não manifold, degenerações, volume>1% global/por shell, interseções novas e contorno frontal estimado além da tolerância. Relatório informa testes indisponíveis, em vez de declará-los aprovados.

Baseline em `source-baseline/`, `baseline-hashes.json` e backup SQLite foram salvos antes das mudanças. Modos existentes e arquivos originais permanecem. UV/materials do Blender são pós-processamento nos motores sem UV/textura nativa. Os GLBs exportados são Y-up; stats do Blender são Z-up em memória. Essa distinção foi medida e respeitada nos diagnósticos.

## Setup, licenças e pendências

`scripts/setup-major-quality.ps1` cria ambientes CPU isolados quando ausentes, reconcilia os locks em todas as execuções e valida versões/imports reais. Um python.exe parcial não torna o recurso disponível. A repetição corrigiu dependências faltantes nos ambientes isolados e passou pipcheck/imports; não alterou runtimes neurais anteriores. `-DownloadMultiview` baixa pesos públicos; ativação ainda exige prova local de inferência/render/exportação. Reutiliza o runtime Hunyuan FP16 já validado. Detector Google6MB e MV4,93GB tiveram bytes/SHA verificados. A licença do código MediaPipe é Apache2; o model card/pesos são documentados separadamente no manifest. Hunyuan usa Tencent Community, já aceita para teste pessoal local. [Hunyuan oficial](https://github.com/Tencent-Hunyuan/Hunyuan3D-2), [Pose Landmarker](https://ai.google.dev/edge/mediapipe/solutions/vision/pose_landmarker).

SPAR3D possui adaptador e gates, mas permanece indisponível: pesos gated sem acesso autorizado, runtime CUDA texture-baker/Windows e inferência local não validados. O modo low-VRAM oficial é~7GB, não uma medição nesta4060. Não foram usados tokens, contornado acesso nem instalado toolkit/VS automaticamente. [API e requisitos oficiais SPAR3D](https://github.com/Stability-AI/stable-point-aware-3d).

TRELLIS.2 permanece descritor futuro, fora do perfil Windows/8GB; não foi instalado. [Upstream](https://github.com/microsoft/TRELLIS.2).

Face/fingers learned refinement, semantic segmentation of hair/clothes, learned anatomical constraints, animation-ready quad retopology, rigging and full neural texture/PBR generation are **not implemented**. Some requested meso/macro intelligence remains bounded by single-view reconstruction; the available controls are diagnostics, reviewed template fitting, existing frontal contour refinement, selective symmetry and micro surface editing. Hidden anatomy cannot be verified from one reference. These limits are explicit in the UI and reports.

## Matriz de aceitação

| Requisito | Estado | Limite verificável |
|---|---|---|
| Execução local/gratuita, preservação, hardware confirmado |Implementado/testado|Motores licenciados conforme manifests; nenhum serviço externo na inferência|
| TripoSR/SG/mini e multiview nativo |Implementado/testado|MVBalanced256/50steps;2/3/4vistas. SPARgated permanece bloqueado|
| Preparo/alpha/ocupação/crop e vínculo da referência |Implementado/testado|Máscaras podem cortar detalhes; UI permite conferir. Vistas opacas não são chamadas de silhuetas medidas|
| QualityMode1/3/5/legacy2, seeds, preservação e escolha |Implementado/testado|Provas reais Hinata3/SG5; TripoSR1 determinístico|
| CharacterUnderstanding editável |Implementado/testado|Pose/landmarks e medidas2D; estilo/categorias manuais; sem segmentação semântica aprendida|
| Anatomia/rosto/dedos e proporções3D corretas |Parcial/limite do modelo|Medições e scaffolding disponíveis; não há correção anatômica neural, nem prova das partes ocultas|
| CharacterBaseMesh |Implementado experimental|Template próprio humanoide; body-only, profundidade assumida, sem identidade/rig|
| GeometryIntegrity |Implementado/testado|Probes geométricos e64raios amostrados; não são prova exaustiva de espessura|
| SymmetryCorrection / refinamento |Implementado/testado com limites|Off/Soft/Strong/Custom, plano manual e regiões/proteções; estimador de plano no módulo. Sem correção aprendida meso/face|
| Macro/meso/micro |Parcial|Macro por template/contorno frontal existente; micro seletivo e simetria; meso neural não disponível|
| Texturas1K/2K/4K, normal high→low |Implementado/testado|Baking/projeção reais; verso não visto neutro; roughness/metallic constantes, não mapas aprendidos|
| GameReady5k/10k/20k/40k/custom |Implementado/testado|Orçamento aproximado de decimation; prova real20k. Sem quad retopology para rig|
| FBX/GLB/OBJ/Unity |Implementado/testado|FBX/UV/escala e GLB/OBJ reimportados; URP/Standard/normal/prefab testados. Sem teste de gameplay/rig|
| GPU/preflight/timing/cancel/config |Implementado/testado|Estimativa antes da alocação; OOM real ainda pode ocorrer; offload não necessário/ativado|
| Interface desktop/mobile |Implementado/testado|Fluxo real imagem→revisão→3candidatos→seleção→GameReady→export; cancelamento real;390×844sem overflow|
| SPAR3D e modelos futuros |Bloqueado/opcional|Acesso/licença gated e runtime Windows precisam de autorização/validação; TRELLIS.2 fora do perfil atual|

Validação final: **136testes passaram em12,87s**; build TypeScript/Vite passou. Há um aviso de depreciação do Starlette/AnyIO e aviso de tamanho do bundleThree.js, sem falha de teste/build. Logs: `logs/major-delivery-tests.log` e `logs/major-delivery-build.log`. A tentativa de usar o ambiente CPU para toda a suíte foi recusada por falta deTorch; a suíte completa passou no runtime de testes apropriado. Não se instalaram dependências CUDA no ambienteCPU para contornar isso.

## Revisão final e correções verificadas

A revisão independente identificou8problemas importantes, nenhum crítico. Todos foram corrigidos e verificados em uma passagem final:

- Upload com crop sobrescrevia os parâmetrosleft/right; testes RED→GREEN cobrem crop com/sem vista adicional.
- Quatro operações seletivas não publicavammesh_report. Os testes agora passam porWorker.process_job; a prova real `final-api-operations.json` executou análise, simetriaSoft, micro e projeção, criando versões e relatórios atuais.
- Landmarks/regiões da imagem original não acompanhavam crop. A transformação usa os limites arredondados em pixels; recorta/clippa regiões, exclui pontos fora da imagem e guarda interpretação original separada. A máscara efetiva é oferecida para marcar operações locais, antes do enquadramento do encoder.
- A máscara disponível era vinculada apenas durante diagnóstico. Ela agora é registrada em toda geração; TripoSR também a salva. `ordinary-cropped-object-regression.json` demonstra imagemRGBopaca→crop→u2netp→TripoSRFast→projeção posterior semQuality/CharacterMode.
- ToggleCharacterMode/base_mesh/generative criava estratégia/seed contraditórias. O navegador confirmou revisão preservada, estratégia normalizada e seednull paraTripoSR.
- RespostaPUTatrasada podia perder edições. Campos são bloqueados duranteSave e respostas com revisão obsoleta são ignoradas. Foi testada resposta atrasada com tentativa de editar;33pontos permaneceram. Inputs numéricosX/Y oferecem edição por teclado.
- Unity importava4Kcomo2K. A reproduçãoRED carregou ambas em2048; a validaçãoGREEN e o pacote final seguro carregaram ambas em4096 emURP/Standard.
- Setup parcial era tratado como completo. Reinstalação reconcilia locks, fazpipcheck/imports e grava prova; availability exige essa prova, não apenas python.exe.

A QA final encontrou adicionalmente um problema de redução nas costuras: decimar diretamente vértices duplicados porUV produzia75componentes,13334bordas abertas e2009faces selecionadas por auto-interseção no20k. A correção reconecta somente pares de bordas opostas únicos, em posições exatamente iguais, com normais importadas e material compatíveis, na cópiaLOW. Não solda por proximidade, não move a superfície nem altera oHIGH. Componentes≤100faces permanecem exatos;104faces pequenas foram preservadas noHinata. A versão final voltou a14componentes,0bordas abertas,0interseções detectadas e20miltriângulos. A publicaçãoGameReady exige comparação real da origem/LOW e recusa regressões estruturais/volume/contorno. A fonte e as saídas de uma operação recusada ficam preservadas; não se preenchem buracos.

O tempo das operações também passou a incluir oBlender desde o início. TesteRED→GREEN reproduziu0s incorretos para32s simulados de trabalho; a prova real `final-transform-timing.json` mediu8,797s de execução e10,058s até o polling confirmar. A medição histórica39,16s doGameReady final vem do relógio externo do ensaio, incluindo bake/render/diagnóstico; a correção de timing afeta novos trabalhos.

Preservação final: `preservation-final.json` confirmou **205arquivos em19assets sem alteração**, além doSHAoriginal doHinata. Cancelamento real2dfb995277fb461c8b5dd436c5bb8836 ficoucancelled, sem candidatos publicados. Backend atualizado ativo no workspace e runtime.json correto; não há trabalho pendente.

## Comparações visuais

[Hinata sem textura em cinco vistas](../data/major-quality-20261012/hinata-geometry-comparison.png) compara TripoSR/TripoSG anteriores e miniBalancedseed44. O mini melhora alguns volumes/apresentação, mas não supera todas as partes doSG e ainda erra relações do corpo. Não há comprovação de ganho universal da escolha de seed ou da densidade. [Imagem única × multiview verdadeiro](../data/major-quality-20261012/native-multiview-comparison.png) demonstra o ganho lateral mensurado no caso próprio. Ambas são figuras com renders reais, sem retoque generativo.

A projeção2KdoHinata deixou23,96%dos texels visíveis cobertos pela frente. Cores detalhadas aparecem apenas nas áreas observadas; cinza nas laterais/costas é incerteza explícita. OGameReady final disponível é neutro com bake4Kde superfície; não se deve confundir maior resolução com pintura neural completa.

## Arquivos, instalação e execução

O inventário completo está em `data/major-quality-20261012/source-changes.json`; os arquivos de fonte originais copiados e os hashes estão emsource-baseline/baseline-hashes.json. Alterações principais:

| Área | Arquivos principais |
|---|---|
| Contratos/API/executor |backend/app.py, schemas.py, storage.py, worker.py, quality_settings.py, progress.py, gpu_manager.py, config.py|
| Interpretação e coordenadas |backend/character_understanding.py, character_routes.py, character_analysis_runtime.py, reference_coordinates.py, cpu_environment.py|
| Geometria |backend/geometry_integrity.py, character_quality.py, geometry_operations.py, symmetry_correction.py, sculpt_refinement.py, topology_seams.py, game_ready_integrity.py|
| Template |backend/character_base_mesh.py, character_base_provider.py; blender/create_character_fixtures.py|
| Motores/candidatos |backend/character_advanced.py, inference_sg.py, inference_hy.py, inference_v2.py, hunyuan_mv_provider.py, inference_mv.py, spar3d_provider.py, inference_spar3d.py|
| Texturas/export |backend/reference_atlas.py, reference_texture_cli.py, materials.py; blender/game_ready.py, pipeline.py; unity/Forge3DImporter.cs|
| Interface |frontend/src/CharacterPanel.tsx, CharacterTools.tsx, QualityPanel.tsx, ModelSetupPanel.tsx, App.tsx, api.ts, generationOptions.ts, styles.css|
| Setup/QA |scripts/setup-major-quality.ps1, validate-cpu-environment.py, download-major-resources.py, benchmark-character-cases.py, validate-final-api.py, start.ps1; testsPython/Unity e locksCPU|

Neste computador os pesos/envs já estão instalados. ExecuteStart-Forge3D.bat; endereçohttp://127.0.0.1:8000. Stop-Forge3D.bat encerra o processo registrado. A configuraçãoBlender aceita executável absoluto e olauncher respeita esse caminho.

Para repetir somente o setupCPU: `powershell -ExecutionPolicy Bypass -File scripts/setup-major-quality.ps1`. Para baixar/verificar novamenteMVpúblico: o mesmo comando com `-DownloadMultiview`; requer o runtimeHunyuan-mini já validado. Pesos mini ficam emmodels/hunyuan-mini;MVemmodels/hunyuan-mv/hunyuan3d-dit-v2-mv;poseemmodels/character. Os downloads oficiais têm manifests/pins/SHA; nenhum peso é baixado na inferência. Os scriptsdownload-triposg.py e download-hunyuan-mini.py só baixam recursos oficiais; sozinhos não equivalem a instalar/validar todo o provedor numa máquina nova. Não inventevalidation.json para ativar um motor.

Testes neste workspace: no runtime de testes comTorch/Trimesh/FastAPI, execute `python -m pytest tests -q --basetemp .test-tmp/novo-ensaio`. Frontend: `cd frontend` e `npm run build`. Os JSONs/logs registram o caminho e runtime efetivamente usados nesta validação.

## Próximas melhorias práticas

1. Preparar frente/lado/costas reais doHinata na mesma pose e comparar oMVcom a mesma referência; este ensaio só pôde provarMVemfixturespróprias.
2. Escolher/clay-revisar a forma antes da cor, marcar assimetrias intencionais e usar refinamentos locais de baixa intensidade. As relações2D indicam problemas, mas não são condicionamento anatômico da rede.
3. Fazer retopologia e correção de rosto/mãos/roupas noBlender para animação; otemplate pode servir de base editável, não traz rig/skinning.
4. AvaliarSPAR3D somente após acesso pessoal/licença e validação do runtimeWindows. A instalação permanece bloqueada/opcional. Hunyuan2.1 não foi ativado; não se alegou compatibilidade sem prova.

A entrega funcional disponível foi concluída dentro desses limites. O objetivo artístico de personagens fiéis em todas as vistas, com anatomia/identidade/rig corretos a partir de uma única imagem, permanece **parcial**; não é demonstrável com os motores e dados deste teste.
