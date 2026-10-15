# Forge3D Studio — UX e workflows independentes

Autoridade: attachment f74f5081-85ce-4a1b-99ce-8dfce2a5f99f/Texto colado.txt, lido integralmente. Usuário exige execução contínua até entrega funcional, sem confirmações entre fases. Este documento registra decisões de implementação, não um pedido de aprovação adicional.

## Resultado e invariantes

Três áreas: Modelar, Texturizar, Biblioteca. Modelagem termina em geometria, sem iniciar textura. Texturização começa em malha existente e preserva sua geometria. Uma submissão pública por domínio; subprocessos internos persistidos/serializados, sem obrigar análise/salvamento intermediário. Advanced mantém providers, candidatos, Character Intelligence, geometria, cabelo, máscaras/regiões, comparação, importação/exportação, diagnósticos e versões. Sem novos pesos, APIs pagas, ambientes, drivers ou core runtime. Sem commits/reset/limpeza do checkout sujo ou dados anteriores.

## Auditoria

Baseline data/ux-upgrade-20261015:216fontes,124pastas de assets,3424arquivos originais com SHA256 e snapshot de fontes; HEAD/status preservados. Capturas before-model.png e before-texture.png. DOM modelagem inicial119botões/31campos (inclui conteúdo não visível). App contém simultaneamente UploadPanel/CharacterPanel/QualityPanel/Inspector/CharacterTools/candidatos/biblioteca e quatro rotas de ferramentas. TextureWorkspace exige chamadas separadas para global, preparação regional e SemanticWorkspace. GenerationOptions suporta texture_output=geometry_only inclusive TripoSR; geração character_mode exige interpretação revisada, portanto esse modo assistido não pode ser ligado automaticamente fingindo revisão humana. Worker já serializa tarefas e encerra subprocessos; Store impede publicação de cancelados. Semântica instalada é retrato7classes, não parsing corporal automático. Esses limites devem sobreviver ao novo fluxo.

## Arquitetura de serviços

Novo pacote backend/workflows: contracts/planner/routes/jobs/texture_cli/catalog, funções pequenas e imports numéricos isolados nos ambientes existentes. APIs POST /api/workflows/model e POST /api/workflows/{source}/texture; GET capacidades e biblioteca; retry cria outra versão, nunca altera falha/original. Kind model_workflow/texture_workflow explícitos, Worker delega antes do dispatch legado. Reusar validação/upload de geração via helper privado e chamadas CLI reais. Ações antigas continuam disponíveis. Sem chamadas HTTP internas ou múltiplos jobs públicos para uma operação comum.

Manifesto workflow.json com domínio, parâmetros, estratégia escolhida, etapas executadas/omitidas, tempos/avisos/resultado. Cache de etapas só reutiliza saída íntegra vinculada a SHA de fonte, referências, opções, código e recursos; retry não reutiliza etapa inválida. request_key evita dupla submissão; cancelamento usa processo owned e guard Store. Falha indispensável não conclui; alternativa legítima produz resultado explicitamente qualificado.

Modelagem escolhe apenas providers/presets existentes e validados. Categorias orientam preparação real; não anunciar classificação automática. Preparação/enquadramento/inferência/checagem já existentes permanecem, texture_output=geometry_only, sem simetria/decimation/refino destrutivo automático. Character Intelligence pode produzir sugestões internas se recurso disponível; nunca marcar revisão humana ou aplicar anatomia inferida como verdade. Candidatos/modos assistidos permanecem avançados.

Texturização resolve modelo/referência salva ou upload real; presets mapeiam1K/2K/4K e perfil neural validado existente. Base neural quando disponível/objetivo suportado, projeção só como alternativa qualificada quando aplicável. Segmentação de retrato/associação/render/refinamento conservador usam módulos existentes. Alinhamento automático precisa evidência de orientação/silhueta/landmarks e limites explícitos; caso ambíguo mantém base legítima e avisa, sem inventar parsing ou revisão humana. Categorias finas continuam manuais opcionais. Vistas extras são observações reais; não chamar vistas geradas de referência. Objetivos de estilo não podem ser anulados por projeção integral indiscriminada. Semântica limita composição/projeção, não condiciona espacialmente denoiser SDXL. UVs/materiais/mapas e identidade mundial são verificados; geometrias originais imutáveis.

## Interface e design system

React19/Vite/Three existentes. Conceitos completos ImageGen: concept-modelar.png, concept-texturizar.png, concept-biblioteca.png em QA; apenas referência visual, nunca imagem de UI ou saída neural em produção. Header64px, marca forge.svg atual, nav3áreas e estado Local/configurações. Duas colunas, lateral≈28vw limitada420px, viewer dominante; sem inspector permanente nem biblioteca horizontal. Fundo#14191D, painel#1B2228, separador#303B43, texto#E7EDF4, secundário#A3AFBD, laranja#FF853C. SegoeUI/sistema; heading≈30px, texto14–16px, controles14px; raios6px. Componentes reutilizáveis (Upload/Segmented/Help/Disclosure/Alert/Progress/Export/Version).

Modelar: imagem, Personagem/Anime/Objeto, Rápido/Equilibrado/Alta, CTA Gerar modelo3D. Texturizar: fonte/importação, referência frontal+extras recolhidos, objetivo suportado, qualidade, CTA Gerar textura. Advanced fechado. Biblioteca: busca/filtro, miniaturas reais/placeholder identificado, modelos agrupados por linhagem, versões e ações. Seleção explícita, não substituir por último job global. Mudanças de fonte invalidam resultado/referência obsoletos. Viewer compacto: vistas/Exibição; wireframe/luz/albedo em menu; comparação contextual. Header/names dinâmicos dos assets reais podem divergir do exemplo Kageyama do conceito.

Ajuda clicável/teclado, foco visível, rótulos, alertas associados, reduced-motion, contraste e informação não só por cor. Progresso indeterminado/etapa real/tempo/cancelar; sem porcentagem inventada. Erros compreensíveis com detalhe técnico sob demanda. Responsivo desktop prioritário e mobile390 sem overflow.

Referências consultadas: NN/G progressive disclosure https://www.nngroup.com/articles/progressive-disclosure/ e WCAG2.2 https://www.w3.org/TR/WCAG22/ . Não declarar conformidade total sem auditoria apropriada.

## Aceitação

Pessoa iniciante: Modelar→imagem/tipo/qualidade→Gerar→resultado→Texturizar→referência/qualidade→Gerar textura→resultado→exportar. Sem visitar máscara/UV/seed no caminho comum. Testes de contrato/cancel/retry/cache/seleção/independência, build/TypeScript, API, regressões e inferências reais seriais na4060; exportsGLB/FBX/OBJ/Unity quando ambiente pronto. Capturas antes/depois, view_image dos conceitos e renders reais, comparação de pelo menos5pontos e limites registrados. Um reviewer final novo, único passe de correções importantes com RED→GREEN, suíte completa; sem re-review.
