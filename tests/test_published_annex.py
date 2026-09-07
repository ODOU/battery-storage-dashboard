"""Anchors from the PUBLISHED edition (IRENA, 2026, ISBN 978-92-9260-761-6): annex
Tables 1, 12-14 and Table A11. These run without the PDF; the last test re-parses
the PDF when it is available locally (env BATTERY_REPORT_PDF or the default path)."""
import json
import os
import shutil
from pathlib import Path

import pandas as pd
import pytest

ROOT = Path(__file__).resolve().parents[1]
def _default_pdf():
    """The published PDF as saved by a browser into Downloads/myreviews — tolerate the ' (1)' suffix
    browsers add to a repeated download. Override with the BATTERY_REPORT_PDF environment variable."""
    hits = sorted(Path(r"C:\Users\OOdou\Downloads\myreviews").glob("IRENA_TEC_Battery_storage_minigrids_W_Africa_2026*.pdf"))
    return str(hits[0]) if hits else r"C:\Users\OOdou\Downloads\myreviews\IRENA_TEC_Battery_storage_minigrids_W_Africa_2026.pdf"

PDF = os.environ.get("BATTERY_REPORT_PDF") or _default_pdf()


@pytest.fixture(scope="module")
def df():
    return pd.read_csv(ROOT / "data" / "scenarios.csv")


def v(df, c, g, m, t, metric):
    r = df[(df.country == c) & (df.grid == g) & (df.mgcost == m) & (df.tier == t) & (df.metric == metric)]
    assert len(r) == 1
    return float(r.value.iloc[0])


def test_value_of_storage_cells_revised_in_published_table_14(df):
    # These cells differ from the May 2026 manuscript chart caches (data/NOTES.md item 10).
    assert round(v(df, "NGA", "restricted", "pessimistic", 5, "vos_usd_m"), 2) == 5008.95
    assert round(v(df, "NGA", "restricted", "pessimistic", 4, "vos_usd_m"), 2) == 3921.62
    assert round(v(df, "NGA", "restricted", "pessimistic", 3, "vos_usd_m"), 2) == 1401.79
    assert round(v(df, "NGA", "leastcost", "pessimistic", 5, "vos_usd_m"), 2) == 14.30
    assert round(v(df, "BFA", "restricted", "pessimistic", 5, "vos_usd_m"), 2) == 2173.34


def test_published_family_totals(df):
    tot = df[df.metric == "vos_usd_m"].groupby(["grid", "mgcost", "tier"]).value.sum()
    assert round(tot[("restricted", "optimistic", 5)], 2) == 24406.52
    assert round(tot[("restricted", "pessimistic", 5)], 2) == 8173.93
    assert round(tot[("leastcost", "optimistic", 2)], 2) == 610.61
    mg = df[df.metric == "mg_capacity_mw"].groupby(["grid", "mgcost", "tier"]).value.sum()
    assert round(mg[("leastcost", "optimistic", 2)], 1) == 567.7
    assert round(mg[("restricted", "optimistic", 5)], 1) == 33990.2


def test_unchanged_anchors_still_hold(df):
    assert round(v(df, "SEN", "restricted", "optimistic", 3, "vos_usd_m"), 2) == 111.27
    assert round(v(df, "NGA", "leastcost", "optimistic", 2, "battery_mwh"), 1) == 1592.8
    assert round(v(df, "BFA", "restricted", "optimistic", 5, "battery_mwh"), 1) == 24957.3


def test_sensitivity_matches_table_a11():
    s = pd.read_csv(ROOT / "data" / "sensitivity.csv")
    r = s[(s.country == "MLI") & (s.scenario == "+100% (2.0x)") & (s.metric == "battery_leverage")]
    assert float(r.value.iloc[0]) == 5.89
    r = s[(s.country == "NGA") & (s.scenario == "Baseline (1.0x)") & (s.metric == "vos_usd_m")]
    assert float(r.value.iloc[0]) == 4891.0


def test_table_1_access_rates():
    t = json.loads((ROOT / "data" / "tables.json").read_text(encoding="utf-8"))["access"]
    assert t["SEN"]["rate_2023"] == "74.2%" and t["SEN"]["target_2030"] == "100%"
    assert t["MLI"]["rate_2023"] == "54.5%" and t["MLI"]["target_2030"] == "87%"
    assert t["BFA"]["rate_2023"] == "21.7%" and t["BFA"]["target_2030"] == "65%"


# --- Parser unit tests on embedded fixtures shaped like the pymupdf text layer (no PDF needed) ---

from scripts import apply_published_annex as ap


def test_num_strips_every_thousands_separator_and_maps_dashes_to_zero():
    assert ap.num("6 201") == 6201.0 and ap.num("1 396.70") == 1396.7 and ap.num("24,406.52") == 24406.52
    assert ap.num(" 127 200") == 127200.0
    for d in ("—", "–", "-", ""):
        assert ap.num(d) == 0.0
    with pytest.raises(ValueError):
        ap.num("n/a")


def test_pct_formats_like_table_1():
    assert ap.pct(74.2) == "74.2%" and ap.pct(100.0) == "100%" and ap.pct(65) == "65%"


