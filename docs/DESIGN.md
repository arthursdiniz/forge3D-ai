# Forge3D AI — design aprovado pelo pedido do usuário

Ferramenta pessoal Windows: imagem → inferência neural local → GLB → Blender → FBX/ZIP Unity. Sem API de geração remota, créditos, login de aplicativo ou SaaS.

## Arquitetura
- React/TypeScript/Vite + React Three Fiber/Drei: upload, pré-processamento, viewport, biblioteca e inspector.
- FastAPI em 127.0.0.1: SQLite, armazenamento por UUID, uploads validados e fila persistente.
- Um executor serial lança um subprocesso de IA em ambiente separado; o processo termina e libera CUDA ao finalizar. Não inicializar PyTorch na API.
- TripoSR oficial com revisão fixada. Rede proibida em inferência, pesos e encoder DINO carregados de diretórios locais. Marching cubes na CPU se a extensão CUDA não estiver disponível; rede neural permanece em CUDA.
- Blender portátil para baking de cores de vértices em textura UV, operações, exportação FBX e reimportação de validação. Preservar original e produzir versões imutáveis.
- Exportação inclui Models, Textures, Editor, README_IMPORT e manifest. Editor Unity configura material URP/Built-in e prefab.

## Critérios
Inferência real comprovada, metadados de hardware/VRAM/tempo/hash, GLB válido e visível, textura existente, FBX reimportado com geometria/UV, ZIP baixável, teste real Unity se licença disponível. Estados sem percentuais artificiais. Falha explícita e recuperável em OOM, timeout ou dependência ausente.

## Decisões
SF3D preferido, mas HEAD dos pesos devolveu 401; não aceitar licença/autenticar pelo usuário. TripoSR é a alternativa autorizada. SPAR3D exige ~7 GB no modo reduzido, sem folga atual; Hunyuan completo texturizado excede o orçamento. Não investir em compilação CUDA customizada inicialmente. Presets ajustam resolução de extração real; otimizações não equivalem a retopologia para animação.

## Autonomia
O pedido fornece escopo e manda implementar imediatamente, sem aprovações técnicas entre fases. Por isso o design e plano são registrados para revisão sem criar etapas adicionais de confirmação. Fonte editável no workspace da conversa; implantação em C:\Projetos\forge3d-ai, preservando .agents existente.
