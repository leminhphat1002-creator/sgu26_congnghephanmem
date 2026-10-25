"""Tải một lần các giọng Piper đã ghim phiên bản và kiểm tra SHA-256."""

import argparse
import hashlib
import json
import os
import tempfile
import urllib.request
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
MANIFEST = ROOT / "app" / "modules" / "audio" / "offline_voices.json"


def verify(path: Path, expected: str) -> bool:
    if not path.is_file():
        return False
    with path.open("rb") as stream:
        return hashlib.file_digest(stream, "sha256").hexdigest() == expected


def download(entry: dict, directory: Path) -> None:
    name = entry["filename"]
    if Path(name).name != name:
        raise ValueError("Invalid voice filename")
    destination = directory / name
    if verify(destination, entry["sha256"]):
        print(f"Verified: {name}", flush=True)
        return
    descriptor, filename = tempfile.mkstemp(prefix=".download-", dir=directory)
    temporary = Path(filename)
    try:
        with os.fdopen(descriptor, "wb") as target:
            with urllib.request.urlopen(entry["url"], timeout=60) as response:
                while block := response.read(1024 * 1024):
                    target.write(block)
        if not verify(temporary, entry["sha256"]):
            raise ValueError(f"Checksum mismatch: {name}")
        temporary.replace(destination)
        print(f"Downloaded and verified: {name}", flush=True)
    finally:
        temporary.unlink(missing_ok=True)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--directory", type=Path, default=ROOT / "tts_models")
    args = parser.parse_args()
    args.directory.mkdir(parents=True, exist_ok=True)
    manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))
    files = [file for voice in manifest["voices"].values() for file in voice["files"]]
    with ThreadPoolExecutor(max_workers=3) as executor:
        list(executor.map(lambda entry: download(entry, args.directory), files))
    print("Offline voices ready: vi / en / ja.")


if __name__ == "__main__":
    main()
