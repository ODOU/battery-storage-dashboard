"""Render dist/index.html in headless Chrome and check the DOM: tabs, SVG charts, no 'undefined'/'NaN' text.

Also verifies the zero-deployment -> em-dash rule: a one-country selection (e.g. BFA) is
injected via a tiny test-only bootstrap script appended after the page's own scripts (BFA
has an exact 0.0 at demand Tier 1 for every metric and every grid/mini-grid-cost family --
unlike NGA, which always carries a small nonzero residual there, so "All four countries"
sums are never exactly zero and would not exercise the rule). The real dist/index.html on
disk is never modified -- the bootstrap is spliced into an in-memory copy rendered from a
temporary file.
"""
import shutil, subprocess, sys, re, tempfile, os
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]

CHROME_CANDIDATES = [
    r"C:\Program Files\Google\Chrome\Application\chrome.exe",
    r"C:\Program Files (x86)\Google\Chrome\Application\chrome.exe",
    os.path.expandvars(r"%LOCALAPPDATA%\Google\Chrome\Application\chrome.exe"),
    r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe",
]

def _find_browser():
    for p in CHROME_CANDIDATES:
        if p and os.path.exists(p):
            return p
    for name in ("chrome", "msedge"):
        p = shutil.which(name)
        if p:
            return p
    return None

CHROME = _find_browser()
if CHROME is None:
    print("SKIP: no Chrome/Edge found")
    sys.exit(3)

dist_html = (ROOT / "dist" / "index.html").read_text(encoding="utf-8")

# Select a single country (BFA) and re-render, after the page's own scripts (and their
# initial render()) have already run -- document order guarantees this runs last.
bootstrap = ('<script>if (typeof S !== "undefined" && typeof renderNow === "function") {'
             ' S.country = "BFA"; renderNow();'
             # then the map/heat-table zero rule for the "people" metric at Tier 1 (both must read "—" for BFA)
             ' S.metric = "minigrid"; S.tier = 1; renderNow();'
             ' document.body.insertAdjacentHTML("beforeend", "<pre id=probe>MAPLABEL=" + document.querySelector("#map text tspan:last-child").textContent'
             ' + "|TICKS=" + [...document.querySelectorAll("svg text.tick")].map(t => t.textContent).join(";") + "</pre>"); }</script>')
assert "</body>" in dist_html, "dist/index.html has no </body> to splice the test bootstrap before"
patched_html = dist_html.replace("</body>", bootstrap + "\n</body>")

fd, tmp_path = tempfile.mkstemp(suffix=".html")
try:
    with os.fdopen(fd, "w", encoding="utf-8") as f:
        f.write(patched_html)
    url = Path(tmp_path).resolve().as_uri()
    dom = subprocess.run([CHROME, "--headless=new", "--disable-gpu", "--allow-file-access-from-files",
                          "--virtual-time-budget=3000", "--dump-dom", url],
                         capture_output=True, text=True, encoding="utf-8", errors="replace").stdout
finally:
    os.remove(tmp_path)

text = re.sub(r"<script.*?</script>", "", dom, flags=re.S)
problems = []
if text.count("<svg") < 6: problems.append(f"only {text.count('<svg')} svg")
if re.search(r">\s*(NaN|undefined|null)\s*<", text): problems.append("NaN/undefined/null rendered")
for i in ("tab-findings", "tab-explorer", "tab-countries", "tab-method"):
    if f'id="{i}"' not in text: problems.append("missing " + i)

# Zero-deployment scenarios (e.g. Tier 1, Burkina Faso) must render as "--", not "0.0 ...".
# With BFA selected, the heat-table's Tier 1 row is all exact 0.0 (no mini-grid deployment
# at that demand tier in BFA, for any grid/mini-grid-cost family) -- so that row's <tr> must
# contain at least one "--" cell, and none of its value cells may read "0.0 ..." / "USD 0 m".
tier1_m = re.search(r'<tr><th scope="row">Tier 1</th>(.*?)</tr>', text, re.S)
tier1_row = tier1_m.group(1) if tier1_m else ""
if not tier1_row: problems.append("Tier 1 heat-table row not found")
elif "—" not in tier1_row: problems.append("Tier 1 heat-table row has no em-dash cell")
if re.search(r">\s*(0\.0 MWh|0\.0 MW|USD 0\.0 m|0 MWh|0 MW|0 k)\s*<", tier1_row): problems.append("Tier 1 heat-table row still shows a literal zero")

# Probe written by the bootstrap after switching to the "people served by mini-grids" metric at Tier 1.
probe = re.search(r"MAPLABEL=(.*?)\|TICKS=(.*?)</pre>", text, re.S)   # `text` has the scripts stripped, so the bootstrap source itself cannot match
if not probe: problems.append("probe not written (renderNow failed?)")
else:
    if probe.group(1).strip() != "—": problems.append(f"BFA map label at Tier 1 / people is {probe.group(1)!r}, expected em-dash")
    ticks = [t for t in probe.group(2).split(";") if t]
    # Every axis tick must be a complete label: a number, or a number with a unit, or "USD …" — never a clipped fragment such as "iD 50.0 bn".
    bad = [t for t in ticks if not re.fullmatch(r"(0|USD .+|< .+|[\d.,  ]+( ?[A-Za-z%/]+)?|baseline|\+\d+ ?%|[A-Za-z][A-Za-z /]+|Tier \d|\d)", t)]
    if bad: problems.append(f"malformed axis ticks: {bad[:8]}")

print("svg:", text.count("<svg"), "len:", len(text))
if problems:
    print("PROBLEMS:", problems); sys.exit(1)
