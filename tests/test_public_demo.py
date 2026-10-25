"""Verified downloads, tunnel readiness and cleanup without publishing in CI."""

import ctypes
import hashlib
import io
import os
import subprocess
import sys
from types import SimpleNamespace

import pytest

from scripts import start_public_demo as demo


def test_download_is_verified_and_cached_without_second_network_call(tmp_path, monkeypatch):
    executable = b"test-only-cloudflared"
    monkeypatch.setattr(demo, "CLOUDFLARED_SHA256", hashlib.sha256(executable).hexdigest())
    calls = []

    def download(request, timeout):
        calls.append(request.full_url)
        assert request.full_url == demo.CLOUDFLARED_URL
        return io.BytesIO(executable)

    monkeypatch.setattr(demo.urllib.request, "urlopen", download)
    path = demo.ensure_cloudflared(tmp_path)
    assert path.read_bytes() == executable
    assert demo.ensure_cloudflared(tmp_path) == path
    assert calls == [demo.CLOUDFLARED_URL]


def test_invalid_download_is_never_installed_and_temporary_file_is_removed(tmp_path, monkeypatch):
    monkeypatch.setattr(demo.urllib.request, "urlopen", lambda *args, **kwargs: io.BytesIO(b"bad"))
    with pytest.raises(demo.DemoError, match="checksum mismatch"):
        demo.ensure_cloudflared(tmp_path)
    assert list(tmp_path.iterdir()) == []


def test_existing_corrupt_executable_is_rejected_without_running_it(tmp_path):
    (tmp_path / f"cloudflared-{demo.CLOUDFLARED_VERSION}.exe").write_bytes(b"corrupt")
    with pytest.raises(demo.DemoError, match="checksum mismatch"):
        demo.ensure_cloudflared(tmp_path)


@pytest.mark.parametrize("connected", [True, False])
def test_link_is_returned_only_when_cloudflare_connection_is_registered(tmp_path, connected):
    logfile = tmp_path / "tunnel.log"
    url = "https://demo-test.trycloudflare.com"
    logfile.write_text(url + ("\nRegistered tunnel connection" if connected else ""))
    process = SimpleNamespace(poll=lambda: None)
    if connected:
        assert demo.wait_for_tunnel(process, logfile, timeout=0.01) == url
    else:
        with pytest.raises(demo.DemoError, match="timed out"):
            demo.wait_for_tunnel(process, logfile, timeout=0.01)


def test_failed_tunnel_does_not_wait_for_timeout(tmp_path):
    with pytest.raises(demo.DemoError, match="stopped before connecting"):
        demo.wait_for_tunnel(SimpleNamespace(poll=lambda: 1), tmp_path / "missing.log")
    assert demo.TUNNEL_URL.search("https://good.trycloudflare.com.evil.test") is None


@pytest.mark.parametrize("failure_stage", ["tunnel", "app"])
def test_startup_failure_stops_both_owned_children(tmp_path, monkeypatch, failure_stage):
    monkeypatch.setattr(demo, "ROOT", tmp_path)
    launched = []
    stopped = []
    url = "https://correct-demo.trycloudflare.com"

    def spawn(arguments, **kwargs):
        process = SimpleNamespace(arguments=arguments, options=kwargs)
        launched.append(process)
        return process

    def link(*args):
        if failure_stage == "tunnel":
            raise demo.DemoError("tunnel test failure")
        return url

    def app_ready(*args):
        raise demo.DemoError("app test failure")

    monkeypatch.setattr(demo.subprocess, "Popen", spawn)
    monkeypatch.setattr(demo, "wait_for_tunnel", link)
    monkeypatch.setattr(demo, "wait_for_app", app_ready)
    monkeypatch.setattr(demo, "stop_owned_process", stopped.append)
    with pytest.raises(demo.DemoError, match="test failure"):
        demo.run_demo(
            {"PORT": "8011", "PUBLIC_BASE_URL": "http://old-local"}, tmp_path / "tool.exe"
        )
    assert launched[0] in stopped
    if failure_stage == "app":
        assert launched[1] in stopped
        assert launched[1].options["env"]["PUBLIC_BASE_URL"] == url
        assert "--host" in launched[1].arguments
        assert "127.0.0.1" in launched[1].arguments
    else:
        assert len(launched) == 1


@pytest.mark.skipif(os.name != "nt", reason="Windows venv redirector and child tree")
def test_stop_removes_venv_redirector_and_its_child_process():
    from ctypes import wintypes

    process = subprocess.Popen(
        [
            sys.executable,
            "-c",
            "import subprocess,sys,time; "
            "child=subprocess.Popen([sys.executable,'-c','import time;time.sleep(60)']); "
            "print(child.pid,flush=True); time.sleep(60)",
        ],
        stdout=subprocess.PIPE,
        text=True,
        creationflags=subprocess.CREATE_NEW_PROCESS_GROUP,
    )
    kernel = ctypes.WinDLL("kernel32", use_last_error=True)
    kernel.OpenProcess.argtypes = [wintypes.DWORD, wintypes.BOOL, wintypes.DWORD]
    kernel.OpenProcess.restype = wintypes.HANDLE
    kernel.WaitForSingleObject.argtypes = [wintypes.HANDLE, wintypes.DWORD]
    kernel.WaitForSingleObject.restype = wintypes.DWORD
    kernel.CloseHandle.argtypes = [wintypes.HANDLE]
    handle = None
    try:
        child_pid = int(process.stdout.readline().strip())
        handle = kernel.OpenProcess(0x00100000, False, child_pid)  # SYNCHRONIZE only.
        assert handle
        demo.stop_owned_process(process)
        assert kernel.WaitForSingleObject(handle, 2000) == 0  # Process has exited.
        assert process.poll() is not None
    finally:
        demo.stop_owned_process(process)
        if handle:
            kernel.CloseHandle(handle)
        process.stdout.close()
