# Importar no Unity

1. Extraia o ZIP e copie a pasta Forge3D_Asset para Assets do seu projeto. Renomeie cada pasta importada com um nome único (por exemplo Chair-a1b2c3d4) para preservar múltiplos assets.
2. Aguarde a compilação do script em Editor. Selecione a pasta Forge3D_Asset na janela Project.
3. Clique Tools → Forge3D → Import selected asset (ID do pacote). O caminho exato fica em editor_menu no asset_manifest.json. Cada exportação recebe uma classe C# e menu únicos para evitar conflitos ao importar vários pacotes.
4. O importer ajusta escala/orientação/normais, associa a textura Albedo e cria Materials/Forge3D.mat e Prefabs/Forge3D.prefab.
5. Arraste o Prefab para sua cena.

Importe cada ZIP uma vez. Para usar o mesmo modelo várias vezes, reutilize o prefab em vez de copiar o mesmo pacote em outra pasta. O pivot permanece centralizado; ajuste a posição do prefab na cena conforme necessário.

Em um projeto com URP ativo, usa Universal Render Pipeline/Lit. No Built-in, usa Standard. Instale/configure URP no seu projeto antes de importar se quiser esse pipeline; o pacote não altera configurações globais do seu jogo.

Texturas são externas: mantenha Models, Textures, Editor e asset_manifest.json juntos. O FBX sozinho não garante material PBR. A textura é cor gerada por TripoSR e convertida por baking; não contém normal/metallic/roughness separados. A reconstrução pode conter sombras da imagem e detalhes estimados do lado não visível. Não é asset animável automaticamente; rig e retopologia ficam fora deste fluxo.

Escala em metros. Use Altura (m) no Forge3D para ajustar a dimensão antes de exportar. Original é preservado. O relatório de reimportação FBX está em asset_manifest.json. unity_import_report.json é criado apenas quando o importer foi executado no seu editor.
