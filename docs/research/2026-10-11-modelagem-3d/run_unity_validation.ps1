param([string[]]$CaseNames = @(), [string]$LogName = 'unity-validation.log')
$ErrorActionPreference = 'Stop'
$workspacePath = [System.IO.Path]::GetFullPath((Join-Path $PSScriptRoot '../../..'))
$researchPath = Join-Path $workspacePath 'data/research-2026-10-11'
$projectPath = Join-Path $researchPath 'UnityValidation'
$exportPath = Join-Path $researchPath 'exports'
if (-not (Test-Path -LiteralPath "$projectPath/ProjectSettings/ProjectVersion.txt")) { throw 'Disposable UnityValidation project must be prepared first.' }
Copy-Item -LiteralPath "$PSScriptRoot/UnityResearchValidation.cs" -Destination "$projectPath/Assets/Editor" -Force
$fixtureCase = @{name='ground_truth'; folder='Assets/Cases/ground_truth'; model='ground_truth.fbx'; expectedTriangles=1092; expectedUnityDimensions=@(0.88,1.62,0.82)}
$validationCases = @($fixtureCase)
$cleanFixturePath = Join-Path $researchPath 'fixture/ground_truth_clean.fbx'
if (Test-Path -LiteralPath $cleanFixturePath) {
    New-Item -ItemType Directory -Force -Path "$projectPath/Assets/Cases/ground_truth_clean" | Out-Null
    Copy-Item -LiteralPath $cleanFixturePath -Destination "$projectPath/Assets/Cases/ground_truth_clean" -Force
    $validationCases += @{name='ground_truth_clean'; folder='Assets/Cases/ground_truth_clean'; model='ground_truth_clean.fbx'; expectedTriangles=214; expectedUnityDimensions=@(0.88,1.62,0.82)}
}
if ($CaseNames.Count -eq 0 -and (Test-Path -LiteralPath $exportPath)) {
    $CaseNames = @(Get-ChildItem -LiteralPath $exportPath -Directory | Where-Object { Test-Path -LiteralPath (Join-Path $_.FullName 'Forge3D_Asset/asset_manifest.json') } | Select-Object -ExpandProperty Name)
}
foreach ($caseName in $CaseNames) {
    if ($caseName -notmatch '^[a-zA-Z0-9_-]+$') { throw "Unsafe case name: $caseName" }
    $packagePath = Join-Path $exportPath "$caseName/Forge3D_Asset"
    $manifestPath = Join-Path $packagePath 'asset_manifest.json'
    if (-not (Test-Path -LiteralPath $manifestPath)) { throw "Export manifest missing: $manifestPath" }
    $packageManifest = Get-Content -LiteralPath $manifestPath -Raw | ConvertFrom-Json
    if (-not (Test-Path -LiteralPath (Join-Path $packagePath $packageManifest.model))) { throw "Exported FBX missing for $caseName" }
    $destinationPath = Join-Path $projectPath "Assets/Cases/$caseName"
    New-Item -ItemType Directory -Force -Path $destinationPath | Out-Null
    Copy-Item -Path "$packagePath/*" -Destination $destinationPath -Recurse -Force
    $beforeStats = $packageManifest.fbx_validation.before
    $validationCases += @{name=$caseName; folder="Assets/Cases/$caseName"; model=$packageManifest.model; expectedTriangles=[int]$beforeStats.triangles; expectedUnityDimensions=@([float]$beforeStats.dimensions[0],[float]$beforeStats.dimensions[2],[float]$beforeStats.dimensions[1])}
}
$configPath = Join-Path $projectPath 'research_config.json'
$lodChains = @()
$sgLODNames = @('sg_three_quarter', 'sg_best_medium', 'sg_best_low')
if (@($sgLODNames | Where-Object { $_ -in $CaseNames }).Count -eq 3) {
    $lodChains = @(@{name='sg_best_lod'; cases=$sgLODNames; thresholds=@(0.60,0.25,0.05)})
}
$config = @{ outputRoot=(Join-Path $researchPath 'unity-results'); summaryPath=(Join-Path $researchPath 'unity-validation.json'); cases=$validationCases; lodChains=$lodChains } | ConvertTo-Json -Depth 8
[System.IO.File]::WriteAllText($configPath, $config)
$logPath = Join-Path $researchPath $LogName
$startedAt = [DateTime]::UtcNow.ToString('o')
$unityProcess = Start-Process -FilePath 'C:/Program Files/Unity/Hub/Editor/6000.3.0f1/Editor/Unity.exe' -ArgumentList @('-batchmode','-force-d3d11','-projectPath',('"'+$projectPath+'"'),'-executeMethod','UnityResearchValidation.BatchValidate','-researchConfig',('"'+$configPath+'"'),'-logFile',('"'+$logPath+'"')) -WindowStyle Hidden -PassThru -Wait
$execution = @{pid=$unityProcess.Id; exitCode=$unityProcess.ExitCode; startedUtc=$startedAt; endedUtc=[DateTime]::UtcNow.ToString('o'); project=$projectPath; log=$logPath; cases=@($validationCases | ForEach-Object { $_.name })}
[System.IO.File]::WriteAllText((Join-Path $researchPath 'unity-execution.json'), ($execution | ConvertTo-Json -Depth 5))
$execution | ConvertTo-Json -Depth 5
if ($unityProcess.ExitCode -ne 0) { throw "Unity validation returned $($unityProcess.ExitCode); inspect $logPath" }
