/* Accessors over the embedded DATA. Global: D */
const D = (() => {
  const rows = DATA.scenarios;
  const idx = new Map();
  for (const r of rows) idx.set(`${r.country}|${r.grid}|${r.mgcost}|${r.tier}|${r.metric}`, r.value);
  const COUNTRIES = ["BFA", "MLI", "NGA", "SEN"];
  const NAMES = { BFA: "Burkina Faso", MLI: "Mali", NGA: "Nigeria", SEN: "Senegal" };
  const COLORS = { BFA: "#0073AE", MLI: "#EE8700", NGA: "#00975F", SEN: "#6E398E" };
  const FAMILIES = [["leastcost", "optimistic"], ["leastcost", "pessimistic"], ["restricted", "optimistic"], ["restricted", "pessimistic"]];
  const FAMILY_LABEL = { leastcost: "Least-cost grid", restricted: "Restricted grid", optimistic: "optimistic MG costs", pessimistic: "pessimistic MG costs" };
  const FAMILY_COLOR = (g, m) => g === "restricted" ? (m === "optimistic" ? "#0073AE" : "#7fb3d5") : (m === "optimistic" ? "#5E5B5C" : "#b5b3b4");
  const MTF_LABEL = { 1: "Tier 1 — task lighting, phone charging", 2: "Tier 2 — lighting, TV, fan", 3: "Tier 3 — medium-power appliances", 4: "Tier 4 — high-power appliances", 5: "Tier 5 — very high-power appliances" };
  const get = (c, g, m, t, k) => { const v = idx.get(`${c}|${g}|${m}|${t}|${k}`); return v === undefined ? null : v; };
  const sum = (g, m, t, k) => COUNTRIES.reduce((a, c) => a + (get(c, g, m, t, k) || 0), 0);
  const byTier = (c, g, m, k) => [1, 2, 3, 4, 5].map(t => c === "ALL" ? sum(g, m, t, k) : get(c, g, m, t, k));
  const THIN = " ";  // narrow no-break space as thousands separator (IRENA guidelines: non-breaking; never wraps)
  const nfmt = n => Math.round(n).toString().replace(/\B(?=(\d{3})+(?!\d))/g, THIN);
  const fmt = (n, kind) => {
    if (n === null || n === undefined || Number.isNaN(n)) return "—";
    // A deployment metric (people served by mini-grids, capacity, energy, value) of exactly 0 means
    // no mini-grid deployment in that scenario (not "zero but deployed"), so it renders as "—", the
    // same as missing. "pct" and "ratio" keep 0 as a meaningful value.
    if ((kind === "mw" || kind === "mwh" || kind === "usdm" || kind === "people") && n === 0) return "—";
    if (kind === "people") return n >= 950e3 ? (n / 1e6).toFixed(n >= 1e7 ? 0 : 1) + " M" : n < 500 ? "< 1 k" : Math.round(n / 1e3) + " k";
    if (kind === "mw") return n >= 1000 ? (n / 1000).toFixed(1) + " GW" : n < 0.05 ? "< 0.1 MW" : n.toFixed(n < 10 ? 1 : 0) + " MW";
    if (kind === "mwh") return n >= 1000 ? (n / 1000).toFixed(1) + " GWh" : n < 0.05 ? "< 0.1 MWh" : n.toFixed(n < 10 ? 1 : 0) + " MWh";
    if (kind === "usdm") return n >= 1000 ? "USD " + (n / 1000).toFixed(1) + " bn" : n < 0.05 ? "< USD 0.1 m" : "USD " + n.toFixed(n < 10 ? 1 : 0) + " m";
    if (kind === "pct") return n.toFixed(1) + "%";   // IRENA style: "5%", no space
    if (kind === "ratio") return n.toFixed(2);
    return String(n);
  };
  return { get, sum, byTier, fmt, nfmt, COUNTRIES, NAMES, COLORS, FAMILIES, FAMILY_LABEL, FAMILY_COLOR, MTF_LABEL };
})();
