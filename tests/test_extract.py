import os, pytest, pandas as pd
from scripts.docx_charts import read_charts
from scripts.extract_docx import extract_scenarios, FAMILIES, _drop_stray, _rows
from scripts.extract_docx import extract_tables, extract_sensitivity

DOCX = r"C:\Users\OOdou\Downloads\myreviews\Report_Battery_MG_Electrification_WestAfrica_SMGRev_Correction.docx"
needs_docx = pytest.mark.skipif(not os.path.exists(DOCX), reason="manuscript not on this machine")

@pytest.fixture(scope="module")
def df():
    return extract_scenarios(read_charts(DOCX))

def v(df, country, grid, mg, tier, metric):
    r = df[(df.country == country) & (df.grid == grid) & (df.mgcost == mg) & (df.tier == tier) & (df.metric == metric)]
    assert len(r) == 1, (country, grid, mg, tier, metric)
    return float(r.value.iloc[0])

@needs_docx
def test_shape(df):
    assert list(df.columns) == ["country", "grid", "mgcost", "tier", "metric", "value"]
    assert len(df) == 4 * 20 * 11
    assert FAMILIES == [("leastcost", "optimistic"), ("leastcost", "pessimistic"),
                        ("restricted", "optimistic"), ("restricted", "pessimistic")]

@needs_docx
def test_annex_anchors(df):
    assert round(v(df, "SEN", "restricted", "optimistic", 3, "vos_usd_m"), 2) == 111.27
    assert round(v(df, "NGA", "leastcost", "optimistic", 2, "battery_mwh"), 1) == 1592.8
    assert round(v(df, "BFA", "restricted", "optimistic", 5, "battery_mwh"), 1) == 24957.3
    assert round(v(df, "NGA", "leastcost", "optimistic", 2, "mg_capacity_mw"), 1) == 399.3
    assert round(v(df, "MLI", "leastcost", "pessimistic", 5, "vos_usd_m"), 2) == 69.84

@needs_docx
def test_new_connections_total_is_172M_every_scenario(df):
    new = df[df.metric.isin(["grid_densification", "grid_extension", "minigrid", "standalone"])]
    tot = new.groupby(["grid", "mgcost", "tier"]).value.sum() / 1e6
    assert ((tot - 172.2).abs() < 0.3).all(), tot

@needs_docx
def test_reconciles_with_four_country_charts(df):
    ch = read_charts(DOCX)
    mg_chart = ch[20]["series"][1]["vals"]              # Mini-grids, 20 points
    mg_sum = df[df.metric == "minigrid"].groupby(["grid", "mgcost", "tier"], sort=False).value.sum()
    for i, (g, m) in enumerate(FAMILIES):
        for t in range(1, 6):
            assert abs(mg_sum[(g, m, t)] - mg_chart[i * 5 + t - 1]) < 1000
    bat_chart = ch[22]["series"][1]["vals"]             # BatteryCapacity kWh, 20 points
    bat_sum = df[df.metric == "battery_mwh"].groupby(["grid", "mgcost", "tier"], sort=False).value.sum()
    for i, (g, m) in enumerate(FAMILIES):
        for t in range(1, 6):
            assert abs(bat_sum[(g, m, t)] - bat_chart[i * 5 + t - 1] / 1000) < 1.0

# --- Environment-independent unit tests (no manuscript required) ---

def test_drop_stray_removes_fixed_position_5():
    assert _drop_stray(list(range(21))) == list(range(5)) + list(range(6, 21))

def test_drop_stray_leaves_20_length_unchanged():
    assert _drop_stray(list(range(20))) == list(range(20))

def test_rows_still_rejects_wrong_length_when_drop_stray_not_applied():
    # Non-VOS branches of extract_scenarios call _rows directly, without
    # _drop_stray. A 21-length (or any non-20) series there must still raise
    # the original AssertionError, not be silently "fixed".
    with pytest.raises(AssertionError):
        list(_rows("XXX", "existing", list(range(21)), 1.0))
    with pytest.raises(AssertionError):
        list(_rows("XXX", "existing", list(range(19)), 1.0))

@needs_docx
def test_tables_json_content():
    t = extract_tables(DOCX)
    assert len(t["mtf"]) == 5 and t["mtf"][2]["kwh_hh_yr"].replace(" ", "") == ">365"
    assert t["mg_costs"][3]["component"].startswith("Li-ion") and t["mg_costs"][3]["optimistic"] == "142 USD/kWh"
    assert t["mg_potential"]["connections"]["NGA"]["hydro"] == 1250813
    assert t["mg_potential"]["settlements"]["BFA"]["pv"] == 92398
    assert t["access"]["BFA"]["rate_2023"] == "21.7%"
    assert set(t["national"]) == {"BFA", "MLI", "NGA", "SEN"}

@needs_docx
def test_sensitivity_csv():
    s = extract_sensitivity(DOCX)
    assert len(s) == 4 * 6 * 11
    r = s[(s.country == "BFA") & (s.multiplier == 2.0) & (s.metric == "fuel_exposure_pct")]
    assert float(r.value.iloc[0]) == 87.3
    r = s[(s.country == "MLI") & (s.multiplier == 1.0) & (s.metric == "battery_leverage")]
    assert float(r.value.iloc[0]) == 2.85
