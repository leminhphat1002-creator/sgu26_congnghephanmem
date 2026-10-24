param()
$ErrorActionPreference = "Stop"
foreach ($name in @('DEPLOY_HOST', 'DEPLOY_USER', 'DEPLOY_SSH_KEY', 'DEPLOY_KNOWN_HOSTS', 'DEPLOY_PYTHON', 'REVISION', 'SEQUENCE')) {
    if (-not [Environment]::GetEnvironmentVariable($name)) { throw "Missing setting: $name" }
}
if ($env:DEPLOY_HOST -notmatch '^[a-zA-Z0-9][a-zA-Z0-9.-]*$') { throw 'Invalid SSH host' }
if ($env:DEPLOY_USER -notmatch '^[a-zA-Z0-9_][a-zA-Z0-9_.-]*$') { throw 'Invalid SSH user' }
if ($env:REVISION -notmatch '^[0-9a-f]{40}$' -or $env:SEQUENCE -notmatch '^[0-9]+$') { throw 'Invalid release identity' }
$root = if ($env:DEPLOY_PATH) { $env:DEPLOY_PATH } else { 'C:\BatTrang' }
$python = $env:DEPLOY_PYTHON
# Restricted remote paths avoid ambiguity in Windows OpenSSH/scp argument handling.
foreach ($path in @($root, $python)) {
    if ($path -notmatch '^[A-Za-z]:\\[A-Za-z0-9_-]+(\\[A-Za-z0-9_.-]+)*$' -or $path -match '\\\.\.?($|\\)') {
        throw 'Use an absolute Windows remote path without spaces, for example C:\BatTrang or C:\Python312\python.exe'
    }
}
$port = if ($env:DEPLOY_PORT) { [int]$env:DEPLOY_PORT } else { 22 }
if ($port -lt 1 -or $port -gt 65535) { throw 'Invalid SSH port' }
$archive = Join-Path $env:RUNNER_TEMP 'package\bat-trang-windows.zip'
if (-not (Test-Path -LiteralPath $archive)) { throw 'Tested ZIP is missing' }
$temporary = Join-Path $env:RUNNER_TEMP ("bat-trang-ssh-" + [guid]::NewGuid().ToString('N'))
New-Item -ItemType Directory -Path $temporary | Out-Null
$key = Join-Path $temporary 'key'
$hostsFile = Join-Path $temporary 'known_hosts'
$encoding = New-Object Text.UTF8Encoding($false)
$remote = "$($env:DEPLOY_USER)@$($env:DEPLOY_HOST)"
try {
    [IO.File]::WriteAllText($key, $env:DEPLOY_SSH_KEY.Trim() + "`n", $encoding)
    [IO.File]::WriteAllText($hostsFile, $env:DEPLOY_KNOWN_HOSTS.Trim() + "`n", $encoding)
    $identity = [Security.Principal.WindowsIdentity]::GetCurrent().User.Value
    & icacls.exe $key /inheritance:r /grant:r "*$($identity):R" | Out-Null
    if ($LASTEXITCODE -ne 0) { throw 'Could not restrict the SSH key file permissions' }
    $options = @('-i', $key, '-o', 'IdentitiesOnly=yes', '-o', 'BatchMode=yes', '-o', 'StrictHostKeyChecking=yes',
                 '-o', "UserKnownHostsFile=$hostsFile", '-o', 'ConnectTimeout=15')
    function Invoke-Remote([string]$command) {
        $encoded = [Convert]::ToBase64String([Text.Encoding]::Unicode.GetBytes("`$ErrorActionPreference = 'Stop'; " + $command))
        & ssh.exe @options -p $port $remote "powershell.exe -NoProfile -NonInteractive -EncodedCommand $encoded"
        if ($LASTEXITCODE -ne 0) { throw 'Remote Windows command failed' }
    }
    $incoming = "$root\incoming\$($env:REVISION)-$([guid]::NewGuid().ToString('N'))"
    Invoke-Remote "New-Item -ItemType Directory -Path '$incoming\deploy' -Force | Out-Null"
    $destination = $incoming.Replace('\', '/')
    & scp.exe @options -P $port $archive "${remote}:$destination/bat-trang-windows.zip"
    if ($LASTEXITCODE -ne 0) { throw 'Could not upload the Windows release' }
    foreach ($name in @('windows_release.py', 'windows_deploy.py', 'service_host.py')) {
        & scp.exe @options -P $port (Join-Path $PSScriptRoot $name) "${remote}:$destination/deploy/$name"
        if ($LASTEXITCODE -ne 0) { throw 'Could not upload Windows deployment tools' }
    }
    Invoke-Remote "Set-Location -LiteralPath '$incoming'; & '$python' -m deploy.windows_deploy --archive '$incoming\bat-trang-windows.zip' --root '$root' --revision '$($env:REVISION)' --sequence '$($env:SEQUENCE)'; if (`$LASTEXITCODE -ne 0) { exit 1 }"
}
finally {
    # Only remove the three explicitly created local paths; no recursive deletion.
    Remove-Item -LiteralPath $key, $hostsFile -Force -ErrorAction SilentlyContinue
    Remove-Item -LiteralPath $temporary -Force -ErrorAction SilentlyContinue
}
