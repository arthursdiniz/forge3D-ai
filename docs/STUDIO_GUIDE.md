# Como usar o Forge3D Studio

Abra `Start-Forge3D.bat` e acesse `http://127.0.0.1:8000`. O programa trabalha e salva os arquivos neste computador. O menu tem três áreas.

## Modelar: criar a forma

1. Abra **Modelar** e arraste uma imagem ou clique na área de envio. Use o objeto inteiro, fundo limpo e membros separados. PNG, JPG ou WEBP, até 20 MB.
2. Escolha **Personagem**, **Anime** ou **Objeto**. Isso orienta a preparação; não é reconhecimento automático de categoria.
3. Escolha **Rápido**, **Equilibrado** ou **Alta**. Equilibrado é um início prático. Alta usa o perfil validado da IA; não garante anatomia ou detalhes melhores.
4. Clique **Gerar modelo 3D**. Aguarde as etapas reais. Você pode cancelar sem apagar o original.
5. O resultado aparece no visualizador com material neutro. **Texturizar** é um próximo passo opcional; a textura não começa sozinha.

No modo automático, Rápido prioriza o perfil rápido do TripoSR; os outros perfis usam um provedor de geometria disponível, com configuração validada. Isso é uma escolha de compatibilidade, não uma classificação universal de fidelidade. Provedor, fundo e seed ficam em **Opções avançadas**. Múltiplas vistas/candidatos, interpretação revisada e modos técnicos legados ficam no botão de ferramentas adicionais.

## Texturizar: dar aparência a uma malha existente

1. No resultado da modelagem ou na **Biblioteca**, selecione o modelo e clique **Texturizar**. Também pode importar GLB, GLTF, OBJ ou FBX estático na área de textura ou pelo botão **+** da Biblioteca.
2. Confira o nome da origem e a prévia 3D. Para modelos importados, envie os arquivos de textura/MTL/BIN associados quando necessários; um GLB com recursos internos normalmente usa só o arquivo do modelo.
3. Adicione a referência frontal. Se houver uma referência salva, sua imagem aparece na área de envio. Clique nela para substituir. Use a aparência e, preferencialmente, a mesma pose do modelo. Costas/lados ficam em **Referências adicionais**.
4. Escolha o objetivo e a qualidade. **Fiel à referência** é apropriado para reproduzir cores e características visíveis. Objetivos de estilo dependem da IA multiview disponível. Qualidade define o atlas em 1K / 2K / 4K; o perfil neural permanece o já validado para a GPU.
5. Clique **Gerar textura** uma vez. Preparação de imagens, UV/material, geração, análise compatível, refinamento conservador e verificações acontecem dentro da tarefa. Não é necessário analisar e salvar máscaras antes.
6. Confira o resultado, **Observações deste resultado** e as vistas laterais/costas. A versão anterior continua na biblioteca. Um refinamento local pode ser omitido se o alinhamento for ambíguo; o aviso explica a decisão.

O fundo é removido automaticamente por padrão. Só selecione **Usar transparência existente** se a imagem realmente tiver uma máscara alpha. Isso evita o erro “A real alpha mask is required” com JPGs/imagens opacas.

MV-Adapter recebe a frontal e gera seis vistas conjuntamente. Vistas adicionais enviadas são observações reais usadas nas etapas compatíveis; não são condicionamentos extras do mesmo modelo neural. O parser instalado interpreta retratos de anime, com categorias amplas; não separa automaticamente todas as peças de roupa ou regiões do corpo. Estilo realista/objetos e poses incompatíveis podem omitir esse refinamento, com aviso.

## Biblioteca, inspeção e versões

- Busque pelo nome e filtre modelos com/sem textura. Uma miniatura é um render real do asset.
- Clique em uma miniatura. O seletor **Versão do modelo** permite retornar ao original ou selecionar uma versão derivada.
- **Comparar com original** usa a origem da versão selecionada. Candidatos de um mesmo lote são identificados no seletor; uma alteração do candidato 2 é comparada com o próprio candidato 2. Não é uma nota automática de fidelidade.
- Use **Frente / Costas / Esquerda / Direita / Diagonal**. Em **Exibição**, alterne textura, albedo sem luz, wireframe, grade, giro, enquadramento e luz.
- Arraste para girar; use scroll para zoom e botão direito para mover. Sem textura, examine a forma real sem o albedo ocultar defeitos.
- Fechar ou recarregar a aba não apaga tarefas/arquivos. A seleção da sessão é restaurada. Depois de encerrar o servidor durante uma tarefa, uma tentativa interrompida fica registrada; **Tentar novamente** cria outra tentativa preservando a anterior.
- Trocar entre as três áreas conserva os rascunhos e bloqueia um segundo envio enquanto a solicitação anterior estiver pendente. Uma resposta atrasada não substitui um modelo escolhido depois.

## Exportar para Unity

1. Selecione a versão desejada e clique **Exportar** no visualizador.
2. Escolha **URP** ou **Built-in** e clique **Preparar exportação**.
3. Ao terminar, baixe o pacote Unity ou arquivos GLB/FBX/OBJ. Fechar e reabrir o diálogo recupera a exportação desta versão e pipeline. Trocar URP/Built-in procura o pacote correspondente ou libera **Preparar exportação**; uma exportação falha pode ser preparada novamente.
4. Extraia o pacote para uma pasta com nome único dentro de `Assets` do projeto Unity. Use o menu `Tools/Forge3D/Import selected asset (ID)` fornecido no pacote para criar materiais/prefab. Não reutilize uma pasta de outro asset.

O pacote inclui texturas, materiais, relatórios e avisos de licença aplicáveis. A validação não transforma uma malha estática em personagem animável: rig, pesos, animações e ajustes artísticos continuam sendo etapas separadas.

## Onde estão as ferramentas técnicas

Abra o botão de controles ao lado de **Exportar**, o link no fim de **Opções avançadas** ou a engrenagem do cabeçalho. O diálogo reúne **Geração**, **Geometria e exportação**, **Textura, rosto e semântica**, **Cabelo 3D**, **Comparação** e **Configurações**.

Interpretação humana, simetria, escultura, máscaras corporais, alinhamento manual, candidatos e modificações de cabelo continuam opcionais. Confira o modelo indicado no topo antes de aplicar. O **Diagnóstico do fluxo unificado** mostra os registros e máscaras reais da tarefa, sem fingir revisão humana.

## Quando houver um problema

- **Gerar** desativado: confira imagem/referência, modelo pronto e se há outra tarefa em andamento. Um modelo importado sem referência exige que você adicione uma frontal.
- **Sem provedor disponível**: consulte a engrenagem. O programa não baixa modelos nem instala serviços automaticamente.
- **Falha**: abra os detalhes e use **Tentar novamente** para repetir a mesma solicitação. Para mudar entrada/configuração, faça uma nova geração. A base de textura e a reconstrução bruta de modelagem só são recuperadas se conteúdo, parâmetros, código, recursos e arquivos continuarem válidos. Se apenas o Blender falhou após a reconstrução, o retry pode retomar dali. Tentativas anteriores à implementação desse checkpoint não possuem essa etapa recuperável.
- **Com observações**: leia o aviso. Regiões ocultas, números, letras e detalhes faciais podem ser estimados ou distorcidos; textura não conserta anatomia ou volume ausente.

Guia de evidência e limites da entrega: `docs/UX_WORKFLOW_AUDIT.md`. Resultados medidos e capturas: `data/ux-upgrade-20261015/`.
