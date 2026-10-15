# Texture Fidelity + Face Detail Workspace

Upgrade local validado em13/10/2026. Melhora cores e detalhes faciais usando pixels reais da referência, máscaras e alinhamento revisados. Cada execução cria uma versão; não modifica anatomia, UVs ou triângulos. A texturização global e os modos anteriores continuam disponíveis.

## Como usar

1. Abra **Texturização IA** e selecione uma malha com albedo/PBR e UVs válidas. Para o Hinata histórico, prefira criar uma nova textura a partir do **GameReady original**; isso preserva as normais autorais que o pipeline antigo perdia.
2. Na textura global, escolha MV-Adapter SDXL ou projeção de referência. Para imagem opaca, escolha **Remover fundo com u2netp local**; “Usar alpha real” exige máscara existente. Preserve UVs quando houver Normal/AO/Metallic-Roughness. A fusão conservadora mistura cores compatíveis em áreas suaves, preservando bordas e cores conflitantes.
3. No **Face Detail Workspace**, escolha rosto/cabelo/olhos/roupa/personalizada. Esses nomes identificam sua seleção, não segmentação neural automática. Anime tem detector CPU opcional; humano, stylized e objeto usam seleção manual. Character Intelligence pode fornecer regiões da mesma referência, verificadas por pixels e dimensões.
4. Clique **Preparar referência e rosto 3D**. O sistema recupera a maior imagem original na ancestralidade; um upload específico do rosto é opcional e tem prioridade. A ampliação do recorte não inventa detalhe.
5. Arraste as caixas em ambas as imagens. Use zoom, polígonos editáveis, áreas protegidas e pelo menos três pares de pontos na mesma ordem para ajustar o alinhamento. Revise olhos, esquerda/direita, cabelo e limite da roupa. Sugestões fracas do detector precisam de revisão.
6. Escolha materiais editáveis para proteger outros slots. Ajuste intensidade e transição da borda. **Conservador** prioriza superfícies frontais; **Alta fidelidade** aceita superfícies visíveis até60°. Mudar o eixo invalida preparação/revisão. Não há projeção da face na nuca.
7. Mantenha **Reaproveitar vistas anteriores** desligado inicialmente. A opção só funciona quando os seis controles de posição e normal conferem exatamente; usa cores sintetizadas anteriores identificadas nos mapas. Não executa nova inferência ou inpainting.
8. Marque **Revisei o alinhamento…** e clique **Refinar somente a região**. Compare referência/antes/proposta de frente,3/4 e lado com zoom sincronizado. **Aprovar** seleciona a versão corrigida; **Rejeitar** reutiliza a anterior. Todos os arquivos permanecem. Resultado inconclusivo publica o modelo e a procedência anteriores, guardando a proposta separadamente.
9. Exporte GLB/FBX/OBJ/ZIP. Copie a pasta do ZIP para um nome único em `Assets` e execute o menu Forge3D incluído. Reutilize o prefab criado; o pacote conserva licenças da geometria e da textura ancestral.

## Causas comprovadas e mudanças

Os projetores misturavam RGB observado com cinza usando a confiança; agora os dois são independentes. Fusão em luz linear só mistura observações compatíveis e evita borrar olhos/bordas. Confiança zero conserva o sentinel neutro dos modos anteriores.

A cópia Trimesh perdia normais autorais:15.678normais do Hinata mudavam, erro máximo1,8993, embora posições/triângulos continuassem iguais. Clonagem de UV e versões regionais agora preservam os atributos. No novo global, erro máximo de roundtrip foi1,192e-7. Assets históricos não foram sobrescritos ou reparados silenciosamente.

O refino usa câmera ortográfica real, posição/normal/UV/material/primitiva, máscara fonte/alvo e alinhamento afim revisado. Visibilidade compara o plano geométrico e o mesmo triângulo no footprint do pixel, em vez de uma janela de profundidade que admitia camadas ocultas próximas. Alpha e fatores glTF são tratados corretamente; mapas de dados permanecem intactos.

Costuras são diagnosticadas em amostras de vértices duplicados com normais compatíveis; densidade é estimada por centroides de triângulos. Correção opcional limita-se a pequenas diferenças suaves dentro da máscara. Não é diagnóstico de todas as costuras, unwrap adaptativo, blur global ou fechamento de buracos.

## Evidência final

Imagem Hinata1024×1536, face138,8pixels originais,20.000triângulos. A comparação regional parte do **novo global corrigido**. No ensaio final:

| Medida | Antes | Depois |
|---|---:|---:|
| Erro RGB alinhado |0,110098|0,056476|
| SSIM local mascarado |0,306613|0,682660|
| Pixels comparados no render |5.699|5.699|
| Texels alterados na proposta |0|21.565|
| Triângulos |20.000|20.000|
| Pixels externos/alpha/mapas de dados |originais|idênticos|

Erro RGB49%menor; olhos, sobrancelhas e boca mais legíveis. **Restam artefatos no nariz, cabelo, laterais e junções do atlas**, mostrados nas imagens. SSIM/RGB medem correspondência frontal observável, não identidade universal.

Hardware reconfirmado: RTX4060 **8188MiB**, i5-12400F,31,82GiBRAM, Windows11,driver595.97. Sem instalação de driver/WSL/Docker ou alteração dos ambientes core existentes.

