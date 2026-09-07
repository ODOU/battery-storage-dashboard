"""Align data/ with the published edition of the report.

Usage:
    python scripts/apply_published_annex.py <IRENA_TEC_Battery_storage_minigrids_W_Africa_2026.pdf>

Run AFTER scripts/extract_docx.py. The manuscript DOCX (chart caches) remains the
only source for the per-country new-connections mix and the value-of-storage
components; the published PDF is the authority for every number it prints. This
script reads, from the published PDF text layer:

  Table 1   current access status and 2030 targets      -> data/tables.json  access.<ISO>.rate_2023 / target_2030
  Table 10  four-country electrification mix (millions)  -> checked against the sum of scenarios.csv (not written)
  Table 12  battery capacity per country (MWh)            -> scenarios.csv  battery_mwh
  Table 13  mini-grid capacity per country (MW)           -> scenarios.csv  mg_capacity_mw
  Table 14  value of storage per country (USD million)    -> scenarios.csv  vos_usd_m
  Table A11 diesel-price sensitivity metrics              -> sensitivity.csv (all 11 metrics)

and overwrites the matching cells, printing every cell whose value changed.
Tables are located by caption, not page number. The PDF is never copied into
the repository.
"""
import json
import re
import sys
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data"
ISO = {"BURKINA FASO": "BFA", "MALI": "MLI", "NIGERIA": "NGA", "SENEGAL": "SEN"}
A11_COLS = ["diesel_price_usd_l", "battery_mwh", "battery_investment_usd_m", "vos_usd_m",
            "total_investment_usd_m", "lcoe_hybrid_usd_kwh", "fuel_exposure_pct", "battery_leverage",
            "renewable_share_pct", "vos_vs_baseline_pct", "vos_ratio"]
DASHES = {"—", "–", "-", "�", ""}


def pdf_text(path):
    import pymupdf
    with pymupdf.open(str(path)) as doc:
        return [page.get_text() for page in doc]


def num(s):
    s = re.sub(r"[\s    ,]", "", s)
    return 0.0 if s in DASHES else float(s)


def find_page(pages, caption_regex):
    # skip the list of tables (caption followed by dot leaders and a page number)
    hits = [i for i, p in enumerate(pages)
            if re.search(caption_regex, p) and not re.search(caption_regex + r"[^\n]*\.{4,}", p)]
    if len(hits) != 1:
        raise RuntimeError(f"caption {caption_regex!r} found on {len(hits)} pages: {hits}")
    return pages[hits[0]]


def parse_scenario_table(page, header_names):
    """Annex Tables 10-14: return {(grid, mgcost, tier): [values in header order]}.

    header_names is the column order printed under the caption (Table 13 prints
    NIGERIA first); it is checked against the page so a reordering is caught."""
    lines = [l.strip() for l in page.split("\n") if l.strip()]
    order = [l.upper() for l in lines if l.upper() in header_names]
    if order != list(header_names):
        raise RuntimeError(f"column order {order} differs from expected {list(header_names)}")
    out, grid, mg, i, ncols = {}, None, None, 0, len(header_names)
    while i < len(lines):
        up = lines[i].upper()
        if "LEAST-COST" in up:
            grid = "leastcost"
        elif "RESTRICTED" in up:
            grid = "restricted"
        elif up.startswith("OPTIMISTIC"):
            mg = "optimistic"
        elif up.startswith("PESSIMISTIC"):
            mg = "pessimistic"
        m = re.match(r"TIER\s+(\d)$", up)
        if m:
            out[(grid, mg, int(m.group(1)))] = [num(x) for x in lines[i + 1:i + 1 + ncols]]
            i += 1 + ncols
            continue
        i += 1
    if len(out) != 20:
        raise RuntimeError(f"expected 20 tier rows, parsed {len(out)}")
    return out


def parse_table_a11(page):
    lines = [l.strip() for l in page.split("\n") if l.strip()]
    names = {k.title(): v for k, v in ISO.items()}
    out, i = {}, 0
    while i < len(lines):
        if lines[i] in names and i + 1 < len(lines) and re.match(r"(Baseline|\+\d+%)", lines[i + 1]):
            scen = lines[i + 1].replace("×", "x")
            out[(names[lines[i]], scen)] = [num(x) for x in lines[i + 2:i + 2 + len(A11_COLS)]]
            i += 2 + len(A11_COLS)
            continue
        i += 1
    if len(out) != 24:
        raise RuntimeError(f"Table A11: expected 24 rows, parsed {len(out)}")
    return out


def parse_table_1(page):
    lines = [l.strip() for l in page.split("\n") if l.strip()]
    start = next(i for i, l in enumerate(lines) if re.match(r"Table 1\b", l))
    out = {}
    for i in range(start, len(lines)):
        iso = ISO.get(lines[i].upper())
        if iso and iso not in out:
            out[iso] = (num(lines[i + 1]), num(re.sub(r"[a-z]$", "", lines[i + 2])))  # strip footnote letter
    if set(out) != set(ISO.values()):
        raise RuntimeError(f"Table 1: countries parsed {sorted(out)}")
    return out


def pct(x):
    return (f"{x:.1f}" if x != int(x) else f"{int(x)}") + "%"


