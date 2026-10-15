# Forge3D AI

Ferramenta pessoal de imagem para modelo 3D, com TripoSR, TripoSG, Hunyuan-mini e Hunyuan multiview nativo na GPU local, Character Intelligence editável, candidatos por seeds, correções seletivas e exportação GLB/FBX/OBJ/ZIP para Unity.

## Iniciar
Aplicativo ativo neste workspace: `C:\Users\arthu\OneDrive\Documentos\Codex\forge3D-ai`. A instalação anterior em `C:\Projetos\forge3d-ai` fornece recursos SG reaproveitados; sua biblioteca foi preservada. Abra `Start-Forge3D.bat`. O navegador abre `http://127.0.0.1:8000`; frontend e API são servidos pelo mesmo processo local. Não há reinstalações no início normal.

Para instalar em uma máquina limpa: Python 3.10–3.12, Node.js 22+, Git e driver NVIDIA compatível com CUDA 12.4. Execute `Setup-Forge3D.bat` uma vez, com internet. Precisa de aproximadamente 12 GB livres para ambientes, cache e pesos; sem Docker/WSL. TripoSR usa licença MIT. SF3D foi avaliado, mas os pesos exigem aceite/acesso pessoal no Hugging Face; não foi instalado.

## Usar o Studio

O menu principal agora tem **Modelar**, **Texturizar** e **Biblioteca**.

1. **Modelar:** envie uma imagem, escolha tipo/qualidade e clique **Gerar modelo 3D**. O resultado contém geometria; não inicia texturização automaticamente.
2. **Texturizar:** selecione o modelo gerado ou importe uma malha, adicione a referência e clique **Gerar textura**. Preparação, geração, análise compatível, refinamento conservador e validações ficam em uma tarefa. A geometria original é preservada.
3. **Biblioteca:** busque modelos, compare versões e exporte GLB, FBX, OBJ ou pacote Unity. Ferramentas de rosto, máscaras, cabelo, geometria, candidatos e configuração continuam no diálogo de opções avançadas.

Leia o [guia passo a passo do Studio](docs/STUDIO_GUIDE.md), com exemplos, controles e solução de erros. [Arquitetura, evidências e limites da reformulação](docs/UX_WORKFLOW_AUDIT.md).

## Fluxo técnico legado nas opções avançadas
1. Arraste PNG/JPG/WEBP (até 20 MB), preferindo um único objeto inteiro em fundo limpo.
2. Escolha TripoSR para textura, TripoSG para geometria sem textura ou **Hunyuan3D 2mini → Avançado** para dois candidatos com seeds, contorno conservador opcional e projeção frontal opcional (costas neutras). O lote Hinata real levou4min21s na RTX4060 de8GB; sem offload. Compare os dois candidatos antes de reduzir/exportar. Detalhes e provas em [CHARACTER_ADVANCED_VALIDATION.md](docs/CHARACTER_ADVANCED_VALIDATION.md). TripoSG oferece Balanced (50 passos/256³), Quality (50 passos/512³) quando validado neste hardware e seed; no TripoSR, selecione Fast (128³/512 px), Balanced (256³/1024 px) ou Quality (320³/2048 px). Balanced/Quality TripoSR consultam cores neurais por texel; Fast interpola cores de vértices. Mais amostras refinam o mesmo campo neural, sem garantia de melhor reconstrução.
3. Escolha o preset de preparação, fundo automático/alpha/manter/remover e recorte opcional. Confira a referência e entrada efetiva em “Original × entrada efetiva”. Presets só controlam enquadramento real.
4. Clique Generate. Aguarde inferência e processamento Blender. Uma tarefa pesada roda por vez, inclusive quando scripts de benchmark estão executando. Os estágios vêm do processo real.
5. Examine o GLB com orbit/zoom/pan, grid, wireframe, textura e iluminação. A biblioteca persiste ao fechar o navegador. “Comparar qualidade” inclui as referências anteriores e Hinata antes/depois em cinco vistas, baseline, modos TripoSR/TripoSG e dois candidatos avançados; compare forma com material neutro; notas 1–5 são manuais e salvas localmente.
6. Opcionalmente use Limpeza conservadora e, no TripoSG/Hunyuan com máscara do objeto, Refinar silhueta. O ajuste frontal é limitado; examine lado e costas. Depois ajuste altura em metros, centralize, recalcule normais ou decime. Cada operação cria nova versão; Original retorna à geração do candidato selecionado; a relação com o lote é preservada. As versões RAW/PROCESSED/GAME OPTIMIZED ficam preservadas. Os valores antes da decimation são estimativas. Resultados e limites em docs/FIDELITY_V3_VALIDATION.md.
7. Clique Export to Unity. Quando terminar, baixe o ZIP, FBX, GLB ou OBJ. O ZIP contém importer de Editor e textura quando há textura neural ou projeção frontal; o menu Tools/Forge3D/Import selected asset (ID) cria o prefab. Renomeie cada pasta importada para manter vários assets e importe cada ZIP uma vez; depois reutilize os prefabs.

