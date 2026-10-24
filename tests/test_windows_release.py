"""Reject tampered packages, wrong revisions and Windows path traversal before extraction."""

import hashlib
import json
import zipfile

import pytest

from deploy.windows_release import extract, verify

REVISION = "b" * 40


def bundle(tmp_path, files=None, revision=REVISION, tamper=False):
    files = files or {"app/main.py": b"sample", "wheelhouse/dependency.whl": b"wheel"}
    metadata = {
        "revision": revision,
        "platform": "win_amd64",
        "python": "3.12",
        "files": {name: hashlib.sha256(data).hexdigest() for name, data in files.items()},
    }
    path = tmp_path / "package.zip"
    with zipfile.ZipFile(path, "w") as archive:
        for name, data in files.items():
            archive.writestr(name, data + (b"changed" if tamper else b""))
        archive.writestr("release.json", json.dumps(metadata))
    return path


def test_valid_archive_extracts_to_new_directory(tmp_path):
    archive = bundle(tmp_path)
    destination = tmp_path / "release"
    extract(archive, destination, REVISION)
    assert (destination / "app" / "main.py").read_bytes() == b"sample"
    with pytest.raises(FileExistsError):
        extract(archive, destination, REVISION)


def test_wrong_revision_is_rejected_before_extraction(tmp_path):
    archive = bundle(tmp_path, revision="a" * 40)
    destination = tmp_path / "release"
    with pytest.raises(ValueError, match="mismatch"):
        extract(archive, destination, REVISION)
    assert not destination.exists()


def test_tampered_contents_are_rejected(tmp_path):
    with pytest.raises(ValueError, match="checksum"):
        verify(bundle(tmp_path, tamper=True), REVISION)


@pytest.mark.parametrize(
    "name",
    [
        "../secret",
        "C:/secret",
        "app\\secret",
        "APP/main.py",
        "app/trailing. /file",
        "app/CON.txt",
        "app/invalid?.py",
    ],
)
def test_windows_unsafe_paths_and_case_aliases_are_rejected(tmp_path, name):
    archive = bundle(tmp_path, {"app/main.py": b"sample", name: b"injected"})
    with pytest.raises(ValueError, match="Unsafe|unlisted"):
        verify(archive, REVISION)


def test_unlisted_file_is_rejected(tmp_path):
    archive = bundle(tmp_path)
    with zipfile.ZipFile(archive, "a") as output:
        output.writestr(".env", "SECRET=value")
    with pytest.raises(ValueError, match="unlisted"):
        verify(archive, REVISION)