def apply(pdf_path, verbose=True):
    pages = pdf_text(pdf_path)
    changes = []
    df = pd.read_csv(DATA / "scenarios.csv")

    def patch(country, grid, mg, tier, metric, new, tol):
        mask = ((df.country == country) & (df.grid == grid) & (df.mgcost == mg)
                & (df.tier == tier) & (df.metric == metric))
        if mask.sum() != 1:
            raise RuntimeError(f"no unique row for {country} {grid} {mg} T{tier} {metric}")
        old = float(df.loc[mask, "value"].iloc[0])
        if abs(old - new) > tol:
            changes.append(f"scenarios.csv {country} {grid}/{mg}/T{tier} {metric}: {old:.3f} -> {new}")
            df.loc[mask, "value"] = new

    # ---- 1. Parse and check everything first; nothing is written until every table has parsed, so a
    #         failure cannot leave data/ half-aligned (scenarios.csv updated, sensitivity.csv stale).
    t12 = parse_scenario_table(find_page(pages, r"Table 12\s+Optimal battery capacity"),
                               ("BURKINA FASO", "MALI", "NIGERIA", "SENEGAL"))
    t13 = parse_scenario_table(find_page(pages, r"Table 13\s+Mini-grids capacity"),
                               ("NIGERIA", "BURKINA FASO", "MALI", "SENEGAL", "TOTAL"))
    t14 = parse_scenario_table(find_page(pages, r"Table 14\s+Value of storage"),
                               ("BURKINA FASO", "MALI", "NIGERIA", "SENEGAL", "TOTAL"))
    t10 = parse_scenario_table(find_page(pages, r"Table 10\s+Electrification mix"),
                               ("EXISTING", "GRID", "GRID", "MINI-GRIDS", "STAND-ALONE"))
    a11 = parse_table_a11(find_page(pages, r"Table A11\s*Battery storage metrics"))
    t1 = parse_table_1(find_page(pages, r"Table 1\s+Current electricity access status and 2030 targets"))
    # The printed TOTAL columns of Tables 13 and 14 must equal the sum of the four printed country cells
    # (within their rounding) — the strongest guard against a mis-parsed or mis-assigned column.
    for name, tbl, tol in (("Table 13", t13, 0.25), ("Table 14", t14, 0.03)):
        for (g, m, t), vals in tbl.items():
            if abs(sum(vals[:4]) - vals[4]) > tol:
                raise RuntimeError(f"{name} {g}/{m}/T{t}: printed TOTAL {vals[4]} vs sum of countries {sum(vals[:4]):.2f}")

    for (g, m, t), vals in t12.items():
        for c, v in zip(["BFA", "MLI", "NGA", "SEN"], vals):
            patch(c, g, m, t, "battery_mwh", v, 0.051)
    for (g, m, t), vals in t13.items():
        for c, v in zip(["NGA", "BFA", "MLI", "SEN"], vals):
            patch(c, g, m, t, "mg_capacity_mw", v, 0.051)
    for (g, m, t), vals in t14.items():
        for c, v in zip(["BFA", "MLI", "NGA", "SEN"], vals):
            patch(c, g, m, t, "vos_usd_m", v, 0.0051)

    # Table 10 (four-country sums) is checked, not written: the per-country mix comes from the DOCX charts.
    for (g, m, t), vals in t10.items():
        for metric, v in zip(["existing", "grid_densification", "grid_extension", "minigrid", "standalone"], vals):
            ours = df[(df.grid == g) & (df.mgcost == m) & (df.tier == t) & (df.metric == metric)].value.sum() / 1e6
            if abs(ours - v) > 0.02:
                raise RuntimeError(f"Table 10 {g}/{m}/T{t} {metric}: published {v} vs scenarios.csv sum {ours:.2f}")

    sn = pd.read_csv(DATA / "sensitivity.csv")
    for (c, scen), vals in a11.items():
        for metric, v in zip(A11_COLS, vals):
            mask = (sn.country == c) & (sn.scenario == scen) & (sn.metric == metric)
            if mask.sum() != 1:
                raise RuntimeError(f"sensitivity.csv: no unique row for {c} {scen} {metric}")
            old = float(sn.loc[mask, "value"].iloc[0])
            if abs(old - v) > 1e-9:
                changes.append(f"sensitivity.csv {c} {scen} {metric}: {old} -> {v}")
                sn.loc[mask, "value"] = v

    tables = json.loads((DATA / "tables.json").read_text(encoding="utf-8"))
    for iso, (rate, target) in t1.items():
        for key, new in (("rate_2023", pct(rate)), ("target_2030", pct(target))):
            old = tables["access"][iso][key]
            if old != new:
                changes.append(f"tables.json access.{iso}.{key}: {old} -> {new}")
                tables["access"][iso][key] = new

    # ---- 2. Write all three files.
    df.to_csv(DATA / "scenarios.csv", index=False)
    sn.to_csv(DATA / "sensitivity.csv", index=False)
    (DATA / "tables.json").write_text(json.dumps(tables, indent=1, ensure_ascii=False) + "\n", encoding="utf-8")

    if verbose:
        print(f"{len(changes)} cell(s) changed against the published edition:")
        for c in changes:
            print("  " + c)
    return changes


if __name__ == "__main__":
    if len(sys.argv) != 2:
        sys.exit(__doc__)
    apply(Path(sys.argv[1]))