## Arquivos e processos
- `data/assets/<id>/`: upload original, source.png, prepared.png, original.glb/raw_generation.glb, scene_codes.safetensors, textured_generation.glb quando disponível, model.glb, texturas, relatórios e process.log.
- `data/quality-upgrade/`: baseline imutável, ablações, benchmark improved, renders comparison, avaliações reviews.json e prova do fluxo. Não apagar para atualizar.
- Export: `Forge3D_Unity.zip`, `Forge3D_Asset/Models/Model.fbx`, `Textures/`, `Editor/`, README e manifest.
- `models/`: pesos, configuração local DINO e u2netp. Nunca são baixados durante inferência.
- `logs/`: instalação, backend e validação. `data/forge3d.sqlite3`: histórico persistente.
- A API não inicializa CUDA. O executor serial lança um subprocesso de IA e o encerra após cada geração, liberando VRAM. Cancelamento/timeout só afetam o subprocesso da tarefa.
- Fechar a aba não encerra o backend. Para encerrar use Stop-Forge3D.bat; tarefas interrompidas são registradas ao reiniciar. Não remova data/models para atualizar a fonte.

## Inferência e limitações
O modelo é o TripoSR oficial, com código fixado na revisão `107cefdc244c39106fa830359024f6a2f1c78871` e pesos `5b521936b01fbe1890f6f9baed0254ab6351c04a` (SHA256 registrado em models/manifest.json). Duas adaptações documentadas evitam compiladores CUDA extras: marching cubes de scikit-image na CPU e configuração DINO local. A rede neural roda em CUDA com pesos originais, sem simulação ou geração por servidor externo. Checkpoint é carregado com `weights_only=True`.

Inferência bloqueia conexões de rede por processo e define os modos offline Hugging Face/Transformers. O teste específico dessa implementação é registrado em docs/QA.md; isso não significa que a instalação ou todos os softwares do computador estejam offline.

Balanced/Quality usam UV xatlas e consultas do campo neural por texel, preservados no Blender. Fast usa bake de vértices com transferência sRGB/linear corrigida, mas menor precisão em tons escuros. Os motores atuais não geram mapas neurais de normal, metallic ou roughness nem removem iluminação de forma aprendida. Game Ready oferece bake real de normal high→low; metallic0 e roughness0,65 são constantes declaradas. Reflexos/sombras da referência podem aparecer na cor e na forma. Lados invisíveis são estimados, detalhes finos podem ser fundidos. Sem rig, auto-rigging, animação ou retopologia. Decimation pode distorcer UVs/detalhes; original preservado. Arquivo válido não comprova qualidade artística para todo asset.

