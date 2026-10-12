param([switch]$NoBrowser)
$ErrorActionPreference = 'Stop'
$projectRoot = Split-Path -Parent $PSScriptRoot
$pythonApi = Join-Path $projectRoot '.venv\Scripts\python.exe'
$url = 'http://127.0.0.1:8000'
function Get-ForgeHealth { try { Invoke-RestMethod -Uri "$url/api/health" -TimeoutSec 2 } catch { $null } }
$health = Get-ForgeHealth
if ($health -and $health.local_only -eq $true) { if (!$NoBrowser) { Start-Process $url }; Write-Host "Forge3D já está aberto em $url"; exit 0 }
$required = @($pythonApi,"$projectRoot\.venv-ai\Scripts\python.exe","$projectRoot\models\triposr\model.ckpt","$projectRoot\frontend\dist\index.html")
foreach ($file in $required) { if (!(Test-Path -LiteralPath $file)) { throw "Ambiente incompleto: $file. Execute Setup-Forge3D.bat uma vez." } }
Push-Location $projectRoot
try { $resolvedBlender = & $pythonApi -c "from pathlib import Path; from backend.config import resolve_blender; print(resolve_blender(Path.cwd()) or '')" } finally { Pop-Location }
if ($LASTEXITCODE -or !$resolvedBlender -or !(Test-Path -LiteralPath $resolvedBlender.Trim())) { throw 'Blender ausente. Configure o caminho em Forge3D ou execute Setup-Forge3D.bat.' }
$listener = [Net.Sockets.TcpListener]::new([Net.IPAddress]::Loopback,8000)
try { $listener.Start(); $listener.Stop() } catch { throw 'Porta 8000 ocupada por outro programa. Feche esse programa antes de iniciar Forge3D.' }
New-Item -ItemType Directory -Force -Path "$projectRoot\data","$projectRoot\logs" | Out-Null
$env:PYTHONUTF8 = '1'
$arguments = @('-m','uvicorn','backend.app:app','--host','127.0.0.1','--port','8000')
$process = Start-Process -FilePath $pythonApi -ArgumentList $arguments -WorkingDirectory $projectRoot -WindowStyle Hidden -PassThru -RedirectStandardOutput "$projectRoot\logs\server.log" -RedirectStandardError "$projectRoot\logs\server-error.log"
@{pid=$process.Id;started=$process.StartTime.ToUniversalTime().ToString('o');root=$projectRoot} | ConvertTo-Json | Set-Content -LiteralPath "$projectRoot\data\runtime.json"
for ($attempt=0;$attempt -lt 30;$attempt++) { Start-Sleep -Milliseconds 1000; $health=Get-ForgeHealth; if ($health) { break }; if ($process.HasExited) { throw "Backend encerrou. Consulte $projectRoot\logs\server-error.log" } }
if (!$health) { throw "Backend não respondeu. Consulte $projectRoot\logs\server-error.log" }
if (!$NoBrowser) { Start-Process $url }
Write-Host "Forge3D aberto em $url"
Write-Host "Modelos: $projectRoot\data\assets"
