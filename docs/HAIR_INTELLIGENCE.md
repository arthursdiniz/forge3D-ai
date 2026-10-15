# Reconstrução de cabelo — uso e evidências

Abra **Cabelo 3D** na barra superior (`http://127.0.0.1:8000/#hair`). Selecione um modelo salvo, mantenha Automático inicialmente e clique **Analisar cabelo**. A referência original é reutilizada; também é possível enviar PNG/JPG/WEBP de até20MB. O modo aceita imagens opacas: a máscara de cabelo vem da segmentação semântica local.

Revise a máscara, rosto e scalp estimado. Se o detector não encontrar um rosto seguro, abra **Revisar regiões**, marque os dois cantos na imagem ou preencha E/T/D/B em porcentagens. Analise novamente. Polígonos permitem corrigir cabelo e proteger acessórios/pele. Referências e regiões ficam em cache e são vinculadas ao modelo; mudar imagem, câmera ou regiões exige nova análise.

Confira **Scalp estimado**, marque **Conferi máscara, rosto e scalp** e clique **Refinar somente cabelo**. Compare frente, diagonal, lado e costas, com textura e com iluminação das normais reais. Use **Cabelo isolado**, Wireframe e Texturas. Aprove ou reverta no painel. Para exportar, selecione a versão em Modelagem → **Export to Unity**. O modelo anterior permanece na biblioteca; nenhuma aprovação sobrescreve seus arquivos. Ao escolher uma versão de cabelo texturizada ou transformada, uma nova reconstrução usa a fonte retida identificada no painel; a versão derivada continua salva.

Vistas adicionais de lado/costas devem ser imagens reais. Informe a caixa do crânio em cada imagem, em porcentagens, para registrar a observação. Sem registro, a imagem é guardada para revisão e não altera a geometria. Esses alinhamentos são estimativas revisáveis; não fornecem espessura física nem anatomia oculta verdadeira.

## O que mudou

Pipeline independente `backend/hair`: UNet/MobileNet de sete classes, detector anime já existente, Depth Anything V2 Small, scalp local, diagnóstico de volume, campo radial da cabeça existente, curvas-guia e massas fechadas com UVs. Perfis de franja anime são triangulares; outros perfis são elípticos/assimétricos. Raspado e curto rente não recebem pontas. Volume, lados, topo, traseira, comprimento, curvatura e espessura alteram geometria.

O reparo acrescenta HairBaseVolume/HairClumps com materiais próprios. Cabelo fundido é preservado, porque uma máscara frontal não autoriza cortar uma superfície craniana. A base acompanha por dentro cabelos já volumétricos; em regiões achatadas, a expansão é limitada pelo suporte capilar observado e por uma hipótese traseira pequena. Raízes tocam a base. Sobreposições deliberadas são registradas, não eliminadas por Boolean/fill holes. Não há regeneração do corpo, suavização global ou fechamento indiscriminado de buracos.

Três candidatos de largura de mechas são renderizados. A seleção busca menor distância entre contornos, condicionada à ausência de regressão do próprio contorno (tolerância de arredondamento de0,0001pixel), sobreposição frontal, proteção facial, massas fechadas e profundidade/base fixas. Se nenhum passa, o original é mantido. Não é um índice universal de fidelidade. A traseira sem referência permanece de baixa confiança. Cores novas são medianas dos pixels de cabelo; mapas, UVs e normais originais são preservados. O módulo não cria texturas detalhadas de fios nem rig.

## Resultado medido em13/10/2026

Hardware: RTX4060,8188MiB,driver595.97; i5-12400F,32GBRAM. Runtime existente Torch2.5.1+cu124/Torchvision0.20.1+Python3.12, sem atualização de driver/bibliotecas principais. Dois checkpoints públicos novos somam105.647.175bytes; licenças/revisões/hashes estão em `models/hair/manifest.json`. Inferência offline, modelos carregados sequencialmente, sem offload. [Pesquisa e licenças](HAIR_RESEARCH_20261013.md).

Caso principal escolhido pelo usuário: Kageyama, fonte323051d419ba4e47a4f421fd25e31d5f, referência1214×1295. O detector falhou no rosto renderizado; a caixa facial foi conferida visualmente `[.454,.10,.546,.18]`. O cabelo craniano já tinha volume; o defeito principal era a ausência de algumas mechas/franja como objetos próprios. A textura e a reconstrução anteriores continuam com defeitos visíveis no rosto/corpo.

| Diagnóstico real | Antes | Depois |
|---|---:|---:|
| Sobreposição com máscara capilar da referência, registro facial/frontal |0,695040|0,708517|
| Distância média entre contornos em câmera1024px |7,5246px|5,6369px|
| Triângulos originais |54.162|54.162, erro máximo0|
| Geometria nova |—|1.872triângulos,3mechas e base fechadas|
| Pixels faciais protegidos cobertos na vista frontal |—|0|

