# Personagens avançados — especificação autorizada

Pedido: corrigir anatomia deformada/aparência oca/textura distorcida, investigar cada etapa e demonstrar melhora no Hinata salvo em data/test-inputs/hinata-shoyo-reference-20261011.png. RTX4060 confirmada:8188MiB, driver595.97; i5-12400F/31,82GiB RAM. Orçamento desejado:180–300s por geração. Preservar modos, arquivos originais e biblioteca atual.

Primeiras evidências: a imagem tem alpha real e a preparação preserva o personagem; baseline TripoSR Quality57126faces é fechado/consistente, mas volume negativo. O adaptador scikit-image produz orientação oposta à convenção de faces do upstream. UVs finitas, PNG2048 real e mesma geometria antes/depois; anatomia/cores incorretas já vêm da reconstrução. O app ativo usa este workspace e não encontra o TripoSG já validado em C:/Projetos/forge3d-ai.

Escopo: corrigir orientação na origem com regressão analítica, reaproveitar os recursos existentes de TripoSG sem substituir data da instalação ativa, comparar preparo/TS/SG e seeds/parâmetros reais. Selecionar configuração somente após renders neutros/texturizados de frente, dois lados e costas e medidas reais de extração, integridade e export. Sem suavização/fill-holes automático; limpeza opcional conserva detalhes e versões.

Modo avançado deve usar os parâmetros que a ablação comprovar úteis, conservar candidatos e permitir escolha humana. Não apresentar score técnico como avaliação de anatomia. Uma opção de textura por referência, se validada, deve informar cobertura somente das superfícies visíveis; não alegar textura aprendida/PBR ou costas observadas. Se esses caminhos não demonstrarem avanço suficiente, deixar a capacidade claramente experimental e explicar o limite, com alternativa prática.

Outros modelos: avaliar fontes oficiais/memória/licença, sem instalar gated/pagos. Nenhum download grande, toolkit/driver ou aceite de licença especial automático. Offload apenas se necessário e comprovado. Antes da entrega: testes/build, browser→API→inferência→GLB→FBX e Unity real; fotografia/renders originais e RAW conferidos por hash.
