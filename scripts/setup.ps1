$ErrorActionPreference = 'Stop'
$projectRoot = Split-Path -Parent $PSScriptRoot
Set-Location -LiteralPath $projectRoot
New-Item -ItemType Directory -Force -Path "$projectRoot\logs","$projectRoot\cache","$projectRoot\models","$projectRoot\tools","$projectRoot\vendor" | Out-Null
function Check-Exit([string]$Stage) { if ($LASTEXITCODE -ne 0) { throw "$Stage falhou (código $LASTEXITCODE). Consulte logs e execute novamente o setup." } }
Write-Host 'Forge3D setup: downloads ocorrem apenas nesta etapa. Pesos TripoSR ~1.68 GB, Blender ~400 MB, PyTorch e dependências vários GB.'
$pythonCommand = Get-Command python -ErrorAction Stop
& $pythonCommand.Source -c 'import sys; assert (3,10) <= sys.version_info[:2] <= (3,12), "Instale Python 3.10 a 3.12"'
Check-Exit 'Verificação Python'
Get-Command git,npm.cmd -ErrorAction Stop | Out-Null
if (!(Test-Path -LiteralPath "$projectRoot\.venv\Scripts\python.exe")) { & $pythonCommand.Source -m venv "$projectRoot\.venv"; Check-Exit 'Ambiente API' }
if (!(Test-Path -LiteralPath "$projectRoot\.venv-ai\Scripts\python.exe")) { & $pythonCommand.Source -m venv "$projectRoot\.venv-ai"; Check-Exit 'Ambiente IA' }
$env:PIP_CACHE_DIR = "$projectRoot\cache\pip"
& "$projectRoot\.venv\Scripts\python.exe" -m pip install -r requirements.txt
Check-Exit 'Dependências API'
# Sequential installs are mandatory: do not mutate the same venv concurrently.
& "$projectRoot\.venv-ai\Scripts\python.exe" -m pip install torch==2.5.1 torchvision==0.20.1 --index-url https://download.pytorch.org/whl/cu124
Check-Exit 'PyTorch CUDA'
& "$projectRoot\.venv-ai\Scripts\python.exe" -m pip install -r requirements-ai.txt
Check-Exit 'Dependências TripoSR'
& "$projectRoot\.venv-ai\Scripts\python.exe" -m pip install -r requirements-quality.txt
Check-Exit 'Dependências de textura neural e UV'
if (!(Test-Path -LiteralPath "$projectRoot\vendor\TripoSR\tsr\system.py")) { git clone https://github.com/VAST-AI-Research/TripoSR.git "$projectRoot\vendor\TripoSR"; Check-Exit 'Código TripoSR' }
git -C "$projectRoot\vendor\TripoSR" checkout 107cefdc244c39106fa830359024f6a2f1c78871
Check-Exit 'Revisão TripoSR'
& "$projectRoot\.venv\Scripts\python.exe" scripts/download-assets.py
Check-Exit 'Pesos e Blender'
& "$projectRoot\.venv-ai\Scripts\python.exe" -c 'import torch,numpy,skimage; assert torch.cuda.is_available(), "CUDA indisponível"; print(torch.cuda.get_device_name(0)); print(torch.ones(1).numpy())'
Check-Exit 'Validação CUDA'
Push-Location frontend
try { if (Test-Path -LiteralPath package-lock.json) { npm.cmd ci --no-audit --no-fund } else { npm.cmd install --no-audit --no-fund }; Check-Exit 'Dependências frontend'; npm.cmd run build; Check-Exit 'Build frontend' } finally { Pop-Location }
Write-Host 'Setup concluído. Abra Start-Forge3D.bat. O início normal não baixa nem reinstala nada.'