SPAR3D/SF3D permanecem indisponíveis por acesso gated aos pesos; TripoSG foi baixado, verificado e testado na RTX4060: cerca de8 GB de pesos, pico4,13 GiB alocados, três referências/FBX aprovados. Gera somente forma; UV/material neutro são pós-processamento. Veja docs/TRIPOSG_VALIDATION.md. Hunyuan2mini foi autorizado sob licença Tencent, instalado separado e validado localmente; gera forma, não textura neural/rig. Perfil avançado384³×2 tem pico PyTorch4,54GiB, totalGPU7,13GiB incluindo desktop. Hunyuan2mv está habilitado em Balanced256/50passos com2–4vistas distintas nomeadas. CPUoffload não foi necessário e permanece desligado. Presets Character/Stylized controlam enquadramento; Character Intelligence adiciona revisão de pose/regiões, medidas2D e template corporal opcional sem fingir condicionamento semântico da rede. Pesquisa e limites em docs/QUALITY_AUDIT.md e docs/MODELS.md.

URP é prioritário no importer quando ativo no seu projeto; Built-in usa Standard. O pacote não instala URP nem altera seu render pipeline. FBX reimportado é validado em geometria, UVs e escala; materiais são associados pelo script de Editor, não presumidos do FBX.

## Desenvolvimento e verificações
`.venv\Scripts\python.exe -m pip install -r requirements-dev.txt` e `.venv\Scripts\python.exe -m pytest tests/test_core.py -q --basetemp=cache\pytest-local`.

Em frontend: `npm run dev` para Vite; `npm run build` para tipos/build. O backend local deve estar na porta 8000. Não execute instalações pip simultaneamente no mesmo venv.

Consulte docs/PROGRESS.md, docs/QA.md e docs/MODELS.md para resultados e pendências reais.


## Quality Mode e personagens — upgrade12/10/2026

Character Intelligence local permite revisar pose/landmarks, medir diferenças e aplicar correções seletivas. QualityMode preserva1/3/5candidatos reais; Avançado2 antigo continua disponível. Hunyuan3D2mv está validado em Balanced com2–4vistas reais. GameReady inclui orçamento explícito, baking CPU de normal high→low e exportações GLB/FBX/OBJ/Unity.

[Uso, medições, limitações e provas](docs/MAJOR_QUALITY_20261012.md). Setup CPU adicional: `powershell -ExecutionPolicy Bypass -File scripts/setup-major-quality.ps1`; multiview público opcional com `-DownloadMultiview`, sob a licença Tencent. SPAR3D continua bloqueado por acesso/runtime não validados; nada gated é baixado automaticamente.
### Texturização independente

Abra **Texturização IA** para escolher uma malha antiga ou importar GLB/GLTF/OBJ/FBX estático. Projeção de vistas reais e MV-Adapter SDXL criam novas versões com geometria verificada; o neural foi executado offline na RTX 4060 de 8 GB com seis vistas conjuntas. Modelagem/exportação continuam sem exigir esses pesos. Consulte [uso, medições, licenças e limites](docs/TEXTURE_ENGINE.md). Setup separado: `Setup-TextureEngine.bat` (download apenas quando explicitamente autorizado).

O **Face Detail Workspace** permite preparar a referência original e o render3D, revisar máscaras/alinhamento e corrigir somente rosto ou outra região. Cria uma nova versão preservando o restante da textura, UVs e geometria. Veja [passo a passo, comparações e limites](docs/TEXTURE_FIDELITY.md). Para imagem opaca na textura global, selecione **Remover fundo**; alpha exige máscara real.


### Cabelo 3D

Reconstrução capilar local com máscaras, scalp revisável e massas/mechas independentes, preservando o modelo anterior. Abra **Ferramentas avançadas → Cabelo 3D** e siga o [guia de uso, resultados e limites](docs/HAIR_INTELLIGENCE.md). A melhoria demonstrada é localizada; regiões ocultas continuam estimadas.

### Semântica e Reference Fidelity

Em **Ferramentas avançadas → Textura, rosto e semântica → Semântica e Reference Fidelity**, revise máscaras reais de retratos e categorias manuais do corpo para restringir a transferência por classe, preservar áreas protegidas e criar versões locais. Veja [como usar, comparações, licenças e limites](docs/SEMANTIC_TEXTURING.md). A proposta SDXL para áreas ausentes é opcional; não corrige anatomia nem garante aparência das costas.
