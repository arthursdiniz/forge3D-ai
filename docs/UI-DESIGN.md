# Direção visual
Conceito: interface-concept.png, gerado pela ferramenta integrada ImageGen apenas para planejar a aparência. Não é saída do gerador de modelos.

Sistema: fundo #171e23, painéis #1e262c, separadores #354047, accent #ff853c, texto #e7edf4 e secundário #a3afbd; fonte Segoe UI/Inter; controles 12–14 px, títulos 17–22 px; raios 5–6 px. Marca vetorial nativa. Três painéis, canvas principal e biblioteca em faixa inferior. Sem dados de exemplo ou métricas fictícias.

Componentes: UploadPanel, Viewer, Inspector, Library; API DTO compartilhado em api.ts. Input e inspector com scroll próprio em desktop; empilhamento e canvas limitado em mobile. Viewport carrega GLB local real, trata falhas e descarta geometrias/materiais/texturas ao trocar asset. Estado vazio segue o conceito; estados gerados usam dados reais.

Extensões funcionais em relação ao conceito: intensidade de luz, cancelar processamento, validar/inspecionar malha, mensagens de erro, download de GLB e relatório FBX. Mantêm tipografia/paleta e são necessárias ao escopo do usuário. Valores e labels de qualidade usam resoluções reais suportadas pelo backend.
