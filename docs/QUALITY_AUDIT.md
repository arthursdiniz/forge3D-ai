# Auditoria de qualidade — 2026-10-09

## Implementação encontrada antes de modificar
- TripoSR oficial (código 107cefdc244c39106fa830359024f6a2f1c78871). Pesos 5b521936b01fbe1890f6f9baed0254ab6351c04a, SHA256 429e2c6b22a0923967459de24d67f05962b235f79cde6b032aa7ed2ffcd970ee.
- Inferência real local, PyTorch 2.5.1+cu124, float32, RTX4060; sockets bloqueados, DINO config local. Nenhum mock/fallback simulado encontrado.
- Imagem com EXIF tratado, RGBA, recorte opcional, u2netp ONNX CPU opcional. Alpha bbox e proporção preservada, composição cinza 128, canvas final 512. O encoder upstream usa cond_image_size=512 e normalização ImageNet internamente.
- Remoção de fundo desligada por padrão. Alpha existente pode ser reprocessado quando a opção é marcada. Não há relatório/aviso de clipping, resolução ou possíveis perdas de máscara.
- Geometria: neural field TripoSR, marching cubes CPU de scikit-image, threshold upstream 25. Presets só alteram extração 128/192/256, não rede/condicionamento. Chunk size 4096. Sem redução de polígonos na geração.
- Material: cores neurais consultadas apenas nos vértices da superfície, quantizadas em GLB. Blender cria Smart UV, material emission por vertex color e bake CPU em 512/1024/2048, depois Principled com albedo/roughness constante. Não gera PBR separado.
- O caminho upstream tsr/bake_texture.py (xatlas + rasterização de posições + consulta do campo neural por texel) **não é usado**. A resolução de textura atual não adiciona amostras neurais, só rasteriza cores interpoladas.
- Normais/shading são preservados no import, mas GLB processado apresenta vértices separados por normais/UV; até ~3 vértices por triângulo. Há desconexão topológica no formato de render. Decimation reconecta posições em bmesh antes de reduzir e preserva UV por loop.
- Confirmado no GLB bruto do baseline: atributos POSITION/COLOR_0, **sem NORMAL**. O import glTF usa shading plano quando não há normais, introduzindo facetas. O novo caminho exportará normais calculadas da mesma geometria explicitamente; isso melhora sombreamento, não adiciona detalhes geométricos.
- Blender corrige convenção Z-up do GLB bruto, centraliza e não subdivide. Exportação FBX reimporta e compara tris/UV/dimensões/posições finitas. Unity associa textura explicitamente, valida altura Y-up/normais/UV e gera prefab.
- QA anterior provou funcionamento e integridade, não superioridade artística. As três vistas eram inclinadas, exposição/material e UVs não tinham métricas comparativas. Falta vista three-quarter e rubrica manual.

## Gargalos/hipóteses a medir
1. Perda confirmada de amostragem: cor da rede → vértices quantizados → interpolação/bake, ignorando texel sampling nativo. Investigar UV islands/seams, cobertura e detalhe com a **mesma geometria/codes**, sem atribuir tudo à IA.
2. Fundo/alpha/enquadramento podem mudar condicionamento e apagar estruturas finas. Preservar alpha confiável, gerar relatório e entrada efetiva visível. Não aplicar upscale/filtros sem causa.
3. Reconstrução limitada pela grade de extração; mais resolução refina superfície existente, não cria conhecimento/detalhe novo. Medir ganho de silhueta e orçamento de VRAM.
4. TripoSR continua tendo limites intrínsecos de reconstrução por uma vista. Inferir lados invisíveis não equivale a multi-view; provar alternativas antes de trocar.

## Provas preservadas
Código anterior em data/quality-upgrade/baseline-source; gerações anteriores ao upgrade em baseline, três categorias (teapot, robot de corpo inteiro, chair com detalhes). Baseline e benchmark final concluídos. O script recusa sobrescrever o baseline ou rotular v2 como v1. Não há pontuações de qualidade inventadas.

Baseline concluído: teapot 42.628 tris, robot 84.848, chair 47.328, pico CUDA 1937.5 MiB em cada caso, FBX reimportado com sucesso. manifest.json e record.json por categoria preservam parâmetros, hashes, tempos e caminhos. Todos foram gerados antes das alterações de pipeline.

Teste da rasterização: diferença de 1.8e-5 em coordenadas normalizadas a 32 px corresponde à quantização subpixel do rasterizador GPU. A tolerância unitária foi ajustada de 1e-5 para 1e-4; posições/flip UV incorretos continuariam falhando. Esses testes analíticos não contam como inferência neural.

