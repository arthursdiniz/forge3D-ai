# Entrega do Forge3D Studio — evidências

15/10/2026. A reformulação reúne **Modelar, Texturizar e Biblioteca**, com ferramentas técnicas opcionais e dois fluxos independentes. O código foi alterado neste checkout; não houve commit, reset, instalação de modelos, troca de driver ou serviço externo novo.

## O que mudou

O visualizador ocupa a maior área da janela; o painel lateral contém a entrada, tipo/objetivo, qualidade e uma ação principal. A Biblioteca usa miniaturas reais e reúne as versões pelo modelo de origem. Seeds, providers, candidatos, interpretação de personagem, geometria, cabelo, máscaras, rosto, UVs, materiais, comparação técnica e configurações continuam nas ferramentas avançadas.

**Modelar** gera geometria sem disparar textura. **Texturizar** usa uma malha existente e coordena preparação, UV/material/base, análise compatível, refinamento conservador, checagem e publicação dentro da mesma tarefa. O fluxo não exige análise/salvamento manual de máscaras. O cancelamento encerra o subprocesso da tarefa; tentativas e originais permanecem salvos. Uma solicitação repetida com a mesma chave/conteúdo não repete a inferência. O formulário conserva a chave após perda da resposta de rede e bloqueia submissões sobrepostas antes do próximo render do React.

O cache de retry exige relatório de identidade geométrica aprovado, arquivos íntegros e vínculo à fonte, referências, opções, código e recursos locais. A reutilização neural também verifica SHA dos pesos. Uma falha indispensável interrompe a tarefa; uma etapa opcional pode manter a base validada com aviso explícito.

## Execuções reais

Hardware reconfirmado: **NVIDIA GeForce RTX 4060, 8188 MiB, driver 610.88**. Os picos totais abaixo incluem navegador/desktop; alocação PyTorch é outra medida.

| Etapa | Caso real | Tempo medido | Memória/resultado |
|---|---|---|---|
| Modelagem pela interface | Hinata, Hunyuan-mini balanced, seed 42 | 82,625s com Blender; 40,89s de inferência | 4182,2MiB alocados; pico total amostrado6177MiB; 114932triângulos; sem textura |
| Textura em uma ação, upload frontal novo | MV-Adapter SDXL, atlas 2K, seed 44 | 141,594s completos; 67,21s de inferência | 3866,8MiB alocados /5352MiB reservados; pico total amostrado7014MiB; seis vistas conjuntas offline |
| Análise automática nessa mesma tarefa | UNet de retrato na referência e no modelo | Incluída no total de textura | Duas inferências reais; etapa separada com pico total1762MiB; sem revisão humana simulada |
| Exportação da versão texturizada | GLB, FBX, OBJ e pacote Unity | Relatório do job preservado | Mesmos114932triângulos orientados no mundo e erro máximo de cantos0,0 nas três reimportações |
| Importação GLB pela Biblioteca | Malha real gerada acima | Concluída, prévia WebGL aberta | POST201, modelo carregado; original de importação preservado |
| Retry com falha deliberada de inspeção | Projeção real em armazenamento isolado | Duas tentativas preservadas | A segunda recuperou a base validada; não repetiu a geração da base |
| Unity 6000.3.0f1 | Pacote realmente exportado | Projeto novo de validação | URP e Built-in: prefab, canais finitos, topologia, material e textura aprovados |

IDs: modelagem `57a3da2b44d640b8b54c083e64a5ca6b`; textura `6097d733eadb408380c086595f45cf0f`; exportação `c14734e691984794825f2861cb0a338b`; importação `84f8fd74f23c40619ea0e985725e01b3`. Cancelamento real `5c0eb6b1c74347c78068ade50318427e` interrompido na verificação de pesos. Retry isolado em `retry-validation.json`; não é uma inferência neural adicional.

No Hinata, a transferência facial automática foi **rejeitada**, com resíduo máximo normalizado0,184 e RMSE0,0675. A base permaneceu intacta e o aviso apareceu no resultado. A melhora demonstrada por esta entrega é a continuidade/clareza do fluxo e sua integridade; não se afirma que o rosto/anatomia atingiu fidelidade artística. O número da camisa ainda pode se distorcer na base neural.

## Testes e regressões

