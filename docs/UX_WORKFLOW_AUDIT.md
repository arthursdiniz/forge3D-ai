# Auditoria da reformulação do Studio

Data: 15/10/2026. Requisitos: attachment f74f5081-85ce-4a1b-99ce-8dfce2a5f99f. Plano e decisões em `docs/superpowers/plans/2026-10-15-unified-studio.md`.

## Funções existentes e novos destinos

| Componente/capacidade existente | Destino | Comportamento preservado |
|---|---|---|
| UploadPanel | Modelar + avançadas / Geração | Referência simples; providers, recorte, seeds, preparação e gerações técnicas continuam disponíveis |
| CharacterPanel | Avançadas / Geração | Análise CPU, edição e interpretação humana; nunca simulada pelo fluxo automático |
| QualityPanel | Avançadas / Geração | Candidatos, seeds e referências adicionais |
| ModelSetupPanel | Configurações locais | Status real, instalação/configuração existente; nenhum download automático novo |
| Inspector | Avançadas / Geometria e exportação | Métricas, originais, operações e formatos |
| CharacterTools | Avançadas / Geometria e exportação | Simetria, escultura, game-ready e validações revisadas |
| Candidates | Avançadas / Geometria e exportação | Candidatos existentes selecionáveis |
| TextureWorkspace | Avançadas / Textura, rosto e semântica | Métodos e materiais manuais completos, mapas e diagnóstico |
| FaceDetailWorkspace | Mesmo painel de textura | Registro, região, proteção, métricas e versões |
| SemanticWorkspace | Mesmo painel de textura | Máscaras/categorias, correções e alinhamento opcionais |
| HairWorkspace | Avançadas / Cabelo 3D | Análise, referências e reconstrução volumétrica opcionais |
| Comparison | Avançadas / Comparação | Dados e avaliações anteriores; sem fabricar novas notas |
| Viewer | Área dominante, Vistas/Exibição | Orbit, albedo, luz, textura, grade, wireframe, enquadrar; seleção de superfície nos módulos técnicos |
| Library | Biblioteca vertical | Todos os ancestrais/versões com miniaturas reais; análises/exportações não viram modelos |
| Import/export | Biblioteca/Texturizar + exportação contextual | Upload seguro de malha/sidecars, GLB/FBX/OBJ/Unity, originais imutáveis |
| Worker/GPU manager | Internos aos dois fluxos | Fila serial, subprocessos possuídos, cancelamento, preflight e medições reais |

O módulo anterior foi preservado em `frontend/src/LegacyWorkspace.tsx`; a nova entrada compõe o Studio e reutiliza seus componentes técnicos. APIs antigas permanecem disponíveis. A geração técnica avançada mantém suas opções legadas explícitas; a ação principal **Gerar modelo 3D** sempre usa `texture_output=geometry_only`.

## Contratos e decisões

- `POST /api/workflows/model`: valida imagem, escolhe somente um provider disponível e perfil validado, prepara e reconstrói, verifica/publica geometria. Não dispara textura. Categoria é preparação declarada, sem classificação automática fictícia. Rápido automático prioriza o perfil rápido do TripoSR; outros perfis priorizam compatibilidade local dos provedores de geometria com seed. Isso não é um ranking de fidelidade visual.
- `POST /api/workflows/{source}/texture`: uma tarefa pública. Referências normalizadas, alpha preparado, UV/material/base neural ou projeção qualificada; detector/segmentação de retrato quando compatíveis, registro automático conservador, composição com classes/oclusão e proteção de pixels, rejeição se métricas piorarem, vistas e publicação final. Estilo não é substituído por uma cópia integral da referência.
- O parser instalado distingue sete classes de retrato. Não é parsing corporal, identidade facial ou reconstrução anatômica. Registro ambíguo mantém a base e registra a omissão; máscaras e candidato permanecem inspecionáveis. Nenhuma flag de revisão humana é fabricada.
- Referências adicionais são observações reais. MV-Adapter recebe a frontal; outras vistas podem contribuir nas etapas locais compatíveis e são diagnosticadas individualmente. Costas sem rosto compatível não recebem uma transferência de retrato inventada.
- Retry cria outra tarefa e preserva a anterior. Cache de base exige identidade da fonte/referências/opções, código/manifestos e todos os arquivos de saída intactos. Não reutiliza uma inferência parcial. `request_key` vinculado a conteúdo evita duplicação de uma solicitação.
- Biblioteca consulta todo o histórico, agrupando versões pelo ancestral real. Miniaturas e modelos são arquivos reais, sem ilustrações geradas apresentadas como resultados.
- Visualização usa os eixos do asset. O ajuste de câmera não deve substituir a vista escolhida após o carregamento; o novo viewer remove a animação inicial de Bounds.

## Evidência em andamento

Baseline: 216 arquivos de fonte e 3424 arquivos de 124 pastas de assets em `data/ux-upgrade-20261015/baseline.json`; cópias e hashes preservados. Suíte anterior267 testes; primeira suíte nova274 passou em40,86s. Testes ampliados de contrato, registro, cache e publicação11 passaram em3,77s. Não interpretar fixtures de orquestração como inferência real.

GPU reconfirmada: NVIDIA GeForce RTX4060,8188MiB, driver610.88. Geração real de Hinata pela interface: `57a3da2b44d640b8b54c083e64a5ca6b`, Hunyuan-mini balanced seed42,114932triângulos, inferência40,89s, pico PyTorch4182,2MiB; evento completo82,625s. O metadado `total_seconds` anterior ao último ajuste ainda registra72,66s de reconstrução; o relatório de estágios registra o total com Blender. Textura `method=none`, `generated=false`, nenhuma tarefa de textura encadeada.

Conceitos completos e primeiras capturas estão na pasta QA. Comparação visual inicial: três áreas no topo; duas colunas; lateral de28vw até420px; viewer dominante; opções avançadas fechadas. Marca SVG existente preservada mesmo quando o conceito ilustrativo mostra outro símbolo. Critérios finais, capturas e limites serão registrados após os testes restantes.
# Fechamento da revisão

As três superfícies mantêm rascunhos; StudioApp mantém as travas e estados de envio. A revisão de contexto cobre seleções/comparações/importações e callbacks avançados tardios. Catálogo conserva lotes e resolve a origem individual de candidatos. O novo `backend/workflows/model_checkpoint.py` permite retomar o pós-processamento sem repetir uma reconstrução íntegra. Avisos por vista rejeitada e exportações vinculadas a fonte/pipeline foram conferidos por regressões. Evidências finais: `docs/UX_STUDIO_VALIDATION.md` e `data/ux-upgrade-20261015/review/`.