Essas máscaras são estimativas semânticas, não anotações de ground truth. O ganho frontal é modesto e localizado; não demonstra fidelidade completa do penteado ou reconstrução do verso.

Fluxo real pela API: análise8,515s + reconstrução/vistas30,407s =38,922s. Pico neural PyTorch224,72MiB alocados/304MiB reservados; working set máximo observado nessa análise1528,89MiB. O monitor separado mediu VRAM total de1758MiB na análise e1735MiB na reconstrução, incluindo desktop/navegador/outros aplicativos. Exportação é medida separadamente e não está incluída nesses38,922s.

Candidato final `d95557822c0b486d8a622218e4eb9810`; exportação `4f3fa73d1b9a411c864e867217d2dce0`. Arquivos em `data/assets/<id>`. Evidências em `data/hair-upgrade-20261013/measured-results.json`, `live-delivery-final.json`, `unity-validation.json`, imagens antes/depois, `hair_geometry.json` e `geometry_export_validation.json`. GLB/FBX/OBJ foram exportados e reimportados de verdade. Unity6000.3.0f1 conferiu3materiais,56.034triângulos, canais finitos, escala/eixo vertical, shaders URP/Standard e preservação dos vértices/normais/UVs do original dentro de1e-5. Sem teste de animação/gameplay.

Hinata foi o controle. A proposta cobriu27pixels faciais protegidos e foi rejeitada: modelo anterior mantido. Os testes A–F de curto/raspado/fluffy/franja/longo/fundido são geometria sintética controlada; não são validação neural universal desses estilos. Os testes neurais reais são os arquivos de Hinata e Kageyama. Foram testados também cancelamento, nova tentativa, isolamento/wireframe, recuperação de contexto e interface em1440px/390px.

Depois da revisão independente,229testes passaram e o build TypeScript/Vite passou. Foram corrigidos normais novas no eixoX, máscaras fracas que causavam erro, ancestralidade de versões texturizadas/transformadas e seleção de candidatos com contorno pior. Nova execução neural/geométrica de Kageyama confirmou os mesmos canais e diagnósticos; GLB/FBX/OBJ também foram reimportados em um caso real com orientaçãoX. A prova Unity anterior continua aplicável ao candidato padrão, cujos vértices, faces, UVs, normais e mapas permaneceram iguais. Unity no eixoX não foi repetido.2098/2098arquivos originais permaneceram com SHA256 iguais. [Revisão, decisões e limitação menor adiada](HAIR_FINAL_REVIEW_20261013.md).

## Limites e próxima melhoria prática

Uma imagem não determina cabelo oculto, raízes, partições internas ou espessura real. O scalp elipsoidal, direção das mechas e classificação por silhueta são hipóteses geométricas auxiliadas por redes de imagem; não há rede treinada para reconstrução3D universal de cabelo. A segmentação foi treinada para anime, exigindo correção manual em cabelo realista/acessórios/oclusões. Caudas presas, partições internas e penteados complexos podem exigir edição de curvas no Blender; não há detecção confiável específica dessas estruturas. Não se promete converter cabelo fundido volumoso em raspado apenas acrescentando superfícies.

O contato raiz/base e a proteção de pixels frontais não certificam ausência de interseções com anatomia oculta; confira vistas laterais/traseiras e a malha. Há uma limitação menor na interface: para editar o alinhamento de uma vista adicional reaberta do cache, reenvie a mesma imagem. A imagem e seu alinhamento salvo continuam disponíveis para análise.

A alternativa mais prática para maior fidelidade é fornecer frente/lado/costas consistentes, revisar as regiões e terminar as mechas independentes no Blender quando necessário. A RTX4060 comportou os pequenos estágios com folga; neste caso, falta informação e modelo especializado, não mais resolução/passos. SAM3 gated e pipelines pesados/serviços pagos não foram instalados. See-through2.5D não foi apresentado como malha3D.

## Recuperação local dos recursos

Esta máquina já contém `.venv-hair` e os checkpoints. A API principal continua independente de NumPy/Torch/Blender importados pelo subsistema. Se recursos ou runtime estiverem ausentes, os modos anteriores permanecem disponíveis e a reconstrução capilar fica indisponível. A preparação de um ambiente novo deve usar Python3.12 local em `.venv-hair` e os caminhos de bibliotecas existentes de `.venv-sg`,`.venv-ai`,`.venv`, sem alterar esses ambientes; o download público está em `scripts/setup-hair-resources.py`. A disponibilidade exige prova real offline/geométrica/de exportação em `models/hair/validation.json`; instalar pesos não equivale a validação.