- Baseline:267 testes aprovados em50,34s. Candidata: **282 testes aprovados em39,56s**, mais **3 testes Node** de submissão. Logs `full-candidate.log` e `submission-green.log`. Testes de orquestração com fixtures não são apresentados como inferência real.
- Após a revisão final e seu único passe de correções: **290 testes aprovados em53,89s**, **4 testes Node**, **7 regressões de navegador aprovadas** e TypeScript/Vite aprovados. Logs `review-full-final.log`, `review-build-final.log`; relatório `review/browser-review-final.json`. Um aviso de depreciação é da dependência Starlette/AnyIO; não é uma falha de teste.
- TypeScript e Vite aprovados. O chunk do visualizador Three.js continua próximo de936KB antes de gzip, com carregamento sob demanda; aviso de tamanho conhecido, sem erro de build.
- APIs: imagem inválida, quatro uploads de vista, arquivo opaco, método/estilo indisponível, chave reutilizada com conteúdo diferente, duas submissões simultâneas, ancestral fora da página, cancelamento terminal, retry, cache corrompido e evidência de cada vista.
- Navegador: imagem→modelo→textura→exportação, upload novo, referência salva visível, recarga durante a tarefa, troca Hinata→Kageyama sem publicar resultado sobre a fonte nova, versões/original, exportação existente recuperada, importação sem sidecar, máscaras carregadas e ferramentas anteriores disponíveis.
- A importação inicialmente reproduziu um erro: FormData nativo enviava um arquivo associado vazio. O formulário foi corrigido para enviar somente arquivos escolhidos e mostrar o erro no diálogo; a repetição retornou201 e abriu o GLB.
- A câmera inicialmente reproduziu a falha de mostrar diagonal apesar de selecionar Frente durante o carregamento. Removido o `Bounds.fit` inicial que substituía a orientação. Com carregamento atrasado de GLB real: RED direção `-0.6279,-0.4607,-0.6273`; GREEN `0,0,-1`. Frente/costas/esquerda/direita verificadas pela direção da câmera, não apenas pelo valor do seletor.
- Teclado: diálogo nativo prende foco, Escape fecha e devolve foco; link para conteúdo mantém a área atual. Foco visível, estados textuais e reduced-motion. Não houve erro de console na rodada candidata; eventos normais de descarte de contexto WebGL são esperados ao desmontar o canvas.
- Desktop1440×1000 e celular390×844 sem overflow horizontal. O cabeçalho do viewer se reorganiza; o painel lateral pode rolar verticalmente conforme conteúdo/altura da janela.
- **3424 arquivos originais em 124 pastas permaneceram com SHA256 idêntico.** Licenças SDXL/MV-Adapter presentes no pacote. Relatórios de preservação e Unity em `preservation-validation.json` e `unity-validation.json`.
- Semântica revisada e refinamento regional anteriores foram executados novamente em pastas novas: geometria, pixels protegidos, UVs, normais e mapas preservados. Provas antigas foram renovadas após essas regressões; algoritmos de cabelo/modelos anteriores permanecem os mesmos.

## Fidelidade visual e cópia

Comparação direta dos três conceitos completos e capturas reais, sem apresentar o conceito como resultado 3D:

| Ponto | Implementação conferida |
|---|---|
| Navegação | Cabeçalho64px, três áreas e indicador Local; área ativa com destaque laranja |
| Hierarquia | Duas colunas, lateral28vw até420px; viewer dominante; sem inspector permanente/galeria inferior |
| Linguagem visual | Paleta escura definida, tipografia Segoe UI/sistema, divisórias, raio6px e CTA laranja |
| Entrada | Upload com prévia real e ajuda; tipo/objetivo e segmentos de qualidade; avançadas fechadas |
| Biblioteca | Lista vertical, busca/filtros, render real, versões, comparação contextual e exportação |
| Estados | Vazio, tarefa real, cancelamento/falha, observações, seleção/versões e foco visíveis |
| Responsividade | Áreas empilhadas em390px; controles do viewer reorganizados sem recorte dos controles principais |

Diferenças intencionais do conceito: SVG da marca original preservado; nomes/contagens/modelos são os dados reais; detalhes ruins da malha/textura continuam visíveis. A barra superior do viewer agrupa ações para evitar título duplicado. Qualidade explica o efeito real no atlas/perfil, em vez de prometer que aumenta definição por si só. Referências salvas têm prévia e controle próprio; importação e avisos reais adicionam conteúdo ao painel. A câmera inicial usa enquadramento conservador para exibir toda a malha; zoom/enquadramento continuam disponíveis. A grade é renderizada pelo viewer real.

Capturas em `data/ux-upgrade-20261015/`: `after-modelar-desktop.png`, `after-texturizar-desktop.png`, `after-biblioteca-desktop.png`, `after-texturizar-mobile.png`; antes em `before-model.png`/`before-texture.png`; conceitos em `concept-*.png`. `browser-checks.json` conserva também tentativas de seletores incorretos; o guia/auditoria distinguem essas falhas de QA dos testes finais bem sucedidos.

## Limites preservados

