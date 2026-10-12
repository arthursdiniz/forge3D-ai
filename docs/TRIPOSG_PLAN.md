# TripoSG — download e teste autorizado

Usuário autorizou download e teste local em 2026-10-09. Pesos oficiais MIT VAST-AI/TripoSG, revisão 2c1c516d22d58db486a058d98d31bb6177344e06, total ~7.95 GB. Código já clonado: fc5c40990181e2a756c4e0b1c2f4d6b5202faf8c. Não baixar BRIA/RMBG ou outros pesos auxiliares; reutilizar alpha/u2netp local, explicitando diferenças de preparação.

1. Download retomável, whitelist e hashes SHA256 do publisher; manifest em models/triposg. Nenhum token necessário.
2. Ambiente .venv-sg isolado; versões compatíveis com Python3.12 e Torch2.5.1 cu124. Não usar requirements upstream numpy1.22.3 incompatível. Não alterar .venv-ai.
3. Adaptador offline, lock GPU compartilhado, batch1, seed42, passos50/guidance7/tokens2048. Hierarchical decoder upstream sem extensão flash CUDA se indisponível. Testar offload somente com suporte/hooks e registrar resultados reais.
4. Inferência de uma referência MIT, RAW, latentes e metadados preservados. Se funcionar, repetir e comparar três categorias; render cinza para comparar geometria sem confundir textura.
5. Provedor só disponível após prova real e teste Blender/FBX. Não fingir textura/UV/PBR/multi-view. Sem troca automática do default TripoSR.
6. Atualizar PROGRESS, relatório, UI/API se candidato realmente utilizável, validar fluxo e documentar limite de 8GB se não houver solução viável.
