# Texture Engine · entrega local 2026-10-12

Upgrade13/10/2026: [Texture Fidelity e Face Detail Workspace](TEXTURE_FIDELITY.md), com correções de RGB/fusão/normais, máscaras e projeção regional, comparações e medições reais. O conteúdo abaixo preserva a documentação da entrega anterior.

O Forge agora separa modelagem e aparência. A seção **Texturização IA** recebe malhas da biblioteca ou arquivos estáticos GLB, GLTF, OBJ e FBX. Cada processamento cria um job `texture` com origem, referências, logs, mapas, seed, cobertura, medidas reais e comparação geométrica. Os modos anteriores continuam disponíveis; TripoSR ganhou a opção **Gerar somente geometria · texturizar depois**, que evita consultas de cor e atlas neural.

## Uso

1. Abra `http://127.0.0.1:8000/#texture` e escolha uma malha salva. Ou importe um arquivo com seus sidecars locais, até 80 MB no modelo e 150 MB no total.
2. Confira a frente. Modelos TripoSR usam +X; Hunyuan e o padrão glTF usam +Z. O painel detecta os assets conhecidos; modelos importados exigem conferência. Esquerda/direita seguem os lados do personagem em relação à frente definida.
3. Escolha **Projeção de referência** ou **MV-Adapter SDXL**. Projeção aceita frente, costas e lados reais com alpha; partes ocultas ficam neutras. O neural aceita uma referência frontal OU texto, conforme os adaptadores testados. Imagens adicionais não condicionam esse modelo.
4. Escolha atlas 1K, 2K ou 4K. Preservar UVs válidas é o padrão. Mapas normal/AO/MR/emissive/alpha mapeado impedem uma nova UV que exigiria rebake não implementado. Roughness e metallic podem ser ajustados por material; são fatores constantes, não mapas neurais.
5. Gere uma nova versão. Confira Antes/Depois, textura/clay, albedo sem iluminação, wireframe, câmeras, atlas, cobertura, confiança e proveniência. Verde indica referência copiada, azul síntese neural e cinza texels não resolvidos; os valores inteiros estão no mapa de proveniência original.
6. Exporte para URP ou Built-in. O ZIP contém FBX, GLB, OBJ/MTL, PNGs reais, manifesto por material, importador C# e licenças aplicáveis. Copie a pasta para `Assets` e execute o menu Forge3D incluído. A exportação reimporta FBX e compara triângulos em coordenadas de mundo nos três formatos. O importador configura cada slot e valida escala, triângulos, UVs e normais.

## Provedores realmente executados

| Provedor | Resultado local | Condicionamento | Aparência |
|---|---|---|---|
| reference_projection | Funcional | Vistas reais nomeadas | Transferência de cores visíveis; sem invenção de áreas ocultas |
| neural_multiview / MV-Adapter SDXL | Inferência real offline → UV → mesh → exportação | Imagem frontal ou texto + geometria | Albedo sintetizado em seis vistas conjuntas; estilos modificam o prompt |
| advanced_pbr | Desabilitado | Nenhum backend validado | Nenhum mapa neural normal/metallic/roughness/AO anunciado |

O código neural oficial e os pesos foram preservados. O renderer e a fusão dependentes de nvdiffrast/CV-CUDA foram substituídos por câmeras NumPy, OpenGL/moderngl, xatlas e projeção local. Os controles reproduzem seis câmeras nativas Z-up: frente, quatro lados no total, cima e baixo. A rotação só ocorre em buffers temporários; a malha publicada conserva coordenadas, instâncias, winding e triângulos, tolerando duplicação de vértices por UV.

FP16, VAE slicing/tiling e offload sequencial foram testados. O VAE fica fora dos hooks meta porque muda para FP32; o cond encoder recebe seu próprio offload. Hooks preservam os dicionários compartilhados do cache de referência do MV-Adapter. Um ensaio inicial expôs a cópia desses dicionários pelo Accelerate; a correção foi reproduzida e testada em CUDA. O executor serial e o lock de GPU evitam carregar modelagem e texturização ao mesmo tempo.

