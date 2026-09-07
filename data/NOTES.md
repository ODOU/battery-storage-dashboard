# Data notes

Base extraction: manuscript SMG revision (May 2026) chart caches and tables.
Aligned with the published edition (IRENA, 2026, ISBN 978-92-9260-761-6) on
31 August 2026 by `scripts/apply_published_annex.py`; see items 10–13 below.

1. Executive summary prints Nigeria Tier 2 battery as "1.592 MWh"; the annex and
   chart cache give 1,592.8 MWh. The dashboard uses 1,592.8 MWh.
2. Value of storage = cost(PV/diesel) − cost(PV/diesel/battery), discounted at 10 %
   (fuel + O&M savings minus incremental investment). Chart caches give the three
   components; `vos_usd_m` is the net.
3. Chart caches are in kWh (battery), kW (MG capacity), USD, people; the CSV is in
   MWh, MW, USD million, people.
4. Tier 1 pessimistic / Tier 1 restricted families have zero mini-grid deployment in
   most countries; the dashboard renders them as a dash, not 0.0.
5. Four-country totals in the text (e.g. 47–110 M mini-grid people, USD 24.4 bn,
   127–130 GWh) are sums of the per-country series; tests assert reconciliation
   with charts 20 and 22.
6. The four VOS charts (7, 11, 15, 19: Increased Investments, Fuel Savings,
   OM Savings, Value of storage, one per country) cache 21 values per series, not
   20: the source Excel range for each has one stray numeric cell at the
   family0/family1 boundary (document position 5) that carries no tier category
   (confirmed against the chart XML's category cache and against both VOS annex
   anchors in the tests). `extract_docx._drop_stray` removes it before the 20-value
   family/tier reshape.
7. Appendix V (called Appendix E in the manuscript) baseline (multiplier 1.0) does not match the Tier 3 / restricted /
   optimistic scenario for any country (Senegal battery 727 vs 351.6 MWh; VoS 228.2 vs 111.27 USD m;
   Burkina Faso 6 201 vs 5 291.6 MWh). Appendix V (p. 82) describes its own scope as "mini-grid PV systems
   that serve settlements not currently reached by the national grid", re-optimised per diesel-price
   level, so it is a separately scoped run, not a subset of Tables 12–14. The dashboard says so under
   the sensitivity panel and in the References. Open question for the authors: the exact settlement set.
8. Hero "171 M people to connect" is the report's rounded figure; the scenario
   data sum to 172.2 M.
9. Nigeria Tier 1 small non-zero mini-grid values (≈1.3 MW for ≈269 k people) are
   genuine Tier 1 loads, not extraction noise. Do not "clean" them.
10. Published Table 14 (value of storage) revised ten pessimistic-cost cells
    relative to the manuscript chart caches: Nigeria least-cost T3–T5 (33.85 →
    33.92, 18.13 → 18.85, 12.89 → 14.30 USD m), Nigeria restricted T2–T5
    (423.24 → 423.43, 1 396.70 → 1 401.79, 3 837.77 → 3 921.62, 4 720.81 →
    5 008.95), Burkina Faso restricted T4 (+0.03) and T5 (2 173.015 → 2 173.34, +0.32) and Senegal
    restricted T5 (+0.01). `vos_usd_m` now carries the published values; the three VOS components
    (investment, fuel, O&M savings) are still the manuscript chart values, are not displayed, and
    for these ten cells no longer sum to the net (the residuals reproduce the revisions to the cent).
    All other annex cells compared (Table 10: 100 checked, not written; Tables 12–14: 80 each) and
    all 264 Table A11 cells matched exactly. Cells that agree within the published rounding keep the
    higher-precision manuscript value (tolerances 0.051 MWh/MW, 0.0051 USD m), which is why family
    sums carry more digits than the printed tables.
11. Published Table 1 gives Senegal 74.2 % access in 2023 (IEA et al., 2024);
    the manuscript's 68 % (Tracking SDG 7) is superseded. Mali 54.5 %, Burkina
    Faso 21.7 %, Nigeria 61.2 % unchanged.
12. The published summary rounds: "nearly USD 25 billion", "about 130 GWh",
    "<8 GWh", "16x higher deployment"; the annex gives 24 406.52 USD m and
    127.2 GWh (127 163.8 MWh, sum of Table 12, Tier 5 restricted optimistic). The
    dashboard quotes the annex values and says so in the References. The 568 MW /
    ≈42 700 settlements / ≈21 million people framing of the Tier 2 market is taken
    from the published summary; Table 11 gives 24.1 M mini-grid people for the same
    scenario (Tier 2, least-cost, optimistic); the 21 M figure follows the Table 9
    basis (mini-grids above 10 kW), as does card 1.
13. Appendix V says hybrid mini-grid LCOE rises "by only 10–15 %" when diesel
    doubles (Box S1 p. 12; p. 83). Table A11's 3-dp LCOE values give 8.8–12.8 % per
    country (±0.5 pp from rounding). The dashboard quotes the report's 10–15 % (card 6);
    the per-country values remain visible in the sensitivity chart. Errata question
    for the authors, not adjudicated on the page.
14. `data/sources.json` (hand-authored, 2026-09-05) holds every fact that is not in a
    chart cache or annex table: published Table 7 wording, Table A6 urban/rural access
    (2023, all four countries; the manuscript's 2020 pairs for two countries are
    superseded), the national-target facts with their table/page, Table A9 pump prices
    and the Appendix V reference case. `extract_docx.py` merges it into tables.json.
15. Report-vs-scenario rounding conventions, as displayed: 171 M (report) vs 172.2 M
    (Table 11 sum, footnoted in the Explorer); Nigeria "127 million" (p. 43; p. 45 says
    130 million; scenarios 126.6 M); "47–110 million" (p. 50; scenarios 47.4–110.8 M;
    the Conclusion says 60–110); "up to 4:1" (report; scenario maximum 4.78 at Burkina
    Faso restricted Tier 2); "less than 8 GWh" under unconstrained grid expansion (Table 12 sums
    to 8.24 GWh at Tier 5 least-cost / optimistic, so the "16x" contrast is 15.4 in the annex);
    "70–122 million people (below Tier 3)" for stand-alone solar (p. 50), while Table 11 gives 121.8–122.0 M
    at Tier 1 in every family and 40.5–66.8 M at Tier 2 (40.5 M in the least-cost / optimistic
    family the sentence refers to), so the lower bound is not reproducible from the annex.
    The dashboard keeps the report's figures and shows the annex value where the two differ.
16. Data properties worth knowing before quoting: `existing` and `grid_densification`
    are constant across all 20 scenarios by construction (they depend only on the
    existing network); the Burkina Faso +10 % diesel row is the only non-monotonic
    sensitivity row (battery 6 201 → 5 555 MWh, renewable share 96 → 91 %); the implied
    battery unit cost (investment / MWh) falls as diesel rises in all four countries;
    `battery_leverage` in Table A11 is not derivable from the other columns (Burkina
    Faso baseline VoS / battery investment = 2.02, tabulated 2.74) and is used as
    printed. All four are open questions for the authors.
