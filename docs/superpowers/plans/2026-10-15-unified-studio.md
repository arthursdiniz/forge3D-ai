# Forge3D Studio Implementation Plan

> REQUIRED SUB-SKILL: superpowers:executing-plans. Execução inline contínua, sem agentes implementadores; um reviewer final novo no modelo mais capaz. Preservar checkout/snapshots, sem commits/reset/limpeza.

Goal: modelar e texturizar com uma ação por domínio, interface simples e ferramentas avançadas preservadas.
Architecture: contratos/planner/router/workers de workflows sobre CLIs existentes; app-shell e superfícies Modelar/Texturizar/Biblioteca com componentes comuns e viewer compacto; legado opcional.
Tech: Python/FastAPI/Pydantic/SQLite/ambientes AI existentes, React19/TypeScript/Vite/Three/lucide, Blender/Unity já instalados.
Spec: ../specs/2026-10-15-unified-studio-design.md

Global constraints: Windows local RTX4060 8188MiB (reconfirmar); GPU pesada serial; sem novos modelos/serviços; modelagem geometry_only, textura sem alterar geometria; originais/versões/instalações preservados; PT-BR; presets com efeito real e prova; não declarar inferência a partir de fixture; nenhuma porcentagem simulada.

Review Focus:
- Troca de fonte/aba/referência durante job não publica resultado ou máscaras sobre outro modelo; orientação acompanha fonte.
- Clique duplo, cancelar, reiniciar servidor e retry não duplicam inferência nem publicam etapa parcial/cancelada.
- Recursos opcionais ausentes, perfil não validado, imagem opaca e referência adicional incompatível produzem ação/aviso honesto, sem sucesso falso.
- Cache de etapa deve invalidar em fonte/ref/opções/recurso/código alterados; saídas intactas e originais preservados.
- Biblioteca antiga com pais fora da página, candidatos/versões/export e transformação não perde linhagem/canais/licenças.

## Task1 Auditoria/design/base (implementado e verificado)
- [x] Ler requisitos, auditar entrypoints/rotas, registrar baseline216fontes/124assets/3424arquivos e screenshots.
- [x] Consultar NN/G/W3C e gerar conceitos completos3áreas; definir contrato/design system e interfaces.
- [x] Terminar auditoria de12componentes e helpers backend; registrar matriz legado→novo/local de cada função. Rodar baseline267tests/TypeScript.

## Task2 Workflows e filas
- [x] RED tests/test_workflow_routes.py: modelagem geometry_only, providers/presets reais, imagem inválida, dedupe/retry, textura fonte válida, upload4vistas, sem recursos e cancel.
- [x] Implement backend/workflows/{contracts,planner,routes,jobs,catalog}.py; extrair enqueue_generation de app sem alterar APIantiga; Worker dispatch kinds novos. Publicação de etapas/tempos/avisos/falha e cache vinculado a conteúdo. GPU serial existente.
- [x] GREEN testes e requests reais. Bibliotecacatalog filtra técnico e mantém ancestrais/versões fora do limite da listagem.

## Task3 Texturização automática
- [x] RED tests/test_texture_workflow.py: sequência real de stages, fallback qualificado, nenhuma revisão humana simulada, classes desconhecidas, pose ambígua, material/UV/dados/geom imutáveis, preview/falha/cancel/cache.
- [x] Implement workflows/texture_cli.py e helpers isolados, reusando neural/core/semantic/region e publicação existente extraída quando necessário. Base→análise/registro confiável→composição conservadora→validação dentro de um job. Recursos ausentes não executam stages fictícios.
- [x] GREEN testes e caso real imagem→textura; medir GPU/tempo, verificar geometria/export/canais/proveniência/licenças.