## Candidatos
SPAR3D e SF3D: HEAD config oficial 401, sem token HF local/env; não podem ser testados agora. TripoSG: código/pesos MIT, revisão 2c1c516d22d58db486a058d98d31bb6177344e06, 7.40 GiB (~7.95 GB) de safetensors totais; sem textura nativa, requisitos GPU limítrofes. Download grande aguarda autorização. Hunyuan2mini/mv: licenças Community próprias, por variante aproximadamente 4.2/5+ GB, não baixar snapshots inteiros com pesos duplicados. Não houve aceitação de termos nem inferência desses modelos nesta etapa.

Fontes primárias: [SPAR3D](https://github.com/Stability-AI/stable-point-aware-3d), [SF3D](https://github.com/Stability-AI/stable-fast-3d), [TripoSG](https://github.com/VAST-AI-Research/TripoSG) e [pesos MIT](https://huggingface.co/VAST-AI/TripoSG), [Hunyuan3D2/mini/mv](https://github.com/Tencent-Hunyuan/Hunyuan3D-2) e [licença](https://github.com/Tencent-Hunyuan/Hunyuan3D-2/blob/main/LICENSE). SPAR3D informa 10.5 GB padrão/~7 GB low VRAM e Windows experimental; SF3D ~6 GB; TripoSG GPU de pelo menos 8 GB. Estes requisitos não comprovam funcionamento com o desktop ocupando ~2.5 GB. O upstream TripoSG não define model_cpu_offload_seq; offload adaptado teria que ser testado. Multi-view continua desabilitado. TRELLIS.2 não integrado.

## Conclusões do upgrade

- O gargalo estava também no processamento: falta de normais, consulta de cor só nos vértices e conversão de cor duplicada. O modelo não foi substituído por um candidato sem prova.
- V2 exporta normais explícitas. Balanced/Quality criam UV xatlas, rasterizam posições de superfície e consultam o decoder CUDA por texel em lotes limitados. PNG sRGB 1024/2048 e UVs são preservados pelo Blender. Não há subdivisão/remeshing que finja detalhe, mapas PBR inventados ou remoção de iluminação aprendida.
- COLOR_0 em glTF é linear. Fast/RAW convertem RGB neural sRGB para linear uma vez; atlas grava PNG sRGB diretamente. A conversão anterior clareava a cor novamente no bake. Fast mantém quantização de vértices em 8 bits, com menor precisão em tons escuros. [Especificação glTF](https://registry.khronos.org/glTF/specs/2.0/glTF-2.0.html).
- Ablação a 192³: numpy.array_equal confirmou vértices/faces do bule exatamente iguais ao baseline; aparência mudou com textura/normais. Isso prova ganho de aparência, não detalhes geométricos novos.
- Ablação na mesma malha do robô Quality: margem UV 16→4, atlas 5498²→2865×2866, superfície rasterizada na textura 2048 de 10.94%→39.40%, 459.010→1.652.530 consultas reais; 9072 charts inalterados. atlas-ablation.json registra as medidas. Resultados intermediários preservados em ablation/atlas-initial. Utilization do xatlas inclui empacotamento/padding, cobertura rasterizada é outra medida. [xatlas](https://github.com/mworchel/xatlas-python).
- Auto preserva qualquer alpha fornecido, inclusive furos internos/cantos opacos. Fundo opaco usa u2netp CPU local. EXIF corrigido no upload; recorte, centralização/proporção, presets reais de ocupação, aviso de baixa resolução/bordas e original/entrada 512 preservados. Oclusão é declarada desconhecida, com inspeção visual; nenhum upscale inventa detalhe.
- Integridade mede componentes, triângulos quase degenerados, bordas abertas/não manifold, UV/normais finitas. Soldagem somente na cópia analítica com tolerância 1e-7 evita tratar seams de render como componentes. Não há limpeza destrutiva automática.
- RAW/PROCESSED são preservados; GAME OPTIMIZED permanece assim após centro/escala, inclusive jobs legados; UNITY EXPORT é separado. Material roughness .65/metallic 0 é constante neutra, não mapa gerado. Unity smoothness .35 acompanha essa constante.
- Lock do sistema é compartilhado por API/benchmark antes de CUDA. Uma inferência por vez, com estágio real de espera. gpu_monitor.json registra uso total nvidia-smi; inference.json picos PyTorch. Pesos/contexto liberados no fim do processo, OOM mantém arquivos já gravados sem simulação/downgrade silencioso. OOM deliberado não foi testado.

## Benchmark final real

Entrada idêntica à baseline: fundo mantido, ocupação .85, mesmas referências oficiais MIT. Mesmo checkpoint TripoSR, encoder 512, batch 1, float32, chunk 4096, offline. Seed não suportada (null). Tempos são subprocesso IA (carga+geometria+atlas no v2), excluem Blender/Unity/renders. Baseline deixava o bake para Blender; não se deve tratar estes tempos como comparação ponta a ponta.

| Caso | Modo | Grade | Textura px | Triângulos | IA s | Pico alocado MiB | FBX |
|---|---|---:|---:|---:|---:|---:|---|
| Bule | Baseline | 192 | 1024 | 42.628 | 14.66 | 1937.5 | passou |
| Bule | Fast | 128 | 512 | 18.588 | 12.67 | 1866.5 | passou |
| Bule | Balanced | 256 | 1024 | 76.368 | 30.81 | 2378.5 | passou |
| Bule | Quality | 320 | 2048 | 120.508 | 44.22 | 3114.5 | passou |
| Robô | Baseline | 192 | 1024 | 84.848 | 13.75 | 1937.5 | passou |
| Robô | Fast | 128 | 512 | 36.864 | 13.11 | 1866.5 | passou |
| Robô | Balanced | 256 | 1024 | 151.672 | 56.78 | 2378.5 | passou |
| Robô | Quality | 320 | 2048 | 238.760 | 111.09 | 3114.5 | passou |
| Cadeira | Baseline | 192 | 1024 | 47.328 | 13.77 | 1937.5 | passou |
| Cadeira | Fast | 128 | 512 | 20.432 | 13.66 | 1866.5 | passou |
| Cadeira | Balanced | 256 | 1024 | 84.668 | 40.00 | 2378.5 | passou |
| Cadeira | Quality | 320 | 2048 | 132.740 | 67.92 | 3114.5 | passou |

Picos reservados PyTorch: Fast 2060, Balanced 3052, Quality 4032 MiB. Desktop/viewer acrescentam uso; não se promete mesmo orçamento para qualquer imagem. JSON de cada caso contém parâmetros, SHA/revisões, seed null, tempos, UVs/textura/triângulos/integridade/FBX.

Quatro vistas: front +X (câmera de condicionamento TripoSR), side -Y, back -X, three-quarter +X/-Y. Câmera/luz/fundo/gerenciamento Standard iguais, seed de render Blender 42 (não seed de geração). Albedo sem luz do render ajuda a separar aparência; não remove luz/reflexos da referência.

## Avaliação visual sem notas automáticas

| Categoria | Observado | Configuração prática nesta referência |
|---|---|---|
| Bule | Vermelho menos lavado e menos facetas. Reflexos ainda geram manchas/saliências falsas; bico/alça/verso aproximados. | Balanced no cotidiano; Quality aumenta amostras de textura, sem resolver a forma. |
| Robô | Olhos/cores mais preservados, cabeça mais suave; mãos/antenas frágeis. Quality: 8 componentes/6 faces quase degeneradas; Balanced: 2/3. | Balanced pelo custo. Quality não demonstrou ganho de silhueta que sempre justifique o tempo maior. |
| Cadeira | Madeira menos desbotada e shading suave; contornos mais amostrados, detalhes do estofamento/costas ainda estimados. | Balanced suficiente; guardar Quality para edição de alta densidade. |

Não há comparação artística entre provedores diferentes: somente TripoSR executável nos acessos/permissões atuais. /#comparison mostra baseline e nove resultados, rubrica manual 1–5 para sete critérios e “Não avaliado” inicial. Teste de persistência salvou só uma observação de QA, sem notas. Não se afirma equivalência ao Meshy.

## Provas de integração

Navegador→API→CUDA→Blender→viewer→otimização→escala→FBX, bule com auto: 84.274→21.066 tris, altura 1.5 m. SHA256 RAW idêntico após operações/exportações; link PROCESSED preservado, GAME OPTIMIZED aponta ao último derivado. Dois triângulos quase degenerados e três componentes reportados, sem remoção.

Unity 6000.3.0f1/URP17.3: dois pacotes reais + benchmark Quality 2048 importados juntos, shader Lit, BaseMap 1024/2048, smoothness .35, triângulos exatos, posições/UV finitas, normais/UVs por vértice, altura Y-up e prefabs. Exit 0, REAL_UNITY_QUALITY_2048_AND_OPTIMIZED_PASS. Provas em data/quality-upgrade/unity-validation.json, flow-verification.json e data/UnityQualityValidation. Gameplay/render final de cena não testados.

25 testes passaram (15 API/core, 10 preparação/UV/mesh/cor), TypeScript/Vite passou, navegador desktop1600×1000/mobile390×844 sem overflow/erros de aplicação. Revisão independente apontou cor Fast, lineage, sobrescrita do baseline e concorrência scripts/API; corrigidos e relidos. Bundle Three.js permanece lazy, com aviso de tamanho do Vite. Pequenas partes soltas/triângulos quase degenerados persistem em alguns resultados, registrados acima; modelo não é prometido para animação.

## Continuação autorizada — TripoSG
O download antes pendente foi autorizado e concluído. O candidato foi validado em três inferências reais/FBX na RTX4060 e integrado como opção de geometria sem textura. Resultados e diferenças de preparação estão em [TRIPOSG_VALIDATION.md](TRIPOSG_VALIDATION.md). O relatório acima preserva o estado do upgrade TripoSR e seu baseline.
