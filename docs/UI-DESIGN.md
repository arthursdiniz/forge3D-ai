# Forge3D Studio — direção visual atual

Atualização de15/10/2026: três áreas **Modelar / Texturizar / Biblioteca**; duas colunas, sem inspector permanente ou galeria inferior. Os controles técnicos continuam no diálogo de ferramentas avançadas. Conceitos e capturas reais em `data/ux-upgrade-20261015/`; os conceitos são referências de interface, nunca modelos ou resultados neurais.

Sistema atual: fundo `#14191D`, painel `#1B2228`, linha `#303B43`, texto `#E7EDF4`, secundário `#A3AFBD`, destaque `#FF853C`. Segoe UI/sistema, títulos30px, corpo14–15px, controles principais40–48px, raios6px. Cabeçalho64px, lateral28vw até420px, visualizador flexível; em390px as áreas se empilham sem rolagem horizontal. MarcaSVG existente preservada.

Componentes atuais em `frontend/src/studio/`: StudioApp, ModelWorkspace, TextureStudio, AssetLibrary, AdvancedTools, useStudio e UI compartilhada (upload, segmentos, ajuda, progresso, diálogo, importação). Viewer existente recebe modo compacto e mantém ferramentas técnicas para outros módulos. Código anterior preservado em LegacyWorkspace; APIs legadas continuam disponíveis.

Estados reais: vazio, referência selecionada/salva, enviando, fila, execução, cancelado, falha, resultado com observações, comparação, importação e download. Sem porcentagens inventadas. Foco visível, navegação de teclado, rótulos, diálogo nativo com Escape/retorno de foco, reduced-motion e mensagem textual além de cor. Não se declara conformidade WCAG integral sem auditoria específica.

Fluxos e ajuda: [STUDIO_GUIDE.md](STUDIO_GUIDE.md). Matriz de migração, decisões e provas: [UX_WORKFLOW_AUDIT.md](UX_WORKFLOW_AUDIT.md).

## Direção anterior, preservada como histórico
Conceito: interface-concept.png, gerado pela ferramenta integrada ImageGen apenas para planejar a aparência. Não é saída do gerador de modelos.

Sistema: fundo #171e23, painéis #1e262c, separadores #354047, accent #ff853c, texto #e7edf4 e secundário #a3afbd; fonte Segoe UI/Inter; controles 12–14 px, títulos 17–22 px; raios 5–6 px. Marca vetorial nativa. Três painéis, canvas principal e biblioteca em faixa inferior. Sem dados de exemplo ou métricas fictícias.

Componentes: UploadPanel, Viewer, Inspector, Library; API DTO compartilhado em api.ts. Input e inspector com scroll próprio em desktop; empilhamento e canvas limitado em mobile. Viewport carrega GLB local real, trata falhas e descarta geometrias/materiais/texturas ao trocar asset. Estado vazio segue o conceito; estados gerados usam dados reais.

Extensões funcionais em relação ao conceito: intensidade de luz, cancelar processamento, validar/inspecionar malha, mensagens de erro, download de GLB e relatório FBX. Mantêm tipografia/paleta e são necessárias ao escopo do usuário. Valores e labels de qualidade usam resoluções reais suportadas pelo backend.
