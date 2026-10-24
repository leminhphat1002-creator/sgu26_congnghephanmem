"""Windows deployment recovery; service operations are simulated, SQLite backups are real."""

import json
import sqlite3
import subprocess
from contextlib import closing

import pytest

from deploy import windows_deploy as target
from scripts.database_snapshot import restore, snapshot

REVISION = "b" * 40
OLD = "a" * 40


def test_database_backup_and_restore_preserves_committed_data(tmp_path):
    database, saved = tmp_path / "app.db", tmp_path / "backups" / "release.db"
    assert not snapshot(database, saved)
    with closing(sqlite3.connect(database)) as db, db:
        db.execute("CREATE TABLE content (value TEXT)")
        db.execute("INSERT INTO content VALUES ('before migration')")
    assert snapshot(database, saved)
    with pytest.raises(FileExistsError):
        snapshot(database, saved)
    with closing(sqlite3.connect(database)) as db, db:
        db.execute("UPDATE content SET value='after migration'")
        db.execute("CREATE TABLE new_schema (id INTEGER)")
    restore(database, saved)
    with closing(sqlite3.connect(database)) as db:
        assert db.execute("SELECT value FROM content").fetchone()[0] == "before migration"
        assert not db.execute("SELECT name FROM sqlite_master WHERE name='new_schema'").fetchone()
    with pytest.raises(FileNotFoundError):
        restore(database, tmp_path / "missing.db")


@pytest.fixture
def deployment(tmp_path, monkeypatch):
    root = tmp_path / "server with spaces"
    root.mkdir()
    (root / "settings.json").write_text(json.dumps({"PUBLIC_BASE_URL": "https://guide.test"}))
    (root / "releases" / OLD).mkdir(parents=True)
    previous = {"revision": OLD, "sequence": 10, "release": f"releases/{OLD}"}
    target.write_state(root / "current-release.json", previous)
    (root / "data").mkdir()
    database = root / "data" / "app.db"
    with closing(sqlite3.connect(database)) as connection, connection:
        connection.execute("CREATE TABLE notes (text TEXT)")
        connection.execute("INSERT INTO notes VALUES ('original')")
    calls = []
    failure = {"stage": None}

    def extract(archive, release, revision):
        calls.append("extract")
        if failure["stage"] == "extract":
            raise ValueError("Checksum failure")
        release.mkdir(parents=True)

    def install(release):
        calls.append("install")
        if failure["stage"] == "install":
            raise RuntimeError("Dependency installation failure")
        return release / ".venv" / "Scripts" / "python.exe"

    def run(command, **kwargs):
        module, *args = command[2:]
        if module == "scripts.database_snapshot":
            action, name = args
            calls.append(action)
            if action == "backup":
                if failure["stage"] == "backup":
                    raise subprocess.CalledProcessError(1, command)
                result = snapshot(database, database.parent / "backups" / name)
                return subprocess.CompletedProcess(command, 0, "created" if result else "skipped")
            restore(database, database.parent / "backups" / name)
        elif module == "alembic":
            calls.append("migrate")
            with closing(sqlite3.connect(database)) as connection, connection:
                connection.execute("CREATE TABLE candidate_schema (id INTEGER)")
                if (
                    database.exists()
                    and connection.execute(
                        "SELECT name FROM sqlite_master WHERE name='notes'"
                    ).fetchone()
                ):
                    connection.execute("UPDATE notes SET text='changed'")
            if failure["stage"] == "migration":
                raise subprocess.CalledProcessError(1, command)
        elif module == "scripts.seed_bat_trang":
            calls.append("seed")
        return subprocess.CompletedProcess(command, 0, "")

    class Service:
        def change(self, action):
            calls.append(action)
            if action == "stop" and failure["stage"] == "cannot-stop":
                raise RuntimeError("Service cannot be stopped")

    def health(base, revision):
        calls.append(f"health:{revision}")
        if revision == REVISION and (
            failure["stage"] == "health"
            or failure["stage"] == "public-health"
            and base.startswith("https")
        ):
            raise RuntimeError("Wrong health revision")

    monkeypatch.setattr(target, "extract", extract)
    monkeypatch.setattr(target, "install", install)
    monkeypatch.setattr(target.subprocess, "run", run)

    def deploy(stage=None, sequence=11):
        failure["stage"] = stage
        return target.deploy("package.zip", root, REVISION, sequence, Service(), health)

    return root, database, calls, deploy, previous


