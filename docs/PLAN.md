# Plano de implementação — 2026-10-09

1. Ambiente: registrar diagnóstico, fixar TripoSR, criar dois venvs, obter pesos e Blender portátil; comprovar tensor CUDA. Esperado: RTX 4060 reconhecida e dependências importáveis.
2. IA: adapter modular, preprocessing PIL/rembg, subprocesso offline com encoder local, extração CPU e estatísticas; executar imagem oficial MIT. Esperado: GLB com milhares de triângulos, cores reais e benchmark de CUDA.
3. Blender/Unity: textura UV a partir de cores neurais, operações versionadas, exportação FBX, reimportação com comparação de triângulos/UV/materiais, ZIP e importer C#. Esperado: relatório estrutural e teste Unity real.
4. API: testes de upload inválido, opções fora do intervalo, path traversal, estados persistentes, falhas de worker e arquivo baixável. Criar antes da implementação, verificar RED→GREEN. API SQLite e executor serial, um processo pesado por vez.
5. UI: conceito completo, layout escuro de três painéis, upload/crop/configuração, viewer com limpeza e câmera, inspector/presets/operações/exportação, histórico e estados de erro. Build TypeScript e fluxo no navegador.
6. Entrega: scripts de setup/start, documentação de uso e licenças, testes de início, duas inferências reais e pacote Unity, QA desktop/mobile e logs. Atualizar PROGRESS em cada marco. Não declarar conclusão com fluxo principal pendente.

## Foco de revisão
Upload que não é imagem; geometria vazia; subprocesso timeout/OOM; falha na restauração de jobs; chamadas simultâneas; path traversal; preservação de UVs e cores; cancelamento e controle de processos; recursos Three.js; escala/orientação Unity.
