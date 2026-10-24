param(
    [int]$Port = 8010,
    [string]$PublicUrl = ""
)

$ErrorActionPreference = "Stop"
$projectRoot = Split-Path -Parent $PSScriptRoot
Set-Location -LiteralPath $projectRoot
$pythonPath = Join-Path $projectRoot ".venv\Scripts\python.exe"
if (-not (Test-Path -LiteralPath $pythonPath)) {
    throw "Create .venv and install requirements-dev.txt first."
}
if (-not $PublicUrl) {
    $network = Get-NetIPConfiguration |
        Where-Object { $_.IPv4DefaultGateway -and $_.IPv4Address } |
        Select-Object -First 1
    if (-not $network) { throw "No active LAN address. Pass -PublicUrl explicitly." }
    $lanAddress = $network.IPv4Address.IPAddress | Select-Object -First 1
    $PublicUrl = "http://${lanAddress}:$Port"
}
$env:PUBLIC_BASE_URL = $PublicUrl
Write-Host "Visitor: $PublicUrl/"
Write-Host "Manager: $PublicUrl/admin"
Write-Host "QR page: $PublicUrl/share"
Write-Host "Keep this terminal open. Phones must be on the same Wi-Fi for LAN addresses."
& $pythonPath -m uvicorn app.main:app --host 0.0.0.0 --port $Port