## Evidências medidas

Hardware confirmado: RTX 4060 **8188 MiB**, driver 595.97; i5-12400F; **34.164.101.120 bytes de RAM**; Windows 11. Runtimes: Python 3.12.10, Torch 2.5.1+cu124, Diffusers 0.32.2, Transformers 4.46.3, Accelerate 1.2.1, NumPy 1.26.4, xatlas 0.0.11, moderngl 5.13.0; Blender 4.5.3 LTS; Unity 6000.3.0f1 e URP 17.3.

| Ensaio real | Inferência | Carregamento + inferência | PyTorch pico alocado | PyTorch pico reservado |
|---|---:|---:|---:|---:|
| Hinata, imagem, seed 44, atlas 1K | 64,69 s | 89,77 s | 3866,8 MiB | 5352,0 MiB |
| Objeto importado, texto, seed 21 | 62,03 s | 83,45 s | 1433,8 MiB | 2280,0 MiB |
| Hinata, API após cancelamento, atlas 2K | 65,49 s | 91,30 s | 3866,8 MiB | 5352,0 MiB |
| Hinata, versão final após revisão, atlas 4K | 64,94 s | 89,67 s | 3866,8 MiB | 5352,0 MiB |

São **20 passos e seis vistas nativas de 512 px**. O exemplo oficial SDXL usa 768; 4K é a resolução do atlas, não geração nativa de detalhes em 4K. Atlases 2K e 4K reaplicados às mesmas vistas reais passaram na identidade e demoraram 4,68 s e 11,862 s, respectivamente. Não são novas inferências. `gpu_monitor.json` registra amostras reais da GPU total, incluindo desktop e outros apps; não equivale ao pico de alocação PyTorch.

A geração final inteira, incluindo carga, fusão 4K e previews, levou **120,969 s**. O monitor total da GPU teve 55 amostras e pico observado de **6884 MiB**, incluindo desktop e outros aplicativos; amostragem não garante capturar cada pico instantâneo. Job final `3b09436697594d489cc9ace821a00f9b`; exportação corrigida `248b6d0e6d76477baf8a59b063dcf40f`. Pacote final: `data/assets/248b6d0e6d76477baf8a59b063dcf40f/Forge3D_Unity.zip`. Metadados e licença da geometria foram preservados; as medidas geométricas antigas ficam separadas das medidas da textura.

Hinata manteve **20.000 triângulos, dimensões, 14 componentes e normal map**. A comparação de triângulos após GLB/FBX/OBJ passou. A cobertura neural foi cerca de **93,5% dos texels ocupados**, com cerca de **6,5% não resolvidos**. Isso não é uma nota de identidade ou fidelidade semântica. O atlas UV original ocupa cerca de 11% da imagem; preservá-lo protege o normal map, com custo de densidade de texels. Não houve remesh, decimation, merge ou fechamento de buracos.

O objeto próprio de dois materiais passou por importação, projeção, inferência por texto, exportação e reimportação. URP e Standard/Built-in conservaram dois slots, normal e AO; foram verificados albedo sRGB, mapas de dados lineares e pixels packed **metallic R=64 / smoothness A=204**, a partir de glTF G/B e fatores. AO glTF R recebe conversão própria para o G do Unity. Alpha/fatores existentes são preservados. Normal maps são tratados como dados, com tangentes Mikk calculadas pelo Unity.

Cancelamento real de subprocesso, nova tentativa concluída, persistência dos jobs, execução offline e preservação do modelo de origem foram verificados. **666 arquivos originais** mantiveram os hashes auditados. TripoSR em geometria-only executou offline, sem consulta de cor/atlas. Testes automatizados incluem winding/instâncias, UVs/overlap, oclusão entre objetos, lados ocultos neutros, materiais/fatores/alpha, entradas inválidas, provedor não validado e cache de offload. Build e navegador desktop/mobile foram executados. O diagnóstico unlit também teve um teste real: agora segue Base Color em vez de escolher o primeiro node de imagem e pintar o normal map como albedo.

