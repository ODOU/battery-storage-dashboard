"""One-off: Natural Earth 110m admin-0 -> simplified GeoJSON of the four focus countries + neighbours."""
import json
from pathlib import Path
import geopandas as gpd

SRC = Path(r"C:\PrivateToolsDevelopment\PlanificationRuraleSenegalFinal\Map\_ne_110m_admin0.gpkg")
OUT = Path(__file__).resolve().parents[1] / "data" / "countries.geojson"
FOCUS = {"BFA", "MLI", "NGA", "SEN"}
NEIGHBOURS = {"MRT", "NER", "TCD", "CMR", "BEN", "TGO", "GHA", "CIV", "LBR", "SLE", "GIN", "GNB", "GMB"}

def main():
    g = gpd.read_file(SRC).to_crs(4326)
    g = g[g["ADM0_A3"].isin(FOCUS | NEIGHBOURS)].copy()
    g["geometry"] = g.geometry.simplify(0.05, preserve_topology=True)
    feats = [{"type": "Feature",
              "properties": {"iso3": r.ADM0_A3, "name": r.ADMIN, "focus": r.ADM0_A3 in FOCUS},
              "geometry": json.loads(gpd.GeoSeries([r.geometry]).to_json())["features"][0]["geometry"]}
             for r in g.itertuples()]
    OUT.write_text(json.dumps({"type": "FeatureCollection", "features": feats}, separators=(",", ":")), encoding="utf-8")
    print(OUT, OUT.stat().st_size, "bytes", len(feats), "features")

if __name__ == "__main__":
    main()
