"""Windows release ZIP verification and offline installation (standard library only)."""

import hashlib
import json
import os
import re
import struct
import subprocess
import sys
import zipfile
from pathlib import Path, PurePosixPath, PureWindowsPath


def validate_revision(revision):
    if not re.fullmatch(r"[0-9a-f]{40}", revision):
        raise ValueError("Expected a full lowercase Git commit SHA")


def digest(path):
    with Path(path).open("rb") as stream:
        return hashlib.file_digest(stream, "sha256").hexdigest()


def verify(archive, revision):
    validate_revision(revision)
    with zipfile.ZipFile(archive) as bundle:
        names = bundle.namelist()
        folded = set()
        for name in names:
            parts = PurePosixPath(name).parts
            if (
                not parts
                or name.startswith("/")
                or "\\" in name
                or ":" in name
                or any(
                    part in {".", ".."}
                    or part.endswith((".", " "))
                    or PureWindowsPath(part).is_reserved()
                    or any(character in part for character in '<>"|?*')
                    for part in parts
                )
                or name.casefold() in folded
                or bundle.getinfo(name).is_dir()
            ):
                raise ValueError("Unsafe or duplicate archive member")
            folded.add(name.casefold())
        metadata = json.loads(bundle.read("release.json"))
        if (
            metadata.get("revision") != revision
            or metadata.get("platform") != "win_amd64"
            or metadata.get("python") != "3.12"
        ):
            raise ValueError("Release revision/platform/Python mismatch")
        hashes = metadata["files"]
        if set(names) != set(hashes) | {"release.json"}:
            raise ValueError("Release contains unlisted or missing files")
        for name, expected in hashes.items():
            if hashlib.sha256(bundle.read(name)).hexdigest() != expected:
                raise ValueError(f"Release checksum mismatch: {name}")
        if not any(name.startswith("wheelhouse/") and name.endswith(".whl") for name in names):
            raise ValueError("Release has no Windows dependency wheels")
        return metadata


def extract(archive, destination, revision):
    verify(archive, revision)
    destination = Path(destination)
    destination.mkdir(parents=True, exist_ok=False)
    with zipfile.ZipFile(archive) as bundle:
        bundle.extractall(destination)


def install(release):
    if os.name != "nt" or sys.version_info[:2] != (3, 12) or struct.calcsize("P") != 8:
        raise RuntimeError("Use Windows x64 with Python 3.12")
    release = Path(release)
    subprocess.run([sys.executable, "-m", "venv", str(release / ".venv")], check=True)
    python = release / ".venv" / "Scripts" / "python.exe"
    subprocess.run(
        [
            str(python),
            "-m",
            "pip",
            "install",
            "--no-index",
            "--find-links",
            str(release / "wheelhouse"),
            "-r",
            str(release / "requirements.txt"),
        ],
        check=True,
    )
    return python
