import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session
from sqlalchemy.pool import StaticPool

from app.core.db import Base
from app.modules.poi import repository
from app.modules.poi.service import (
    DEFAULT_RADIUS_METERS,
    choose_activation,
    find_nearby,
    haversine,
)


def test_haversine_same_location():
    assert haversine(10.0, 106.0, 10.0, 106.0) == 0


def test_haversine_returns_meters():
    # Khoảng cách một độ kinh tuyến ở xích đạo xấp xỉ 111 km.
    distance = haversine(0.0, 0.0, 0.0, 1.0)
    assert 111_000 < distance < 112_000


def test_haversine_rejects_invalid_latitude():
    with pytest.raises(ValueError):
        haversine(91.0, 106.0, 10.0, 106.0)


def test_haversine_rejects_invalid_longitude():
    with pytest.raises(ValueError):
        haversine(10.0, 181.0, 10.0, 106.0)


def test_default_activation_radius_is_80_meters():
    assert DEFAULT_RADIUS_METERS == 80.0


def test_activation_inside_radius():
    assert choose_activation(50.0) is True


def test_activation_at_boundary():
    assert choose_activation(80.0) is True


def test_activation_outside_radius():
    assert choose_activation(81.0) is False


def test_activation_rejects_negative_distance():
    with pytest.raises(ValueError):
        choose_activation(-1.0)


@pytest.fixture
def db_session():
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)

    with Session(engine) as session:
        yield session

    Base.metadata.drop_all(engine)
    engine.dispose()


def test_create_and_get_location(db_session):
    location = repository.create_location(
        db_session,
        name="Dinh Độc Lập",
        latitude=10.0,
        longitude=106.0,
    )

    result = repository.get_location(db_session, location.id)

    assert result is not None
    assert result.name == "Dinh Độc Lập"
    assert result.radius == 80.0


def test_list_locations(db_session):
    repository.create_location(db_session, name="Địa điểm A")
    repository.create_location(db_session, name="Địa điểm B")

    locations = repository.list_locations(db_session)

    assert len(locations) == 2
    assert locations[0].name == "Địa điểm A"


def test_update_location(db_session):
    location = repository.create_location(
        db_session,
        name="Tên cũ",
    )

    updated = repository.update_location(
        db_session,
        location.id,
        name="Tên mới",
    )

    assert updated is not None
    assert updated.name == "Tên mới"


def test_delete_location(db_session):
    location = repository.create_location(
        db_session,
        name="Địa điểm cần xóa",
    )

    assert repository.delete_location(db_session, location.id) is True
    assert repository.get_location(db_session, location.id) is None


def test_update_missing_location_returns_none(db_session):
    assert (
        repository.update_location(
            db_session,
            999,
            name="Không tồn tại",
        )
        is None
    )


def test_find_nearby_filters_by_distance(db_session):
    repository.create_location(
        db_session,
        name="Gần",
        latitude=10.0,
        longitude=106.001,
    )
    repository.create_location(
        db_session,
        name="Xa",
        latitude=10.0,
        longitude=106.01,
    )
    repository.create_location(
        db_session,
        name="Không có GPS",
    )

    results = find_nearby(db_session, 10.0, 106.0)

    names = [location.name for location, distance in results]

    assert "Gần" in names
    assert "Xa" not in names
    assert "Không có GPS" not in names


def test_find_nearby_sorts_nearest_first(db_session):
    repository.create_location(
        db_session,
        name="Xa hơn",
        latitude=10.0,
        longitude=106.002,
    )
    repository.create_location(
        db_session,
        name="Gần hơn",
        latitude=10.0,
        longitude=106.001,
    )

    results = find_nearby(db_session, 10.0, 106.0)

    assert results[0][0].name == "Gần hơn"
    assert results[0][1] < results[1][1]
