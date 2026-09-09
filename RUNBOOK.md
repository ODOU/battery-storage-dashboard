# Runbook: battery storage mini-grids dashboard

Operating manual for the companion dashboard to IRENA (2026), *Unlocking battery storage
potential for sustainable mini-grid electrification in West Africa* (ISBN 978-92-9260-761-6).
It is written so that a colleague can rebuild, update, check and publish the dashboard without
the original developer. Read it top to bottom once; afterwards jump to the procedure you need.

Last verified: 9 September 2026, against 46 passing tests.

## 1. What this is and who owns it

- **Purpose.** A single HTML file that presents the report's six key findings, a 20-scenario
  explorer for the four countries (Burkina Faso, Mali, Nigeria, Senegal), country profiles,
  method and sources. It opens from disk and makes no network request. It is a companion by the
  report's lead author, not an official IRENA publication; the page says so in its footer.
- **Owner.** The report's lead author (SEAPS team). Contact them before changing any number.
- **Where it lives.**
  - Working copy (source of truth): `Projects/BatteryStorageDashboard/` in the private
    development repository on the author's machine (git branch `master`).
  - Public copy: https://github.com/ODOU/battery-storage-dashboard (a snapshot of the folder,
    no private history). Local clone: `Projects/BatteryStorageDashboard-github/`.
  - Live page: https://odou.github.io/battery-storage-dashboard/ (GitHub Pages serves
    `index.html` at the repository root; `dist/index.html` is the same file).
  - Published report: https://www.irena.org/Publications/2026/Aug/Unlocking-battery-storage-potential-for-sustainable-mini-grid-electrification-in-West-Africa

## 2. Layout of the folder

| Path | Role | Edit by hand? |
|---|---|---|
| `dist/index.html` | The deliverable, built by `scripts/build.py`. Tracked in git so the last build is always available. | No, rebuild it |
| `src/index.html`, `src/style.css`, `src/app.js`, `src/charts.js`, `src/data.js`, `src/map.js` | Page skeleton, styles and behaviour; inlined into `dist/index.html` at build time | Yes |
| `data/scenarios.csv` | 880 rows: 4 countries × 20 scenarios × 11 metrics, from the manuscript chart caches, aligned with the published annex | No, regenerate |
| `data/sensitivity.csv` | 264 rows: Appendix V, Table A11 | No, regenerate |
| `data/tables.json` | MTF tiers, cost assumptions, Table 9, access rates, national facts, pump prices | No, regenerate |
| `data/sources.json` | Hand-authored facts with their page in the report (published Table 7 wording, Table A6 access, national targets, Table A9 pump prices, Appendix V reference case) | Yes |
| `data/findings.json` | Hero figures, the six finding cards, the four recommendations, scenario glyph specs, figure titles and sources | Yes |
| `data/example_es1.json` | The worked example of Figure 11 | No, regenerate |
| `data/countries.geojson` | Simplified Natural Earth boundaries for the map | No (one-off) |
| `data/NOTES.md` | Every documented difference between manuscript, published tables and dashboard; read before quoting a figure | Yes |
| `scripts/extract_docx.py` | Manuscript DOCX → `data/` (chart caches, tables) merged with `sources.json` | Yes |
| `scripts/apply_published_annex.py` | Published PDF → overwrite the cells the annex prints (Tables 1, 12, 13, 14, A11), check Table 10 | Yes |
| `scripts/build.py` | Inline everything into `dist/index.html`; validates data, refuses external URLs | Yes |
| `tests/` | 46 tests, see section 5 | Yes |
| `README.md`, `BACKLOG.md` | Overview and deferred items | Yes |

## 3. Prerequisites

1. **Python**: the `OnSSET_SENEGAL` conda environment. Every command below uses
   `$PY = C:\Users\OOdou\AppData\Local\anaconda3\envs\OnSSET_SENEGAL\python.exe`.
   On another machine, any Python 3.10+ with `pip install -r requirements.txt` works.
2. **Console encoding**: set `PYTHONIOENCODING=utf-8` before running the scripts (the PDF text
   contains characters the default Windows console cannot print).
3. **Chrome or Edge** installed (the smoke test renders the page headless; it skips if absent).
4. **Source files, kept outside the repository, never committed:**
   - The manuscript DOCX (SMG revision, May 2026):
     `Downloads/myreviews/Report_Battery_MG_Electrification_WestAfrica_SMGRev_Correction.docx`.
     Needed only to regenerate the per-country technology mix and the value-of-storage
     components, which the published PDF does not print.
   - The published PDF: `Downloads/myreviews/IRENA_TEC_Battery_storage_minigrids_W_Africa_2026*.pdf`
     (the browser may add " (1)" to the name; the tests tolerate that). Download from the report
     page; irena.org refuses generic fetchers, so use a browser or `curl` with a browser
     user agent. The 31 August 2026 file has SHA-256 starting `ba7f7073253d0e6b`.
