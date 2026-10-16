from app.modules.poi.service import haversine_distance_m, validate_coordinates
from app.core.exceptions import AppError
import pytest


def test_haversine_same_point_is_zero():
    assert haversine_distance_m(10.0, 106.0, 10.0, 106.0) == pytest.approx(0)


def test_haversine_known_distance_is_reasonable():
    # Khoảng 111 km cho một độ vĩ tuyến.
    assert haversine_distance_m(0, 0, 1, 0) == pytest.approx(111_195, rel=0.01)


@pytest.mark.parametrize("lat,lon", [(91, 0), (-91, 0), (0, 181), (0, -181)])
def test_invalid_coordinates_raise_app_error(lat, lon):
    with pytest.raises(AppError):
        validate_coordinates(lat, lon)
