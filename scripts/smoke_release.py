"""Run the packaged app in an isolated Windows venv with offline dependencies."""

import argparse
import json
import os
import socket
import subprocess
import tempfile
import time
import urllib.error
import urllib.request
from pathlib import Path

from deploy.windows_release import extract, install


def smoke(archive, revision):
    with tempfile.TemporaryDirectory(prefix="bat-trang-smoke-") as temporary:
        release = Path(temporary) / "release"
        extract(archive, release, revision)
        python = install(release)
        environment = os.environ.copy()
        with socket.socket() as listener:
            listener.bind(("127.0.0.1", 0))
            port = listener.getsockname()[1]
        environment.update(
            {
                "DATABASE_URL": "sqlite:///./data/smoke.db",
                "AUDIO_DIR": "./audio_files",
                "APP_REVISION": revision,
                "PUBLIC_BASE_URL": f"http://127.0.0.1:{port}",
            }
        )
        for command in (
            ("alembic", "upgrade", "head"),
            ("scripts.seed_bat_trang",),
            ("scripts.check_offline_tts",),
            ("scripts.seed_bat_trang",),
        ):
            subprocess.run([str(python), "-m", *command], cwd=release, env=environment, check=True)
        with (Path(temporary) / "server.log").open("w+", encoding="utf-8") as log:
            process = subprocess.Popen(
                [
                    str(python),
                    "-m",
                    "uvicorn",
                    "app.main:app",
                    "--host",
                    "127.0.0.1",
                    "--port",
                    str(port),
                ],
                cwd=release,
                env=environment,
                stdout=log,
                stderr=subprocess.STDOUT,
            )
            base = environment["PUBLIC_BASE_URL"]
            try:
                for _ in range(60):
                    if process.poll() is not None:
                        raise RuntimeError("Packaged server exited before becoming healthy")
                    try:
                        with urllib.request.urlopen(base + "/health", timeout=2) as response:
                            assert response.headers["X-App-Revision"] == revision
                            assert json.load(response) == {"status": "ok"}
                        break
                    except (OSError, urllib.error.URLError):
                        time.sleep(1)
                else:
                    raise RuntimeError("Packaged server health check timed out")
                with urllib.request.urlopen(base + "/narration/catalog", timeout=5) as response:
                    assert len(json.load(response)) == 5
                for path in ("/", "/admin", "/static/admin/script.js", "/share/qr.png"):
                    with urllib.request.urlopen(base + path, timeout=5) as response:
                        assert response.status == 200
                try:
                    urllib.request.urlopen(base + "/api/admin/dashboard", timeout=5)
                except urllib.error.HTTPError as error:
                    assert error.code == 401
                else:
                    raise AssertionError("Admin dashboard must require authentication")
            except Exception:
                log.flush()
                log.seek(0)
                print(log.read())
                raise
            finally:
                process.terminate()
                try:
                    process.wait(timeout=15)
                except subprocess.TimeoutExpired:
                    process.kill()
                    process.wait(timeout=10)
    print("Windows ZIP smoke test passed")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--archive", required=True, type=Path)
    parser.add_argument("--revision", required=True)
    args = parser.parse_args()
    smoke(args.archive, args.revision)