5. **Git identity**: commits are authored as Thierry Odou; the public repository is pushed with
   the GitHub account stored in Git Credential Manager on the author's machine (account `ODOU`).

## 4. Procedures

All commands run in Git Bash from `Projects/BatteryStorageDashboard/` unless stated.

### 4.1 Rebuild the page after editing text or code

```
export PYTHONIOENCODING=utf-8
$PY scripts/build.py          # writes dist/index.html, prints its size
$PY -m pytest -q              # expect: 46 passed (45 passed, 1 skipped without the PDF)
```

Open `dist/index.html` in a browser and look at the tab you changed. Then commit
(section 4.6) and, when the result is agreed, publish (section 4.7).

### 4.2 Change a sentence on the page

- Cards, hero figures, recommendations: `data/findings.json`. Each card carries its scenario
  (`scenario`, `scenario_text`), figure title (`figure`) and source (`source`); each
  recommendation carries the report's text (`body`), optional `actions` and the finding numbers
  it links to.
- Country profiles, Method tab, Explorer notes: string literals in `src/app.js`
  (`NUTSHELL`, the Method template near the end of the file).
- References and footer: `src/index.html`.
- Country facts, pump prices, MTF wording: `data/sources.json`, then regenerate `tables.json`
  (section 4.3) because `tables.json` is a generated file.

House rules the tests enforce: percentages as `5%`, thousands with a narrow no-break space
(`42 700`), the report's citation string verbatim, no em dashes in prose, and a set of
wording anchors listed in `tests/test_build.py::test_wording_anchors_from_the_published_report`.
If a rewrite changes an anchored phrase, update the test in the same commit and say why.

### 4.3 Update the numbers when the report or the manuscript changes

Run the three steps in this order; each one overwrites files in `data/`.

```
export PYTHONIOENCODING=utf-8
$PY scripts/extract_docx.py "C:/Users/OOdou/Downloads/myreviews/Report_Battery_MG_Electrification_WestAfrica_SMGRev_Correction.docx"
$PY scripts/apply_published_annex.py "C:/Users/OOdou/Downloads/myreviews/IRENA_TEC_Battery_storage_minigrids_W_Africa_2026.pdf"
$PY scripts/build.py
$PY -m pytest -q
git diff --stat data/
```

What to expect:
- `extract_docx.py` prints `wrote scenarios.csv, example_es1.json, tables.json, sensitivity.csv`.
  It refuses to run if the chart order in the DOCX changed (error names the chart).
- `apply_published_annex.py` prints every cell it changed. With the 31 August 2026 PDF it
  reports 11 changes against the manuscript (ten value-of-storage cells and Senegal's access
  rate); re-running it on already aligned data prints `0 cell(s) changed`. It raises, and writes
  nothing, if a table caption is missing, a column order differs, a printed TOTAL does not equal
  the sum of its countries, or Table 10 disagrees with the per-country mix.
- `git diff --stat data/` shows only the files you expected. If `scenarios.csv` changed after a
  no-change run, stop and investigate before committing.

If only the hand-authored facts changed (`sources.json`), you still need `extract_docx.py`
to regenerate `tables.json`; there is no shortcut.

### 4.4 Add or change a source file on a new machine

Put the DOCX and PDF in `Downloads/myreviews/` under the names above, or point the tests at the
PDF with `export BATTERY_REPORT_PDF="<path>"`. Without them, the source-dependent tests skip
and everything else still runs.

### 4.5 Check the page before hand-over

1. `$PY -m pytest -q` is green.
2. Open `dist/index.html`; check the four tabs; on the Explorer, move the tier slider and select
   a country; on the findings tab, open a recommendation and click a "See Finding" link.
3. Print preview (Ctrl+P): every tab prints, hero figures in dark ink.
4. Optional headless render, useful for a quick visual diff:
   `"C:/Program Files/Google/Chrome/Application/chrome.exe" --headless=new --disable-gpu --hide-scrollbars --allow-file-access-from-files --window-size=1280,2300 --virtual-time-budget=8000 --screenshot=out.png "file:///C:/PrivateToolsDevelopment/Projects/BatteryStorageDashboard/dist/index.html"`

### 4.6 Commit

```
git add data/ src/ dist/index.html tests/ README.md RUNBOOK.md
git -c user.name="Thierry Odou" -c user.email="thierryodou@gmail.com" commit
```

Commit the rebuilt `dist/index.html` together with the change that caused it; the tests fail
if the committed build is stale.

### 4.7 Publish to GitHub Pages

The public repository is a snapshot of this folder. To publish the committed state:

