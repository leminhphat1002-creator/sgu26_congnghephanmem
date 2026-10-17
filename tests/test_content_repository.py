from datetime import UTC, datetime, timedelta

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from app.core.db import Base
from app.modules.content.models import NarrationCache
from app.modules.content.repository import ContentRepository


@pytest.fixture
def session(tmp_path):
    database_file = tmp_path / "content_test.db"
    engine = create_engine(f"sqlite:///{database_file}")
    Base.metadata.create_all(engine)

    with Session(engine) as db_session:
        yield db_session

    engine.dispose()


def test_save_and_get_cache(session):
    repository = ContentRepository(session)

    saved = repository.save(
        page_title="Ben Thanh Market",
        language="en",
        extract="A market in Ho Chi Minh City.",
        source_url="https://en.wikipedia.org/wiki/B%E1%BA%BFn_Th%C3%A0nh_Market",
    )

    cached = repository.get("Ben Thanh Market", "en")

    assert cached is not None
    assert cached.id == saved.id
    assert cached.extract == "A market in Ho Chi Minh City."
    assert cached.source_url is not None


def test_save_updates_existing_cache(session):
    repository = ContentRepository(session)

    repository.save("Test Page", "vi", "Nội dung cũ")
    repository.save("Test Page", "vi", "Nội dung mới")

    cached = repository.get("Test Page", "vi")

    assert cached is not None
    assert cached.extract == "Nội dung mới"


def test_get_returns_none_when_cache_missing(session):
    repository = ContentRepository(session)

    assert repository.get("Không tồn tại", "vi") is None


def test_get_removes_expired_cache(session):
    expired = NarrationCache(
        page_title="Expired Page",
        language="vi",
        extract="Nội dung hết hạn",
        created_at=datetime.now(UTC).replace(tzinfo=None) - timedelta(hours=2),
        expires_at=datetime.now(UTC).replace(tzinfo=None) - timedelta(hours=1),
    )
    session.add(expired)
    session.commit()

    repository = ContentRepository(session)

    assert repository.get("Expired Page", "vi") is None
    assert session.query(NarrationCache).count() == 0


def test_invalidate_cache(session):
    repository = ContentRepository(session)

    repository.save("Test Page", "vi", "Tiếng Việt")
    repository.save("Test Page", "en", "English")

    deleted = repository.invalidate("Test Page", "vi")

    assert deleted == 1
    assert repository.get("Test Page", "vi") is None
    assert repository.get("Test Page", "en") is not None


def test_save_rejects_non_positive_ttl(session):
    repository = ContentRepository(session)

    with pytest.raises(ValueError, match="ttl_seconds"):
        repository.save("Test Page", "vi", "Nội dung", ttl_seconds=0)
