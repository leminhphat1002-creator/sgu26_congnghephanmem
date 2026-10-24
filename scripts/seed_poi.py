"""Lệnh seed cũ nay chỉ bổ sung dữ liệu Bát Tràng."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.core.db import get_sessionmaker
from scripts.seed_bat_trang import seed


def main() -> None:
    with get_sessionmaker()() as session:
        seed(session)
    print("Bat Trang demo data ready; existing content preserved.")


if __name__ == "__main__":
    main()
