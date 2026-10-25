"""Lệnh seed cũ nay chỉ bổ sung dữ liệu Bát Tràng."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from scripts.seed_bat_trang import main

if __name__ == "__main__":
    main()
