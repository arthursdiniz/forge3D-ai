param([switch]$DownloadAuthorized)
$ErrorActionPreference='Stop'
$textureRoot=Split-Path $PSScriptRoot -Parent
Set-Location -LiteralPath $textureRoot
if(!(Test-Path -LiteralPath '.venv-sg/Lib/site-packages/torch')){throw 'Existing validated CUDA runtime is missing. Run the modeling setup first.'}
if(!(Test-Path -LiteralPath '.venv-texture/Scripts/python.exe')){& .venv/Scripts/python.exe -m venv .venv-texture; if($LASTEXITCODE){throw 'Texture venv creation failed.'}}
# Reuse validated read-only libraries; no pip mutations of working AI environments.
$textureSites=@((Resolve-Path '.venv-sg/Lib/site-packages').Path,(Resolve-Path '.venv-ai/Lib/site-packages').Path,(Resolve-Path '.venv/Lib/site-packages').Path)
Set-Content -LiteralPath '.venv-texture/Lib/site-packages/forge-runtime.pth' -Value $textureSites -Encoding ascii
& .venv-texture/Scripts/python.exe -c "import torch,diffusers,transformers,accelerate,einops,xatlas,moderngl,numpy,PIL; print(torch.__version__,diffusers.__version__,transformers.__version__,accelerate.__version__,numpy.__version__); assert torch.cuda.is_available()"
if($LASTEXITCODE){throw 'Texture dependencies are incomplete; existing environments were not modified.'}
& .venv-ai/Scripts/python.exe scripts/texture-runtime-info.py --mode core
if($LASTEXITCODE){throw 'Core runtime dependency record failed.'}
& .venv-texture/Scripts/python.exe scripts/texture-runtime-info.py --mode neural
if($LASTEXITCODE){throw 'Neural runtime dependency record failed.'}
if($DownloadAuthorized){& .venv/Scripts/python.exe scripts/download-texture-resources.py --authorized-local-test; if($LASTEXITCODE){throw 'Texture resource verification failed.'}}
Write-Output 'Texture runtime prepared. Availability still requires end-to-end validation.json.'
