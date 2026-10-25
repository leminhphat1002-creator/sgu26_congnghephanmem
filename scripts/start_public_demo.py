"""Own a temporary HTTPS tunnel and app together; Ctrl+C stops both on Windows."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import struct
import subprocess
import sys
import tempfile
import time
import urllib.error
import urllib.request
from datetime import datetime
from pathlib import Path

from scripts.run_local import ROOT, load_configuration, preflight, require_free_port

CLOUDFLARED_VERSION = "2026.10.3"
CLOUDFLARED_SHA256 = "76b2805253d0d6ffacb092a7acfbee99e7af6917835c0c5410e23f3ef5052da2"
CLOUDFLARED_URL = (
    "https://github.com/cloudflare/cloudflared/releases/download/"
    f"{CLOUDFLARED_VERSION}/cloudflared-windows-amd64.exe"
)
TUNNEL_URL = re.compile(r"https://[a-z0-9]+(?:-[a-z0-9]+)*\.trycloudflare\.com(?![a-z0-9.-])")


class DemoError(RuntimeError):
    """A diagnostic safe to print without connection credentials."""


def verified(path: Path) -> bool:
    if not path.is_file():
        return False
    with path.open("rb") as stream:
        return hashlib.file_digest(stream, "sha256").hexdigest() == CLOUDFLARED_SHA256


def ensure_cloudflared(directory: Path) -> Path:
    directory.mkdir(parents=True, exist_ok=True)
    target = directory / f"cloudflared-{CLOUDFLARED_VERSION}.exe"
    if target.exists():
        if not verified(target):
            raise DemoError(
                "cloudflared checksum mismatch; remove that cached executable and retry."
            )
        return target
    print("Downloading official Windows cloudflared (first run only; about 55 MB)...", flush=True)
    descriptor, temporary_name = tempfile.mkstemp(prefix="cloudflared-", dir=directory)
    temporary = Path(temporary_name)
    try:
        started = time.monotonic()
        with os.fdopen(descriptor, "wb") as destination:
            request = urllib.request.Request(
                CLOUDFLARED_URL, headers={"User-Agent": "BatTrangGuide"}
            )
            with urllib.request.urlopen(request, timeout=30) as response:
                total = 0
                while chunk := response.read(1024 * 1024):
                    total += len(chunk)
                    if total > 100 * 1024 * 1024 or time.monotonic() - started > 180:
                        raise DemoError("cloudflared download exceeded the size/time limit; retry.")
                    destination.write(chunk)
        if not verified(temporary):
            raise DemoError("Downloaded cloudflared checksum mismatch; executable was not started.")
        temporary.replace(target)
        return target
    finally:
        temporary.unlink(missing_ok=True)


def wait_for_tunnel(process, logfile: Path, timeout: float = 60) -> str:
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        if process.poll() is not None:
            raise DemoError(f"Tunnel stopped before connecting. See {logfile}")
        output = logfile.read_text(encoding="utf-8", errors="replace")
        match = TUNNEL_URL.search(output)
        if match and "Registered tunnel connection" in output:
            return match.group(0)
        time.sleep(0.2)
    raise DemoError(f"Tunnel connection timed out. Check network access; see {logfile}")


def wait_for_app(process, origin: str, timeout: float = 30) -> None:
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        if process.poll() is not None:
            raise DemoError("Website process stopped. See the app log printed above.")
        try:
            with urllib.request.urlopen(origin + "/health", timeout=1) as response:
                if json.load(response) == {"status": "ok"}:
                    return
        except (OSError, ValueError):
            pass
        time.sleep(0.2)
    raise DemoError("Website did not become ready within 30 seconds.")


def stop_owned_process(process) -> None:
    if process is None or process.poll() is not None:
        return
    if os.name == "nt":
        # Windows venv python.exe redirects to another process. Stop our entire child tree.
        subprocess.run(
            ["taskkill.exe", "/PID", str(process.pid), "/T", "/F"],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            timeout=10,
            check=False,
        )
    else:
        process.terminate()
    process.wait(timeout=10)


def run_demo(config: dict, executable: Path) -> None:
    logs = ROOT / "data" / "logs"
    logs.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now().strftime("%Y%m%dT%H%M%S%f")
    tunnel_log = logs / f"tunnel-{stamp}.log"
    app_log = logs / f"public-app-{stamp}.log"
    app_process = tunnel_process = None
    environment = os.environ.copy()
    environment.update(config)
    origin = f"http://127.0.0.1:{config['PORT']}"
    group = subprocess.CREATE_NEW_PROCESS_GROUP if os.name == "nt" else 0
    print(f"Creating temporary HTTPS link. Tunnel log: {tunnel_log}", flush=True)
    try:
        with tunnel_log.open("wb") as tunnel_output, app_log.open("wb") as app_output:
            tunnel_process = subprocess.Popen(
                [
                    str(executable),
                    "tunnel",
                    "--no-autoupdate",
                    "--protocol",
                    "http2",
                    "--url",
                    origin,
                ],
                stdout=tunnel_output,
                stderr=subprocess.STDOUT,
                stdin=subprocess.DEVNULL,
                creationflags=group,
                cwd=ROOT,
            )
            url = wait_for_tunnel(tunnel_process, tunnel_log)
            environment["PUBLIC_BASE_URL"] = url
            print(f"App log: {app_log}", flush=True)
            app_process = subprocess.Popen(
                [
                    sys.executable,
                    "-m",
                    "uvicorn",
                    "app.main:app",
                    "--host",
                    "127.0.0.1",
                    "--port",
                    config["PORT"],
                    "--proxy-headers",
                    "--forwarded-allow-ips",
                    "127.0.0.1",
                ],
                stdout=app_output,
                stderr=subprocess.STDOUT,
                stdin=subprocess.DEVNULL,
                creationflags=group,
                cwd=ROOT,
                env=environment,
            )
            wait_for_app(app_process, origin)
            print(f"\nVisitor: {url}/\nManager: {url}/admin\nQR page: {url}/share", flush=True)
            print(
                "Temporary demo: visitors can use other Wi-Fi or mobile data. "
                "Keep this terminal and computer running; Ctrl+C stops both app and tunnel. "
                "A new run creates a new link and QR.",
                flush=True,
            )
            while True:
                if app_process.poll() is not None or tunnel_process.poll() is not None:
                    raise DemoError(
                        "App or tunnel stopped. Check the logs and run PublicDemo again."
                    )
                time.sleep(0.5)
    finally:
        try:
            stop_owned_process(tunnel_process)
        finally:
            stop_owned_process(app_process)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", type=Path, default=ROOT / "local.settings.json")
    parser.add_argument("--port", type=int, default=8011)
    args = parser.parse_args()
    if os.name != "nt" or sys.version_info[:2] != (3, 12) or struct.calcsize("P") != 8:
        print("Public demo requires Windows and Python 3.12 x64.", file=sys.stderr)
        return 1
    try:
        if not args.config.is_file():
            raise DemoError("Copy local.settings.example.json to local.settings.json first.")
        config = load_configuration(
            ROOT,
            args.config,
            os.environ,
            {"PORT": args.port, "BIND_HOST": "127.0.0.1", "PUBLIC_BASE_URL": ""},
        )
        os.chdir(ROOT)
        os.environ.update(config)
        preflight(config)
        require_free_port("127.0.0.1", args.port)
        executable = ensure_cloudflared(ROOT / "data" / "tools")
        run_demo(config, executable)
        return 0
    except KeyboardInterrupt:
        print("\nStopped public demo.", flush=True)
        return 130
    except (DemoError, ValueError) as error:
        print(f"Public demo failed: {error}", file=sys.stderr)
        return 1
    except Exception as error:
        print(
            f"Public demo failed ({type(error).__name__}); check network, setup and logs. "
            "See docs/FREE_HOSTING.md.",
            file=sys.stderr,
        )
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
