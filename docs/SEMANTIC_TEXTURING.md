# Semântica e Reference Fidelity

## O que está implementado

Módulo local independente dentro de **Texturização → Semântica e Reference Fidelity**. A rede existente Anime-Face-Segmentation executa segmentação real de retratos: cabelo, rosto, pele, olhos, boca, roupa genérica e fundo. O restante fica desconhecido. Não convertemos landmarks, remoção de fundo ou nomes de presets em classes neurais. Humano usa o perfil manual; estilizado usa a rede de retratos com revisão obrigatória.

A taxonomia inclui sobrancelhas, nariz, orelhas, pescoço, braços, pernas, mãos, pés, roupa superior/inferior, mangas, meias, calçados, acessórios, objetos, decoração e região personalizada. Esses rótulos finos exigem anotação manual neste backend. Pincel, borracha, restauração e polígonos modificam mapas categóricos persistentes, com proveniência. Correções criam outra análise; não alteram a imagem original. Sugestões do Character Intelligence são recuperadas somente quando os pixels da imagem correspondem, e permanecem sugestões.

Cada vista tem uma imagem real, máscara de referência, máscara da superfície renderizada e registro revisado. O registro pode usar caixas ou pares de pontos pela API. A interface oferece caixas/recortes numéricos e dois cantos no canvas. A região editável é separada das âncoras de alinhamento. Outra pose exige novo alinhamento; caixas não resolvem deformações articulares. As máscaras são amostradas por vizinho mais próximo. Visibilidade usa profundidade, normal geométrica e identidade da primitiva/superfície. Uma categoria incompatível bloqueia transferência; rosto/pele formam a única família compatível. O clique na malha consulta a classe no atlas UV, convertendo a convenção glTF para a convenção interna.

Reference Fidelity prioriza pixels da referência, respeita classes selecionadas, classes protegidas e polígonos de proteção da API. Fusão preserva bordas e evita misturar classes incompatíveis. Ajuste de cor modifica somente a região elegível com ganhos RGB e intensidade. Propagação usa vizinhos próximos na mesma componente/material/classe e normais compatíveis; é geométrica, não inpainting neural. Costuras usam correspondência real de superfície. Não há suavização da malha ou fechamento de buracos.

SDXL + MV-Adapter pode propor aparência para texels elegíveis sem observação. Executa seis vistas conjuntamente e reutiliza os pesos/offload já instalados e autorizados. **As nossas máscaras restringem projeção/composição; não condicionam espacialmente o denoiser SDXL.** Faces geradas precisam de evidência facial no alvo; não são inferidas em costas desconhecidas. Pixels observados/protegidos têm prioridade. A proposta exige inspeção e aprovação, sem garantia de fidelidade nas áreas ocultas.

O módulo preserva vértices, triângulos, transforms, UVs, normais, slots, alpha, materiais e mapas de dados existentes. Requer albedo PBR e UVs válidas, com sobreposição ≤0,5% e atlas até4K. Modelos sem essas condições recebem diagnóstico para texturização global prévia; não há rebake silencioso. Não produz PBR neural detalhado nem separação física de iluminação. Misturas de intensidade registram BlendWeight e origem distinta de cópia integral.

## Como usar

1. Abra **Texturização**, selecione um modelo salvo texturizado e confira **Frente da malha**.
2. Abra **Semântica e Reference Fidelity**. Use a referência salva ou envie uma imagem real; adicione costas/lados quando disponíveis. Escolha anime, estilizado ou humano/manual e **Analisar / salvar correções semânticas**.
3. Confira referência e superfície renderizada. Ajuste o recorte de cabeça e o alinhamento em **Alinhamento revisado**. Use zoom, pincel/borracha/restauração ou polígonos; duplo clique encerra o polígono. Categorias finas são manuais. Salve/análise novamente depois de corrigir.
4. Selecione classes que receberão edição e marque **Proteger** nas demais. Clique na malha para consultar a classe; cinza/desconhecido é ausência de evidência. Para preservar números/logos, delimite corretamente roupa superior/inferior e use referências na mesma pose.
5. Escolha restaurar pixels ou ajuste de cor. Mantenha áreas ausentes para trabalho conservador; SDXL é uma proposta opcional com seed, estilo e descrição. Confira todas as máscaras/vistas antes de marcar a revisão e criar uma versão.
6. Compare original/candidato de frente, dos lados e costas. Aprove ou rejeite; ambos permanecem salvos. **Preparar GLB / FBX / OBJ / ZIP** exporta a versão selecionada. Na Unity use o importador do pacote, que configura URP/Built-in e espaços de cor.

