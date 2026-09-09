# West Africa Battery Storage Mini-grids Dashboard

Companion to the IRENA report *Unlocking battery storage potential for
sustainable mini-grid electrification in West Africa* (IRENA, 2026,
ISBN 978-92-9260-761-6), published 31 August 2026:
<https://www.irena.org/Publications/2026/Aug/Unlocking-battery-storage-potential-for-sustainable-mini-grid-electrification-in-West-Africa>

**Status:** figures aligned with the published edition (31 August 2026); reviewed, redesigned
and published on 8 September 2026. Live at <https://odou.github.io/battery-storage-dashboard/>
(public snapshot repository `ODOU/battery-storage-dashboard`). Publish only after the local
build has been reviewed; see `RUNBOOK.md` section 4.7.

Operating manual: `RUNBOOK.md` (rebuild, update the numbers, test, publish, troubleshoot).

Single-file web companion (`dist/index.html`) to the report: key findings
storyboard + 20-scenario × 4-country explorer. Opens from disk; makes no
network request.

## What is inside

- **Key findings**: six headline cards (mini-grid potential,
  market size, constrained-grid technology mix, progression by tier, value
  of storage by scenario family, battery investment leverage) plus the
  policy recommendations.
- **Explorer**: interactive controls (demand tier, grid outlook, mini-grid
  cost case, map metric) driving the four-country choropleth map, KPI row,
  technology mix, tier trends, 20-scenario heat-table, diesel-price
  sensitivity chart and a CSV export of the underlying data.
- **Countries**: a profile per country (Burkina Faso, Mali, Nigeria, Senegal)
  summarising the range of outcomes across scenario families.
- **Method & data**: MTF tiers, cost assumptions, the value-of-storage
  definition, Table 9, tools and sources, the references and the boundaries
  disclaimer. The map in the Explorer carries the report's map disclaimer.

## Design

Front-end principles applied on 2026-09-05 after comparing IRENA's own site (Graphik on
navy/#007db1 with pale tints), the IEA report pages (assertion-plus-narrative sections, sticky
outline) and Our World in Data (every chart framed with a title, context and source):

- **IRENA brand as the token system** (`src/style.css` `:root`): IRENA Blue `#0073AE`, IRENA
  Grey `#5E5B5C`, the technology palette for series, a navy cover band from IRENA's own blue ramp,
  pale-blue tints for panels, Solar PV yellow `#F9D900` as the single accent; geometric display
  face for titles (Century Gothic → Gotham → Montserrat), Segoe UI/Arial body, tabular numerals;
  percentages written `5%` and thousands with a thin space, as the Publications Management
  Guidelines require.
- **Structure as information**: every chart carries a figure title above and a `Source: Table …`
  line below; the six cards are numbered because the report presents its findings in that
  sequence; the Explorer states the selected scenario in one line above the results.
- **Signature element, the scenario glyph**: a 5 × 4 mini-matrix of the twenty scenarios
  (columns Tier 1–5; rows least-cost/optimistic, least-cost/pessimistic, restricted/optimistic,
  restricted/pessimistic) with the cells a figure refers to lit. It appears on each headline
  figure, each finding card and the Explorer's current selection, so the lever attribution of
  every number is visible at a glance. Scenario specs live in `data/findings.json` (`scenario`,
  `scenario_text`, `figure`, `source`).
- Motion, kept subtle: hero figures count up, finding cards and their charts draw in as they
  scroll into view, map fills cross-fade; all of it off under reduced-motion and print. No external
  fonts or scripts (the file stays offline), keyboard and screen-reader paths kept. The four policy
  recommendations expand to the report's own text and link to the findings they rest on.

## Rebuild

````
$PY scripts/extract_docx.py <path-to-manuscript.docx>       # → data/ (chart caches: per-country mix, VOS components)
$PY scripts/apply_published_annex.py <path-to-published.pdf> # → data/ aligned with published Tables 1, 12–14, A11
$PY scripts/make_geojson.py                                  # → data/countries.geojson (one-off)
$PY scripts/build.py                                         # → dist/index.html
$PY -m pytest
````

The DOCX (SMG revision, May 2026) is still needed because the published PDF
has no per-country new-connections mix and no value-of-storage components;
the PDF (public) is the authority for every number it prints. Neither file
is kept in the repository; the tests skip the source-dependent checks when
they are absent. Facts that come from neither (published Table 7 wording,
Table A6 urban/rural access, national targets, pump prices, the Appendix V
reference case) live in `data/sources.json` with their page in the report;
edit that file, not `tables.json`.

Python: OnSSET_SENEGAL conda environment
(`C:\Users\OOdou\AppData\Local\anaconda3\envs\OnSSET_SENEGAL\python.exe`).

Tests (`pytest`, 46 tests) build into a temporary directory and never rewrite
`dist/`; `test_data_integrity.py` checks the committed CSVs without either
source file; `test_build.py` resolves every storyboard number and country
range from the data and pins the wording anchors of the 2026-09-05 review;
`test_published_annex.py` unit-tests the PDF parsers on fixtures and, when
`BATTERY_REPORT_PDF` (or the default Downloads path) exists, re-applies the
published PDF and expects a no-op. `dist/index.html` is stamped with the date
of the last commit touching `data/`, so a rebuild of unchanged data is
byte-identical and the tests assert that the committed file is current.

## Data notes

See `data/NOTES.md` for the documented differences between the report text,
its chart caches and the published annex (battery-figure rounding, the stray
chart-cache cell, zero-deployment rendering, the ten value-of-storage cells
revised at publication, the report's rounded summary figures). Read it
before quoting any figure from this dashboard.

## Publication status

31 August 2026: embargo footer removed; `apply_published_annex.py` run on the published PDF
(ten value-of-storage cells and Senegal's 2023 access rate updated; see `data/NOTES.md`
items 10–11); official reference and ISBN added.

5–8 September 2026: full review against the published edition, IRENA-brand redesign, prose
pass, motion and expandable recommendations; published on GitHub Pages. How to update and
republish: `RUNBOOK.md`.
