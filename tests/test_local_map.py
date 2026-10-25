"""Validate the shipped geographic extract, including the static release path."""

from fastapi.testclient import TestClient

from app.main import app
from scripts.export_bat_trang_map import transform_coordinates
from scripts.seed_bat_trang import load_content


def test_tile_projection_known_equator_and_north():
    assert transform_coordinates([0, 0], 1, 0, 4096, 2) == [0.0, 0.0]
    assert transform_coordinates([0, 4096], 1, 0, 4096, 2) == [0.0, 85.051129]


def test_shipped_background_covers_catalog_and_stays_in_bat_trang():
    with TestClient(app) as client:
        response = client.get("/static/app/bat-trang-basemap.geojson")
    assert response.status_code == 200
    data = response.json()
    west, south, east, north = data["bbox"]
    for poi in load_content()["pois"]:
        assert west < poi["longitude"] < east
        assert south < poi["latitude"] < north
    assert data["metadata"]["license"] == "ODbL-1.0"
    assert len(data["metadata"]["tiles"]) == 4
    layers = {feature["properties"]["layer"] for feature in data["features"]}
    assert {"water", "building", "transportation", "transportation_name"} <= layers

    def validate_geometry(geometry):
        if geometry["type"] == "GeometryCollection":
            for part in geometry["geometries"]:
                validate_geometry(part)
            return

        def validate_coordinates(coords):
            if isinstance(coords[0], int | float):
                lon, lat = coords
                assert west - 0.000001 <= lon <= east + 0.000001
                assert south - 0.000001 <= lat <= north + 0.000001
            else:
                for child in coords:
                    validate_coordinates(child)

        validate_coordinates(geometry["coordinates"])

    for feature in data["features"]:
        validate_geometry(feature["geometry"])
