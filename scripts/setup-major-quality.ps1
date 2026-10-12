param([switch]$DownloadMultiview)
$ErrorActionPreference='Stop'
$taskRoot=Split-Path -Parent $PSScriptRoot
$basePython=Join-Path $taskRoot '.venv\Scripts\python.exe'
if(!(Test-Path -LiteralPath $basePython)){throw 'Execute Setup-Forge3D.bat primeiro.'}
foreach($item in @(@{Name='.venv-character';Lock='requirements-character-lock.txt'},@{Name='.venv-geometry';Lock='requirements-geometry-lock.txt'})){
    $target=Join-Path $taskRoot $item.Name
    $python=Join-Path $target 'Scripts\python.exe'
    if(!(Test-Path -LiteralPath $python)){
        & $basePython -m venv $target
        if($LASTEXITCODE){throw 'Falha ao criar ambiente CPU isolado.'}
    }
    $proof=Join-Path $target 'forge3d-validation.json'
    if(Test-Path -LiteralPath $proof){Remove-Item -LiteralPath $proof}
    # Reconcile every run: an interrupted install may leave python.exe with no packages.
    & $python -m pip install -r (Join-Path $taskRoot $item.Lock)
    if($LASTEXITCODE){throw 'Falha ao instalar dependências CPU; ambientes anteriores preservados.'}
    & $python -m pip check
    if($LASTEXITCODE){throw 'Conflito no ambiente CPU; não continuar automaticamente.'}
    & $python (Join-Path $PSScriptRoot 'validate-cpu-environment.py') $item.Name.Substring(6)
    if($LASTEXITCODE){throw 'Imports/versões CPU não passaram; ambiente permanece indisponível.'}
}
& $basePython (Join-Path $PSScriptRoot 'download-major-resources.py') pose
if($LASTEXITCODE){throw 'Download/verificação do detector de pose falhou.'}
if($DownloadMultiview){
    if(!(Test-Path -LiteralPath (Join-Path $taskRoot '.venv-hy\Scripts\python.exe'))){throw 'Instale/valide Hunyuan-mini antes do multiview; reutiliza seu runtime FP16 testado.'}
    & $basePython (Join-Path $PSScriptRoot 'download-major-resources.py') multiview
    if($LASTEXITCODE){throw 'Download/verificação dos pesos públicos multiview falhou.'}
    Write-Host 'Pesos baixados; provedor exige prova de inferência/render/exportação local para ficar disponível.'
}
Write-Host 'CPU CharacterUnderstanding/GeometryIntegrity configurados. Nenhum peso gated, credencial ou driver foi instalado.'