## Task4 App e superfícies
- [x] TDD adequado para comportamento; código visual reversível verificado no navegador, sem testes que espelham CSS.
- [x] Create frontend/src/studio/{StudioApp,ModelWorkspace,TextureStudio,AssetLibrary,AdvancedTools,StudioViewer,ui,useStudio,workflowOptions}.tsx/ts e studio.css conforme fronteiras reais. App vira composição. Manter legado através de módulos avançados; arquivos anteriores não removidos.
- [x] Navegação3áreas/aliases, primários únicos, placeholders honestos, upload/preview/tipo/qualidade/objetivo com efeitos reais, helps/errors/timers/cancel. Sem gráficos/controles inertes.
- [x] Build + browser desktop/mobile; comparar conceitos e screenshots via view_image, ajustar cópia/tipografia/layout/ícones/estados, registrar5pontos/copydiff.

## Task5 Biblioteca/viewer/import/export
- [x] RED contracts catálogo/linhagem, selecionar modelo antigo, novas versões, resultados obsoletos, import/sidecars e seleção de export.
- [x] Integrar listas/filtros/thumbs reais/versões/antesdepois, viewer menus e foco, export/contexto avançado/hair/semantic/regional/geometry. Nenhum algoritmo antigo eliminado.
- [x] GREEN e browser reais: library→texture, import→texture, original→versão→retorno, exportUnity.

## Task6 Entrega comprovada
- [x] Testes267+novos, build/TypeScript, fluxo usabilidade real de modelagem sem textura→texturização1ação→export/Unity, cancel/retry/indisponíveis; tempo/VRAM, preservar3424originais; source-bound proofs atualizadas só após regressão pertinente.
- [x] Docs UI-DESIGN/README/guia/auditoria/capturas/evidência/fidelidade/copydiff/inventário/limites.
- [x] Reviewer final único read-only fresh gpt-6-astra conforme skill; regrade e UM passe Important/Critical RED→GREEN+suíte; menores/rulings completos; sem re-review. Final nos10itens do usuário.

Ledger:
Preflight: geração/upload/API/worker→workflow; renderer/semantic/regional→texturejob; catálogo/jobDTO→UI/versões; reports→export; preservar coerência de eixo/proveniência em todas as fronteiras.
Ruling: especificação detalhada e fase19 autorizam implementação contínua sem aprovações intermediárias da skill — nenhum requisito de negócio em aberto impede arquitetura — custo: usuário avalia direção visual pelo resultado e capturas.
Ruling: preservar checkout existente e todos os snapshots, inclusive QA, em vez de criar/limpar worktree ou commitar — usuário exige dados/funcionalidades anteriores — custo: alterações locais sem commit e maior uso de disco.
Ruling: conceitos são referência de UI, nunca assets/saídas3D — modelos e thumbs em produção são reais, incluindo seus defeitos — custo: qualidade da malha real pode divergir do desenho conceitual.


2026-10-15 execution checkpoint:
- Baseline267passed50.34s; new5route tests RED missingmodule -> GREEN2.53s; cache/alignment RED -> GREEN; full274passed40.86s.
- T2 routes/planner/catalog/modeldispatch/texturedispatch implemented. T3 base+automatic portrait gate+protected semantic composition+metric rejection+final publish in one job; validated-stage retry cache hashes source/references/options/code/resource manifests and output files. Pending additional sequence/cancel/cache regressions and real inference.
- T4 new3areas compiled TypeScript/Vite; advanced modules preserved in optional dialog. First actual screenshot after-model-first.png reviewed against concept. Pending consistent secondary screens/mobile/actions/stale results and copy/fidelity review.
- GPU currently RTX4060 8188MiB driver610.88; initial1051MiB in use. Live Hinata modeling from actual UI job57a3da2b44d640b8b54c083e64a5ca6b, geometry_only Hunyuanmini balanced42, running.
- Core/new helpers corrected actual pose runtime path: backend/character_analysis_runtime.py (not backend/character/cli.py). Automatic body analysis remains optional advanced; no fake reviewed interpretation.
- First default-sandbox TestClient hung due blocked loopback; exact own test processes27060/8948 terminated. Tests rerun elevated successful. Idle own uvicorn252/7020 restarted, new parent25284/child31288. No originals removed.
- Existing local proof invalidation audited proofs-changed.json. Need actual neural/regional regression before refreshing hashes; no bypass of runtime health checks.


