# Fidelidade v3 — forma e proporções

Entrega local de 2026-10-10. Preferência do usuário: forma e proporções do objeto/personagem. App instalado em `C:\Projetos\forge3d-ai`; fonte desta conversa em `C:\Users\arthu\OneDrive\Documentos\Codex\forge3D-ai`.

## O que foi entregue

- **TripoSG Quality 512³**: extração real do mesmo campo neural, 50 passos, guidance 7, 2048 tokens, FP16, encoder 224, chunk 8192 e seed 42. Só aparece quando a prova local corresponde ao código, pesos e perfil. Nenhum peso novo foi baixado.
- **Limpeza conservadora**: nova versão; remove faces degeneradas/duplicadas e fragmentos com até 32 faces E extensão até 0,6% do modelo. Não une vértices ou costuras UV. Normais recalculadas respeitam os grupos de suavização e arestas duras originais.
- **Refinar silhueta**: usa máscara real e câmera frontal ortográfica estimada. Deslocamento lateral limitado a 3% da altura; preserva altura, profundidade e conectividade. Não junta intervalos separados do contorno. Ajustes só são aceitos se aumentarem a sobreposição frontal. Referências sem máscara são rejeitadas.
- Relatórios e versões preservados. Decimation e outros transforms removem a medição de contorno da metadata atual; a medição continua na versão que foi efetivamente avaliada.
- Comparação inclui o personagem usado no aplicativo, mantendo bule, cadeira, robô e benchmarks anteriores. Quatro vistas, material neutro, métricas reais e avaliações humanas sem notas automáticas.

Textura de TripoSG, rig e retopologia não foram adicionados. A infraestrutura matemática de projeção foi testada, mas não está exposta como recurso de texturização. A prioridade desta entrega permaneceu na geometria.

## Experimento real: Balanced → Quality → limpeza e silhueta

Mesma referência/seed 42 por caso. O antes/depois do contorno compara Quality limpo com sua versão refinada, usando a mesma máscara e câmera estimada. **IoU é sobreposição 2D, não percentual de qualidade ou anatomia correta.**

| Referência | Balanced triângulos | Quality triângulos | Após limpeza/refinamento | Contorno antes → depois | Pico PyTorch Quality | Tempo subprocesso IA |
|---|---:|---:|---:|---:|---:|---:|
| Personagem do usuário | 115.706 | 471.304 | 470.284 | 87,60% → 93,33% | 4.669,6 MiB | 63,95 s |
| Bule oficial | 256.152 | 1.023.432 | 1.023.423 | 91,43% → 96,23% | 4.730,4 MiB | 58,15 s |
| Cadeira oficial | 274.722 | 1.112.208 | 1.112.177 | 68,26% → 75,35% | 4.781,7 MiB | 60,76 s |

RTX 4060 8 GB, PyTorch 2.5.1+cu124, Blender 4.5.3 LTS. Valores de VRAM são alocação máxima do PyTorch, não o consumo total do desktop. Tempos acima incluem o subprocesso IA; não incluem toda a preparação/renderização/exportação Blender.

No personagem, a limpeza removeu 72 fragmentos muito pequenos (1.016 faces) e quatro faces degeneradas. A extração 512 também produziu mais ilhas do que 256: polígonos adicionais não equivalem a uma forma aprendida melhor. O ajuste deixou pernas/braços mais próximos do contorno frontal; mãos, rosto, cabelo, espessura lateral e verso ainda têm erros visíveis. A cadeira permanece um caso difícil.

Ablação real do encoder 448: 93.522 triângulos, pico 4.229,5 MiB e 52,32 s. Mudou a forma sem benefício claro de proporções; ficou arquivada em `fidelity-v3/character/encoder448` e o padrão permaneceu 224. Não foi usado um encoder diferente ou um modelo treinado novamente.

## Verificação

