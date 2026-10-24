"""Exercise native PowerShell transport with command doubles; no network or real key."""

import os
import subprocess
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]


@pytest.mark.skipif(os.name != "nt", reason="Windows PowerShell transport")
@pytest.mark.parametrize("failure", ["none", "upload", "remote"])
def test_transport_pins_host_key_propagates_failure_and_removes_temp_key(tmp_path, failure):
    package = tmp_path / "package"
    package.mkdir()
    (package / "bat-trang-windows.zip").write_bytes(b"test-only-package")
    script = tmp_path / "exercise.ps1"
    script.write_text(
        r"""
$ErrorActionPreference = 'Stop'
$global:remoteCalls = 0
$global:uploadCalls = 0
function global:icacls.exe { $global:LASTEXITCODE = 0 }
function global:ssh.exe {
    $global:remoteCalls++
    if ($args -notcontains 'StrictHostKeyChecking=yes') { throw 'Host checking disabled' }
    $encoded = ($args[-1] -split ' ')[-1]
    $command = [Text.Encoding]::Unicode.GetString([Convert]::FromBase64String($encoded))
    if ($command -notmatch 'C:\\BatTrang') { throw 'Wrong remote Windows root' }
    $global:LASTEXITCODE = if ($env:MOCK_FAILURE -eq 'remote') { 1 } else { 0 }
}
function global:scp.exe {
    $global:uploadCalls++
    if ($args -notcontains 'StrictHostKeyChecking=yes') { throw 'Unpinned upload' }
    if ($args[-1] -notmatch '^deploy@example.test:C:/BatTrang/incoming/') {
        throw 'Wrong Windows upload destination'
    }
    $global:LASTEXITCODE = if ($env:MOCK_FAILURE -eq 'upload') { 1 } else { 0 }
}
try {
    & $env:TRANSPORT_SCRIPT
    if ($env:MOCK_FAILURE -ne 'none') { throw 'Expected a transport failure' }
    if ($global:remoteCalls -ne 2 -or $global:uploadCalls -ne 4) {
        throw 'Missing transport operations'
    }
}
catch {
    if ($env:MOCK_FAILURE -eq 'none') { throw }
    if ($env:MOCK_FAILURE -eq 'upload' -and $_ -notmatch 'upload the Windows release') { throw }
    if ($env:MOCK_FAILURE -eq 'remote' -and $_ -notmatch 'Remote Windows command failed') { throw }
}
if (Get-ChildItem -LiteralPath $env:RUNNER_TEMP -Filter 'bat-trang-ssh-*') {
    throw 'Temporary SSH material was not removed'
}
""",
        encoding="utf-8",
    )
    environment = os.environ.copy()
    environment.update(
        {
            "RUNNER_TEMP": str(tmp_path),
            "DEPLOY_HOST": "example.test",
            "DEPLOY_USER": "deploy",
            "DEPLOY_SSH_KEY": "TEST-ONLY-NOT-A-KEY",
            "DEPLOY_KNOWN_HOSTS": "example.test ssh-ed25519 test-only",
            "DEPLOY_PYTHON": r"C:\Python312\python.exe",
            "DEPLOY_PATH": r"C:\BatTrang",
            "DEPLOY_PORT": "22",
            "REVISION": "b" * 40,
            "SEQUENCE": "11",
            "MOCK_FAILURE": failure,
            "TRANSPORT_SCRIPT": str(ROOT / "deploy" / "remote.ps1"),
        }
    )
    result = subprocess.run(
        [
            str(Path(os.environ["SystemRoot"]) / "System32/WindowsPowerShell/v1.0/powershell.exe"),
            "-NoProfile",
            "-NonInteractive",
            "-File",
            str(script),
        ],
        env=environment,
        capture_output=True,
        text=True,
        timeout=30,
    )
    assert result.returncode == 0, result.stdout + result.stderr