| Ensaio real | Tempo | Memória medida |
|---|---|---|
| Global imagem,20passos/6vistas512/atlas4K/seed44 |65,85s inferência;93,28s load+infer |3866,8MiB alocados;5352MiB reservados PyTorch |
| Global texto,objeto com2materiais/seed21/atlas1K |58,8s inferência;78,71s load+infer |1433,8MiB alocados;2280MiB reservados PyTorch |
| Regional final,sem nova rede |24,765s CLI |3294,99MiB working set real;3189,05MiB RSS amostrado da árvore;1447MiB GPU total amostrada |
| Detector anime CPU/offline na referência |1,121s |não usa CUDA |

GPU total inclui desktop/navegador e é amostrada; difere do pico do allocator PyTorch. RAM global não foi medida com monitor válido. Leitura preliminar de4,68MiB media só o launcher e foi descartada; o log foi preservado.

O job regional final pela API levou29,188s incluindo inspeção Blender. O global SDXL utiliza o offload sequencial já validado no módulo independente; não se anuncia execução completa da rede em8GB sem offload. O refino por pixels não carrega SDXL ou uma rede de inpainting.

**191 testes passaram**, com um aviso de depreciação AnyIO/Starlette existente. Build passou, mantendo o aviso Viewer>500KB. Navegador desktop/mobile, arraste, troca de eixo, aprovação/rejeição, cancelamento/nova tentativa e exportação foram exercitados. GLB/FBX/OBJ passaram por comparação de triângulos orientados. Unity6000.3 validou URP/Built-in,20.000triângulos do personagem e24 do objeto, UVs/normais, materiais distintos, albedo sRGB, NormalMap, AO, MR→metallic/smoothness e transparência. Foi teste batchmode/nographics, sem alegar render de gameplay.

Evidências: `data/texture-fidelity-20261013/{hinata-regional-final-footprint,global-image,global-text,object-region,diagnostics-final}`, `final-live-flow.json`, `unity-validation.json`, `final-review.md`, `publish-full.log`, `delivery-inventory.json`. Quatro Important da revisão foram reproduzidos e corrigidos num único ciclo; nenhuma segunda revisão. Tentativas anteriores e falhas do harness permanecem.

Os **1.673arquivos originais de66pastas** mantiveram seus SHA-256. A entrega guarda snapshot de263arquivos de código/documentação,13alterações nos21arquivos previamente auditados, inventário dos módulos novos e todos os ensaios. Sem Git neste diretório, não houve commit/PR; snapshots e logs ficam preservados e ocupam espaço local.

## Modelos avaliados

Instalado apenas o par públicoYOLOv3+HRNetV2 do [anime-face-detector](https://github.com/hysts/anime-face-detector),28landmarks para anime aproximadamente frontal. Fonte98a9fb480fa04bdd96acbe4d98da191a898267f3, pesos285.272.072bytes, revisões/SHA-256 em `models/texture-face/manifest.json`. Código/modelos MIT e componentes Apache2; execução CPU/offline com arquivos locais explícitos e validação de hashes. Nenhuma dependência nova instalada no core; falha/confiança insuficiente conserva seleção manual.

[Anime-Face-Segmentation](https://github.com/siyeong0/Anime-Face-Segmentation) e [SAM2](https://github.com/facebookresearch/sam2) foram avaliados, não instalados/validados. SAM2 tem um caminho Windows que recomendaWSL; o detector mínimo aproveitou bibliotecas existentes. [MVPaint](https://github.com/3DTopia/MVPaint), [Paint3D](https://github.com/OpenTexture/Paint3D) e [MV-Adapter](https://github.com/huanngzh/MV-Adapter) serviram como referências técnicas, sem anúncio de APIs intercambiáveis ou novos provedores. SDXL/MV-Adapter mantêm licenças previamente autorizadas; não houve modelo gated ou serviço pago.

## Limites e decisões

- Pixels originais e máscaras/alinhamento revisados são a base. Detector é auxiliar; segmentação/inpainting não estão implementados. Partes ocultas ou ambíguas conservam a aparência anterior e precisam de referências/revisão.
- UVs/mapas de dados ficam intactos. UV inválida/overlap significativo, atlas>4K, material sem albedo/PBR ou instâncias compartilhadas são rejeitados explicitamente. Baixa densidade facial exige um rebake separado.
- RGB/SSIM são medidas projetadas; aprovação humana continua necessária. Referência<32pixels produz avaliação inconclusiva. Textura não recupera geometria ausente.
- Cache só entra se controles e superfície editável visível conferem. É estimativa neural, não pixel original; fica desligado por padrão porque acrescentou artefatos apesar de melhorar médias.
- `requires_geometry_refinement` do histórico registra perda de atributos de shading, não prova deformação anatômica. Re-texturize o GameReady original para preservar normais. Para forma/costas mais fiéis, a alternativa prática é acrescentar referências reais de frente/lado/costas ou revisar a malha no Blender e retornar à textura.

## Arquivos principais

Projetores `backend/{reference_texture,neural_texture}.py`; `backend/texture_engine/{native,uv,pipeline,contracts,texture_fusion,face_reference,face_detection,region_camera,region_masks,face_projection,face_refinement,texture_metrics,texture_seams,cached_views,region_context,region_routes,providers,cli,jobs}.py`; integração em `backend/{app,worker}.py`; interface `frontend/src/{FaceDetailWorkspace,TextureWorkspace}.tsx` e `styles.css`; testes e scripts de verificação. O inventário final lista arquivos alterados/novos, hashes e preservação dos originais.
