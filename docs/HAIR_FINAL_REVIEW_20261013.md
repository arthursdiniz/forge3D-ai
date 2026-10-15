# Revisão final do módulo capilar

Uma revisão independente, somente leitura, inspecionou o código e as evidências salvas. Não encontrou problemas críticos. Quatro problemas importantes foram reproduzidos, corrigidos em uma única rodada e cobertos por regressões RED→GREEN:

1. Normais novas no eixo X: guardar normais antes de alterar os vértices evita invalidar o cache e rotacioná-las duas vezes. O teste reconstrói ambas as orientações e verifica as normais após exportação/reimportação GLB.
2. Máscaras com menos de 32 pixels: resultado `manual_required` agora preserva motivo, parâmetros, máscaras e imagens para revisão, sem acessar camadas inexistentes. Dois casos reais do fluxo de análise, com respostas neurais controladas, passaram.
3. Descendentes texturizados/transformados: `metadata.hair` é reconhecido independentemente do tipo de tarefa; análise/refinamento usam a fonte retida. Fonte ausente é rejeitada antes de enfileirar. Quatro casos API passaram. O navegador reproduziu a chamada para a versão incorreta e confirmou a chamada corrigida para a fonte retida, com explicação visível. Esse teste de navegador usa um descendente sintético em memória e intercepta a chamada, sem escrever tarefas.
4. Contorno pior apesar de maior IoU: candidatos precisam manter a distância de contorno dentro de 0,0001 pixel do valor anterior, tolerância de arredondamento do diagnóstico. Quando nenhum passa, a publicação mantém o original. A ponta espúria controlada elevou IoU de 0,9 para 0,97561, mas piorou contorno de 1,0243 para 2,0918 pixels e agora é rejeitada.

Suíte final: **229 testes passaram**, com aviso preexistente de depreciação AnyIO/Starlette. Build TypeScript/Vite passou, com aviso preexistente sobre tamanho do chunk Viewer. Logs de RED, GREEN e suíte completa estão em `data/hair-upgrade-20261013`. Não houve segunda revisão.

## Problema menor adiado

Ao restaurar uma análise com vistas adicionais, as caixas salvas são recuperadas, mas os campos para editá-las aparecem apenas depois de reenviar a imagem correspondente. A recuperação da imagem e o registro anterior continuam funcionando; para alterar o alinhamento, reenviar a mesma imagem é a solução atual.

## O que a revisão não certificou

- Ausência de penetração em toda a anatomia oculta: contato raiz/base e proteção frontal não comprovam folga tridimensional interna. Exige inspeção lateral/traseira/manual.
- Fidelidade universal de penteados ou do verso oculto, sem referência/ground truth.
- Execuções novas de GPU, Unity e navegador pelo revisor: ele inspecionou as evidências; essas execuções foram feitas pelo implementador.
- Alterações anteriores de Texture Fidelity, fora do baseline desta revisão capilar. A suíte completa inclui suas regressões, mas isso não equivale a revisão especializada desse código.

## Decisões e custos

- Redes compactas públicas MIT/Apache para segmentação/profundidade relativa: cabem no ambiente Windows/8 GB sem atualizar o núcleo. Custo: o verso e a espessura continuam hipóteses; sistemas completos de fios/camadas não foram instalados.
- Preservar cabelo fundido e adicionar base/mechas independentes: protege rosto, corpo, UVs e materiais. Custo: cabelo antigo e defeitos fundidos permanecem, com sobreposições intencionais e sem retopologia/rig.
- Medir máscaras observadas/projetadas e triângulos originais: evita declarar um índice universal de identidade. Custo: referências fracas exigem correção e revisão humana.
- Base abaixo de cabelo já volumétrico; expansão de áreas achatadas limitada ao suporte capilar observado: evita faixas artificiais e inflação global. Custo: a melhora frontal pode ser localizada; vistas reais e acabamento no Blender continuam necessários.

O trabalho permanece no checkout local existente, com planos, evidências e originais preservados. A instrução do usuário de trabalhar continuamente e preservar o estado anterior prevalece sobre menus genéricos de integração Git; nenhum commit, push, merge ou limpeza do trabalho anterior foi realizado.
