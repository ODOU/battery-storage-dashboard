"""The build: single file, no network, every storyboard claim resolvable from the data files, and
the wording anchors that the 2026-09-05 review fixed (so they stay fixed).

The build runs once into a temporary directory; the committed dist/index.html is compared to it
separately so that running the tests never rewrites a tracked file."""
import json, re, subprocess, sys
from pathlib import Path
import pandas as pd
import pytest
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from scripts.build import build, check_no_external_urls, validate, SVG_NS


@pytest.fixture(scope="module")
def html(tmp_path_factory):
    out = build(tmp_path_factory.mktemp("dist") / "index.html")
    return out.read_text(encoding="utf-8")


@pytest.fixture(scope="module")
def findings():
    return json.loads((ROOT / "data" / "findings.json").read_text(encoding="utf-8"))


@pytest.fixture(scope="module")
def s():
    return pd.read_csv(ROOT / "data" / "scenarios.csv")


@pytest.fixture(scope="module")
def sn():
    return pd.read_csv(ROOT / "data" / "sensitivity.csv")


def test_build_single_file_no_network(html):
    body = re.sub(r'<section id="references">.*?</section>', "", html, flags=re.S)
    body = body.replace(SVG_NS, "")  # XML namespace identifier, not a network request
    assert "http://" not in body and "https://" not in body
    assert "<link" not in body and 'src="' not in body        # everything inlined
    assert "window.DATA" in html and '"scenarios"' in html
    assert html.count('"country":"NGA"') == 220 + 66          # scenarios 20 × 11 + sensitivity 6 × 11, no duplicates
    assert not re.search(r"\{\{\w+\}\}", html)                # every template token substituted


def test_committed_dist_matches_a_fresh_build(html):
    """dist/index.html is tracked; it must be the build of the committed sources (the data date
    is stamped from git, so a rebuild of unchanged data is byte-identical)."""
    committed = (ROOT / "dist" / "index.html").read_text(encoding="utf-8")
    strip = lambda h: re.sub(r"Data as of \d{4}-\d{2}-\d{2}", "Data as of DATE", re.sub(r'"built":"\d{4}-\d{2}-\d{2}"', '"built":"DATE"', h))
    assert strip(committed) == strip(html), "dist/index.html is stale — run scripts/build.py and commit it"


def test_validate_rejects_truncated_data():
    good = {"scenarios": [{"country": "X", "grid": "g", "mgcost": "m", "tier": 1, "metric": "existing"}] * 880,
            "sensitivity": [0] * 264, "tables": {}, "findings": {}, "geo": {"features": []}}
    with pytest.raises(ValueError, match="duplicate"):
        validate(good)
    with pytest.raises(ValueError, match="880"):
        validate({**good, "scenarios": good["scenarios"][:10]})


def test_check_no_external_urls_whitelists_svg_ns_but_catches_others():
    check_no_external_urls(f'<svg xmlns="{SVG_NS}"><rect/></svg>')  # (a) SVG namespace only -> passes
    with pytest.raises(RuntimeError):  # (b) a real external URL -> raises
        check_no_external_urls('<script src="https://example.org/x.js"></script>')
    check_no_external_urls(  # (c) external URL only inside <section id="references"> -> passes
        '<body><p>no external url here</p>'
        '<section id="references"><a href="https://example.org/paper">ref</a></section></body>')


def test_chrome_smoke(html):
    r = subprocess.run([sys.executable, str(ROOT / "tests" / "smoke_chrome.py")], capture_output=True, text=True)
    if r.returncode == 3:
        pytest.skip("no Chrome/Edge found")
    assert r.returncode == 0, r.stdout + r.stderr


def test_citation_disclaimers_and_status(html):
    cite = "IRENA (2026), <i>Unlocking battery storage potential for sustainable mini-grid electrification in West Africa</i>, International Renewable Energy Agency, Abu Dhabi"
    assert html.count(cite) == 2                                   # footer and References, the report's own citation string
    assert "Unlocking Battery Storage Potential" not in html      # no title-case variant
    assert "978-92-9260-761-6" in html
    assert "do not imply any endorsement or acceptance by IRENA" in html and "official endorsement" not in html
    assert "delimitation of frontiers or boundaries" in html      # copyright-page disclaimer
    assert "not an official IRENA publication" in html
    assert "manuscript under review" not in html and "INTERNAL" not in html and "// Task" not in html


def test_wording_anchors_from_the_published_report(html):
    """Sentences the review corrected against the published edition must not regress."""
    assert "from Tier 3 upwards" in html and "from Tier 2 upwards" not in html
    assert "with optimistic mini-grid costs at Tier 5, the value of storage reaches USD 24.4 billion" in html
    assert "rises by only 10–15%" in html and "rounds this to" not in html
    assert "Agenbroad" in html and "ESMAP (2019)" in html
    for wrong in ("WRI", "cost-of-service tool", "PANER", "Vision Sénégal", "national statistics", "Standalone solar", "Open Source Spatial"):
        assert wrong not in html, wrong
    assert "Solar PV mini-grids installed in Africa, 2024" in html and "installed 2025" not in html
    assert "business model and de-risking" in html
    assert "limited grid expansion" in html and "limited grid extension" not in html


