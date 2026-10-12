$ErrorActionPreference = 'Stop'
$projectRoot = Split-Path -Parent $PSScriptRoot
$runtimeFile = Join-Path $projectRoot 'data\runtime.json'
if (!(Test-Path -LiteralPath $runtimeFile)) { Write-Host 'Forge3D não está iniciado pelo launcher.'; exit 0 }
$runtime = Get-Content -LiteralPath $runtimeFile | ConvertFrom-Json
$process = Get-Process -Id $runtime.pid -ErrorAction SilentlyContinue
if (!$process) { Write-Host 'Forge3D já está encerrado.'; exit 0 }
if ([Math]::Abs(($process.StartTime.ToUniversalTime()-[datetime]$runtime.started).TotalSeconds) -gt 2) { throw 'PID foi reutilizado. Nenhum processo foi encerrado.' }
if ([IO.Path]::GetFullPath($runtime.root) -ne [IO.Path]::GetFullPath($projectRoot)) { throw 'Servidor pertence a outro diretório.' }
# Process tree contains only uvicorn and its owned AI/Blender children.
& taskkill.exe /PID $process.Id /T /F | Out-Null
if ($LASTEXITCODE -ne 0) { throw 'Não foi possível encerrar Forge3D.' }
Write-Host 'Forge3D encerrado. Jobs interrompidos serão marcados como falha no próximo início.'
