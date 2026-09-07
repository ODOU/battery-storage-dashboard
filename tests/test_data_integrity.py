"""Integrity of the COMMITTED data files, independent of the manuscript DOCX and the published
PDF: shape, uniqueness, absence of gaps, the accounting identities that hold by construction, and
the family totals printed in the report. Everything here is what a reviewer would recompute before
quoting a number from the dashboard."""
import json
from pathlib import Path

import pandas as pd
import pytest

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data"
COUNTRIES = ["BFA", "MLI", "NGA", "SEN"]
FAMILIES = [("leastcost", "optimistic"), ("leastcost", "pessimistic"), ("restricted", "optimistic"), ("restricted", "pessimistic")]
METRICS = {"existing", "grid_densification", "grid_extension", "minigrid", "standalone", "battery_mwh",
           "vos_investment_usd_m", "vos_fuel_savings_usd_m", "vos_om_savings_usd_m", "vos_usd_m", "mg_capacity_mw"}
MIX = ["grid_densification", "grid_extension", "minigrid", "standalone"]
A11 = {"diesel_price_usd_l", "battery_mwh", "battery_investment_usd_m", "vos_usd_m", "total_investment_usd_m",
       "lcoe_hybrid_usd_kwh", "fuel_exposure_pct", "battery_leverage", "renewable_share_pct", "vos_vs_baseline_pct", "vos_ratio"}


@pytest.fixture(scope="module")
def s():
    return pd.read_csv(DATA / "scenarios.csv")


@pytest.fixture(scope="module")
def sn():
    return pd.read_csv(DATA / "sensitivity.csv")


def fam(s, metric):
    return s[s.metric == metric].groupby(["grid", "mgcost", "tier"]).value.sum()


def test_scenarios_shape_and_keys(s):
    assert list(s.columns) == ["country", "grid", "mgcost", "tier", "metric", "value"]
    assert len(s) == 4 * 2 * 2 * 5 * 11 == 880
    assert set(s.country) == set(COUNTRIES) and set(s.metric) == METRICS
    assert set(zip(s.grid, s.mgcost)) == set(FAMILIES) and set(s.tier) == {1, 2, 3, 4, 5}
    assert not s.duplicated(["country", "grid", "mgcost", "tier", "metric"]).any()
    assert s.value.notna().all()


def test_new_connections_mix_is_the_same_population_in_every_scenario(s):
    """Grid densification + extension + mini-grids + stand-alone is the population to connect,
    which does not depend on the scenario: 172.18 M across the four countries (report: 171 M)."""
    tot = s[s.metric.isin(MIX)].groupby(["grid", "mgcost", "tier"]).value.sum() / 1e6
    assert tot.between(172.1, 172.3).all(), tot
    assert tot.max() - tot.min() < 1e-6
    per_country = s[s.metric.isin(MIX)].groupby(["country", "grid", "mgcost", "tier"]).value.sum().groupby("country")
    assert (per_country.max() - per_country.min() < 1e-3).all()


def test_existing_and_densification_do_not_depend_on_the_scenario(s):
    for metric in ("existing", "grid_densification"):
        spread = s[s.metric == metric].groupby("country").value.agg(lambda x: x.max() - x.min())
        assert (spread < 1e-3).all(), (metric, spread)


def test_deployment_metrics_are_non_negative_and_move_together(s):
    for metric in ("battery_mwh", "mg_capacity_mw", "vos_usd_m", "minigrid"):
        assert (s[s.metric == metric].value >= 0).all(), metric
    # a scenario with mini-grid capacity has battery capacity and value of storage, and vice versa
    w = s[s.metric.isin(["battery_mwh", "mg_capacity_mw", "vos_usd_m"])].pivot_table(index=["country", "grid", "mgcost", "tier"], columns="metric", values="value")
    assert ((w.mg_capacity_mw > 0) == (w.battery_mwh > 0)).all()
    assert ((w.mg_capacity_mw > 0) == (w.vos_usd_m > 0)).all()


