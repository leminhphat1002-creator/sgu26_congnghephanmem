param(
    [int]$Port = 8010,
    [string]$PublicUrl = ""
)

$ErrorActionPreference = "Stop"
$projectRoot = Split-Path -Parent $PSScriptRoot
if (-not $PublicUrl) {
    $network = Get-NetIPConfiguration |
        Where-Object { $_.IPv4DefaultGateway -and $_.IPv4Address } |
        Select-Object -First 1
    if (-not $network) { throw "No active LAN address. Pass -PublicUrl explicitly." }
    $lanAddress = $network.IPv4Address.IPAddress | Select-Object -First 1
    $PublicUrl = "http://${lanAddress}:$Port"
}
Write-Host "Keep this terminal open. Phones must be on the same Wi-Fi for LAN addresses."
& (Join-Path $PSScriptRoot "run_local.ps1") -Port $Port -BindHost "0.0.0.0" -PublicUrl $PublicUrl
exit $LASTEXITCODE