def test_find_page_skips_the_list_of_tables_and_demands_a_unique_hit():
    toc = "LIST OF TABLES\nTable 12\tOptimal battery capacity ............ 63\n"
    body = "Table 12\tOptimal battery capacity per country\nBURKINA FASO\n"
    assert ap.find_page([toc, body], r"Table 12\s+Optimal battery capacity") == body
    with pytest.raises(RuntimeError, match="found on 0 pages"):
        ap.find_page([toc], r"Table 12\s+Optimal battery capacity")
    with pytest.raises(RuntimeError, match="found on 2 pages"):
        ap.find_page([body, body], r"Table 12\s+Optimal battery capacity")


def _scenario_page(headers, ncols):
    lines = ["Table 99\tFixture", *headers]
    n = 0
    for grid in ("Least-cost grid expansion", "Restricted grid expansion"):
        lines.append(grid)
        for mg in ("Optimistic mini-grid costs", "Pessimistic mini-grid costs"):
            lines.append(mg)
            for t in range(1, 6):
                lines.append(f"Tier {t}")
                for _ in range(ncols):
                    n += 1
                    lines.append("—" if n == 1 else f"{n} 000.5")
    return "\n".join(lines)


def test_parse_scenario_table_returns_20_rows_in_the_printed_column_order():
    page = _scenario_page(["NIGERIA", "BURKINA FASO", "MALI", "SENEGAL", "TOTAL"], 5)
    out = ap.parse_scenario_table(page, ("NIGERIA", "BURKINA FASO", "MALI", "SENEGAL", "TOTAL"))
    assert len(out) == 20 and out[("leastcost", "optimistic", 1)][0] == 0.0     # dash → 0
    assert out[("restricted", "pessimistic", 5)] == [96000.5, 97000.5, 98000.5, 99000.5, 100000.5]
    with pytest.raises(RuntimeError, match="column order"):                        # a re-ordered table is refused, not mis-assigned
        ap.parse_scenario_table(page, ("BURKINA FASO", "MALI", "NIGERIA", "SENEGAL", "TOTAL"))
    with pytest.raises(RuntimeError, match="expected 20"):
        ap.parse_scenario_table("\n".join(page.split("\n")[:-6]), ("NIGERIA", "BURKINA FASO", "MALI", "SENEGAL", "TOTAL"))


def test_parse_table_a11_reads_24_rows_and_normalises_the_multiplier_sign():
    lines = ["Table A11\tBattery storage metrics"]
    for name in ("Burkina Faso", "Mali", "Nigeria", "Senegal"):
        for scen in ("Baseline (1.0×)", "+10% (1.1×)", "+25% (1.25×)", "+50% (1.5×)", "+75% (1.75×)", "+100% (2.0×)"):
            lines += [name, scen, *[f"{i}.5" for i in range(11)]]
    out = ap.parse_table_a11("\n".join(lines))
    assert len(out) == 24 and out[("MLI", "+100% (2.0x)")] == [i + 0.5 for i in range(11)]
    with pytest.raises(RuntimeError, match="expected 24"):
        ap.parse_table_a11("\n".join(lines[:-13]))


def test_parse_table_1_strips_footnote_letters():
    page = "Table 1\tCurrent electricity access status and 2030 targets\nCOUNTRY\nBurkina Faso\n21.7\n65\nMali\n54.5\n87\nNigeria\n61.2\n100\nSenegal\n74.2\n100b\n"
    assert ap.parse_table_1(page) == {"BFA": (21.7, 65.0), "MLI": (54.5, 87.0), "NGA": (61.2, 100.0), "SEN": (74.2, 100.0)}
    with pytest.raises(RuntimeError, match="countries parsed"):
        ap.parse_table_1("Table 1\tCurrent electricity access\nMali\n54.5\n87\n")


def test_apply_writes_nothing_when_a_later_table_fails(tmp_path, monkeypatch):
    """Parse-then-write: a failure in Table A11 or Table 1 must leave scenarios.csv untouched."""
    work = tmp_path / "data"
    shutil.copytree(ROOT / "data", work)
    monkeypatch.setattr(ap, "DATA", work)
    monkeypatch.setattr(ap, "pdf_text", lambda p: ["Table 12\tOptimal battery capacity\n" + _scenario_page(["BURKINA FASO", "MALI", "NIGERIA", "SENEGAL"], 4)[15:]])
    before = (work / "scenarios.csv").read_bytes()
    with pytest.raises(RuntimeError):
        ap.apply(Path("fixture.pdf"), verbose=False)
    assert (work / "scenarios.csv").read_bytes() == before


@pytest.mark.skipif(not os.path.exists(PDF), reason="published PDF not on this machine")
def test_reapplying_published_pdf_is_a_no_op(tmp_path, monkeypatch):
    from scripts import apply_published_annex as ap
    work = tmp_path / "data"
    shutil.copytree(ROOT / "data", work)
    monkeypatch.setattr(ap, "DATA", work)
    assert ap.apply(Path(PDF), verbose=False) == []
