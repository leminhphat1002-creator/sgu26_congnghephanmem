"""Stable WinSW entry point. Copied to the server once; no third-party imports."""

import json
import os
import subprocess
import sys
from pathlib import Path


def runtime_environment(root):
    root = Path(root).resolve()
    config = json.loads((root / "settings.json").read_text(encoding="utf-8-sig"))
    port = int(config.get("PORT", 8010))
    if not 1024 <= port <= 65535:
        raise ValueError("PORT must be between 1024 and 65535")
    environment = os.environ.copy()
    environment.update(
        {
            "DATABASE_URL": f"sqlite:///{(root / 'data' / 'app.db').as_posix()}",
            "AUDIO_DIR": str(root / "audio_files"),
            "PUBLIC_BASE_URL": config["PUBLIC_BASE_URL"],
            "PORT": str(port),
            "BIND_HOST": config.get("BIND_HOST", "127.0.0.1"),
            "TRUSTED_PROXY_IPS": config.get("TRUSTED_PROXY_IPS", "127.0.0.1"),
        }
    )
    return environment


def read_release(root):
    root = Path(root).resolve()
    state = json.loads((root / "current-release.json").read_text(encoding="utf-8"))
    release = (root / state["release"]).resolve()
    if release.parent != root / "releases":
        raise ValueError("Release directory must be directly inside server releases")
    return state, release


def main(root):
    state, release = read_release(root)
    environment = runtime_environment(root)
    environment["APP_REVISION"] = state["revision"]
    return subprocess.call(
        [
            str(release / ".venv" / "Scripts" / "python.exe"),
            "-m",
            "uvicorn",
            "app.main:app",
            "--host",
            environment["BIND_HOST"],
            "--port",
            environment["PORT"],
            "--proxy-headers",
            "--forwarded-allow-ips",
            environment["TRUSTED_PROXY_IPS"],
        ],
        cwd=release,
        env=environment,
    )


if __name__ == "__main__":
    raise SystemExit(main(Path(sys.argv[1])))