def test_headline_and_card_numbers_resolve_from_the_data(html, findings, s, sn):
    fam = lambda metric: s[s.metric == metric].groupby(["grid", "mgcost", "tier"]).value.sum()
    mix = s[s.metric.isin(["grid_densification", "grid_extension", "minigrid", "standalone"])].groupby(["grid", "mgcost", "tier"]).value.sum()
    # hero
    assert findings["headline"][0]["value"] == "171 M" and 172.0e6 < mix.iloc[0] < 172.3e6          # report rounds 172.2 → 171
    assert findings["headline"][1]["value"] == "568 MW" and round(fam("mg_capacity_mw")[("leastcost", "optimistic", 2)]) == 568
    assert findings["headline"][2]["value"] == "USD 24.4 bn" and round(fam("vos_usd_m")[("restricted", "optimistic", 5)] / 1000, 1) == 24.4
    assert findings["headline"][2]["scenario"] == {"tiers": [5], "grid": "restricted", "mgcost": "optimistic"}   # the lever attribution shown by the glyph
    assert "Tier 5 · restricted grid · optimistic mini-grid costs" in findings["headline"][2]["scenario_text"]
    assert findings["headline"][1]["scenario"] == {"tiers": [2], "grid": "leastcost", "mgcost": "optimistic"}
    cards = {c["id"]: c for c in findings["cards"]}
    # card 2: per-country Tier 2 capacities and the Africa reference line
    t2 = {c: float(s[(s.country == c) & (s.grid == "leastcost") & (s.mgcost == "optimistic") & (s.tier == 2) & (s.metric == "mg_capacity_mw")].value.iloc[0]) for c in ("NGA", "BFA", "MLI", "SEN")}
    assert [round(t2[c]) for c in ("NGA", "BFA", "MLI", "SEN")] == [399, 92, 56, 20]
    assert "Nigeria 399 MW, Burkina Faso 92 MW, Mali 56 MW, Senegal 20 MW" in cards["market"]["text"]
    assert findings["africa_mg_pv_mw_2024"] == 148.65 and "149 MW" in cards["market"]["text"]
    assert 2200 < fam("battery_mwh")[("leastcost", "optimistic", 2)] < 2300 and "2.25 GWh" in cards["market"]["text"]
    # card 3: mini-grid share of new connections under the restricted grid — majority from Tier 3, not Tier 2
    share = fam("minigrid") / mix
    for m in ("optimistic", "pessimistic"):
        assert share[("restricted", m, 2)] < 0.5 and all(share[("restricted", m, t)] > 0.5 for t in (3, 4, 5)), m
    assert round(share[("restricted", "optimistic", 2)] * 100) == 43 and "43% at Tier 2" in cards["constrained"]["text"]
    lvl = lambda ser, name: ser.index.get_level_values(name)
    mgp = fam("minigrid"); mg = mgp[(lvl(mgp, "grid") == "restricted") & (lvl(mgp, "tier") >= 2)]
    assert 47e6 <= mg.min() and mg.max() <= 111e6 and "47–110" in cards["constrained"]["number"]
    # second-largest source under least-cost holds only with optimistic costs (pessimistic: stand-alone is second at Tiers 3-4)
    sa = fam("standalone")
    assert all(fam("minigrid")[("leastcost", "optimistic", t)] > sa[("leastcost", "optimistic", t)] for t in (3, 4, 5))
    assert fam("minigrid")[("leastcost", "pessimistic", 3)] < sa[("leastcost", "pessimistic", 3)]
    assert "with optimistic mini-grid costs they remain" in cards["constrained"]["text"]
    # card 4: stand-alone ≈ 122 M at Tier 1 in every family, 41–67 M at Tier 2 (report: "70–122 million below Tier 3", NOTES item 15)
    t1 = sa[lvl(sa, "tier") == 1]; t2 = sa[lvl(sa, "tier") == 2]
    assert 121e6 < t1.min() and t1.max() < 123e6 and round(t2.min() / 1e6) == 41 and round(t2.max() / 1e6) == 67
    assert "41–67 million at Tier 2" in cards["progression"]["text"] and "70–122 million" in cards["progression"]["text"] and "stand-alone" in cards["progression"]["text"].lower()
    # card 5: USD 24.4 bn / 127 GWh cell named with both levers; 16× vs < 8 GWh under least-cost
    bat = fam("battery_mwh"); lc_max = bat[lvl(bat, "grid") == "leastcost"].max()
    assert round(bat[("restricted", "optimistic", 5)] / 1000) == 127 and round(lc_max / 1000, 1) == 8.2   # report: "less than 8 GWh", "16x"
    assert bat[("restricted", "optimistic", 5)] / lc_max > 15
    assert "restricted grid expansion with optimistic mini-grid costs at Tier 5" in cards["value"]["text"] and "127 GWh" in cards["value"]["text"] and "8.2 GWh" in cards["value"]["text"]
    # card 6: leverage ranges and the report's 10–15% LCOE sentence
    lev = sn[sn.metric == "battery_leverage"].pivot_table(index="country", columns="multiplier", values="value")
    assert (round(lev[1.0].min(), 2), round(lev[1.0].max(), 2)) == (1.94, 2.85) and (round(lev[2.0].min(), 2), round(lev[2.0].max(), 2)) == (3.72, 5.89)
    lcoe = sn[sn.metric == "lcoe_hybrid_usd_kwh"].pivot_table(index="country", columns="multiplier", values="value")
    assert ((lcoe[2.0] / lcoe[1.0] - 1).between(0.08, 0.14)).all()
    fe = sn[(sn.metric == "fuel_exposure_pct") & (sn.country == "BFA") & (sn.multiplier == 2.0)].value.iloc[0]
    assert round(fe) == 87 and "87% of Burkina Faso" in cards["hedge"]["text"]
    assert lev[2.0]["SEN"] > lev[2.0]["BFA"] and "gain most" not in cards["hedge"]["text"]   # Senegal outranks Burkina Faso: no "landlocked gain most"
    # card 1: PV share of the maximum potential (Table 9)
    pot = json.loads((ROOT / "data" / "tables.json").read_text(encoding="utf-8"))["mg_potential"]["connections"]
    tot = {k: sum(pot[c][k] for c in pot) for k in ("pv", "hydro", "wind")}
    assert tot["pv"] / sum(tot.values()) > 0.98 and tot["hydro"] / sum(tot.values()) < 0.02 and tot["wind"] / sum(tot.values()) < 0.001
    for c in findings["cards"]:
        assert c["number"] in html


