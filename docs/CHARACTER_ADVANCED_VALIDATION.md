# Personagens avançados — validação de 11/10/2026

O modo **Hunyuan3D 2mini → Avançado** está disponível no aplicativo local. Gera dois candidatos reais com seeds42/43, conserva RAWs e permite escolha humana. Usa 50 passos, guidance5, FP16, encoder DINO518 nativo e extração384³. O preparo conserva a imagem mascarada em resolução original antes do encoder. A correção do TripoSR também orienta corretamente a superfície extraída.

Caso de teste: `data/test-inputs/hinata-shoyo-reference-20261011.png`, SHA256 `5003a9a4c73a99d72902fd6f732de211d37aa62754d0ec1162c08a5fef6fa454`. Hardware confirmado antes da implementação e novamente na validação: RTX4060/8188MiB, driver595.97, i5-12400F e31,82GiB RAM. Inferências CUDA locais, sem serviço pago, sem offload e sem pesos restritos. O usuário autorizou expressamente o teste pessoal local sob a licença Tencent.

## Diagnóstico por etapa

| Etapa | Evidência e decisão |
|---|---|
| Imagem | Referência1024×1536 com alpha real; o corpo inteiro estava presente. Alpha muito fraco amplia o bbox de23,21–1000,1510; bbox confiante é247,25–788,1475. Preservamos o arquivo e a máscara; o enquadramento por si não explica a anatomia. |
| Reconstrução | TripoSR já produz rosto/mãos/cabelo deformados antes da textura. TripoSG512 e seeds/guidance alternativos aumentam detalhe/amostragem e fragmentos, sem demonstrar solução anatômica suficiente. Hunyuan-mini gerou torso, roupas, membros e cabelo mais coerentes neste caso. |
| Extração | O adaptador TripoSR usava orientação oposta à densidade positiva no interior. Repetição mantém exatamente posições e conjuntos de triângulos, invertendo o volume RAW de−0,0113867 para+0,0113867. Correção `gradient_direction=ascent`, com regressão esférica pela convenção upstream. |
| UVs/material | UVs existentes e mapas TripoSR2048 são reais e finitos; a aparência incorreta já existe na previsão neural. Hunyuan não gera textura nativa. UVs editáveis são adicionadas pelo Blender; opção frontal projeta a referência sobre superfícies visíveis, com costas/oclusões neutras. |
| Visualizador/normais | Materiais usam culling normal; faces internas causavam a aparência oca. A operação antiga Normais também orientava patches separados pelas costuras UV. Corrigida usando geometria temporária apenas para decidir flips; posições e pares posição/UV por face preservados por teste Blender real. Sem DoubleSide para disfarçar. Textura desligada mostra material neutro e restaura a cor original ao ligar. |
| Exportação | Quatro perfis/candidatos passaram FBX→reimportação em Blender. O pacote real da interface passou importação Unity6000.3.0f1/URP17.3, textura1024, UVs/normais, escala1,5m e prefab. |

## Ablações reais

Tempo de geração dos ensaios TS/SG inclui IA e preparação/QA384 inicial. HY256/384 simples mede subprocesso IA; o lote avançado inclui dois candidatos, preparo, UVs, limpeza limitada, refinamento, projeção e cinco renders384. Não comparar esses tempos como se tivessem exatamente o mesmo escopo.

| Provedor/variante | Triângulos RAW | Tempo (s) | Pico PyTorch (MiB) | Observação |
|---|---:|---:|---:|---|
| TripoSR Quality corrigido |57126|43,00|3114,5|Mesma geometria; orientação corrigida. |
| TripoSR Character90% |56968|46,54|3114,5|Enquadramento não corrigiu anatomia; mais componentes. |
| TripoSG Balanced/seed42 |109440|83,64|4225,0|Geometria neutra, sem cor nativa. |
| TripoSG Quality512/seed42 |444118|88,26|4666,0|Mais fragmentos que256; sem melhora suficiente de rosto. |
| TripoSG Quality/seed7 |447460|95,13|4665,5|Alternativa real preservada. |
| TripoSG Quality/seed1234 |459470|82,90|4665,2|Alternativa real preservada. |
| TripoSG Quality/guidance4 |445302|81,93|4666,0|Ablação real, sem adotá-la como solução anatômica. |
| Hunyuan-mini256/seed42 |114932|48,02 (IA)|4182,2|Forma coerente; fechado; detalhes simplificados. |
| Hunyuan-mini384/seed42 |259824|91,09 (IA)|4644,1|Detalhes de superfície mais densos; maior número de ilhas. |
| Avançado384×2 protótipo |259520/261652 finais|214,39|4644,1|Dois candidatos preservados; escolha humana. |
| Avançado384×2 pela interface |259520/261652 finais|260,60|4644,1|4min21s; dentro dos3–5min desejados. |