2026-10-15 acceptance checkpoint:
- T1 audit complete, matrix docs/UX_WORKFLOW_AUDIT.md.267baseline,282candidate tests passed39.56s. Frontend behavior guard3 Node tests RED missingmodule->GREEN; concurrency route and per-view/cache-integrity negatives RED->GREEN.
- T2/T3 contracts and serial orchestration accepted: actualUI Hinata model57a3da2b44d640b8b54c083e64a5ca6b; texture6097d733eadb408380c086595f45cf0f; exportc14734e691984794825f2861cb0a338b; newupload, reloadselection, switchsource and cancelled5c0eb6b1c74347c78068ade50318427e exercised.
- Texture141.594s full,67.21s inference,3866.8MiB allocated/5352MiB reserved; actual6jointviews offline. Real portrait parsing source+target executed. Automatic gate rejected maxresidual.184/RMSE.0675; keptbase and qualified warning. No false human review/no wholebody parsing. GPUtotal sampling in base/gpu_monitor.json.
- T5 realexport GLB/FBX/OBJ worldtriangles114932 exactly preserved. Unity6000.3 real URP/Built-in pass in QA/unity-validation.json. ActualGLBimport84f8fd74f23c40619ea0e985725e01b3 completed after browserRED empty optional sidecar→frontendfilterfixGREEN201/model_loaded. e2e-import-id.txt corrected from stale older failedimport to thisactualnewjob.
- Real retry in isolatedstore: deliberate postbase inspectionfault, validbasecache reused, original/failedattempt retained; retry-validation.json. Cache further strengthened with geometryreporttrue and nestedresourceidentity; unitnegatives passed.
- T4/T5 browser: original↔texture, export recovery,4automaticmaskimages loaded, legacytexture source6097, hair reconstruction and comparison/settings surfaces, nativeEscape/focus trap/return, skiplink preservesarea, importedmodelwithoutrefbuttondisabled. UIQA first Hairvisiblefalse was wrong selector/earlyquery; correct heading Reconstrução de cabelo provedtrue. No console errors in candidate pass; normal contextlost events only.
- Preservation:3424originalfiles/124assets SHAunchanged, actualimport/exportlicensesverified, preservation-validation.json. Existingsemantic/regional CLIs rerun in newQA folders; protectedUV/normals/maps/geometry unchanged. Legacy sourceproofs renewed only afterthese real runs+suite; no new models/downloads/drivers/API.
- T4 remaining final responsive screenshots/fidelity/copydiff; T6 pending finaldocs, fresh reviewer and one permitted fixpass. All backend/GLB/Unity checks above are actual; orchestration fixtures explicitly separated.
- Task4: Ruling: preserve technical legacy generation including its explicit native appearance choices in advanced, while basicModelar alwaysgeometryonly — honors preserveexistingmodes + separatemainflows — cost: advancedsurface retains older technical labels.
- Task6: Ruling: no git/task-done helper that requires commit range or deletes workspace; reviewuses sourcebaseline snapshot and tracked patch because user asks preservecurrentdirtywork and QA — cost: artifactbased review rather than cleanbranch history.

2026-10-15 final review dispatch:
- Product frozen after actual camera RED→GREEN. InitialBounds.fit overwrotefront in nextframe even maxDuration0; removedonlyinitialfit, keptclip/manualviewposition andexplicitEnquadrar. BrowsercapturedexactnegativeZ front,positiveZ back,negativeX left,positiveX right. Inspector/usercontrols preserved.
- Finaldesktop3areas andmobile390 screenshots saved/reviewed directlyagainst3ImageGenconcepts;5pointfidelity+copydiff in docs/UX_STUDIO_VALIDATION.md. ModelSVGoriginal/nativeGLBdetails remainreal. Mobileheader110px controlsfit; closed-menu descendantDOMrects wereexcludedfromvisiblecontrolaudit.
- Fresh sole reviewer /root/ux_final_review gpt-6-astra xhigh dispatched read-only, fork none,39files baselinepatch. No implementer agents. Waiting verdict; one Important/Critical fixpass only. Evidence/UI docs may be completed while product stays frozen.
- Main tasks1–5 completion: full282pytest passed39.56s,3frontendNode tests passed, TypeScript/Vite build passed; actualworkflow/import/export/Unity/sourcepreservation + cameraactualviewchecks accepted. No commits/worktree cleanup perpreviousruling. Task6 finalreview/closure remains.