def test_country_nutshell_ranges_resolve_from_the_data(html, s):
    g = lambda c, gr, m, k: s[(s.country == c) & (s.grid == gr) & (s.mgcost == m) & (s.metric == k)].set_index("tier").value
    # Mali 2.4–2.7 M and Senegal 1.4–2.4 M mini-grid people, Tiers 2–5, least-cost / OPTIMISTIC only
    mli, sen = g("MLI", "leastcost", "optimistic", "minigrid").loc[2:5] / 1e6, g("SEN", "leastcost", "optimistic", "minigrid").loc[2:5] / 1e6
    assert 2.3 <= mli.min() and mli.max() <= 2.7 and 1.35 <= sen.min() and sen.max() <= 2.4
    assert g("MLI", "leastcost", "pessimistic", "minigrid").loc[2:5].max() < 1e6     # why the cost case must be named
    assert html.count("Under least-cost grid expansion with optimistic mini-grid costs, mini-grids serve") == 2
    # Burkina Faso: stand-alone ≈ 20 M at Tier 1; new grid extension ≈ 8 M at Tier 2, 14–18 M at Tiers 4–5; densification ≈ 3 M
    assert 19.5e6 < g("BFA", "leastcost", "optimistic", "standalone")[1] < 20.5e6
    ext = pd.concat([g("BFA", "leastcost", m, "grid_extension") for m in ("optimistic", "pessimistic")], axis=1)
    assert 7.5e6 < ext.loc[2].min() and ext.loc[2].max() < 9e6 and 14e6 < ext.loc[4:5].min().min() and ext.loc[4:5].max().max() < 18.5e6
    assert 2.9e6 < g("BFA", "leastcost", "optimistic", "grid_densification")[1] < 3.1e6
    assert "best served by grid extension" not in html                                 # report says grid *expansion*
    # Nigeria: 127 M people to connect, 71% of the total; 74–80% of restricted MG capacity and 61–74% of VOS at Tiers 3–5
    mixk = ["grid_densification", "grid_extension", "minigrid", "standalone"]
    nga = s[(s.country == "NGA") & (s.grid == "leastcost") & (s.mgcost == "optimistic") & (s.tier == 3) & s.metric.isin(mixk)].value.sum()
    tot = s[(s.grid == "leastcost") & (s.mgcost == "optimistic") & (s.tier == 3) & s.metric.isin(mixk)].value.sum()
    assert 126e6 < nga < 128e6 and round(nga / tot * 100) in (73, 74)                # report rounds to 71% of 171 M
    for k, lo, hi in (("mg_capacity_mw", 0.73, 0.81), ("vos_usd_m", 0.60, 0.75)):
        r = s[(s.grid == "restricted") & (s.tier >= 3) & (s.metric == k)].groupby(["mgcost", "tier"]).value
        share = r.apply(lambda x: x[s.loc[x.index, "country"] == "NGA"].sum() / x.sum())
        assert lo <= share.min() and share.max() <= hi, (k, share)


def test_countries_and_method_content(html):
    for t in ("least-cost grid expansion", "restricted grid expansion", "Multi-Tier Framework", "142 USD/kWh", "Table 9", "OnSSET", "Particle Swarm",
              "kWh per household per year", "Baseline pump prices", "grid densification", "2023–2030 modelling horizon", "Table A6",
              '"kwh_hh_yr":803', '"MLI":0.98'):   # the sensitivity note is rendered at runtime from tables.json
        assert t in html, t
