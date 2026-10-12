# Personagens avançados — plano de implementação

> Execução inline com superpowers:executing-plans; revisão independente única no final.

**Goal:** melhora visual e técnica comprovada no Hinata dentro do orçamento de3–5min, ou limite demonstrado com alternativa prática.
**Architecture:** diagnóstico por etapas e ablações reais isoladas; orientação correta no adaptador; recursos SG existentes reutilizados; candidatos preservados e refinamentos conservadores. Configuração de produto depende dos resultados.
**Tech Stack:** Python/PyTorch, scikit-image/Trimesh/xatlas, Blender4.5.3, FastAPI/React/Three, Unity6000.3.
**Spec:** ../specs/2026-10-11-character-advanced-design.md

## Restrições e revisão
Originais/modos/biblioteca preservados; sem remesh/fill-holes/smooth automático; somente seed suportada; no mínimo frente,ambos os lados,verso neutro/textura. Volume positivo não comprova anatomia. Uma vista não observa costas. Não há Git neste workspace: preservar snapshots em data/character-advanced-20261011.

### 1. Orientação e diagnóstico
- [x] RED teste com campo de densidade esférico positivo no interior, passando pela mesma convenção upstream.
- [x] GREEN helper backend/isosurface.py e integração em triposr_runtime.py; posições e conjuntos de triângulos idênticos no Hinata, volume-0,0113867→+0,0113867. Normais/faces externas; teste esfera e inspeção de volume passaram.
- [x] Comparar RAW/textured/processed/imported e renderer com culling; documentar defeitos restantes.

### 2. Ablação real e recursos locais
- [x] Reusar ambiente/vendor/pesos SG instalados: junctions somente para recursos ausentes, health/CUDA reais. Biblioteca atual permanece no workspace.
- [x] scripts/benchmark-character-advanced.py: TSQuality corrigido, preparo experimental, SGBalanced/Quality e seeds/guidance relevantes, todos preservados. Registrar tempo ponta a ponta e picos Torch/uso totalGPU.
- [x] Inspecionar cinco vistas neutras e texturizadas; comparar dimensões/componentes/bordas/normais/UV e rosto/mãos/separação de membros. Escolher parâmetros com evidência.

### 3. Modo avançado com limites explícitos
- [x] RED contratos de parâmetros e candidatos, seleção/linhagem/export, conservação de textura/UV e cancelamento.
- [x] Implementar backend/character_advanced.py e integração worker/schemas/providers/API; candidatos sequenciais e preservados, parâmetros validados. Refinamento conservador opcional só se melhorar, sem se passar por anatomia aprendida.
- [x] UI no layout existente: modo e candidatos, limites de textura/tempo, medidas reais; manter modos anteriores.

### 4. Verificação e entrega
- [x] Repetir fluxo real no Hinata, medir180–300s ou reportar desvio. FBX/Unity normals,UV/material/escala/prefab; testes/build e Playwright desktop/mobile.
- [x] Revisão única, correções RED/GREEN, hashes/snapshot/relatório antes/depois; explicar qualquer objetivo não atendido e próximo caminho viável.

Ruling: autorização explícita atual é para investigar e implementar; não pedir nova confirmação para cada escolha reversível. Downloads/licenças especiais continuam fora das mutações desta etapa até necessidade concreta.

Ruling2026-10-11: usuário autorizou explicitamente download/teste pessoal local Hunyuan3D-2mini sob licença Tencent. Pesos públicos3819958234bytes, revisãof90a0f7df7d5e6f71109cf333f6a95a0ae3194a6/SHA3cc66f3bea33e4062b7dbc875ffe1d70c4888914aec3e91b60f94e9bd01b522b, códigof8db63096c8282cb27354314d896feba5ba6ff8a. Testar separado; sem paint/serviço pago/toolkit.

Ruling: cópia integral do ambiente SG para OneDrive mostrou custo desnecessário; tentativa arquivada. AmbienteHY isolado utiliza dependências SG fixadas em leitura via.pth, com pymeshlab instalado somente no próprio ambiente. Não executar pip em SG nem modificar seus arquivos.

Evidência: HYmini256/seed42/50passos/guidance5/FP16 executou em48,02s, pico4182,2MiB/reservado4590,0MiB; sem offload e sem OOM. RAW114932triângulos, fechado/volume positivo,10componentes/5quase-degenerados; necessita inspeção visual e export. SG cinco ablações82–95s ponta a ponta;512gerou mais ilhas, não demonstrou rosto/anatomia melhor por si.

Task1–4 complete: orientação e presets testados RED→GREEN; sete ablações TS/SG, HY256/384 e dois lotes avançados reais preservados. Lote da interface260,60s/4644,1MiB PyTorch/7305MiB total; seeds repetem RAWs exatos.50renders768 de5variantes, mais5neutros da versão otimizada. Quatro FBX roundtrips e fluxo UI→candidato2→52330tri/1,5m→download→UnityURP/prefab passaram.71testes,build6,32s,QA desktop/mobile e cinco vistas×dois materiais passaram.

Final: fixed Original atravessava lote e trocava candidato2→1 — test_original_stops_at_selected_candidate_generation_boundary RED→GREEN.
Final: fixed publicação parcial no cancelamento/falha — test_cancel_during_second_candidate_copy_publishes_neither_child e test_failed_second_candidate_copy_leaves_no_completed_half_batch RED→GREEN; cancelamento antes do commit também coberto. Transação conjunta de lote/candidatos.
Final: Ruling: comparação sem imagens ou com baseline nos dois lados afeta a prova pedida; tratada como importante, defaults/aparência corrigidos e navegador demonstrou antes RED/depois GREEN. Custo se errado: trocar seleção/aparência na entrada, sem alterar arquivos.
Final: fixed QA encontrou Normais orientando patchesUV isolados — test_normal_operation_orients_uv_seam_patches_without_changing_shape_or_uvs RED→GREEN e Hinata antigo real; faces corretas com posições/UVs conservadas. Ensaio falho preservado e rotulado.
Final: Ruling: review não julgou legalidade/licença, anatomia perfeita/invisíveis, outro hardware ou gameplay. Autorização humana Tencent já existe; escopo declarado como teste pessoal, GPU confirmada/importação técnica, sem inferir esses outros resultados. Custo: exige avaliação humana/manual para uso além do ensaio.
Final: sem menores pendentes da revisão. Warning de chunk932KB e depreciação AnyIO anteriores permanecem, sem erro de build/testes.
Ruling: semGit neste workspace, preservar plano/provas/snapshot final em data/character-advanced-20261011; não apagar ledger/originais ao finalizar.
