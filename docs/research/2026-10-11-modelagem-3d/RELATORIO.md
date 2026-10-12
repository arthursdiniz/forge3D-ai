# Modelagem 3D com IA para jogos e Unity

Pesquisa e experimentos locais — 11 de outubro de 2026.

## Resultado e decisão prática

Para o Forge3D na RTX 4060 de 8 GB, a recomendação é manter dois caminhos: **modelagem procedural assistida por IA para objetos geométricos** e **imagem → malha neural → revisão e preparação para Unity para objetos de forma mais livre**. Os testes abaixo mostram sensibilidade à referência, enquadramento e parâmetros; não estabelecem um gerador universalmente superior.

O próximo candidato local mais relevante é **TRELLIS.2/Pixal3D nativo no ComfyUI, com checkpoints INT8**. A implementação existe, mas não foi executada nesta pesquisa. O requisito de 24 GB do repositório Microsoft não pode ser aplicado automaticamente ao port quantizado, e os relatos de 6 GB não comprovam que todas as etapas caibam na GPU do usuário. [ComfyUI: anúncio](https://blog.comfy.org/p/trellis2-and-pixal3d-are-now-native), [workflow oficial](https://docs.comfy.org/tutorials/3d/trellis2).

Foram executadas **10 novas inferências locais**, além da criação procedural, refinamento, simplificação, exportação e importação. Modelos comerciais e outros pesos pesquisados não foram chamados ou baixados. Resultados anteriores do projeto não foram apresentados como testes novos.

## O que precisa ser aprendido sobre modelagem

Uma malha usa vértices, arestas e faces para representar a superfície. Em jogos, a forma precisa funcionar com UVs, materiais, normais, escala, pivô e interação. Modelagem poligonal, escultura e métodos procedurais oferecem controles distintos; uma imagem de renderização é somente uma observação da malha. A Wikipedia ajuda a organizar essas bases, mas não demonstra qual IA é melhor. [3D modeling](https://en.wikipedia.org/wiki/3D_modeling), [Polygonal modeling](https://en.wikipedia.org/wiki/Polygonal_modeling).

**Forma e material devem ser avaliados separadamente.** Detalhes finos podem ser representados por normal maps de forma eficiente; isso é desejável quando a silhueta permanece correta. Uma alça, uma abertura ou uma peça móvel que existe apenas na textura não tem a geometria necessária para interação. [Unity: normal maps](https://docs.unity3d.com/6000.1/Documentation/Manual/StandardShaderMaterialParameterNormalMap.html).

**Decimation, remesh e retopologia resolvem problemas diferentes.** Reduzir triângulos não cria automaticamente fluxo de arestas adequado à deformação. Quads ajudam edição e animação, mas não são um certificado de qualidade: Unity normalmente triangula as faces na importação. “Optimize Mesh” no importador reorganiza os dados para processamento; não reconstrói a forma artística. [Unity: importação de modelos](https://docs.unity3d.com/6000.0/Documentation/Manual/FBXImporter-Model.html).

**Fotogrametria** usa fotografias sobrepostas do mesmo objeto real para estimar estrutura. É especialmente interessante quando o objeto existe e a fidelidade ao mundo real é importante. Exige cobertura e imagens com textura, exposição e foco adequados; superfícies reflexivas, transparentes ou uniformes são difíceis. [Wikipedia: photogrammetry](https://en.wikipedia.org/wiki/Photogrammetry), [COLMAP: tutorial](https://colmap.github.io/tutorial.html).

**NeRF e Gaussian splatting** são especialmente voltados à síntese de vistas e aparência de cenas. A representação original não é automaticamente uma malha editável com UVs, collider e rig. Extrair ou reconstruir uma superfície é outra etapa. Não comparar um vídeo convincente de splats diretamente com a qualidade de um asset poligonal de jogo. [Wikipedia: NeRF](https://en.wikipedia.org/wiki/Neural_radiance_field), [NeRF: autores](https://www.matthewtancik.com/nerf), [Gaussian splatting: Wikipedia](https://en.wikipedia.org/wiki/Gaussian_splatting), [artigo/projeto Inria](https://repo-sam.inria.fr/fungraph/3d-gaussian-splatting/).

## Como usar IA: métodos comparados

| Método | Onde é útil | Principal limite | Situação nesta pesquisa |
|---|---|---|---|
| IA escreve Blender Python ou parâmetros procedurais | Móveis, caixas, módulos arquitetônicos, peças repetitivas | O script precisa representar corretamente a construção; formas orgânicas são difíceis | Cadeira construída, limpa e exportada realmente |
| Uma imagem → malha neural | Bases rápidas para props estilizados e orgânicos | Partes escondidas são inferidas; perspectiva e contorno condicionam a forma | TripoSG e TripoSR executados |
| Texto → imagem de conceito → malha | Explorar aparência antes da geometria | Detalhes incoerentes da imagem podem virar geometria errada | Pesquisado; sem teste de geração de conceito nesta rodada |
| Vistas consistentes → gerador multiview nativo | Objetos com costas, furos e lados importantes | Vistas independentes podem mudar o próprio objeto | Pesquisado; os testes locais usaram uma imagem por inferência |
| Fotografias reais → fotogrametria | Capturar um objeto existente | Captura, iluminação e superfícies inadequadas prejudicam correspondências | Pesquisado; sem conjunto fotográfico real disponível |
| High-poly → low-poly + bake | Preservar aparência com orçamento de renderização menor | Simplificação pode alterar silhueta e UV; retopologia pode exigir artista | Decimation testada; nenhum normal map novo foi assado |

Métodos antigos de texto para 3D por otimização, como DreamFusion, mostram como um modelo de imagens pode orientar uma representação 3D. Isso explica a técnica, mas não torna o método a melhor escolha de produção em 2026. O TRELLIS original também recomenda texto → imagem → pipeline condicionada por imagem para maior detalhe e criatividade. [DreamFusion](https://dreamfusion3d.github.io/), [TRELLIS](https://github.com/microsoft/TRELLIS).

A via procedural não é infalível: pesquisas como Text2CAD-Bench apontam dificuldades de LLMs com operações e topologias complexas. A recomendação é executar, medir e inspecionar o script, não tratar texto gerado como geometria correta por definição. [Text2CAD-Bench](https://arxiv.org/html/2605.18430v1).

## Modelos e ferramentas: escolha atual

| Candidato | Capacidade documentada | Hardware/limite relevante | Recomendação |
|---|---|---|---|
| TripoSR | Imagem única, geometria e cor; bake de textura opcional; código/pesos MIT | README informa cerca de 6 GB nas opções padrão | Baseline texturizado local, já disponível. [Fonte](https://github.com/VAST-AI-Research/TripoSR) |
| TripoSG | Difusão de forma; saída GLB; simplificação opcional | README pede CUDA e pelo menos 8 GB; não fornece texturização completa | Base de geometria local, avaliada nesta rodada. [Fonte](https://github.com/VAST-AI-Research/TripoSG) |
| Stable Fast 3D | GLB com UV, cor com remoção de iluminação e parâmetros de material | Aproximadamente 6 GB no padrão; Windows experimental; pesos com acesso condicionado | Candidato eficiente para comparar pipeline de material; não instalado. [Fonte](https://github.com/Stability-AI/stable-fast-3d) |
| TRELLIS.2 Microsoft | Malha com PBR e representação O-Voxel | Referência oficial pede NVIDIA ≥24 GB e Linux; tempos publicados em H100 | Relevante para qualidade, não validado nesta RTX 4060. [Fonte](https://huggingface.co/microsoft/TRELLIS.2-4B) |
| TRELLIS.2/Pixal3D ComfyUI | Nodes nativos, checkpoints INT8, VAEs BF16, remesh/UV/bake | Menor requisito potencial; resolução e etapas intermediárias mudam consumo | Prioridade para o próximo teste local, ainda sem garantia de 8 GB. [TRELLIS.2](https://docs.comfy.org/tutorials/3d/trellis2), [Pixal3D](https://docs.comfy.org/tutorials/3d/pixal3d) |
| Hunyuan3D 2.1 | Forma e texturização PBR | 10 GB forma, 21 GB textura, 29 GB conjunto segundo README | Não é a primeira opção para esta GPU. [Fonte](https://github.com/Tencent-Hunyuan/Hunyuan3D-2.1) |
| Hunyuan3D 3.1 API | Serviço com até oito vistas e PBR opcional | Serviço externo; PBR desligado por padrão; contagem padrão de faces muito alta para assumir uso direto | Candidato remoto, sem teste ou compra de créditos. [Fonte](https://intl.cloud.tencent.com/zh/document/product/1284/75540) |
| Meshy 7.1 / T2 | Imagem, múltiplas imagens, PBR, remesh e geração Smart Topology | Opções variam por modelo; T2 pode gerar partes separadas com contagem alvo | Comparar alta fidelidade versus topologia para jogo. Não chamar opção antiga lowpoly como recomendação atual. [Fonte](https://docs.meshy.ai/en/api/image-to-3d) |
| Tripo comercial | Geração multiview, texturas/PBR e saída quad opcional | Ao menos duas vistas; objeto e iluminação devem ser consistentes | Não confundir com modelos abertos TripoSR/TripoSG. [Fonte](https://developers.tripo3d.ai/en/docs/generation-multiview-to-model/standard) |

Wonder3D e InstantMesh são referências úteis de geração de vistas e reconstrução sparse-view. Podem melhorar cobertura da forma, mas também herdam problemas de vistas inconsistentes e etapas de material. Não foram instalados apenas para aumentar a quantidade de candidatos. [Wonder3D](https://github.com/xxlong0/Wonder3D), [InstantMesh](https://github.com/TencentARC/InstantMesh).

### Licenças fazem parte da escolha

A licença do núcleo não cobre automaticamente cada dependência. O pipeline padrão TripoSG usa BRIA RMBG-1.4; o Forge3D local usa seu preparador próprio/u2netp e, neste experimento, recebeu alpha já existente. O pipeline Microsoft TRELLIS.2 inclui BRIA RMBG-2.0 e DINOv3; a versão nativa ComfyUI usa BiRefNet em lugar de BRIA. Esses caminhos devem ser diferenciados ao revisar licenças. [RMBG-1.4](https://huggingface.co/briaai/RMBG-1.4), [RMBG-2.0](https://huggingface.co/briaai/RMBG-2.0), [BiRefNet Comfy-Org](https://huggingface.co/Comfy-Org/BiRefNet), [licença DINOv3](https://github.com/facebookresearch/dinov3/blob/main/LICENSE.md).

Hunyuan3D 2.1 tem licença própria com restrições territoriais e disposições relativas aos outputs; não é equivalente a MIT para distribuição mundial. SF3D usa a Stability Community License e prevê condições comerciais ligadas à receita. Revisar a licença exata da versão e das dependências antes de escolher um pipeline comercial. [Hunyuan3D: licença](https://github.com/Tencent-Hunyuan/Hunyuan3D-2.1/blob/main/LICENSE), [SF3D: model card](https://huggingface.co/stabilityai/stable-fast-3d).

## Feedbacks: o que os usuários relatam

| Data | Relato | Como interpretar |
|---|---|---|
| 05/02/2025 | Modelos Meshy com UV/resolução estranhos após importar GLB no UnityGLTF. [Thread](https://www.reddit.com/r/Unity3D/comments/1iic9hl/glb_import_issues_weird_uv_mapping_and_low/) | Integração pode ser o problema; não prova falha do gerador. |
| 28/04/2025 | Jogo Unity usa bases Meshy e limpeza, UV e rig no Blender; props em grande parte tradicionais. [Thread](https://www.reddit.com/r/Unity3D/comments/1k9rlyc/heres_how_the_comic_book_style_is_done_in_my_game/) | Exemplo de workflow híbrido com resultado em projeto real. |
| 27/11/2025 | Alguns usuários exigem retopologia; outro aceita outputs em jogo top-down. [Thread](https://www.reddit.com/r/aigamedev/comments/1p8bwnj/are_meshy_or_any_other_services_game_ready_for_3d/) | Critérios de câmera e acabamento explicam parte da discordância. |
| 21/04/2026 | Tower defense usa modelos simplificados e separa canhão da torre para rotação. [Thread](https://www.reddit.com/r/meshyai/comments/1ss07jr/my_experience_using_meshy_for_game_models/) | Mostra utilidade para protótipo e distância; não é jogo finalizado nem benchmark. |
| 26/05/2026 | Machado Tripo termina com refinamento, retopologia manual e bake no Substance. [Thread](https://www.reddit.com/r/TopologyAI/comments/1tnyc39/turning_an_image_into_a_gameready_3d_asset_using/) | “Pronto para jogo” dependeu de trabalho artístico adicional. |
| 19/06/2026 | UVs fragmentados dificultam trocar materiais apenas em partes de assets IA. [Blender Artists](https://blenderartists.org/t/retexturing-ai-assets/1645653) | Separação semântica e UVs editáveis merecem avaliação própria. |
| 26/06/2026 | Vistas geradas separadamente alteram detalhes; imagem única inventa costas. [Thread](https://www.reddit.com/r/Tripo_ai/comments/1ufuo74/single_image_vs_multiview_in_tripo_where_each_one/) | Consistência de entrada importa; o autor também relata erros de orientação. |
| 11/09/2026 | Comentários ainda pedem retrabalho da topologia, apesar de reconhecerem progresso. [Thread](https://www.reddit.com/r/aigamedev/comments/1wd9xcw/is_meshy_topology_good/) | Amostras e versões ausentes; não demonstram vencedor universal. |

As threads têm vieses, exigências diferentes e poucas comparações controladas. A síntese útil é medir **tempo até asset aceitável na câmera real do jogo**, incluindo revisão, material, UV e otimização. Não transformar preferência de fórum em ranking técnico.

## Experimento controlado executado

**Hardware:** RTX 4060, 8.188 MiB reportados pelo driver; PyTorch 2.5.1+cu124; Blender 4.5.3 LTS. Modelos e dependências já existentes da instalação foram lidos; todas as novas saídas ficaram no workspace. Inferência bloqueou conexões de rede. O lock da GPU da instalação foi adquirido em modo de arquivo somente leitura, evitando inferências simultâneas.

**Referência:** cadeira procedural de 0,88 × 0,82 × 1,62 m, nove partes combinadas, quatro renders ortográficos de 512². Somente frente ou três quartos foram usados como entrada de cada geração. Não houve condicionamento multiview. As imagens ficaram preservadas após a limpeza geométrica da referência.

O export procedural original tinha 1.092 triângulos, com degenerados numéricos. Uma revisão independente confirmou que a área positiva pertencia à superfície exterior; não havia massa superficial interna contaminando a amostragem. Weld e remoção de degenerados produziram uma nova versão com **214 triângulos**, sem novo bevel e com os mesmos limites. O controle com defeito e a versão limpa foram mantidos separadamente.

**Parâmetros controlados:** TripoSG padrão 50 passos, guidance 7, 2.048 tokens, seed 42, extração 256³; variações de ocupação 65%/83,33%/87,5%, seed 7, 25 passos, 512³ e vista três quartos. TripoSR foi comparado em MC 256 com atlas neural e bake de cores de vértice. Um controle adicional igualou a resolução das texturas em 1024².

**Métrica de forma:** 25 mil pontos amostrados por área em cada malha, distância média bidirecional de superfície, expressa em porcentagem da maior dimensão normalizada. Menor é melhor. F-score usa limiar de 2% dessa dimensão. Escala, centro e melhor yaw foram normalizados com conhecimento da referência: é uma comparação **favorável ao gerador**, que não mede escala absoluta ou orientação pronta para Unity.

O piso amostral ao comparar a mesma superfície com amostras independentes foi **0,41%**. Não subtrair esse valor dos erros. Distância de superfície, F-score e inspeção visual medem aspectos diferentes. Não chamar os números de “percentual de qualidade” nem inferir anatomia/material/topologia a partir deles.

### Resultados de geometria

| Variante | Triângulos | Distância de superfície ↓ | F-score (2%) ↑ |
|---|---:|---:|---:|
| TripoSG frente · padrão | 230.912 | 1,46% | 77,14% |
| TripoSG frente · ocupação 87,5% | 186.744 | 2,82% | 68,42% |
| TripoSG frente · extração 512³ | 921.552 | 1,48% | 77,01% |
| TripoSG frente · seed 7 | 176.308 | 2,53% | 76,69% |
| TripoSG frente · ocupação 65% | 161.960 | 2,49% | 79,82% |
| TripoSG frente · 25 passos | 230.728 | 1,47% | 76,88% |
| TripoSG · entrada três quartos | 319.266 | 0,86% | 92,29% |
| TripoSR · atlas neural 1024 | 96.468 | 6,01% | 26,95% |
| TripoSR · vértices 512 | 96.468 | 6,01% | 26,95% |
| TripoSR · vértices 1024 | 96.468 | 6,01% | 26,95% |
| TripoSG melhor · 6.384 tris | 6.384 | 0,87% | 92,17% |
| TripoSG melhor · 31.926 tris | 31.926 | 0,86% | 92,26% |
| TripoSG 512 · silhueta refinada | 921.552 | 1,47% | 77,22% |

- **A vista em três quartos ajudou neste objeto:** distância 1,46% → 0,86%, redução relativa de 41,13% dessa métrica. A imagem revela profundidade e separação de partes que a frente esconde. Isso não prova a mesma melhora em todos os objetos.
- **512³ não melhorou a forma medida:** 230.912 → 921.552 triângulos, com distância 1,46% → 1,48%. O aumento da amostragem do mesmo campo acrescentou densidade e um componente separado.
- **Ocupação maior não foi melhor:** 87,5% teve erro maior que o padrão 83,33%; 65% também piorou a distância média. F-score e distância não ordenaram todas as variantes da mesma forma.
- **25 passos foi uma opção de velocidade nesta amostra:** distância próxima ao padrão de 50 passos. Comparar os tempos de geração na tabela; carregamento e cache também influenciam o tempo total.
- **Seed altera o resultado:** seed 7 piorou a distância desta cadeira. Testar alternativas é útil, mas escolher um seed com base no objeto conhecido não demonstra generalização.
- **TripoSG foi mais fiel que TripoSR nesta cadeira:** no input em três quartos, a distância TripoSR foi 6,01%, contra 0,86% TripoSG. TripoSR também mostrou falhas claras em pernas, encosto e profundidade. Uma importação/renderização tecnicamente válida não torna essas formas equivalentes.

Os arquivos de latentes das variantes TripoSG 256 e 512 tiveram o mesmo SHA256. A alteração controlou a extração do mesmo resultado neural. A inspeção visual também encontrou planos e espessuras inferidos incorretamente junto às pernas/partes ocultas, mesmo no caso com melhor métrica. A distância baixa não substitui revisão das vistas.

Tempos abaixo são do subprocesso de inferência, incluindo carregamento, preparação e geração, conforme `inference.json`. Não representam tempo total de revisão/exportação/Unity. VRAM é pico alocado pelo PyTorch, sem incluir todo o desktop.

| Inferência | Tempo subprocesso | Geração/extração | Pico PyTorch |
|---|---:|---:|---:|
| TripoSG frente · padrão | 59.64 s | 38.80 s | 4225.0 MiB |
| TripoSG frente · ocupação 87,5% | 47.87 s | 37.67 s | 4225.0 MiB |
| TripoSG frente · extração 512³ | 60.72 s | 50.20 s | 4731.5 MiB |
| TripoSG frente · seed 7 | 47.63 s | 37.62 s | 4225.0 MiB |
| TripoSG frente · ocupação 65% | 49.23 s | 37.65 s | 4225.0 MiB |
| TripoSG frente · 25 passos | 32.19 s | 22.33 s | 4225.0 MiB |
| TripoSG · entrada três quartos | 56.69 s | 39.38 s | 4225.0 MiB |
| TripoSR · atlas neural 1024 | 93.23 s | 9.62 s | 2378.5 MiB |
| TripoSR · vértices 512 | 21.78 s | 8.72 s | 2378.5 MiB |
| TripoSR · vértices 1024 | 21.39 s | 9.26 s | 2378.5 MiB |

### Textura, simplificação e refinamento

No controle adicional, MC 256 e texturas 1024² foram iguais nas duas pipelines. Posições de vértices idênticas: **Sim**; faces idênticas: **Sim**; cores de vértice idênticas: **Sim**. Portanto, mudar o bake/atlas **não corrigiu a geometria**. UVs e amostragem de cor diferem, e este teste não atribui nota artística de textura. O caso anterior com bake 512 foi mantido como outra pipeline, sem atribuir sua diferença exclusivamente ao método. TripoSR aqui gera base color, sem mapas novos de normal/metallic/roughness.

A simplificação do melhor caso reduziu **319.266 → 6.384 triângulos (98%)**. A distância foi 0,86% → 0,87% e o F-score permaneceu próximo. A revisão por vistas e o Unity complementam esse número; não se conclui que 6 mil triângulos sejam o orçamento ideal para todo jogo. A variante intermediária tem 31.926 triângulos.

Refinar a silhueta do caso 512 aumentou IoU frontal de **92,13% → 93,05%**, com limite de deslocamento e sem mudar conectividade. Distância 3D passou de 1,48% para 1,47%. É um ganho frontal pequeno, não uma reconstrução nova das costas ou profundidade.

Verificação real em Unity 6000.3.0f1 com URP: importação FBX, arrays, materiais, prefab, collider e renders. O controle original com defeito é mantido como reprovação esperada; a referência limpa é a entrega procedural. Os relatórios distinguem integração de limpeza superficial.

| Caso Unity | Triângulos | Compatibilidade de importação | Limpeza superficial |
|---|---:|---|---|
| ground_truth | 714 | Não | Não |
| ground_truth_clean | 214 | Sim | Sim |
| sg_best_low | 6.384 | Sim | Sim |
| sg_best_medium | 31.926 | Sim | Sim |
| sg_three_quarter | 319.266 | Sim | Não |
| sr_three_quarter_neural | 96.468 | Sim | Não |
| sr_three_quarter_vertex | 96.468 | Sim | Não |
| sr_three_quarter_vertex1024 | 96.468 | Sim | Não |

[Resumo completo da validação Unity](<C:/Users/arthu/OneDrive/Documentos/Codex/forge3D-ai/data/research-2026-10-11/unity-validation.json>). Os testes não medem frame time de um jogo ou comportamento final de física.

O prefab com três LODs usa realmente as malhas de 319.266, 31.926 e 6.384 triângulos, com níveis forçados e renderizados. O collider de caixa foi conferido por limites e raycast. A malha alta ainda tem duas faces de área quase zero; as reduzidas passaram a inspeção de limpeza. A altura de saída neural é cerca de 1,90 m e precisa ser ajustada ao uso: a normalização do benchmark não resolve escala física automaticamente. Pacote portátil para URP: [sg_best_lod.unitypackage](<C:/Users/arthu/OneDrive/Documentos/Codex/forge3D-ai/data/research-2026-10-11/unity-results/sg_best_lod.unitypackage>).

### Limites do teste

Durante a execução foram encontrados dois problemas de infraestrutura: Numba/rembg tentou criar cache no ambiente instalado somente leitura; o cache do experimento foi redirecionado ao workspace. O bake de vértices também reteve uma referência RNA de cor através de mudanças de modo no Blender, produzindo UnicodeDecodeError. Um wrapper de pesquisa passou a salvar o nome da camada antes da mudança de modo, e a mesma preparação concluiu. O código do produto não foi alterado; o problema encontrado permanece documentado para uma correção futura. A documentação Blender confirma a invalidação de referências a dados de malha ao mudar de modo. [Blender: memória e mudança de modo](https://github.com/blender/blender/blob/main/doc/python_api/rst/info_gotchas_crashes.rst).

Uma cadeira e uma execução por configuração não sustentam superioridade para toda uma biblioteca. A referência foi conhecida e usada no alinhamento e seleção do melhor caso: essa escolha é um oracle experimental, não um seletor automático aplicável a qualquer imagem. Detalhes pequenos ainda ficam sujeitos ao ruído de amostragem. Os dois modelos locais não representam as versões comerciais atuais de Tripo/Meshy.

Os métodos de textura usam UVs e formas de amostragem diferentes. Mesmo no controle com dimensões iguais, aparência precisa de inspeção, não de uma conclusão baseada no número de pixels. Não foram testados personagens deformando, rig, normal-map bake high→low, distribuição comercial dos outputs ou um jogo completo com orçamento de GPU.

## Workflow recomendado para o Forge3D e Unity

1. **Definir o uso:** objeto rígido ou deformável, peças móveis, câmera final, silhueta, medidas e orçamento de cena. Não escolher um limite de triângulos universal para todos os projetos.
2. **Escolher o método pela forma:** procedural para objetos construídos por regras; gerador neural para bases mais livres; fotogrametria quando o objeto existe e há captura adequada.
3. **Preparar referência:** objeto inteiro e isolado, alpha revisado, perspectiva moderada, iluminação difusa. Para móveis, conferir furos e separação das pernas. Não reaplicar remoção automática a uma boa máscara sem necessidade.
4. **Validar geometria antes do material:** quatro vistas com material neutro, wireframe, proporções, componentes, aberturas e verso. Testar poucas alternativas controladas em vez de aumentar todos os parâmetros simultaneamente.
5. **Produzir malha de jogo:** preservar high-poly; simplificar e comparar silhueta. Fazer retopologia quando edição ou deformação exigirem. Separar partes móveis e definir pivôs. Assar detalhes em mapas somente quando existir correspondência high/low adequada.
6. **Preparar material:** base color sem luz excessivamente embutida, normal/metallic/roughness quando realmente gerados ou criados. TripoSG nesta instalação não gera PBR. Conferir canais de textura e shader na iluminação do jogo.
7. **Importar e validar:** FBX com material configurado no Unity, ou GLB por importador compatível. Conferir escala, normais, tangentes, UV e prefab. Para GLB, registrar nome e versão do importador. [Unity glTFast](https://docs.unity3d.com/Packages/com.unity.cloud.gltfast@6.15/manual/ImportEditor.html), [UnityGLTF](https://github.com/KhronosGroup/UnityGLTF).
8. **Verificar na cena:** LODs conforme tamanho na tela, collider simples apropriado e teste na câmera final. Medir frame time, memória de texturas e draw calls no dispositivo alvo. Um collider de caixa e um LODGroup de um nível são controles de integração, não uma estratégia final. [Unity: LOD Group](https://docs.unity3d.com/6000.0/Documentation/Manual/class-LODGroup.html).

### Referências de entrada para tentar

Para criar uma imagem de conceito destinada a um prop rígido, descrever construção e contorno: “single wooden chair game prop, four clearly separated legs, two horizontal back slats, complete object, three-quarter product view, diffuse neutral lighting, plain background, no text”. É um ponto de partida, não um prompt testado em gerador de imagens nesta rodada. Conferir visualmente o número de pernas e as aberturas antes de reconstruir.

Para multiview, fotografar/renderizar o **mesmo objeto** em frente, lados e costas, com proporções e detalhes constantes. Modelos específicos aceitam esse condicionamento; juntar quatro imagens em uma colagem para um modelo single-view não ativa capacidade multiview. [Tripo: multiview](https://developers.tripo3d.ai/en/docs/generation-multiview-to-model/standard), [Meshy: instruções](https://www.meshy.ai/tutorials/multi-view-image-to-3d).

### Próxima rodada com maior potencial

Comparar workflow nativo ComfyUI TRELLIS.2 e Pixal3D em ambiente isolado, começando com uma imagem e refinamento moderado. Registrar sampling, decode, remesh, UV e bake separadamente: chegar ao sampling não comprova que o export completo caiba em memória. Há issues de OOM no remesh e consumo elevado de RAM em multiview. [PR nativo](https://github.com/Comfy-Org/ComfyUI/pull/14718), [issue de remesh](https://github.com/Comfy-Org/ComfyUI/issues/15996), [issue multiview/RAM](https://github.com/Comfy-Org/ComfyUI/issues/16620).

Ampliar o conjunto para pelo menos objetos sólidos, alças/furos, partes finas e materiais distintos, com seeds repetidas e uma parte reservada para avaliação. Separar seleção de parâmetros dos objetos usados no resultado final. Incluir tempo humano de correção e teste na cena Unity. Benchmarks perceptuais publicados são úteis, mas precisam ser complementados por contratos do asset e sua estrutura real. [3DGen-Bench](https://github.com/3DTopia/3DGen-Bench).

## Evidências e reprodução

- [Métricas geométricas](<C:/Users/arthu/OneDrive/Documentos/Codex/forge3D-ai/data/research-2026-10-11/geometry_metrics.json>)
- [Manifest das nove inferências iniciais](<C:/Users/arthu/OneDrive/Documentos/Codex/forge3D-ai/data/research-2026-10-11/manifest.json>)
- [Calibração da amostragem](<C:/Users/arthu/OneDrive/Documentos/Codex/forge3D-ai/data/research-2026-10-11/metric_calibration.json>)
- [Controle de texturas 1024](<C:/Users/arthu/OneDrive/Documentos/Codex/forge3D-ai/data/research-2026-10-11/texture_control.json>)
- [Seleção experimental](<C:/Users/arthu/OneDrive/Documentos/Codex/forge3D-ai/data/research-2026-10-11/selection.json>)
- [Cadeira procedural limpa GLB](<C:/Users/arthu/OneDrive/Documentos/Codex/forge3D-ai/data/research-2026-10-11/fixture/ground_truth_clean.glb>)
- [Cadeira neural reduzida GLB](<C:/Users/arthu/OneDrive/Documentos/Codex/forge3D-ai/data/research-2026-10-11/optimized/sg_best_low/model.glb>)
- [Verificação no Unity](<C:/Users/arthu/OneDrive/Documentos/Codex/forge3D-ai/data/research-2026-10-11/unity-validation.json>)
- [Galeria por quatro vistas](<C:/Users/arthu/OneDrive/Documentos/Codex/forge3D-ai/data/research-2026-10-11/galeria.html>)
- [Comparação visual neutra](<C:/Users/arthu/OneDrive/Documentos/Codex/forge3D-ai/data/research-2026-10-11/comparacao.png>)

Scripts: [create_fixture.py](<C:/Users/arthu/OneDrive/Documentos/Codex/forge3D-ai/docs/research/2026-10-11-modelagem-3d/create_fixture.py>), [clean_fixture.py](<C:/Users/arthu/OneDrive/Documentos/Codex/forge3D-ai/docs/research/2026-10-11-modelagem-3d/clean_fixture.py>), [run_experiments.py](<C:/Users/arthu/OneDrive/Documentos/Codex/forge3D-ai/docs/research/2026-10-11-modelagem-3d/run_experiments.py>), [evaluate_geometry.py](<C:/Users/arthu/OneDrive/Documentos/Codex/forge3D-ai/docs/research/2026-10-11-modelagem-3d/evaluate_geometry.py>), [postprocess_experiments.py](<C:/Users/arthu/OneDrive/Documentos/Codex/forge3D-ai/docs/research/2026-10-11-modelagem-3d/postprocess_experiments.py>), [texture_control.py](<C:/Users/arthu/OneDrive/Documentos/Codex/forge3D-ai/docs/research/2026-10-11-modelagem-3d/texture_control.py>), [render_aligned.py](<C:/Users/arthu/OneDrive/Documentos/Codex/forge3D-ai/docs/research/2026-10-11-modelagem-3d/render_aligned.py>), [blender_safe_pipeline.py](<C:/Users/arthu/OneDrive/Documentos/Codex/forge3D-ai/docs/research/2026-10-11-modelagem-3d/blender_safe_pipeline.py>), [verify_research.py](<C:/Users/arthu/OneDrive/Documentos/Codex/forge3D-ai/docs/research/2026-10-11-modelagem-3d/verify_research.py>), [UnityResearchValidation.cs](<C:/Users/arthu/OneDrive/Documentos/Codex/forge3D-ai/docs/research/2026-10-11-modelagem-3d/UnityResearchValidation.cs>), [run_unity_validation.ps1](<C:/Users/arthu/OneDrive/Documentos/Codex/forge3D-ai/docs/research/2026-10-11-modelagem-3d/run_unity_validation.ps1>)

Não foram alterados o backend/frontend do Forge3D nem os pesos instalados. Scripts de pesquisa e um projeto Unity descartável foram criados para esta investigação. As recomendações que extrapolam a cadeira são identificadas como recomendações apoiadas na documentação e nos relatos, não como resultados medidos.