def test_family_totals_printed_in_the_report(s):
    vos, mg, bat = fam(s, "vos_usd_m"), fam(s, "mg_capacity_mw"), fam(s, "battery_mwh")
    assert round(vos[("restricted", "optimistic", 5)], 2) == 24406.52       # "nearly USD 25 billion" (Table 14)
    assert round(vos[("restricted", "pessimistic", 5)], 2) == 8173.93
    assert round(vos[("leastcost", "optimistic", 2)], 2) == 610.61
    assert round(mg[("leastcost", "optimistic", 2)], 1) == 567.7             # "568 MW"
    assert round(mg[("restricted", "optimistic", 5)], 1) == 33990.2
    assert round(bat[("restricted", "optimistic", 5)], 1) == 127163.8        # "about 130 GWh" (Table 12)
    assert 2200 <= bat[("leastcost", "optimistic", 2)] <= 2300               # "around 2.25 GWh" at Tier 2
    # "less than 8 GWh in unconstrained grid expansion scenarios": Table 12 sums to 8.24 GWh at Tier 5
    # least-cost / optimistic — the report's figure is rounded (NOTES item 15); the ratio to 127.2 GWh is 15.4 ("16x").
    assert 8000 < bat[bat.index.get_level_values("grid") == "leastcost"].max() < 8300


def test_sensitivity_shape_and_consistency(sn):
    assert list(sn.columns) == ["country", "scenario", "multiplier", "metric", "value"]
    assert len(sn) == 4 * 6 * 11 == 264 and set(sn.metric) == A11
    assert sorted(sn.multiplier.unique()) == [1.0, 1.1, 1.25, 1.5, 1.75, 2.0]
    assert not sn.duplicated(["country", "multiplier", "metric"]).any() and sn.value.notna().all()
    w = sn.pivot_table(index=["country", "multiplier"], columns="metric", values="value")
    base = w.xs(1.0, level="multiplier")
    for c in COUNTRIES:
        # the diesel price column tracks the multiplier exactly; VOS, LCOE and fuel exposure rise monotonically with it
        assert (w.loc[c].diesel_price_usd_l / base.loc[c].diesel_price_usd_l - w.loc[c].index).abs().max() < 0.01
        for metric in ("vos_usd_m", "lcoe_hybrid_usd_kwh", "fuel_exposure_pct"):
            assert w.loc[c][metric].is_monotonic_increasing, (c, metric)
        assert (w.loc[c].vos_ratio - w.loc[c].vos_usd_m / base.loc[c].vos_usd_m).abs().max() < 0.02


def test_tables_json_carries_every_field_the_page_reads():
    t = json.loads((DATA / "tables.json").read_text(encoding="utf-8"))
    assert [r["tier"] for r in t["mtf"]] == [1, 2, 3, 4, 5]
    assert len(t["mg_costs"]) == 6 and t["mg_costs"][3]["optimistic"] == "142 USD/kWh"
    for c in COUNTRIES:
        assert set(t["mg_potential"]["connections"][c]) == {"pv", "hydro", "wind"}
        assert set(t["access"][c]) == {"rate_2023", "target_2030", "urban", "rural"}
        assert all(len(row) == 3 for row in t["national"][c])                # label, value, source
        assert isinstance(t["pump_prices_usd_l"][c], float)
    assert t["reference_case"]["kwh_hh_yr"] == 803
    src = json.loads((DATA / "sources.json").read_text(encoding="utf-8"))
    assert t["mtf"] == src["mtf"] and t["national"] == src["national"]      # tables.json is generated from sources.json


def test_example_nets_to_the_reports_usd_20000():
    ex = json.loads((DATA / "example_es1.json").read_text(encoding="utf-8"))
    tot = {c: sum(v[c] for v in ex.values()) for c in ("With Batteries", "Without Batteries")}
    assert 19000 < tot["Without Batteries"] - tot["With Batteries"] < 22000