Evidências locais em `data/texture-engine-20261012`: `live-flow.json`, `preservation.json`, `object-flow/result.json`, ensaios `neural-hinata-trial1` e `neural-object-text-trial1`, renders `diagnostics/{before,after,clay,unlit}`, montagens `diagnostics/before-after.png` e `diagnostics/all-views.png`. Validação Unity em `data/UnityTextureValidation`.

Evidência final após correções: `delivery-texture-result.json`, `delivery-hinata-result.json`, `final-object-export.json`, `preservation-final.json`, importações `import-formats-final/result.json`, nova validação Unity em `data/UnityTextureFinalValidation` (URP e Built-in, dois materiais e packed PBR). Em `diagnostics-final`, Antes/Clay reutilizam os renders controlados da mesma geometria; Depois/Unlit foram renderizados novamente a partir do GLB final. As montagens `before-after.png` e `all-views.png` correspondem à versão final entregue. O gerador dessas folhas usa Pillow já disponível, organizando os PNGs reais com legendas; não altera a aparência do modelo nem gera imagens por IA.

TripoSR geometry-only foi executado também pela API: job `186fa281a34e4b1ea7fb4cd6c3ef5904`, 8340 triângulos, 4,69 s de inferência e 27,422 s para o job; pico alocado 1866,5 MiB e reservado 2060 MiB. RAW sem `COLOR_0`, sem consulta de cor/atlas; exportação `a1ba524aebb84f968ec5b2b74233da83` passou na identidade GLB/FBX/OBJ.

## Setup, pesos e licenças

`Setup-TextureEngine.bat` prepara um venv próprio que referencia bibliotecas CUDA/core existentes, sem modificá-las. O download só ocorre explicitamente com `scripts/setup-texture.ps1 -DownloadAuthorized`. **Esse parâmetro pressupõe a autorização/licença do usuário**, como registrada nesta conversa; nenhum gate ou aceite de conta foi contornado. A inferência bloqueia rede e usa arquivos locais. Cada recurso tem revisão, bytes e SHA-256; toda inferência verifica os hashes dos pesos. Mudanças no código/recursos invalidam a disponibilidade e exigem revalidação. Os scripts `verify-texture-*.py` registram os ensaios deste caso; seus diretórios são evidências preservadas, não substitua saídas existentes para revalidar.

