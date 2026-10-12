# Fidelidade v3 — melhoria autorizada em 2026-10-10

Objetivo: melhorar saída real do Forge3D local para Unity, especialmente o personagem anime já usado pelo usuário. Referência de corpo inteiro, atual TripoSG/seed42 com mãos/cabelo imprecisos e sem cor. Preservar app, pesos, biblioteca, RAW, latentes e benchmarks históricos. Usuário pediu continuidade autônoma; execução inline, sem novos pesos grandes/serviços pagos/licenças.

Preferência recebida: **forma e proporções** são o maior problema. Refinamento lateral opcional da silhueta frontal por máscara real, com deslocamento máximo de 3% da altura, preservando Y/Z, faces e peças separadas. Medir IoU do contorno antes/depois apenas como métrica 2D. Aceitar somente melhora estrita; rejeitar empate ou piora. Texturização foi adiada para manter a prioridade em geometria.

## Projeto e testes

1. Extração real512³, mesmos pesos/seed/preparo50passos. Primeiro ablação isolada contra256³; habilitar Quality somente após sucesso GPU, comparação de detalhes e exportação. Não representar polígonos adicionais como conhecimento novo. Encoder448 será só ablação se necessário; permanecer224 por padrão sem evidência de benefício.
2. Limpeza conservadora opcional em subprocesso CPU no ambiente AI; Blender renderiza e exporta a nova versão. Excluir faces degeneradas/duplicadas e fragmentos de no máximo 32 faces E 0,6% da extensão. Preservar UVs, grupos de normais, peças maiores e RAW. API valida os limites. Testar acessórios, costuras UV, normais e reindexação após remoção.
3. Preparar alpha real 512 e câmera frontal estimada com escala uniforme baseada na altura. Rasterização com profundidade; ajuste lateral por correspondência de intervalos do contorno. Linhas que juntariam partes separadas são ignoradas. Máscara obrigatória. Matemática de projeção de cores foi testada como infraestrutura interna; não há recurso de textura SG oferecido ao usuário.
4. UI no layout existente: Quality SG validado, limpeza e refinamento explícitos, nova versão e relatório. Medição pertence à versão medida: transforms posteriores a removem para evitar resultados desatualizados. API impede opções sem implementação. Biblioteca e exportações preservadas.
5. Benchmark final em duas referências oficiais (bule/cadeira) e personagem usado pelo usuário, mantendo o robô e os benchmarks anteriores. Nove variantes reais e quatro vistas neutras; sem escores perceptuais automáticos. Testes, FBX roundtrip, Unity URP geometry-only, Playwright desktop/mobile e revisão independente.

## Registro

- [x] Ablação 512 e linha base preservadas; VRAM/tempo registrados. Encoder 448 não apresentou benefício claro; padrão 224 mantido.
- [x] RED/GREEN limpeza, silhueta e normais; nove FBXs e renders reais inspecionados.
- [x] Quality validado em três referências; geração, limpeza, refinamento, redução, escala e export pela UI.
- [x] FBX/Unity e regressão: 51 testes, UI desktop/mobile, Unity URP real, relatório de limitações e PROGRESS.

Decisão: trabalhar primeiro com capacidades e pesos instalados. Hunyuan multi-view tem implementação oficial, mas pesos/licença e execução local permanecem pendentes; não enviar várias vistas ao modeloSG de imagem única. Reavaliar depois desta entrega com dados concretos.

Decisão: projeto fonte não é Git. Preservar snapshot/hash de código e dados em fidelity-v3, sem git init/commits improvisados. Skills customizadas GPU/Blender/QA lidas no projeto instalado. Docs de bibliotecas e APIs serão verificadas antes de usar parâmetros novos.
