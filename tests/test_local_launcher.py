"""Configuration, read-only preflight and native Windows launch failures."""

import json
import os
import socket
import subprocess
import sys
from pathlib import Path

import pytest
from alembic import command
from alembic.config import Config
from sqlalchemy import create_engine, text
from sqlalchemy.engine import make_url

from scripts.run_local import ROOT, check_database, load_configuration, require_free_port


def test_saved_config_environment_and_cli_use_stable_absolute_paths(tmp_path, monkeypatch):
    root = tmp_path / "project with spaces"
    root.mkdir()
    filename = root / "settings.json"
    filename.write_text(json.dumps({"PORT": 8020, "AUDIO_DIR": "recordings"}), encoding="utf-8")
    monkeypatch.chdir(tmp_path)
    config = load_configuration(root, filename, {"PORT": "8030"}, {"PORT": 8040})
    assert config["PORT"] == "8040"
    assert config["PUBLIC_BASE_URL"] == "http://127.0.0.1:8040"
    assert config["AUDIO_DIR"] == str(root / "recordings")
    assert Path(make_url(config["DATABASE_URL"]).database) == root / "data" / "app.db"
    assert config["PIPER_MODEL_DIR"] == str(root / "tts_models")
    assert load_configuration(root, filename, {"PORT": "8030"}, {})["PORT"] == "8030"
    assert load_configuration(root, filename, {}, {})["PORT"] == "8020"


@pytest.mark.parametrize(
    "saved",
    [
        {"PORT": True},
        {"PORT": 8010.0},
        {"PORT": 80},
        {"PORT": 65536},
        {"PUBLIC_BASE_URL": "https://example.org/admin"},
        {"PUBLIC_BASE_URL": "https://user:secret@example.org"},
        {"PUBLIC_BASE_URL": "https://example.org/?a=b"},
        {"PUBLIC_BASE_URL": "https://example.org/#part"},
        {"PUBLIC_BASE_URL": "https://example.org?"},
        {"PUBLIC_BASE_URL": "https://example.org#"},
        {"PUBLIC_BASE_URL": "https://example.org:99999"},
        {"PUBLIC_BASE_URL": "https://example.org\n"},
        {"PUBLIC_BASE_URL": "file:///etc"},
        {"PUBLIC_BASE_URL": None},
        {"AUDIO_DIR": ""},
        {"BIND_HOST": "invalid.example.org"},
        {"TRUSTED_PROXY_IPS": "*"},
        {"DATABASE_URL": "sqlite:///:memory:"},
        {"PUBLIC_URL_TYPO": "https://example.org"},
    ],
)
def test_invalid_configuration_is_rejected_before_startup(tmp_path, saved):
    filename = tmp_path / "settings.json"
    filename.write_text(json.dumps(saved), encoding="utf-8")
    with pytest.raises(ValueError):
        load_configuration(tmp_path, filename, {}, {})


def test_missing_database_does_not_create_file_or_directory(tmp_path):
    target = tmp_path / "missing directory" / "app.db"
    with pytest.raises(ValueError, match="Database missing"):
        check_database(f"sqlite:///{target.as_posix()}")
    assert not target.parent.exists()


def test_preflight_checks_schema_and_preserves_existing_records(tmp_path, monkeypatch):
    target = tmp_path / "catalog #1.db"
    url = f"sqlite:///{target.as_posix()}"
    monkeypatch.setenv("DATABASE_URL", url)
    config = Config(str(ROOT / "alembic.ini"))
    config.set_main_option("script_location", str(ROOT / "migrations"))
    command.upgrade(config, "head")
    engine = create_engine(url)
    with engine.begin() as connection:
        connection.execute(
            text(
                "INSERT INTO admin_users (username, password_hash) VALUES ('manager', 'test-only')"
            )
        )
        connection.execute(
            text("INSERT INTO locations (name, is_ready) VALUES ('Edited place', 1)")
        )
        connection.execute(
            text(
                "INSERT INTO poi_narrations (location_id, language, title, content) "
                "VALUES (1, 'vi', 'Edited title', 'Edited content')"
            )
        )
    before = target.read_bytes()
    assert check_database(url) == {"admins": 1, "locations": 1, "narrations": 1}
    assert target.read_bytes() == before
    with engine.begin() as connection:
        connection.execute(text("UPDATE alembic_version SET version_num='old-unknown'"))
    before = target.read_bytes()
    with pytest.raises(ValueError, match="migration is outdated"):
        check_database(url)
    assert target.read_bytes() == before
    engine.dispose()


def test_occupied_port_reports_failure_without_stopping_listener():
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as listener:
        listener.bind(("127.0.0.1", 0))
        listener.listen()
        host, port = listener.getsockname()
        with pytest.raises(ValueError, match="Stop the existing app"):
            require_free_port(host, port)
        assert listener.getsockname() == (host, port)


@pytest.mark.skipif(os.name != "nt", reason="Native Windows launcher")
def test_powershell_wrapper_works_from_another_directory_and_propagates_failure(tmp_path):
    settings = tmp_path / "settings with spaces.json"
    settings.write_text(
        json.dumps({"DATABASE_URL": f"sqlite:///{(tmp_path / 'missing.db').as_posix()}"}),
        encoding="utf-8",
    )
    environment = os.environ.copy()
    for key in ("DATABASE_URL", "PUBLIC_BASE_URL", "PORT"):
        environment.pop(key, None)
    result = subprocess.run(
        [
            str(Path(os.environ["SystemRoot"]) / "System32/WindowsPowerShell/v1.0/powershell.exe"),
            "-NoProfile",
            "-NonInteractive",
            "-ExecutionPolicy",
            "Bypass",
            "-File",
            str(ROOT / "scripts" / "run_local.ps1"),
            "-PythonPath",
            sys.executable,
            "-ConfigPath",
            str(settings),
            "-CheckOnly",
        ],
        cwd=tmp_path,
        env=environment,
        capture_output=True,
        text=True,
        timeout=30,
    )
    assert result.returncode == 1, result.stdout + result.stderr
    assert "Database missing" in result.stderr
    assert not (tmp_path / "missing.db").exists()
