"""Build a Windows x64/Python 3.12 release with the exact dependency wheels for CD."""

import argparse
import json
import os
import shutil
import struct
import subprocess
import sys
import tempfile
import zipfile
from pathlib import Path

from deploy.windows_release import digest, validate_revision
from scripts.setup_offline_tts import MANIFEST, verify

ROOT = Path(__file__).resolve().parents[1]


def build(revision, output):
    validate_revision(revision)
    if os.name != "nt" or sys.version_info[:2] != (3, 12) or struct.calcsize("P") != 8:
        raise RuntimeError("Build this release on Windows x64 with Python 3.12")
    output = Path(output).resolve()
    output.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix="bat-trang-build-") as temporary:
        stage = Path(temporary)
        # Explicit allowlist: no runtime DB, .env, admin passwords or local venv.
        for name in ("app", "migrations", "scripts", "deploy"):
            shutil.copytree(
                ROOT / name,
                stage / name,
                ignore=shutil.ignore_patterns("__pycache__", "*.pyc", ".env"),
            )
        for name in ("requirements.txt", "alembic.ini"):
            shutil.copy2(ROOT / name, stage / name)
        voices = json.loads(MANIFEST.read_text(encoding="utf-8"))["voices"]
        (stage / "tts_models").mkdir()
        for voice in voices.values():
            for entry in voice["files"]:
                source = ROOT / "tts_models" / entry["filename"]
                if not verify(source, entry["sha256"]):
                    raise RuntimeError("Run python -m scripts.setup_offline_tts before building")
                shutil.copy2(source, stage / "tts_models" / source.name)
        subprocess.run(
            [
                sys.executable,
                "-m",
                "pip",
                "download",
                "--only-binary=:all:",
                "--dest",
                str(stage / "wheelhouse"),
                "-r",
                str(stage / "requirements.txt"),
            ],
            check=True,
        )
        hashes = {
            path.relative_to(stage).as_posix(): digest(path)
            for path in sorted(stage.rglob("*"))
            if path.is_file()
        }
        (stage / "release.json").write_text(
            json.dumps(
                {"revision": revision, "platform": "win_amd64", "python": "3.12", "files": hashes},
                indent=2,
            ),
            encoding="utf-8",
        )
        with zipfile.ZipFile(output, "w", zipfile.ZIP_DEFLATED) as bundle:
            for path in sorted(stage.rglob("*")):
                if path.is_file():
                    bundle.write(path, path.relative_to(stage).as_posix())
    output.with_suffix(".zip.sha256").write_text(digest(output) + "\n", encoding="ascii")
    print(f"Windows release: {output.name}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--revision", required=True)
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()
    build(args.revision, args.output)