```
cd /c/PrivateToolsDevelopment/Projects/BatteryStorageDashboard-github
git -C /c/PrivateToolsDevelopment archive HEAD Projects/BatteryStorageDashboard | tar -x --strip-components=2
cp dist/index.html index.html
git add -A
git -c user.name="Thierry Odou" -c user.email="thierryodou@gmail.com" commit -m "<what changed>"
git push origin main
```

GitHub Pages rebuilds in one to two minutes. Verify with
`curl -s -o /dev/null -w '%{http_code}' https://odou.github.io/battery-storage-dashboard/`
(expect 200) and reload the page in a browser.

Publish only after the author has looked at the local build; the rule in this project is
"commit locally first, push on agreement".

### 4.8 Share

- Link: https://odou.github.io/battery-storage-dashboard/ (public, no account needed).
- File: send `dist/index.html` (about 240 kB). It opens by double-click. Some mail gateways
  strip `.html` attachments; zip it or use Teams if that happens.
- SharePoint or OneDrive show the file as a download, not a page.

## 5. Tests: what each file guards

| File | What it checks | Needs |
|---|---|---|
| `tests/test_data_integrity.py` | Shape and uniqueness of both CSVs, the 172.18 M mix identity in every scenario, family totals printed in the report, monotonic sensitivity metrics, `tables.json` consistent with `sources.json` | nothing |
| `tests/test_build.py` | Single file, no external URL, committed build current, every hero and card number and every country range recomputed from the CSVs, wording anchors, recommendations text, citation and disclaimers; runs the Chrome smoke test | Chrome (skips otherwise) |
| `tests/test_published_annex.py` | Published anchor values; parser unit tests on fixtures; re-applying the PDF is a no-op | PDF for the last test |
| `tests/test_extract.py` | Extractor output from the DOCX | DOCX (skips otherwise) |
| `tests/test_geojson.py`, `tests/test_docx_charts.py` | Map data and chart reader | nothing |
| `tests/smoke_chrome.py` | Headless render: charts present, no `NaN`/`undefined`, zero rule (`—`) on the map and heat table, axis ticks complete, recommendations expandable | Chrome |

Run everything: `$PY -m pytest -q`. Run one file: `$PY -m pytest -q tests/test_build.py`.

## 6. Troubleshooting

| Symptom | Cause | Remedy |
|---|---|---|
| `1 skipped` in the test summary | The published PDF is not at the default path | Save it to `Downloads/myreviews/` or set `BATTERY_REPORT_PDF` |
| `test_committed_dist_matches_a_fresh_build` fails | `dist/index.html` was not rebuilt after a source change | `$PY scripts/build.py`, then commit the result |
| `UnicodeEncodeError ... cp1252` | Console encoding | `export PYTHONIOENCODING=utf-8` |
| `apply_published_annex.py`: `caption ... found on 0 pages` | Different PDF edition, or the text layer changed | Check the caption regex in the script against the PDF; do not edit `data/` by hand |
| `apply_published_annex.py`: `column order ... differs` | The annex table prints countries in a new order | Update the header tuple in `apply()`; the script refuses to guess |
| `extract_docx.py`: `chart N is not the ... chart` | The manuscript's chart order changed | Update `COUNTRY_CHARTS` in the script after checking `docx_charts.read_charts` titles |
| Page opens blank, or a tab is empty | A JavaScript error; the page shows a red banner with the message | Open the browser console (F12); usually a malformed `findings.json` |
| Charts show but line charts have no lines | The line-trace animation was applied to a chart that never revealed | Only charts inside `#cards` are primed; check `observeReveals` in `src/app.js` |
| Live page not updating after a push | GitHub Pages still building, or the browser cache | Wait two minutes, hard-reload (Ctrl+F5); check the Actions tab of the repository |
| `git push` says `repository not found` | Wrong account in Git Credential Manager | `git credential-manager github list` should show `ODOU`; otherwise sign in again |
| "42 700" wraps across two lines | A normal space instead of the narrow no-break space | Numbers in text go through `nb()` in `src/app.js`; counts use `D.nfmt` |

## 7. Limits and open questions

- The DOCX remains the only source for the per-country technology mix and the value-of-storage
  components; the published PDF does not print them.
- Report headline figures that differ from the annex are shown as annex values with the
  report's figure named alongside (171 M vs 172.2 M; "nearly USD 25 billion" vs USD 24.4 bn;
  "< 8 GWh" vs 8.2 GWh; "70–122 million" vs 41–67 million at Tier 2). Details in `data/NOTES.md`.
- Questions for the authors, still open: the settlement set of the Appendix V run; the
  definition of `battery_leverage` in Table A11; whether the Burkina Faso +10% diesel row is a
  converged optimisation; whether the Figure 11 example is discounted. See `BACKLOG.md`.
- Deferred improvements are listed in `BACKLOG.md`.

## 8. Change log of the runbook

- 2026-09-09: first version, written after the 5–8 September review, redesign and publication.