O caso Kageyama está na biblioteca como fonte `323051d419ba4e47a4f421fd25e31d5f`; análise corrigida `75e34e2ea3ef43599b09e20ec4c92769`, candidato de teste `8566a8a66bbf4403bcb4d5422315634b`. A aprovação/rejeição foi testada; o teste terminou com o original selecionado. A interface recupera análises e candidatos salvos após recarregar. Erros de referência alterada/axis/modelo exigem outra análise. Cancelar e criar novamente reutiliza os recursos/cache válidos; o trabalho cancelado não publica uma análise concluída.

## Validação e qualidade medida

GPU confirmada: RTX4060 **8188MiB**, driver595.97, Windows nativo. Nenhum driver, Torch, NumPy ou runtime principal foi atualizado. Rede de máscaras: pico75,33MiB alocados/132MiB reservados; inferência0,558s Kageyama,0,100s Hinata,0,269s referência estilizada. Preparação/detecção/save adicionam tempo. Análise+atlas reais levam aproximadamente11–91s nos casos medidos; pintura conservadora15–118s, conforme atlas/vistas. Fluxo pela API com correções Kageyama:53,64s de pintura/validação/render.

Comparações abaixo usam pixels visíveis com registro e classes revisadas. São diagnósticos de reconstrução da referência, **não** ground truth3D, identidade universal, acurácia independente do parser ou pontuação oficial MeshyBench. RGB é MAE normalizado; SSIM maior é melhor.

| Caso | Pixels medidos | RGB antes → depois | SSIM antes → depois |
| --- | ---: | ---: | ---: |
| Kageyama cabeça |1685|0,1080 →0,0093|0,2655 →0,9486|
| Hinata cabeça |2442|0,0608 →0,0106|0,3444 →0,9715|
| Naruto estilizado |903|0,1134 →0,0538|0,2236 →0,7936|
| Uniforme frente, máscaras manuais |16490|0,0804 →0,0035|0,6975 →0,9880|
| Uniforme costas, referência real |19290|0,1061 →0,0030|0,6363 →0,9903|

O uniforme usa duas ilustrações reais compatíveis já salvas, número9, e polígonos implementador-anotados com proveniência. Não usa vistas SDXL como verdade observada. A primeira métrica das costas continha uma transformação duplicada da câmera; foi preservada como diagnóstico falho, corrigida por regressão e repetida em result2/result3. O Naruto original era somente geometria: uma nova versão de projeção global/UV1K serviu de baseline, sem alterar o original.

A inspeção lateral encontrou artefatos de projeção no result3. Uma nova versão result4-conservative aumentou o cosseno mínimo para0,8 e reteve mais aparência anterior em ângulos rasantes, sem suavizar geometria. Frente:14.023pixels, RGB0,056234→0,002901 e SSIM0,809782→0,991051; costas:15.790pixels, RGB0,096064→0,002066 e SSIM0,695482→0,994644. As amostras são diferentes da tabela anterior, portanto os scores não comparam os candidatos diretamente. Há ganho visível nos números/logos; bordas laterais e transições ainda exigem revisão. Nenhum desses resultados certifica perfeição em todas as vistas.

Teste opcional SDXL: seed44,6vistas512,20passos, inferência65,38s, carga+inferência92,42s, pintura/render total174,97s. Pico3866,8MiB alocados/5352MiB reservados; monitor GPU total6185MiB incluindo desktop/navegador. Completa1.349.573texels estimados e mantém observação/proteção. Não certificamos melhora de identidade nas costas geradas. O perfil cabe nesta4060 medida; preflight verifica5500MiB livres antes desse caminho.

