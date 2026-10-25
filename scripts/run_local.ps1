param(
    [string]$ConfigPath = "",
    [string]$PythonPath = "",
    [int]$Port,
    [string]$BindHost = "",
    [string]$PublicUrl = "",
    [switch]$CheckOnly,
    [switch]$PrepareAudio,
    [switch]$PublicDemo
)

$ErrorActionPreference = "Stop"
$projectRoot = Split-Path -Parent $PSScriptRoot
if ($CheckOnly -and $PrepareAudio) { throw "Choose CheckOnly or PrepareAudio." }
if ($PublicDemo -and ($CheckOnly -or $PrepareAudio -or $BindHost -or $PSBoundParameters.ContainsKey("PublicUrl"))) {
    throw "PublicDemo owns its HTTPS address and loopback binding; use only Port/ConfigPath/PythonPath."
}
if (-not $ConfigPath) { $ConfigPath = Join-Path $projectRoot "local.settings.json" }
if (-not (Test-Path -LiteralPath $ConfigPath -PathType Leaf)) {
    throw "Copy local.settings.example.json to local.settings.json first."
}
$ConfigPath = (Resolve-Path -LiteralPath $ConfigPath).Path
$candidates = if ($PythonPath) { @($PythonPath) } else {
    @(
        (Join-Path $projectRoot ".venv\py312\Scripts\python.exe"),
        (Join-Path $projectRoot ".venv\Scripts\python.exe")
    )
}
$selectedPython = $null
foreach ($candidate in $candidates) {
    if (-not (Test-Path -LiteralPath $candidate -PathType Leaf)) { continue }
    & $candidate -c "import sys,struct; sys.exit(0 if sys.version_info[:2]==(3,12) and struct.calcsize('P')==8 else 1)"
    if ($LASTEXITCODE -eq 0) {
        $selectedPython = (Resolve-Path -LiteralPath $candidate).Path
        break
    }
}
if (-not $selectedPython) {
    throw "Python 3.12 x64 venv not found. See docs/local-windows.md or pass -PythonPath."
}
$launchArgs = @("-m", "scripts.run_local", "--config", $ConfigPath)
if ($PSBoundParameters.ContainsKey("Port")) { $launchArgs += @("--port", "$Port") }
if ($BindHost) { $launchArgs += @("--host", $BindHost) }
if ($PSBoundParameters.ContainsKey("PublicUrl")) { $launchArgs += "--public-url=$PublicUrl" }
if ($CheckOnly) { $launchArgs += "--check" }
if ($PrepareAudio) { $launchArgs += "--prepare-audio" }
if ($PublicDemo) {
    $demoPort = if ($PSBoundParameters.ContainsKey("Port")) { $Port } else { 8011 }
    $launchArgs = @("-m", "scripts.start_public_demo", "--config", $ConfigPath, "--port", "$demoPort")
}
Push-Location -LiteralPath $projectRoot
try {
    Write-Host "Python: $selectedPython"
    & $selectedPython @launchArgs
    $result = $LASTEXITCODE
}
finally { Pop-Location }
exit $result
