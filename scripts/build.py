"""Inline data + src into one dist/index.html. Fails if any external URL slipped in, if a data
file is missing or malformed, or if a template token was left unsubstituted."""
import csv, json, re, subprocess, datetime
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]
SRC, DATA, DIST = ROOT / "src", ROOT / "data", ROOT / "dist"
SCRIPTS = ["data.js", "charts.js", "map.js", "app.js"]
REGENERATE = {"scenarios.csv": "scripts/extract_docx.py then scripts/apply_published_annex.py",
              "sensitivity.csv": "scripts/extract_docx.py then scripts/apply_published_annex.py",
              "tables.json": "scripts/extract_docx.py (merges data/sources.json)",
              "example_es1.json": "scripts/extract_docx.py",
              "countries.geojson": "scripts/make_geojson.py",
              "findings.json": "hand-authored — restore from git",
              "sources.json": "hand-authored — restore from git"}
SCENARIO_METRICS = {"existing", "grid_densification", "grid_extension", "minigrid", "standalone", "battery_mwh",
                    "vos_investment_usd_m", "vos_fuel_savings_usd_m", "vos_om_savings_usd_m", "vos_usd_m", "mg_capacity_mw"}

# The SVG XML namespace identifier required by document.createElementNS(). It is a
# constant string literal, never dereferenced as a network request/fetch by the
# browser, so it is whitelisted out of the external-URL embargo check below.
SVG_NS = "http://www.w3.org/2000/svg"

def check_no_external_urls(html):
    """Raise RuntimeError if html contains an external http(s) URL outside the
    <section id="references"> block, ignoring the inert SVG_NS XML namespace literal."""
    body = re.sub(r'<section id="references">.*?</section>', "", html, flags=re.S)
    body = body.replace(SVG_NS, "")  # not a network request -- see SVG_NS comment above
    if re.search(r"https?://", body):
        raise RuntimeError("external URL found outside references: " + re.search(r"https?://\S{0,60}", body).group(0))

def _read(name):
    p = DATA / name
    if not p.exists():
        raise FileNotFoundError(f"{p} is missing — regenerate with {REGENERATE.get(name, '?')}")
    return p

def _csv(name):
    with open(_read(name), encoding="utf-8", newline="") as f:
        rows = list(csv.DictReader(f))
    for i, r in enumerate(rows, 2):
        for k in ("tier", "value", "multiplier"):
            if k in r:
                try:
                    r[k] = int(r[k]) if k == "tier" else float(r[k])
                except ValueError:
                    raise ValueError(f"{name} row {i}: column {k}={r[k]!r} is not a number") from None
    return rows

def _json(name):
    return json.loads(_read(name).read_text(encoding="utf-8"))

def validate(data):
    """Shape checks on the inlined data: the dashboard renders blank charts, not errors, when a
    series is missing, so a truncated file must fail the build instead."""
    s = data["scenarios"]
    if len(s) != 880:
        raise ValueError(f"scenarios.csv: {len(s)} rows, expected 880 (4 countries × 20 scenarios × 11 metrics)")
    keys = {(r["country"], r["grid"], r["mgcost"], r["tier"], r["metric"]) for r in s}
    if len(keys) != 880:
        raise ValueError("scenarios.csv: duplicate (country, grid, mgcost, tier, metric) keys")
    if {r["metric"] for r in s} != SCENARIO_METRICS:
        raise ValueError(f"scenarios.csv: metric set {sorted({r['metric'] for r in s})}")
    if len(data["sensitivity"]) != 264:
        raise ValueError(f"sensitivity.csv: {len(data['sensitivity'])} rows, expected 264 (4 × 6 × 11)")
    t = data["tables"]
    for key in ("mtf", "mg_costs", "mg_potential", "access", "national", "pump_prices_usd_l", "reference_case"):
        if key not in t:
            raise ValueError(f"tables.json: missing '{key}' — re-run scripts/extract_docx.py")
    f = data["findings"]
    for key in ("headline", "cards", "recommendations", "recommendations_source", "africa_mg_pv_mw_2024"):
        if key not in f:
            raise ValueError(f"findings.json: missing '{key}'")
    if len({feat["properties"]["iso3"] for feat in data["geo"]["features"] if feat["properties"].get("focus")}) != 4:
        raise ValueError("countries.geojson: expected four focus countries")

def data_date():
    """Date of the last commit touching data/ (so a rebuild of unchanged data is byte-identical);
    the newest file's mtime when git is unavailable."""
    try:
        out = subprocess.run(["git", "log", "-1", "--format=%cs", "--", str(DATA)], cwd=ROOT, capture_output=True, text=True, timeout=20)
        if out.returncode == 0 and out.stdout.strip():
            return out.stdout.strip()
    except (OSError, subprocess.SubprocessError):
        pass
    return max(datetime.date.fromtimestamp(p.stat().st_mtime) for p in DATA.iterdir()).isoformat()

def build(out=None):
    data = {"scenarios": _csv("scenarios.csv"),
            "sensitivity": _csv("sensitivity.csv"),
            "tables": _json("tables.json"),
            "example": _json("example_es1.json"),
            "findings": _json("findings.json"),
            "geo": _json("countries.geojson"),
            "built": data_date()}
    validate(data)
    html = (SRC / "index.html").read_text(encoding="utf-8")
    html = html.replace("{{STYLE}}", (SRC / "style.css").read_text(encoding="utf-8"))
    html = html.replace("{{DATA_JSON}}", json.dumps(data, separators=(",", ":"), ensure_ascii=False).replace("</", "<\\/"))
    html = html.replace("{{SCRIPTS}}", "\n".join((SRC / s).read_text(encoding="utf-8") for s in SCRIPTS))
    html = html.replace("{{BUILT}}", data["built"])
    left = re.findall(r"\{\{\w+\}\}", html)
    if left:
        raise RuntimeError(f"unsubstituted template tokens: {sorted(set(left))}")
    check_no_external_urls(html)
    out = Path(out) if out else DIST / "index.html"
    out.parent.mkdir(exist_ok=True, parents=True)
    out.write_text(html, encoding="utf-8")
    print(out, f"{out.stat().st_size/1e6:.2f} MB")
    return out

if __name__ == "__main__":
    build()
