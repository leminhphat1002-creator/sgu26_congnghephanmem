"""Export a small, attributed OpenFreeMap extract for the local Bát Tràng map.

Optional authoring dependency: mapbox-vector-tile==2.2.0 (not needed by the app).
Only four z14 tiles are downloaded, sequentially, under OpenFreeMap's offline limits.
"""

import json
import math
import urllib.request
from datetime import UTC, datetime
from pathlib import Path

BOUNDS = (105.900, 20.965, 105.930, 20.995)
ROOT = Path(__file__).resolve().parents[1]
USER_AGENT = (
    "BatTrangAudioGuide/0.1 " "(+https://github.com/leminhphat1002-creator/sgu26_congnghephanmem)"
)
LAYERS = (
    "landcover",
    "landuse",
    "park",
    "water",
    "building",
    "waterway",
    "transportation",
    "transportation_name",
)


def download(url):
    request = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    with urllib.request.urlopen(request, timeout=30) as response:
        payload = response.read(5_000_001)
    if len(payload) > 5_000_000:
        raise ValueError("Unexpectedly large map response")
    return payload


def transform_coordinates(coords, x, y, extent, scale):
    """Convert the decoder's y-up tile coordinates from Web Mercator to WGS84."""
    if isinstance(coords[0], int | float):
        px, py = coords[:2]
        longitude = (x + px / extent) / scale * 360 - 180
        latitude = math.degrees(
            math.atan(math.sinh(math.pi * (1 - 2 * (y + 1 - py / extent) / scale)))
        )
        return [round(longitude, 6), round(latitude, 6)]
    return [transform_coordinates(value, x, y, extent, scale) for value in coords]


def export():
    import mapbox_vector_tile
    from shapely.geometry import box, mapping, shape

    metadata = json.loads(download("https://tiles.openfreemap.org/planet"))
    template = metadata["tiles"][0]
    if not template.startswith("https://tiles.openfreemap.org/"):
        raise ValueError("Unexpected map source")
    zoom = 14
    scale = 2**zoom

    def tile(lon, lat):
        return (
            int((lon + 180) / 360 * scale),
            int((1 - math.asinh(math.tan(math.radians(lat))) / math.pi) / 2 * scale),
        )

    xmin, ymax = tile(BOUNDS[0], BOUNDS[1])
    xmax, ymin = tile(BOUNDS[2], BOUNDS[3])
    if (xmax - xmin + 1) * (ymax - ymin + 1) > 4:
        raise ValueError("This exporter is limited to four tiles")
    region = box(*BOUNDS)
    features = []
    sources = []
    for x in range(xmin, xmax + 1):
        for y in range(ymin, ymax + 1):
            url = template.format(z=zoom, x=x, y=y)
            sources.append(url)
            decoded = mapbox_vector_tile.decode(download(url))
            west = x / scale * 360 - 180
            east = (x + 1) / scale * 360 - 180
            north = math.degrees(math.atan(math.sinh(math.pi * (1 - 2 * y / scale))))
            south = math.degrees(math.atan(math.sinh(math.pi * (1 - 2 * (y + 1) / scale))))
            clip = region.intersection(box(west, south, east, north))
            for layer_name in LAYERS:
                layer = decoded.get(layer_name)
                if not layer:
                    continue
                extent = layer["extent"]

                for feature in layer["features"]:
                    geometry = dict(feature["geometry"])
                    geometry["coordinates"] = transform_coordinates(
                        geometry["coordinates"], x, y, extent, scale
                    )
                    geometry = shape(geometry)
                    if not geometry.is_valid:
                        geometry = geometry.buffer(0)
                    geometry = geometry.intersection(clip)
                    if geometry.is_empty:
                        continue
                    properties = feature["properties"]
                    features.append(
                        {
                            "type": "Feature",
                            "properties": {
                                "layer": layer_name,
                                "class": properties.get("class", ""),
                                "name": properties.get("name:vi") or properties.get("name", ""),
                            },
                            "geometry": mapping(geometry),
                        }
                    )
    output = {
        "type": "FeatureCollection",
        "bbox": BOUNDS,
        "metadata": {
            "exported_at": datetime.now(UTC).isoformat(),
            "source": "https://openfreemap.org/quick_start/",
            "tiles": sources,
            "license": "ODbL-1.0",
            "license_url": "https://opendatacommons.org/licenses/odbl/1-0/",
            "attribution": "OpenFreeMap / © OpenMapTiles / © OpenStreetMap contributors",
        },
        "features": features,
    }
    target = ROOT / "app/static/app/bat-trang-basemap.geojson"
    target.write_text(
        json.dumps(output, ensure_ascii=False, separators=(",", ":")), encoding="utf-8"
    )
    print(f"Exported {len(features)} features, {target.stat().st_size:,} bytes")


if __name__ == "__main__":
    export()