- **51 testes passaram**, incluindo limites de API, máscara real, conservação da entrada RGB, componentes significativos, UVs, continuidade das normais nas costuras, arestas duras, reindexação, rejeição de empate/piora e ausência de métricas antigas em derivados.
- TypeScript/Vite build passou. Aviso de bundle do Viewer acima de 500 kB permanece; nenhum erro de compilação.
- Nove variantes do benchmark com quatro renders neutros e nove FBXs reimportados pelo Blender. Front/side/rear/three-quarter disponíveis na comparação. Renders finais do personagem, bule e cadeira inspecionados.
- Playwright usado porque o Browser plugin não está disponível: geração Quality pelo botão, limpeza, refinamento, Wireframe, Low Poly, altura, export e ZIP real de 3.603.981 bytes. Desktop 1600×1000 e mobile 390×844 sem overflow horizontal; zero erros/warnings de aplicação nas verificações finais. Doze pares de vistas de comparação carregaram, opções antigas do robô permanecem e as notas manuais começam em branco.
- Fluxo criado pela interface: `9bf02fe535e641d1b21adde6db22a05d` → `bbad9d39ead04db991dd9497825f14ee` → `f80793177414403bb92763e18f5985dd` → `f91ac45c5ed14b1fa9414eb2248ffd4e` → `8f772aedab93419096fb371e2452ef6e` → export `1e3f183a4056411b8fe6f4b89237b5c3`.
- **Unity 6000.3.0f1 / URP 17.3** importou o FBX realmente exportado: 94.054 triângulos, altura 1,4999999 m, UVs/normais/posições finitas, normais não nulas, material URP Lit neutro, smoothness 0,35, prefab criado e nenhuma textura. Material antigo com textura foi limpo pelo importer. Escopo batchmode/nographics; gameplay e render de uma cena não foram testados.
- RAW e modelos pais conferidos por SHA256 após operações. RAW da nova geração: `34b3e7b5191a44ccd98b4ffcdf91c0c40bbb46802cc28f295981be3b26858994`. Latentes e fonte preservados.
- Revisão independente identificou limites amplos, costuras de normais, perda de grupos após reindexação, máscaras retangulares e métricas desatualizadas; correções verificadas por testes de regressão antes da entrega.

## Provas e como usar

Na instalação: `data/quality-upgrade/fidelity-v3/manifest.json`, `flow-verification.json`, `release-verification.json`, `final-source/`; `models/triposg/quality_validation.json`; `data/UnityFidelityV3Validation/Assets/Forge3D_Asset/unity_import_report.json`. A primeira tentativa de normais está arquivada em `fidelity-v3/ablation/normals-initial`; versões anteriores do usuário não foram substituídas. Screenshots ficam na pasta de visualizações desta conversa.

No app: TripoSG → Quality → Generate → Limpeza conservadora → Refinar silhueta. Examine frente, lado e costas antes de reduzir polígonos. Cada clique gera uma nova entrada na biblioteca. Depois reduza para seu orçamento, ajuste a altura e exporte para Unity. Compare também Balanced: ele continua útil quando Quality acrescenta ruído.

## Limites e próxima etapa

Ainda existem componentes desconectados, triângulos quase degenerados e arestas não manifold em alguns resultados. O critério de limpeza é intencionalmente conservador; não transforma qualquer malha em watertight ou adequada para rig. A inspeção Blender de normais geométricas por vértice pode apontar zeros em vértices incidentes apenas a degenerados, mesmo quando as normais explícitas do GLB são válidas; a validação real do FBX reduzido no Unity passou.

Não foi alegado treinamento/fine-tuning ou melhora universal de qualidade 3D. Uma vista não determina anatomia oculta. Para um salto maior, a próxima experiência é um modelo com condicionamento multi-view nativo, usando vistas consistentes e avaliação de forma em vários ângulos. Hunyuan3D-2mv foi pesquisado, mas não instalado, licenciado ou validado localmente. Pesos grandes e aceite de outra licença permanecem fora desta etapa, conforme a missão fornecida pelo usuário.