Pico reservado PyTorch5160MiB (5,04GiB). Pico total `nvidia-smi` na repetição7305MiB (7,13GiB), incluindo desktop/outros programas,123 amostras. Alocado PyTorch4644,1MiB (4,54GiB). Não houve OOM. Mesmas seeds repetiram os RAWs exatamente:42=`876cab359037b0acb49e81bdc5e0627ef954997b33bb1458326be3d4a3445e9b`,43=`be71c521c40dbdd307dae80d037f3585c77acfe9ee87904a2252b4a9c186a93a`. Tempo varia com CPU/desktop e processamento adicional.

## Comparação visual e integridade

No aplicativo, **Comparar qualidade → Hinata** oferece frente, ambos os lados, costas e3/4, com materiais originais e geometria neutra. Foram gerados50 renders768 reais de cinco variantes. As imagens de Blender são double sided: orientação/culling também são investigados no visualizador WebGL e por medidas; não atribuir correção anatômica ao ajuste de faces.

Contato geral: `data/character-advanced-20261011/validation-evidence/hinata-before-after.png`. Cinco vistas completas: `hinata-five-views-textured.png` e `hinata-five-views-clay.png` no mesmo diretório. Renders neutros usam luz/enquadramento comparáveis por eixo frontal; os materiais/projeções conservam suas próprias cores/iluminação da imagem. Nenhum render foi produzido por IA de imagem ou usado para alterar a referência.

Melhora observada: cabelo com volume mais coerente, menor ruído no torso/roupa, braços/pernas mais regulares e número10 legível na projeção frontal. Rosto e dedos continuam simplificados; não há geometria facial precisa nem rig. Costas são inferidas; não há prova de fidelidade ao desenho traseiro ausente. A projeção tem costuras e alinhamento aproximado nos lados e não remove luz/sombra da referência.

Refinamento opcional conserva faces, altura e profundidade. Deslocamento limitado a3% da altura, strength0,45; sobreposição frontal2D: seed42 de84,87%→89,16%, seed43 de81,00%→86,67%. Esses números **não são notas de anatomia, identidade ou fidelidade3D**. Reverte quando não melhora o contorno. Limpeza remove somente fragmentos ≤32faces e extensão≤0,6% da altura; sem remesh, smooth ou fill-holes.

Candidato1:259520faces,1componente,20quase degenerados,3bordas/1aresta não manifold; defeitos expostos nos relatórios. Candidato2:261652faces,2componentes,25quase degenerados,0bordas/0arestas não manifold,volume positivo. Pequeno componente de64faces foi preservado por exceder o limite conservador. Normais explicitamente armazenadas nos GLBs são finitas e não nulas; alguns diagnósticos de normais geométricas de vértices no Blender são zero junto a triângulos quase degenerados e constam do relatório, sem ocultação.

Fluxo real selecionou candidato2 → Low Poly20% → altura1,5m → ZIP/FBX. Resultado52330triângulos,0degenerados,0bordas/0não manifold,fechado/externo,UVs/normais finitas,2componentes (52296+34faces). Decimation preservou corpo/cabelo/roupas nas vistas avaliadas, mas não equivale a retopologia de animação. Os RAWs próprios de cada seed permanecem preservados, nunca substituídos pela versão reduzida. Cinco vistas neutras adicionais da versão otimizada estão em validation-evidence/optimized43.

## Provas do fluxo e revisão

