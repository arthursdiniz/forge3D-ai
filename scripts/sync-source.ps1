param([string]$Destination = 'C:\Projetos\forge3d-ai')
$ErrorActionPreference = 'Stop'
$sourceRoot = Split-Path -Parent $PSScriptRoot
$destinationRoot = [IO.Path]::GetFullPath($Destination)
if ($sourceRoot.TrimEnd('\') -eq $destinationRoot.TrimEnd('\')) { Write-Output 'Fonte já está no destino.'; exit 0 }
if ($destinationRoot.TrimEnd('\') -ne 'C:\Projetos\forge3d-ai') { throw 'Destino não autorizado por este script.' }
$excluded = @('.venv','.venv-ai','.venv-sg','.test-tmp','.playwright-mcp','node_modules','vendor','models','tools','data','cache','logs','.git','.agents','__pycache__','.pytest_cache')
function Copy-SourceTree([string]$Source,[string]$Target) {
    New-Item -ItemType Directory -Path $Target -Force | Out-Null
    foreach ($item in Get-ChildItem -LiteralPath $Source -Force) {
        if ($item.Name -in $excluded -or $item.Name.StartsWith('.venv')) { continue }
        $next = Join-Path $Target $item.Name
        if ($item.PSIsContainer) { Copy-SourceTree $item.FullName $next }
        else { Copy-Item -LiteralPath $item.FullName -Destination $next -Force }
    }
}
Copy-SourceTree $sourceRoot $destinationRoot
Write-Output "Fonte sincronizada para $destinationRoot; ambientes, pesos, assets e .agents preservados."