def test_healthy_release_updates_pointer_and_preserves_existing_data(deployment):
    root, _, calls, deploy, _ = deployment
    deploy()
    assert json.loads((root / "current-release.json").read_text())["revision"] == REVISION
    assert "seed" not in calls
    assert calls.index("install") < calls.index("stop") < calls.index("backup")


@pytest.mark.parametrize("stage", ["migration", "health", "public-health"])
def test_failed_release_restores_database_and_previous_release(deployment, stage):
    root, database, calls, deploy, previous = deployment
    with pytest.raises(RuntimeError, match="previous release restored"):
        deploy(stage)
    assert json.loads((root / "current-release.json").read_text()) == previous
    with closing(sqlite3.connect(database)) as connection:
        assert connection.execute("SELECT text FROM notes").fetchone()[0] == "original"
        assert not connection.execute(
            "SELECT name FROM sqlite_master WHERE name='candidate_schema'"
        ).fetchone()
    assert calls.index("restore") < len(calls) - 1
    assert calls[-1] == f"health:{OLD}"


@pytest.mark.parametrize("stage", ["extract", "install"])
def test_preparation_failure_does_not_stop_current_app(deployment, stage):
    _, _, calls, deploy, _ = deployment
    with pytest.raises((ValueError, RuntimeError)):
        deploy(stage)
    assert "stop" not in calls


def test_failed_backup_blocks_migration_and_restarts_old_app(deployment):
    _, _, calls, deploy, _ = deployment
    with pytest.raises(RuntimeError):
        deploy("backup")
    assert "migrate" not in calls and "restore" not in calls
    assert calls[-1] == f"health:{OLD}"


def test_stale_deploy_never_stops_app(deployment):
    _, _, calls, deploy, _ = deployment
    with pytest.raises(ValueError, match="older CI run"):
        deploy(sequence=9)
    assert not calls


def test_first_deploy_failure_removes_only_new_database(deployment):
    root, database, calls, deploy, _ = deployment
    (root / "current-release.json").unlink()
    database.unlink()
    with pytest.raises(RuntimeError):
        deploy("health")
    assert "seed" in calls
    assert not database.exists()
    assert not (root / "current-release.json").exists()


def test_first_deploy_seeds_once(deployment):
    root, database, calls, deploy, _ = deployment
    (root / "current-release.json").unlink()
    database.unlink()
    deploy()
    assert calls.count("seed") == 1


def test_cannot_stop_service_never_changes_database(deployment):
    _, _, calls, deploy, _ = deployment
    with pytest.raises(RuntimeError, match="cannot be stopped"):
        deploy("cannot-stop")
    assert "backup" not in calls and "migrate" not in calls


def test_release_pointer_cannot_escape_server_root(tmp_path):
    target.write_state(tmp_path / "current-release.json", {"release": "../other"})
    with pytest.raises(ValueError, match="inside server releases"):
        target.read_release(tmp_path)


def test_health_does_not_accept_a_healthy_old_release(monkeypatch):
    class Response:
        status = 200
        headers = {"X-App-Revision": OLD}

        def __enter__(self):
            return self

        def __exit__(self, *args):
            pass

    monkeypatch.setattr(target.urllib.request, "urlopen", lambda *a, **k: Response())
    monkeypatch.setattr(target.time, "sleep", lambda _: None)
    with pytest.raises(RuntimeError, match="expected release revision"):
        target.wait_health("http://localhost:8010", REVISION, attempts=1)
