"""Extract report data from the manuscript DOCX into data/*.csv|json."""
import json, re, sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import docx
import pandas as pd
from docx.oxml.ns import qn
from docx.table import Table
from docx.text.paragraph import Paragraph
from scripts.docx_charts import read_charts

DATA = Path(__file__).resolve().parents[1] / "data"
FAMILIES = [("leastcost", "optimistic"), ("leastcost", "pessimistic"),
            ("restricted", "optimistic"), ("restricted", "pessimistic")]
COUNTRY_CHARTS = {"BFA": (4, 6, 7), "MLI": (8, 10, 11), "NGA": (12, 14, 15), "SEN": (16, 18, 19)}
MIX_SERIES = {"Existing connections": "existing", "Grid Densification (New)": "grid_densification",
              "Grid extension (New)": "grid_extension", "Mini-grids": "minigrid", "StandAlone": "standalone"}
VOS_SERIES = {"Increased Investments": "vos_investment_usd_m", " Fuel Savings": "vos_fuel_savings_usd_m",
              "OM Savings": "vos_om_savings_usd_m", "Value of storage": "vos_usd_m"}
CAP_COUNTRY = {"Nigeria": "NGA", "Burkina Faso": "BFA", "Mali": "MLI", "Senegal": "SEN"}
STRAY_IDX = 5  # doc position of the stray subtotal cell in VOS chart series caches

def _drop_stray(vals):
    """The four VOS chart series (charts 7, 11, 15, 19 - one per country) cache 21
    values, not 20: the manuscript's source range for each has a stray numeric cell
    at the family0/family1 boundary (doc position 5) that carries no tier category.
    Confirmed structurally (idx present in c:val but absent from the lvl-1 tier
    c:cat) across all 16 VOS series and against both VOS annex anchors (see
    data/NOTES.md item 6). Only call this for VOS series - any other chart whose
    series length is wrong must still fail _rows's len == 20 assertion below.
    A 20-length input is returned unchanged."""
    if len(vals) == 21:
        return vals[:STRAY_IDX] + vals[STRAY_IDX + 1:]
    return vals

def _rows(country, metric, vals, scale):
    assert len(vals) == 20, (country, metric, len(vals))
    for i, (g, m) in enumerate(FAMILIES):
        for t in range(1, 6):
            yield dict(country=country, grid=g, mgcost=m, tier=t, metric=metric, value=vals[i * 5 + t - 1] * scale)

def _check_chart_identity(charts):
    """COUNTRY_CHARTS indexes word/charts/chartN.xml by position. Before reshaping, check that each
    index still points at the chart it is supposed to: the series names of the mix / battery / VOS
    charts, the country named in the neighbouring per-country chart title (the manuscript titles
    the 'Additional mini-grid connections — <Country>' chart that follows each mix chart, except for
    Burkina Faso), the country series of the capacity chart and the title of the battery chart. A
    re-ordered manuscript then fails here, naming the chart, instead of shifting every country."""
    names = lambda i: [s["name"] for s in charts[i]["series"]]
    for c, (mix, bat, vos) in COUNTRY_CHARTS.items():
        if set(names(mix)) != set(MIX_SERIES):
            raise ValueError(f"chart {mix} is not the {c} electrification-mix chart: series {names(mix)}")
        if names(bat) != ["Total"]:
            raise ValueError(f"chart {bat} is not the {c} battery-capacity chart: series {names(bat)}")
        if set(names(vos)) != set(VOS_SERIES):
            raise ValueError(f"chart {vos} is not the {c} value-of-storage chart: series {names(vos)}")
        country = {v: k for k, v in CAP_COUNTRY.items()}[c]
        if c != "BFA" and country not in charts[mix + 1]["title"]:
            raise ValueError(f"chart {mix + 1} title {charts[mix + 1]['title']!r} does not name {country}: chart order changed?")
    if set(names(21)) != set(CAP_COUNTRY) or "capacity" not in charts[21]["title"].lower():
        raise ValueError(f"chart 21 is not the four-country mini-grid capacity chart: {charts[21]['title']!r} {names(21)}")
    if "Battery" not in charts[22]["title"] or names(22)[1] != "BatteryCapacity":
        raise ValueError(f"chart 22 is not the four-country value-of-storage/battery chart: {charts[22]['title']!r}")

def extract_scenarios(charts):
    _check_chart_identity(charts)
    rows = []
    for c, (mix, bat, vos) in COUNTRY_CHARTS.items():
        for s in charts[mix]["series"]:
            rows += _rows(c, MIX_SERIES[s["name"]], s["vals"], 1.0)
        rows += _rows(c, "battery_mwh", charts[bat]["series"][0]["vals"], 1e-3)
        for s in charts[vos]["series"]:
            rows += _rows(c, VOS_SERIES[s["name"]], _drop_stray(s["vals"]), 1e-6)
    for s in charts[21]["series"]:
        rows += _rows(CAP_COUNTRY[s["name"]], "mg_capacity_mw", s["vals"], 1e-3)
    df = pd.DataFrame(rows, columns=["country", "grid", "mgcost", "tier", "metric", "value"])
    df["value"] = df["value"].round(4)
    return df

