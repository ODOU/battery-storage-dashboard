# Backlog

Items deferred from the 2026-08-28 build reviews and the 2026-09-05 whole-dashboard review.
Non-blocking. Everything the 2026-09-05 review found blocking was fixed in the three commits of
that day (wording and sources; rendering and accessibility; tests and pipeline hardening).

## Presentation
- Choropleth colour scale is quintile-based over all scenarios (fixed meaning, legend with break
  values); a log scale would separate the three smaller countries better when Nigeria dominates.
- No dark mode (`color-scheme: only light` is declared deliberately).
- Value-of-storage decomposition chart (investment / fuel / O&M components are in the data but not
  rendered): `charts.js` cannot draw negative series yet (`vos_investment_usd_m` is negative), so give
  `nice()`/`yAxis` a signed domain first.
- Responsiveness below 548 px could not be rendered headlessly (Chrome floors the window width);
  check once on a phone.

## Build and data pipeline
- 36 % of the inlined `scenarios.csv` rows (`existing`, the three VOS components) and 6 of 11
  sensitivity metrics are never rendered; kept deliberately so the file is a complete data export.
- `make_geojson.py` hard-codes the Natural Earth gpkg path of a sibling project (one-off script).
- `apply_published_annex.py` writes a genuine dash in a published table as 0.0. The UI restores the
  dash through `D.fmt`; the CSV loses the distinction.

## Data questions for the authors (see data/NOTES.md items 7, 15, 16)
- Appendix V (manuscript "Appendix E") baseline does not match the Tier 3 / restricted / optimistic
  scenario for any country. Confirm the settlement set of the Appendix V run.
- Definition of `battery_leverage` in Table A11 (not derivable from the other columns).
- Whether the Burkina Faso +10 % diesel row is a converged optimisation.
- Hero "171 M" vs scenario total 172.2 M; Nigeria "127 million" (p. 43) vs "130 million" (p. 45).
- Whether `example_es1.json` (Figure 11) is discounted or undiscounted lifetime cost.
