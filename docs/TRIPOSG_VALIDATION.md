# TripoSG local — resultado do download e validação

2026-10-09: download/teste autorizado pelo usuário e concluído. Pesos oficiais [VAST-AI/TripoSG](https://huggingface.co/VAST-AI/TripoSG/tree/2c1c516d22d58db486a058d98d31bb6177344e06), MIT, cerca de 7,95 GB (7,40 GiB), em `C:\Projetos\forge3d-ai\models\triposg`. Os três safetensors foram comparados com SHA256 do publisher; tamanhos e hashes de todos os arquivos estão em download_manifest.json. Código [upstream](https://github.com/VAST-AI-Research/TripoSG) fixado em fc5c40990181e2a756c4e0b1c2f4d6b5202faf8c, sem edição do vendor.

## O que está disponível

Na tela de geração, selecione **TripoSG · geometria**. TripoSR continua o default com textura. TripoSG oferece somente Balanced: 50 passos, guidance7, tokens2048, dense7/hierarchical8 (256³), seed42 por padrão, FP16 CUDA, decoder chunk8192. Gera forma; Blender adiciona UV Smart Project e material neutro, sem inventar textura/PBR. O botão Texturas fica desabilitado para esses assets. RAW, latentes, modelo processado e versões otimizadas são preservados.

## Medições reais na RTX 4060 8 GB

| Referência | RAW / processado (tris) | Subprocesso IA | Pico alocado / reservado PyTorch | FBX |
|---|---:|---:|---:|---|
| Bule | 256.152 / 256.152 | 59,20 s | 4.225 / 4.414 MiB | Aprovado |
| Robô | 409.676 / 409.674 | 54,84 s | 4.225 / 4.322 MiB | Aprovado |
| Cadeira | 274.722 / 274.722 | 54,02 s | 4.225 / 4.318 MiB | Aprovado |

Tempos incluem preparação/carregamento/IA, mas não Blender ou Unity. Pico PyTorch não inclui desktop/viewport e outros processos. Houve também uma inferência inicial do bule em128³, sem contar uma tentativa anterior que falhou por dependência ainda sendo instalada. Todas as gerações concluídas usaram pesos reais locais e sockets bloqueados. Não foi necessário CPU offload; esse modo permanece não validado e não exposto pela UI. Não foi provocado OOM.

Observação visual das referências e quatro vistas neutras: o bule conserva alça aberta, bico e tampa com superfície menos marcada pelos reflexos que TripoSR; ainda há ondulações no corpo. O robô tem cabeça/olhos mais regulares, mas dedos e antenas continuam imprecisos. A cadeira conserva pernas separadas e encosto almofadado; detalhes do entalhe são simplificados. Essas são observações humanas, sem escore automático ou garantia para outras imagens. O cenário testado contém uma cadeira isolada, não uma cena com vários objetos.

Integridade: bule um componente; robô/cadeira nove, incluindo componentes pequenos. RAW do robô tem duas arestas não manifold; o Blender elimina duas faces ao importar/exportar. Há 8–20 triângulos de área quase zero no RAW. Sem limpeza automática das partes soltas; avalie antes de colisão, edição ou animação. FBX aprovado significa preservação de geometria/UV/escala, não topologia ideal ou fidelidade artística.

## Preparação e comparação

O canvas512 recebe alpha existente ou u2netp em CPU sobre branco. O processador DINO oficial redimensiona para256, recorta224 e normaliza ImageNet. `prepared_encoder.png` mostra o RGB correspondente ao crop efetivamente consumido; JSON registra shape/hash. Ocupação padrão5/6; API/CLI recusam valores acima de87,5%, e slider termina em87%, evitando corte adicional pelo centro do encoder. BRIA/RMBG não foi baixado; isso difere da remoção de fundo upstream.

Em **Comparar qualidade**, selecione TripoSG e use **Geometria neutra em ambos**. As cinco variantes possuem quatro vistas. Camera/luz giram com o eixo frontal do provedor; dimensão/energia da área são escaladas para manter a iluminação comparável. Os modelos gerados permanecem intactos. O preparo segue cada provedor (TripoSR cinza/512, SG branco/224); a comparação avalia pipelines completos, não isola apenas a arquitetura. Albedo não está disponível no SG. Notas1–5 são sempre manuais.

## Ambiente e continuidade

`.venv-sg` é independente de `.venv-ai`: Torch2.5.1+cu124/Torchvision0.20.1+cu124 foram copiados para diretórios próprios; dependências SG instaladas sequencialmente. Python3.12.10, Diffusers0.32.2, Transformers4.46.3, Accelerate1.2.1, PEFT0.13.2, NumPy1.26.4. `pip check` passou; requirements-triposg-lock.txt registra versões completas. Não houve instalação de driver, toolkit CUDA ou compilador.

TripoSG usa a extração hierárquica real do upstream com scikit-image. `diso/DiffDMC` é opcional e importado incondicionalmente upstream; o adaptador bloqueia explicitamente esse caminho flash ausente, sem substituir a geração. `_decode` conserva o decoder neural com consultas em chunks8192. O contexto CUDA termina junto com o subprocesso. SR/SG/benchmarks compartilham o mesmo lockGPU.

Download retomável: `.venv\Scripts\python.exe scripts\download-triposg.py`. Benchmark: `.venv\Scripts\python.exe scripts\benchmark-triposg.py`; ele reutiliza resultados existentes, sem sobrescrever RAW. `--refresh-clay` recalcula somente as comparações neutras. O início normal do aplicativo não baixa nada.

Evidências no projeto instalado: `models/triposg/download_manifest.json`, `models/triposg/validation.json`, `logs/download-triposg.log`, `data/quality-upgrade/triposg/benchmark/<caso>/record.json`, `benchmark/manifest.json`, `comparison/<caso>/*_clay`. A disponibilidade exige ambiente, pesos completos, módulos upstream e prova com revisões/perfil compatíveis. O histórico TripoSR e seu baseline foram preservados.

## Fluxo UI e Unity concluído
Geração pelo botão Generate confirmou provider=triposg, seed42, Balanced único e entrada224px. O bule repetido produziu RAW com o mesmo SHA256 do benchmark; nenhum arquivo original mudou após Low Poly (256.152→51.230tris) e escala1,5m. Pacote API exportado/reimportado e Unity6000.3.0f1/URP17.3 aprovados:51.230tris, alturaY1,5m, UVs/normais/vertices finitos, shaderLit, textura0 e prefab criado. O teste reutilizou um material com albedo TripoSR anterior e confirmou que o importer limpa o mapa ao importar SG. Batchmode/nographics; sem gameplay/render de cena final. Prova em data/quality-upgrade/triposg/flow-verification.json e data/UnityTripoSGValidation.

30 testes passaram (19API/contratos +11preparo/cor/textura/integridade), TypeScript/Vite compilou, revisão independente concluída e correções relidas. Playwright1600×1000 e390×844: seleção SR/SG, controles corretos, wireframe/GLB, três casos×quatro vistas, comparação neutra, sem overflow. Contexto novo depois do restart: zero erros/warnings no console. Browser plugin não estava disponível; QA feita com o Playwright disponível. Build avisa somente do chunk grande do viewer; testes avisam de alias AnyIO depreciado.