def _iter_tables_with_caption(d):
    """Yield (caption_text_before_table, Table)."""
    last = ""
    for el in d.element.body.iterchildren():
        if el.tag == qn("w:p"):
            t = Paragraph(el, d).text.strip()
            if t:
                last = t
        elif el.tag == qn("w:tbl"):
            yield last, Table(el, d)

def _grid(tbl):
    return [[c.text.strip() for c in r.cells] for r in tbl.rows]

def _find(d, startswith):
    for cap, tbl in _iter_tables_with_caption(d):
        if cap.replace("  ", " ").startswith(startswith):
            return _grid(tbl)
    raise KeyError(startswith)

def _num(s):
    return int(s.replace(",", "")) if s not in ("-", "") else 0

C3 = {"Burkina Faso": "BFA", "Mali": "MLI", "Nigeria": "NGA", "Senegal": "SEN"}

def _sources():
    """Hand-authored facts from the published edition (data/sources.json), each with its
    source in the report. They are not derived from the manuscript and take precedence over
    the manuscript tables wherever the two overlap (MTF wording, urban/rural access)."""
    return json.loads((DATA / "sources.json").read_text(encoding="utf-8"))

def extract_tables(docx_path):
    d = docx.Document(docx_path)
    src = _sources()
    mtf = src["mtf"]  # published Table 7 wording (the manuscript table differs in punctuation/spacing)
    costs = [{"component": r[0], "optimistic": r[1], "pessimistic": r[2]} for r in _find(d, "Table 8.")[1:]]
    t9 = _find(d, "Table 9:")
    pot = {"connections": {}, "settlements": {}}
    block = "connections"
    for r in t9[1:]:
        if r[0].startswith("New connections"): block = "connections"; continue
        if r[0].startswith("Number of settlements"): block = "settlements"; continue
        if r[0] in C3:
            pot[block][C3[r[0]]] = {"hydro": _num(r[1]), "wind": _num(r[2]), "pv": _num(r[3])}
    t1 = _find(d, "Table 1.")
    access = {C3[r[0]]: {"rate_2023": r[1] if r[1].endswith("%") else r[1] + "%",
                         "target_2030": r[2].rstrip("*") + "%"} for r in t1[1:] if r[0] in C3}
    # Urban/rural splits: published Table A6 (2023, all four countries) via sources.json —
    # the manuscript's Tables 2 and 4 carried 2020 values for two countries only.
    for c in C3.values():
        access[c].update(src["access_urban_rural"][c])
    return {"mtf": mtf, "mg_costs": costs, "mg_potential": pot, "access": access,
            "access_urban_rural_source": src["access_urban_rural"]["source"],
            "national": src["national"], "pump_prices_usd_l": src["pump_prices_usd_l"],
            "reference_case": src["reference_case"]}

SENS_COLS = ["diesel_price_usd_l", "battery_mwh", "battery_investment_usd_m", "vos_usd_m",
             "total_investment_usd_m", "lcoe_hybrid_usd_kwh", "fuel_exposure_pct", "battery_leverage",
             "renewable_share_pct", "vos_vs_baseline_pct", "vos_ratio"]

def extract_sensitivity(docx_path):
    d = docx.Document(docx_path)
    rows = []
    for r in _find(d, "Table E 1")[1:]:
        if r[0] not in C3:
            continue
        scen = r[1].replace("×", "x")                          # same normalisation as apply_published_annex
        m = re.search(r"\(([\d.]+)\s*x\)", scen)
        if not m:
            raise ValueError(f"sensitivity scenario label {r[1]!r} has no '(N.Nx)' multiplier")
        mult = float(m.group(1))
        for col, name in zip(r[2:], SENS_COLS):
            rows.append(dict(country=C3[r[0]], scenario=scen, multiplier=mult, metric=name,
                             value=float(col.replace(",", ""))))
    return pd.DataFrame(rows)

def main(docx_path):
    charts = read_charts(docx_path)
    DATA.mkdir(exist_ok=True)
    extract_scenarios(charts).to_csv(DATA / "scenarios.csv", index=False)
    ex = {s["name"].replace("0&M", "O&M"): dict(zip(s["cats"], s["vals"])) for s in charts[1]["series"]}
    (DATA / "example_es1.json").write_text(json.dumps(ex, indent=1) + "\n", encoding="utf-8")
    (DATA / "tables.json").write_text(json.dumps(extract_tables(docx_path), indent=1, ensure_ascii=False) + "\n", encoding="utf-8")
    extract_sensitivity(docx_path).to_csv(DATA / "sensitivity.csv", index=False)
    print("wrote scenarios.csv, example_es1.json, tables.json, sensitivity.csv")

if __name__ == "__main__":
    main(sys.argv[1])
