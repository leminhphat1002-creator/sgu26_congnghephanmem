param(
    [Parameter(Mandatory = $true)][string]$Root,
    [Parameter(Mandatory = $true)][string]$PythonPath,
    [Parameter(Mandatory = $true)][string]$WinSwPath
)
$ErrorActionPreference = "Stop"
$Root = [IO.Path]::GetFullPath($Root)
$PythonPath = (Resolve-Path -LiteralPath $PythonPath).Path
$WinSwPath = (Resolve-Path -LiteralPath $WinSwPath).Path
if (Get-Service -Name BatTrangGuide -ErrorAction SilentlyContinue) {
    throw "BatTrangGuide already exists. Do not overwrite a running service installation."
}
& $PythonPath -c "import sys, struct; assert sys.version_info[:2] == (3, 12) and struct.calcsize('P') == 8"
if ($LASTEXITCODE -ne 0) { throw "Use a persistent Windows x64 Python 3.12 installation." }
New-Item -ItemType Directory -Path $Root -Force | Out-Null
Copy-Item -LiteralPath $WinSwPath -Destination (Join-Path $Root "BatTrangGuide.exe")
Copy-Item -LiteralPath (Join-Path $PSScriptRoot "service_host.py") -Destination $Root
$settings = Join-Path $Root "settings.json"
if (-not (Test-Path -LiteralPath $settings)) {
    Copy-Item -LiteralPath (Join-Path $PSScriptRoot "settings.example.json") -Destination $settings
}
$escape = { param($value) [Security.SecurityElement]::Escape($value) }
$escapedPython = & $escape $PythonPath
$escapedRoot = & $escape $Root
$xml = @"
<service>
  <id>BatTrangGuide</id>
  <name>Bat Trang Audio Guide</name>
  <description>Windows service for the Bat Trang student project.</description>
  <executable>$escapedPython</executable>
  <arguments>&quot;$escapedRoot\service_host.py&quot; &quot;$escapedRoot&quot;</arguments>
  <workingdirectory>$escapedRoot</workingdirectory>
  <startmode>Automatic</startmode>
  <stoptimeout>30sec</stoptimeout>
  <stopparentprocessfirst>false</stopparentprocessfirst>
  <logpath>$escapedRoot\logs</logpath>
  <log mode="roll" />
  <serviceaccount><domain>NT AUTHORITY</domain><user>LocalService</user></serviceaccount>
</service>
"@
[IO.File]::WriteAllText((Join-Path $Root "BatTrangGuide.xml"), $xml)
# The web process can read code and modify only its runtime folders.
& icacls.exe $Root /grant '*S-1-5-19:(OI)(CI)RX' | Out-Null
if ($LASTEXITCODE -ne 0) { throw "Could not grant LocalService access to the application folder." }
foreach ($name in @('data', 'audio_files', 'logs')) {
    $directory = Join-Path $Root $name
    New-Item -ItemType Directory -Path $directory -Force | Out-Null
    & icacls.exe $directory /grant '*S-1-5-19:(OI)(CI)M' | Out-Null
    if ($LASTEXITCODE -ne 0) { throw "Could not grant LocalService access to runtime folder: $name" }
}
& (Join-Path $Root "BatTrangGuide.exe") install
if ($LASTEXITCODE -ne 0) { throw "WinSW service installation failed." }
Write-Host "Installed but not started. Deploy a tested ZIP before starting BatTrangGuide."