Após a revisão, a proteção foi acumulada entre todas as vistas e o pincel passou a ter a mesma prioridade do canvas sobre polígonos; restauração recupera a máscara neural original. Uma repetição real SDXL executou em170,60s (61,99s de inferência), com3866,8/5352MiB alocados/reservados e6032MiB de pico total, compondo1.331.796texels gerados. O histórico de recursos SDXL/MV-Adapter agora persiste independentemente da última edição, mantendo avisos de licença em exportações posteriores com completion=preserve. Esses três achados importantes foram reproduzidos em6 regressões, corrigidos e incluídos na suíte completa262passed. Não houve achado crítico ou menor na revisão independente.

Três personagens e uniforme/completion passaram GLB/FBX/OBJ com comparação de triângulos em coordenadas de mundo. Cinco pacotes reais passaram a primeira importação Unity6000.3 em URP e Built-in; após as correções, seis pacotes finais, incluindo a edição posterior à síntese, passaram novamente em um projeto novo (12 relatórios de importação). Slots/canais/espaços de cor foram conferidos. Clay frente/lados/costas é idêntico: textura não reparou anatomia ou volume. Testes automatizados cobrem alpha/mapas/UV/normais/proteção/oclusão/cancelamento/bindings. UI real: pincel, borracha, restauração, polígono, persistência, seleção UV, aprovação/rejeição, desktop1440 e mobile390 sem overflow. Uma restauração assíncrona obsoleta e conversão UV foram reproduzidas/corrigidas. A análise final `6f8378ead3214576997b087812926abd` confirmou apagamento dentro de um polígono persistido: label0/origem2, com22,36s de execução real. Os modos SDXL image/text, regional e cabelo foram repetidos com exportações reais antes de atualizar suas provas.

Evidências: `data/semantic-upgrade-20261014`, comparações iniciais em `comparisons` e finais em `comparisons-reviewed`, pacotes finais em `post-review-packages.json`, importação final em `unity-reviewed-validation.json`, casos em `measured.json`, fluxo real em `browser-evidence.json`, integridade em `preservation.json`, inventário em `final-delivery.json`. A disponibilidade depende de hashes de fontes e provas reais; alterações relevantes exigem revalidação.

## Recursos, licenças e limites

Auditoria dos nove projetos: [SEMANTIC_RESEARCH_20261014.md](SEMANTIC_RESEARCH_20261014.md). AnimeSeg tem classes de corpo mais adequadas, porém a licença explícita dos artefatos consultados não pôde ser confirmada. StyleAnime não tinha parser público executável; SCHP exige validação própria de pesos/licenças/runtime Windows. Não baixamos esses recursos. MVPaint/Paint3D orientam princípios de propagação/UV, sem instalar seus runtimes/pesos. Tripo é referência arquitetural, sem API paga. Hunyuan2.1 Paint não foi instalado: exigência publicada21GB, licença distinta, sem prova8GB. SD2.1 adapters estão publicados, mas o base oficial respondeu401; não usamos mirrors/credenciais.

O parser de retratos usa o código/checkpoint MIT já instalado e hash validado em `models/hair/manifest.json`. Inferência bloqueia rede e não baixa automaticamente. Cache inclui imagem/recorte/perfil/código/manifesto. Não foi baixado nem redistribuído dataset de treinamento. SDXL usa OpenRAIL++ e MV-Adapter Apache2, com recursos/revisões já autorizados; os pacotes derivados incluem avisos/licenças aplicáveis. Setup reaproveita ambientes e pesos existentes; não há instalação adicional oculta.

**Limites restantes:** anatomia e cabelo achatado são geometria; continuam visíveis. Uma imagem não determina as costas. Parsing automático completo do corpo/anime/humano, correspondência de poses articuladas, OCR garantido, denoising condicionado por classes, UV inpainting neural dedicado e materiais PBR físicos continuam pendentes. Para ganho prático maior, forneça vistas reais consistentes e corrija as máscaras de corpo; para geometria insuficiente use o módulo de cabelo/modelagem ou ajuste manual antes de texturizar. Não reivindicamos equivalência a plataformas comerciais.