2026-10-15 final review verdict and single fix pass:
- Sole fresh reviewer ux_final_review completed read-only: 6 Important, 1 Minor, no Critical; all39 source SHA match. Findings: assisted-body provider payload; stale async context; submit guard lost on area unmount; candidate original lineage; mixed rejected-view warning; modeling inference checkpoint. Declined to judge: none.
- Re-grade: all six Important stand. Pipeline recovery re-graded Important: changing pipeline leaves a stale package visible and disables the requested export; this is a blocked promised action, not cosmetic polish. Include pipeline/source-bound recovery and failed-export retry in the same fix. Deferred minors: none after this re-grade.
- RED confirmed: browser deliberately delayed responses reproduced stale navigation, duplicate model POST on tab return, candidate2 comparing with batch, and Built-in blocked by URP. scripts/verify-studio-review-browser.js (4/4 fail); Node assisted provider helper missing; tests/test_workflow_review.py mixed-view warning and inference retry fail (7 failures). Fixtures are orchestration regressions, not neural inference evidence.
- One fix pass begins; no second reviewer or additional review loop. Existing originals/dirty checkout/QA preservation rulings remain.

2026-10-15 closure:
- Final: fixed assisted-body effective provider — scripts/test-studio-review.cjs RED→GREEN, suite290/290; 4/4 Node tests including existing submission cases.
- Final: fixed stale shared context — delayed version navigation RED→GREEN; delayed original comparison and import additionally pass; scripts/verify-studio-review-browser.js, suite290/290.
- Final: fixed duplicate submit on area unmount — delayed model POST produced2 requests RED→GREEN one pending request; texture lock and reference draft also pass; suite290/290.
- Final: fixed candidate original — test_catalog_preserves_batch_but_resolves_each_candidates_own_original + browser second-candidate comparison RED→GREEN; actual catalog2296→b474 candidate2 verified; suite290/290.
- Final: fixed omitted rejected-view warning — test_partial_automatic_view_rejection_is_visible_even_when_refinement_succeeds RED→GREEN; suite290/290.
- Final: fixed modeling postprocessing retry — test_model_retry_reuses_only_intact_content_bound_inference six variants RED→GREEN; suite290/290. Actual Hunyuan-mini58.265s first attempt (deliberate pre-Blender failure),9.922s retry, exactly1 inference call; checkpoint and reference SHA intact; allocated4182.2MiB,totalGPUpeak5319MiB. model-checkpoint-validation.json.
- Final: fixed export pipeline/source recovery — browser Built-in blocked by URP RED→GREEN; prior failed Built-in permits preparation and wrong URP links are absent; suite290/290.
- Final verification: review-full-final.log290passed53.89s; Node4/4; browser7/7; TypeScript/Vite review-build-final.log passed;7browser regressions are isolated API fixtures, real neural/Blender/Unity evidence separate. Initial native-input draft assertion corrected to inspect retained File preview, no product edit. First final screenshot captured lazy loading; ready screenshot added after waiting, no product edit.
- Final preservation3424/3424 and real export/import check passed again. Server22464 restored hidden, healthOK/idle. Texture neural/projection/regional/semantic ready; advancedPBR unavailable honestly. Worker-bound semantic/hair proof changed only reconstruction branch (dispatch returns earlier); snapshots retained before narrowly renewing SHA after suite+actual retry. No new downloads/models/services.
- Final docs/guide/audit/screens updated and reviewed directly. Latest screenshots after-final-modelar-ready-desktop, after-final-texturizar-desktop/mobile, after-final-biblioteca-desktop. No horizontal overflow390px, no console errors in final real navigation. No Critical or remaining Important; no deferred minors after pipeline re-grade. Declined to judge: none. No second review.
- Closure applies verification-before-completion and finishing-a-development-branch with existing preserve-local-checkout ruling: leave all changes/QA in place, no Git integration/cleanup. All five earlier Ruling lines and costs are carried to final handoff; no extra permission gate.
