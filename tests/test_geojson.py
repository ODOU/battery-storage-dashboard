import json, os
from pathlib import Path
GJ = Path(__file__).resolve().parents[1] / "data" / "countries.geojson"

def test_geojson_present_and_small():
    assert GJ.exists() and GJ.stat().st_size < 150_000

def test_focus_countries():
    fc = json.loads(GJ.read_text(encoding="utf-8"))
    focus = {f["properties"]["iso3"] for f in fc["features"] if f["properties"]["focus"]}
    assert focus == {"BFA", "MLI", "NGA", "SEN"}
    assert all(f["geometry"]["type"] in ("Polygon", "MultiPolygon") for f in fc["features"])