| Recursos instalados | Revisão | Licença |
|---|---|---|
| SDXL base FP16, ~6,938 GB + configs/tokenizers | 462165984030d82259a11f4367a4eed129e94a7b | [CreativeML Open RAIL++-M](https://huggingface.co/stabilityai/stable-diffusion-xl-base-1.0/blob/main/LICENSE.md) |
| MV-Adapter imagem/geometria, 3.603 GB; texto/geometria, 1.964 GB | 6de4033df6b53366f3c009d22f5ec434bb55e59f | [Apache 2.0](https://github.com/huanngzh/MV-Adapter/blob/main/LICENSE) |
| Código MV-Adapter | 4277e0018232bac82bb2c103caf0893cedb711be | Apache 2.0 |

Total de pesos autorizado próximo de **12,51 GB**, em `models/texture`; manifests separam licença de código e modelo. A licença da geometria continua no pacote quando a origem é Hunyuan. A consulta SD 2.1 respondeu HTTP 401 sem autenticação; não houve uso de espelhos para contornar acesso. [Hunyuan3D-2.1 Paint](https://github.com/Tencent-Hunyuan/Hunyuan3D-2.1) pede aproximadamente 21 GB para textura; [TRELLIS.2](https://github.com/microsoft/TRELLIS.2) foi descartado neste ambiente Windows/8GB pelos requisitos oficiais Linux/24GB. Nenhum WSL, Docker, driver, toolkit ou serviço pago foi instalado. [MV-Adapter oficial](https://github.com/huanngzh/MV-Adapter), [xatlas Python](https://github.com/mworchel/xatlas-python), [offload Diffusers](https://huggingface.co/docs/diffusers/optimization/memory).

## Limites práticos

O rosto, olhos, padrões pequenos e costuras ainda podem perder detalhe ou mudar. As costas são síntese inferida a partir da frente; a iluminação do gerador pode estar incorporada ao albedo. Não há segmentação semântica validada, especialização neural treinada em anime, remoção aprendida de iluminação ou inpainting adicional. A fusão seleciona a observação de maior confiança de ângulo/profundidade para evitar ghosting; padding não equivale a eliminar todas as costuras. Texels sem observação continuam neutros e identificados. Normal/AO/MR vêm da origem; novos mapas detalhados desses canais não são inventados.

Importação é estática, com uma UV, sem rig/animation/morph, extensões obrigatórias ou texture transforms não preserváveis. Sidecars GLTF/OBJ devem usar nomes simples locais, sem caminhos externos; FBX pode remapear basenames para arquivos enviados, sem abrir o caminho absoluto gravado no arquivo, e aceita texturas embutidas. Fatores glTF `normalTexture.scale` e `occlusionTexture.strength` diferentes de 1 são recusados antes da carga/texturização/exportação: faça baking de seu efeito no Blender. Fontes com normal/data/alpha mapeado e UVs inválidas exigem reparo/rebake no Blender. O depth test usa a superfície geométrica, sem ray traversal específico para transparência por material. Built-in Standard tem limites próprios de culling em superfícies de duas faces; para cards/folhas, prefira URP ou um shader próprio. Esses casos não foram apresentados como solucionados.

Para mais fidelidade prática: referências frente/costas/lados na mesma pose, inspeção manual dos mapas e correções localizadas em um pintor 3D. Para detalhe neural nativo maior, falta validar outro perfil/modelo; aumentar o atlas sozinho não resolve. A geometria permanece igual e deve ser aprovada antes desta etapa.

## Arquivos e manutenção

Principais mudanças: `backend/texture_engine/*` (contratos, providers/lifecycle, importação, UV/identidade, controles, neural/fusão, PBR/export/erros), `backend/app.py`, `backend/worker.py`, `backend/schemas.py`, `backend/inference_v2.py`, `blender/import_static.py`, `blender/pipeline.py`, `frontend/src/TextureWorkspace.tsx`, `Viewer.tsx`, `App.tsx`, `api.ts`, `generationOptions.ts`, `styles.css`, `unity/Forge3DImporter.cs`, `scripts/setup-texture.ps1`, download/verificação/diagnósticos e testes Texture/Unity. O inventário com hashes está em `data/texture-engine-20261012/delivery-inventory.json`, incluindo os 17 arquivos auditados, componentes, pesos e evidências. Não há Git nesta cópia local; baseline, SQLite e assets originais foram preservados em vez de inventar commits.

## Revisão final

A revisão independente terminou após uma primeira tentativa impedida pelo limite de uso. Não encontrou Critical. Quatro Important e a imprecisão de métricas reclassificada como Important foram corrigidos em uma única rodada: validação de whitespace OBJ/MTL; caminho real de PNG no OBJ exportado; recusa de fatores PBR não preserváveis; FBX com albedo embutido; métricas/seed de versões sucessivas. Sete novos casos falharam antes das correções; oito testes focados passaram depois e a suíte completa passou com **163 testes**, com um aviso de depreciação Starlette existente. GLTF+sidecars e FBX+PNGs passaram em importações reais, com identidade e originais preservados. O FBX embutido também passou no teste Blender real.

Minor adiado: o rodapé global continua mostrando métricas da seleção de modelagem, enquanto **Mapas e integridade** mostra as medidas corretas da versão de textura selecionada. Consulte esse painel para tempo/VRAM da textura. O relatório independente e os logs RED/GREEN estão em `data/texture-engine-20261012/final-review.md` e `final-regressions-*.log`.