Uma imagem não revela toda a geometria/cores das costas. A reconstrução pode deformar anatomia; textura não cria volume de cabelo nem corrige proporções. O perfil neural local mantém resolução nativa 512 / 20 passos e offload já validado; atlas 4K não recupera detalhes ausentes. O parser é de retrato de anime, não de corpo inteiro. Alinhamento ambíguo conserva a base; classificações finas e correções artísticas continuam opcionais nas ferramentas avançadas. Não há rig/animação automática nem backend PBR detalhado validado. Não foram instalados modelos novos ou serviços pagos.

## Revisão final e correções verificadas

A única revisão independente, em contexto novo, encontrou seis problemas Important e um Minor; nenhum Critical ou comportamento sem julgamento. A recuperação de pipeline foi reclassificada como Important porque desativava a ação de exportação solicitada. Todos entraram no mesmo passe de correção, sem segunda revisão. Veredito em `data/ux-upgrade-20261015/review/verdict.md`.

- Corpo assistido voltou a enviar `character_base_mesh`; os demais modos conservam o provedor escolhido. Teste Node RED→GREEN.
- Navegação, seleção de versões, comparação, importação e callbacks avançados compartilham uma revisão de contexto. Jobs tardios permanecem no histórico; seleções obsoletas não sobrescrevem o contexto atual. Browser com respostas atrasadas RED→GREEN.
- Travas/chaves/envios pendentes ficam no Studio; formulários e rascunhos permanecem montados ao trocar de área. Duplicação de POST de modelagem reproduzida antes da correção e bloqueada depois; textura também verificada.
- Catálogo mantém o agrupamento por lote e informa a origem real de cada versão e seu candidato. A versão real `2296cc495ab044648a80ff51f3142bbb` agora aponta para `b474d0636fab40b3ab295b7bd0bb76b7`, candidato 2; não para a geração irmã. API real e browser fixture aprovados.
- Cada vista incompatível produz aviso, mesmo quando outra vista é aceita e o refinamento passa. Teste de ramificação mista RED→GREEN; não é uma nova inferência neural.
- Modelagem passou a salvar um checkpoint da reconstrução antes do Blender. A chave inclui SHA das entradas, parâmetros, código backend/vendor e recursos do provedor/rembg; cada arquivo de saída é conferido, assim como os cabeçalhos GLB. Cache ausente, adulterado ou desatualizado exige inferência nova. Seis variantes de teste verificam reutilização/invalidação.
- Exportação usa fonte e pipeline fixados no diálogo; troca de pipeline recupera somente o pacote correspondente e uma falha permite novo preparo. Browser RED→GREEN.

**Novo ensaio real do checkpoint:** Hinata/Hunyuan-mini balanced42, sem offload, uma inferência, falha deliberada antes do Blender, retry pela API e pós-processamento Blender real. Primeira tentativa58,265s; retry9,922s; exatamente uma chamada ao provedor. PyTorch4182,2MiB; pico total amostrado5319MiB. Entrada e checkpoint originais permaneceram intactos. Relatório `model-checkpoint-validation.json`, diretório isolado `model-checkpoint-flow/`. A primeira tentativa não inclui Blender e os estados de cache/desktop diferem do ensaio anterior; esses tempos não demonstram ganho de velocidade entre provedores.

O worker mudou apenas no ramo de reconstrução generate/model_workflow; os despachos de semântica, textura/importação e cabelo retornam antes desse ramo. Seus algoritmos e a evidência real já coletada permanecem iguais. As duas provas que incluem o SHA do worker foram renovadas somente após290 testes, regressões pertinentes e o novo ensaio real; cópias anteriores estão em `review/proofs-before-final/`.

Capturas finais adicionais: `after-final-modelar-ready-desktop.png`, `after-final-texturizar-desktop.png`, `after-final-biblioteca-desktop.png` e `after-final-texturizar-mobile.png`. Inspeção visual direta aprovada; nenhum erro JS/console na navegação final e nenhum overflow horizontal em390px. A primeira captura final de Modelar ocorreu enquanto o viewer lazy carregava, e foi mantida como registro intermediário. Uma tentativa de captura alterou apenas o hash após escrever sessionStorage e não reinicializou o React; a captura definitiva recarrega a página. Um teste intermediário de rascunho leu o input nativo deliberadamente esvaziado; a asserção correta conferiu o File/preview mantido pelo React. Nenhuma dessas correções de QA exigiu mudança no produto.

Servidor atualizado funcionando em127.0.0.1:8000, fila ociosa, recursos neural/projeção/regional/semântica disponíveis; PBR avançado segue indisponível. Preservação3424/3424 revalidada após as correções. Sem pendências menores da revisão após a reclassificação; os limites artísticos/técnicos acima continuam explícitos.

Guia de uso: `docs/STUDIO_GUIDE.md`; matriz de funções: `docs/UX_WORKFLOW_AUDIT.md`.