- Lote real `050aa8e345fb4260b679b851e8c8d3ab`; candidatos `00ba7940a4ee49baa7d1f7aff3b13bd5` / `b474d0636fab40b3ab295b7bd0bb76b7`.
- Redução `2296cc495ab044648a80ff51f3142bbb`; escala `238a6262ea0547fe817210aee947c450`; export `e1f431f373db43db865c418b62301122`.
- `data/character-advanced-20261011/ui-flow-verification.json`: fontes/RAWs/linhagem e relatório Unity real. Projeto de QA isolado `data/UnityCharacterAdvancedValidation`; batchmode/nographics, sem cena renderizada/gameplay/rig.
- ZIP baixado pela própria interface: `data/character-advanced-20261011/Forge3D-Hinata-Advanced-Unity.zip`; hash igual ao export original: `d127aedda977568806a8dadb1755745f4e03c024bc4279d6c5884191e9899bf9`. Inclui LICENSE/NOTICE Tencent.
- Desktop1600×1000 e mobile390×844: candidato2 selecionável, wireframe/textura/neutro, Original mantendo seed43, redução/escala/download. Cinco vistas×dois materiais carregadas, sem overflow horizontal ou erros de execução no percurso de comparação final. Context Lost é esperado ao desmontar Canvas; conexões recusadas ocorreram somente durante reinício explícito da API.
- Revisão independente única: duas falhas importantes reproduzidas RED→GREEN e corrigidas (Original atravessava lote e trocava seed43→42; publicação parcial no cancelamento). Publicação final ocorre em transação SQLite conjunta do lote e dos dois candidatos, inclusive checagem de cancelamento antes do commit.
- Comparação inicialmente podia mostrar o mesmo baseline nos dois painéis ou conservar albedo indisponível ao trocar caso. Seleção inicial e estado de aparência corrigidos e verificados no navegador.

## Decisões e limites práticos

1. Reusar recursos SG instalados por junctions, evitando baixar pesos duplicados; dados ativos permanecem neste workspace.
2. Hunyuan pessoal autorizado, em ambiente separado. Tentativa de cópia integral lenta preservada em`.venv-hy-copy-partial`; ambiente final usa dependências SG fixadas em leitura e extras próprios. Não modificar SG por pip. Essa dependência local de caminho deve ser considerada ao mover a instalação.
3. Novo modo troca o prior de reconstrução e conserva candidatos; não representa treinamento/fine-tuning da IA. Offload não foi necessário, portanto não foi habilitado nem alegado validado.
4. Projeção frontal e ajuste de contorno são opcionais, com limites explícitos. Não gerar costas coloridas inventadas nem usar suavização/fechamento para parecer correto.
5. Problemas de seleção/publicação e aparência de comparação foram tratados como importantes por afetarem o resultado escolhido e a avaliação pedida. Revisão não julgou a legalidade da licença, fidelidade de superfícies invisíveis, outro hardware ou gameplay; o escopo da entrega permanece local, hardware confirmado e importação técnica.

Há melhora visual/técnica demonstrada neste Hinata, mas **não foi atingido um personagem anatomicamente preciso, texturizado por inteiro e pronto para animação a partir de uma imagem**. Mais passos/resolução não fornecem informação inexistente. Alternativa prática: referência coerente frontal/lateral/traseira em pose estável, reconstrução que realmente aceite múltiplas vistas ou modelagem guiada no Blender, correção manual de rosto/mãos, retopologia/UVs e rig. Integração multi-view não faz parte desta entrega; Hunyuan2mv permanece indisponível. TRELLIS/TRELLIS2 não foram baixados pelo orçamento/requisitos oficiais de GPU/plataforma; SF3D/SPAR3D continuam gated, sem instalação.

Fontes primárias: [Hunyuan3D-2 oficial](https://github.com/Tencent-Hunyuan/Hunyuan3D-2), [pesos mini públicos](https://huggingface.co/tencent/Hunyuan3D-2mini/tree/main/hunyuan3d-dit-v2-mini), [licença Tencent](https://github.com/Tencent-Hunyuan/Hunyuan3D-2/blob/main/LICENSE), [TripoSG oficial](https://github.com/VAST-AI-Research/TripoSG), [TRELLIS2 oficial](https://github.com/microsoft/TRELLIS.2). Pesos mini fixados emf90a0f7df7d5e6f71109cf333f6a95a0ae3194a6, código emf8db63096c8282cb27354314d896feba5ba6ff8a; SHA256 safetensors3cc66f3bea33e4062b7dbc875ffe1d70c4888914aec3e91b60f94e9bd01b522b.

Verificação adicional no asset TripoSR antigo: a versão de Normais pré-correção4abc344f30fb42b7b20cfa110383b1f7 foi preservada como ensaio de QA falho. A versão corrigidaaa70f55494cc422fa10acb0a1b89e334 mantém57126triângulos, posições/UVs, volume+0,0113867067 e0bordas/não manifold. O original51764b49c97743508f5391760330dc1f mantém seu arquivo e orientação anteriores; novas gerações já usam o extrator corrigido.

Verificação final:71testes passaram (inclui Blender real com costurasUV),build6,32s passou; warning de bundleViewer932KB e depreciaçãoAnyIO sem falhas. Original Hinata conferido por hashes, referência intacta e snapshot final em release-source; resultados em release-verification.json. Nenhum menor pendente da revisão independente.
