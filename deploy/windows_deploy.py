"""Deploy a CI-tested Windows ZIP to a preconfigured WinSW service, with SQLite rollback."""

import argparse
import contextlib
import json
import os
import re
import subprocess
import time
import urllib.error
import urllib.request
import uuid
from pathlib import Path
from urllib.parse import urlsplit

from deploy.service_host import read_release, runtime_environment
from deploy.windows_release import extract, install, validate_revision


def write_state(path, state):
    temporary = path.with_suffix(".tmp")
    temporary.write_text(json.dumps(state), encoding="utf-8")
    temporary.replace(path)


class WindowsService:
    def __init__(self, name):
        if not re.fullmatch(r"[a-zA-Z0-9_-]+", name):
            raise ValueError("Invalid Windows service name")
        self.name = name

    def change(self, action):
        # Name is passed as an environment variable, never interpolated as PowerShell code.
        environment = os.environ.copy()
        environment["BAT_TRANG_SERVICE"] = self.name
        state = "Stopped" if action == "stop" else "Running"
        command = "Stop-Service" if action == "stop" else "Start-Service"
        powershell = (
            Path(os.environ["SystemRoot"]) / "System32/WindowsPowerShell/v1.0/powershell.exe"
        )
        subprocess.run(
            [
                str(powershell),
                "-NoProfile",
                "-NonInteractive",
                "-Command",
                "$ErrorActionPreference = 'Stop'; "
                f"{command} -Name $env:BAT_TRANG_SERVICE; "
                "$service = Get-Service -Name $env:BAT_TRANG_SERVICE; "
                f"$service.WaitForStatus('{state}', [TimeSpan]::FromSeconds(90))",
            ],
            env=environment,
            check=True,
            timeout=120,
        )


def wait_health(base, revision, attempts=60):
    for _ in range(attempts):
        try:
            request = urllib.request.Request(
                base.rstrip("/") + "/health", headers={"Cache-Control": "no-cache"}
            )
            with urllib.request.urlopen(request, timeout=5) as response:
                if (
                    response.status == 200
                    and response.headers.get("X-App-Revision") == revision
                    and json.load(response) == {"status": "ok"}
                ):
                    return
        except (OSError, ValueError, urllib.error.URLError):
            pass
        time.sleep(2)
    raise RuntimeError("Health check did not return the expected release revision")


@contextlib.contextmanager
def deployment_lock(root):
    import msvcrt

    root.mkdir(parents=True, exist_ok=True)
    with (root / "deploy.lock").open("a+b") as lock:
        lock.seek(0)
        lock.write(b"0")
        lock.flush()
        lock.seek(0)
        msvcrt.locking(lock.fileno(), msvcrt.LK_NBLCK, 1)
        try:
            yield
        finally:
            lock.seek(0)
            msvcrt.locking(lock.fileno(), msvcrt.LK_UNLCK, 1)


def deploy(archive, root, revision, sequence, service, health=wait_health):
    """Caller holds deployment_lock. Dependency preparation happens before stopping service."""
    validate_revision(revision)
    if sequence < 1:
        raise ValueError("Invalid CI run sequence")
    root = Path(root).resolve()
    environment = runtime_environment(root)
    parsed = urlsplit(environment["PUBLIC_BASE_URL"])
    if (
        parsed.scheme not in {"http", "https"}
        or not parsed.hostname
        or parsed.username
        or parsed.password
        or parsed.query
        or parsed.fragment
        or parsed.path not in {"", "/"}
    ):
        raise ValueError("Set PUBLIC_BASE_URL to an HTTP/HTTPS origin")
    if parsed.scheme != "https" and parsed.hostname not in {"127.0.0.1", "localhost"}:
        raise ValueError("Public deployment requires HTTPS")
    pointer = root / "current-release.json"
    previous = None
    if pointer.exists():
        previous, _ = read_release(root)
        if sequence < previous["sequence"]:
            raise ValueError("Refusing to deploy an older CI run")
    release = root / "releases" / f"{revision}-{uuid.uuid4().hex[:8]}"
    extract(archive, release, revision)
    python = install(release)

    def run(*args):
        return subprocess.run(
            [str(python), "-m", *args],
            cwd=release,
            env=environment,
            check=True,
            capture_output=True,
            text=True,
        )

    database = root / "data" / "app.db"
    backup_name = f"deploy-{revision}-{uuid.uuid4().hex}.db"
    created_backup = False
    changed_database = False
    service.change("stop")
    existed = database.exists()
    try:
        backup = run("scripts.database_snapshot", "backup", backup_name).stdout.strip()
        if backup not in {"created", "skipped"}:
            raise RuntimeError("Unexpected database backup result")
        created_backup = backup == "created"
        if existed and not created_backup:
            raise RuntimeError("Existing database was not backed up; refusing migration")
        changed_database = True
        run("alembic", "upgrade", "head")
        if not existed:
            run("scripts.seed_bat_trang")
        state = {
            "revision": revision,
            "sequence": sequence,
            "release": release.relative_to(root).as_posix(),
        }
        write_state(pointer, state)
        service.change("start")
        health(f"http://127.0.0.1:{environment['PORT']}", revision)
        health(environment["PUBLIC_BASE_URL"], revision)
    except Exception as failure:
        try:
            # Never restore a database while the candidate service may still write to it.
            service.change("stop")
            if changed_database and created_backup:
                run("scripts.database_snapshot", "restore", backup_name)
            elif changed_database and not existed:
                # Only the explicitly named, newly created DB and its sidecars are removed.
                for path in (database, Path(str(database) + "-wal"), Path(str(database) + "-shm")):
                    path.unlink(missing_ok=True)
            if previous:
                write_state(pointer, previous)
                service.change("start")
                health(f"http://127.0.0.1:{environment['PORT']}", previous["revision"])
            else:
                pointer.unlink(missing_ok=True)
        except Exception as recovery:
            raise RuntimeError("Deployment failed; recovery needs manual attention") from recovery
        raise RuntimeError("Deployment failed; previous release restored (if present)") from failure
    print(f"Windows deployment verified: {revision}")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--archive", required=True, type=Path)
    parser.add_argument("--root", required=True, type=Path)
    parser.add_argument("--revision", required=True)
    parser.add_argument("--sequence", required=True, type=int)
    parser.add_argument("--service", default="BatTrangGuide")
    args = parser.parse_args()
    if os.name != "nt":
        parser.error("This deployment target must run Windows")
    with deployment_lock(args.root.resolve()):
        deploy(args.archive, args.root, args.revision, args.sequence, WindowsService(args.service))


if __name__ == "__main__":
    main()
