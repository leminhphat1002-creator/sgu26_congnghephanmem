"""Cấu hình logging cơ bản. Tuần 7 sẽ nâng cấp thành log JSON có request_id."""

from __future__ import annotations

import logging


def setup_logging(level: str = "INFO") -> None:
    logging.basicConfig(
        level=getattr(logging, level.upper(), logging.INFO),
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    )
