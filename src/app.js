/* app.js */
const $ = s => document.querySelector(s);
const F = DATA.findings, T = DATA.tables;
const TECH = { grid_densification: ["Grid densification", "#9b6fb5"], grid_extension: ["Grid extension", "#6E398E"], minigrid: ["Mini-grids", "#F9D900"], standalone: ["Stand-alone solar", "#F4B700"] };
const TIERS = ["Tier 1", "Tier 2", "Tier 3", "Tier 4", "Tier 5"];
const P = v => D.fmt(v, "people"), MW = v => D.fmt(v, "mw"), MWH = v => D.fmt(v, "mwh"), USD = v => D.fmt(v, "usdm");
/* Thousands written "42 700" in the text must not wrap: replace the space with a narrow no-break space. */
const nb = t => String(t).replace(/(\d) (?=\d{3}(?!\d))/g, "$1 ");
const multLabel = m => m === 1 ? "baseline" : "+" + Math.round((m - 1) * 100) + "%";

/* ---------- scenario glyph: the 20-scenario matrix (5 tiers × 4 families) with the cells a figure refers to lit ---------- */
const SCEN_LABEL = sc => sc.all ? "every scenario" : [sc.tiers ? sc.tiers.map(t => "Tier " + t).join(", ") : "Tiers 1–5", sc.grid ? D.FAMILY_LABEL[sc.grid] : "both grid outlooks", sc.mgcost ? D.FAMILY_LABEL[sc.mgcost] : "both cost cases"].join(", ");
function glyph(sc, cls = "") {
  const on = (g, m, t) => sc.all || ((!sc.grid || sc.grid === g) && (!sc.mgcost || sc.mgcost === m) && (!sc.tiers || sc.tiers.includes(t)));
  const cells = D.FAMILIES.map(([g, m], r) => [1, 2, 3, 4, 5].map(t => `<rect x="${(t - 1) * 8}" y="${r * 8}" width="6" height="6" rx="1"${on(g, m, t) ? ' class="on"' : ""}/>`).join("")).join("");
  return `<svg class="glyph ${cls}" viewBox="-1 -1 40 32" role="img" aria-label="Scenario: ${SCEN_LABEL(sc)}"><title>Scenario: ${SCEN_LABEL(sc)}</title>${cells}</svg>`;
}

/* ---------- tabs (ARIA tablist, arrow keys, URL hash) ---------- */
const TABS = [...document.querySelectorAll("#tabs button")];
function showTab(name, focus) {
  if (!TABS.some(b => b.dataset.tab === name)) name = "findings";
  TABS.forEach(b => { const on = b.dataset.tab === name; b.classList.toggle("active", on); b.setAttribute("aria-selected", on ? "true" : "false"); b.tabIndex = on ? 0 : -1; if (on && focus) b.focus(); });
  document.querySelectorAll(".tab").forEach(s => s.classList.toggle("active", s.id === "tab-" + name));
  if (location.hash !== "#" + name) history.replaceState(null, "", "#" + name);
  redraw(name);   // charts are sized to their container, which has no width while its tab is hidden
}
/* Redraw the charts of one tab (after it becomes visible, or after a resize). Defined with function hoisting so showTab can call it before the render functions exist. */
function redraw(name) {
  if (typeof renderNow !== "function") return;
  if (name === "findings") drawCards(); else if (name === "explorer") renderNow(); else if (name === "countries") renderCountry(); else if (name === "method") drawExample();
}
let resizeT; window.addEventListener("resize", () => { clearTimeout(resizeT); resizeT = setTimeout(() => redraw((location.hash || "#findings").slice(1)), 150); });
TABS.forEach((b, i) => {
  b.setAttribute("role", "tab"); b.id = "tabbtn-" + b.dataset.tab; b.setAttribute("aria-controls", "tab-" + b.dataset.tab);
  b.addEventListener("click", () => showTab(b.dataset.tab));
  b.addEventListener("keydown", e => { const k = { ArrowRight: i + 1, ArrowLeft: i - 1, Home: 0, End: TABS.length - 1 }[e.key]; if (k === undefined) return; e.preventDefault(); showTab(TABS[(k + TABS.length) % TABS.length].dataset.tab, true); });
});
document.querySelectorAll(".tab").forEach(s => { s.setAttribute("role", "tabpanel"); s.setAttribute("aria-labelledby", "tabbtn-" + s.id.replace("tab-", "")); });
window.addEventListener("hashchange", () => showTab(location.hash.slice(1)));

/* ---------- hero ---------- */
$("#headline").innerHTML = F.headline.map(h => `<div>${glyph(h.scenario)}<b>${h.value}</b><span>${h.label}</span><small>${h.scenario_text}</small></div>`).join("");
$("#glyph-key").innerHTML = `${glyph({ tiers: [3], grid: "restricted", mgcost: "optimistic" })} Each glyph is the report's twenty-scenario matrix. Columns are Tiers 1 to 5; rows are the four families (least-cost or restricted grid, optimistic or pessimistic mini-grid costs); the lit cells are the scenarios a figure refers to.`;

/* ---------- key findings ---------- */
const CARD_CHARTS = {
  mg_potential: el => { const c = T.mg_potential.connections; const tot = k => D.COUNTRIES.reduce((a, x) => a + c[x][k], 0);
    C.hbar({ el, label: "Maximum mini-grid potential by technology, people", cats: ["Solar PV", "Hydro", "Wind"], values: [tot("pv"), tot("hydro"), tot("wind")], color: "#F9D900", fmt: P }); },
  market_bar: el => C.bar({ el, label: "Mini-grid capacity at Tier 2, least-cost grid, optimistic costs, by country", cats: D.COUNTRIES.map(c => D.NAMES[c]), series: [{ name: "MG capacity, Tier 2", color: "#F9D900", values: D.COUNTRIES.map(c => D.get(c, "leastcost", "optimistic", 2, "mg_capacity_mw")) }], fmt: MW, refLine: { value: F.africa_mg_pv_mw_2024, label: "Solar PV mini-grids installed in Africa, 2024" } }),
  constrained_stack: el => C.bar({ el, label: "New connections by technology and tier, restricted grid, optimistic costs", cats: TIERS, stacked: true, fmt: P, series: Object.keys(TECH).map(k => ({ name: TECH[k][0], color: TECH[k][1], values: D.byTier("ALL", "restricted", "optimistic", k) })) }),
  progression_area: el => C.area({ el, label: "New connections by technology and tier, least-cost grid, optimistic costs", x: TIERS, fmt: P, series: ["standalone", "minigrid", "grid_extension", "grid_densification"].map(k => ({ name: TECH[k][0], color: TECH[k][1], values: D.byTier("ALL", "leastcost", "optimistic", k) })) }),
  value_bar: el => C.bar({ el, label: "Value of storage by tier and scenario family", cats: TIERS, fmt: USD, legendCols: 4, series: D.FAMILIES.map(([g, m]) => ({ name: `${D.FAMILY_LABEL[g]}<br>${m}`, color: D.FAMILY_COLOR(g, m), values: D.byTier("ALL", g, m, "vos_usd_m") })) }),
  leverage_line: el => { const S = DATA.sensitivity; const mult = [...new Set(S.map(r => r.multiplier))].sort((a, b) => a - b);
    C.line({ el, label: "Battery investment leverage ratio by diesel price increase and country", x: mult.map(multLabel), fmt: v => D.fmt(v, "ratio"), xlabel: "diesel pump price vs baseline", ylabel: "USD avoided diesel per USD of battery",
      series: D.COUNTRIES.map(c => ({ name: D.NAMES[c], color: D.COLORS[c], values: mult.map(m => { const r = S.find(x => x.country === c && x.multiplier === m && x.metric === "battery_leverage"); return r ? r.value : null; }) })) }); }
};
$("#cards").innerHTML = F.cards.map((c, i) => `<article class="card" aria-labelledby="card-h-${c.id}"><p class="eyebrow">Finding ${i + 1}</p><div class="card-head"><h3 id="card-h-${c.id}">${c.title}</h3>${glyph(c.scenario)}</div><div class="num">${c.number}</div><p>${nb(c.text)}</p><div class="chart"><p class="fig-title">${c.figure}</p><div id="card-${c.id}"></div><p class="src"><b>Source:</b> ${c.source}. <b>Scenario:</b> ${c.scenario_text}.</p></div></article>`).join("");
function drawCards() { F.cards.forEach(c => { const fn = CARD_CHARTS[c.chart]; if (!fn) { console.error("unknown card chart", c.chart); return; } fn($("#card-" + c.id)); }); }
drawCards();
$("#recs").innerHTML = F.recommendations.map(r => `<li>${r}</li>`).join("");
$("#recs").insertAdjacentHTML("afterend", `<p class="src"><b>Source:</b> headings as printed in the report (${F.recommendations_source}).</p>`);

/* ---------- explorer state ---------- */
const DEFAULTS = { tier: 3, grid: "restricted", mgcost: "optimistic", metric: "vos_usd_m", country: null };
const S = { ...DEFAULTS };
const METRICS = { vos_usd_m: ["Value of storage", USD], battery_mwh: ["Battery capacity", MWH], mg_capacity_mw: ["Mini-grid capacity", MW], minigrid: ["People served by mini-grids", P] };
/* Fixed choropleth breaks per metric: quintiles of all positive per-country values across the 20
   scenarios, so a colour keeps its meaning whatever the controls show. */
const BREAKS = Object.fromEntries(Object.keys(METRICS).map(k => {
  const vals = D.COUNTRIES.flatMap(c => D.FAMILIES.flatMap(([g, m]) => [1, 2, 3, 4, 5].map(t => D.get(c, g, m, t, k)))).filter(v => v > 0).sort((a, b) => a - b);
  const q = p => vals[Math.min(vals.length - 1, Math.floor(p * vals.length))];
  return [k, [q(.2), q(.4), q(.6), q(.8)]];
}));
const seg = (key, opts) => `<div><span class="lbl-ctl" id="lbl-${key}">${key === "grid" ? "Grid expansion outlook" : "Mini-grid costs"}</span><div class="seg" role="group" aria-labelledby="lbl-${key}" data-key="${key}">${opts.map(o => `<button data-v="${o}" aria-pressed="${S[key] === o}" class="${S[key] === o ? "on" : ""}">${o === "leastcost" ? "Least-cost" : o[0].toUpperCase() + o.slice(1)}</button>`).join("")}</div></div>`;
$("#controls").innerHTML = `<div><label for="tier">Demand tier: <span id="tier-lbl"></span></label><input type="range" id="tier" min="1" max="5" step="1" value="${S.tier}"></div>` + seg("grid", ["leastcost", "restricted"]) + seg("mgcost", ["optimistic", "pessimistic"]) +
  `<div><label for="metric">Map metric</label><select id="metric">${Object.keys(METRICS).map(k => `<option value="${k}">${METRICS[k][0]}</option>`).join("")}</select></div>` +
  `<div><label for="country">Country</label><select id="country"><option value="">All four countries</option>${D.COUNTRIES.map(c => `<option value="${c}">${D.NAMES[c]}</option>`).join("")}</select></div>` +
  `<div><label class="lbl-ctl">&nbsp;</label><button class="btn" id="reset">Reset</button></div>`;
let pending = false;
const render = () => { if (pending) return; pending = true; requestAnimationFrame(() => { pending = false; renderNow(); }); };
$("#tier").addEventListener("input", e => { S.tier = +e.target.value; render(); });
document.querySelectorAll(".seg").forEach(g => g.addEventListener("click", e => { if (e.target.dataset.v) { S[g.dataset.key] = e.target.dataset.v; render(); } }));
$("#metric").value = S.metric; $("#metric").addEventListener("change", e => { S.metric = e.target.value; render(); });
$("#country").addEventListener("change", e => { S.country = e.target.value || null; render(); });
$("#reset").addEventListener("click", () => { Object.assign(S, DEFAULTS); sensView = "battery_leverage"; $("#tier").value = S.tier; $("#metric").value = S.metric; $("#country").value = ""; render(); });
M.init($("#map"), { legend: $("#map-legend"), onSelect: iso => { S.country = iso; $("#country").value = iso || ""; render(); } });

function renderNow() {
  $("#tier-lbl").textContent = D.MTF_LABEL[S.tier];
  document.querySelectorAll(".seg").forEach(g => g.querySelectorAll("button").forEach(b => { const on = b.dataset.v === S[g.dataset.key]; b.classList.toggle("on", on); b.setAttribute("aria-pressed", on); }));
  const [mname, mfmt] = METRICS[S.metric];
  $("#scenario-line").innerHTML = `${glyph({ tiers: [S.tier], grid: S.grid, mgcost: S.mgcost })}<span><b>${D.MTF_LABEL[S.tier]}</b> <span class="sep">·</span> ${D.FAMILY_LABEL[S.grid]} expansion <span class="sep">·</span> ${D.FAMILY_LABEL[S.mgcost].replace("MG", "mini-grid")} <span class="sep">·</span> ${S.country ? D.NAMES[S.country] : "all four countries"}</span>`;
  $("#map-title").textContent = `${mname}, ${TIERS[S.tier - 1]} · ${D.FAMILY_LABEL[S.grid]} · ${D.FAMILY_LABEL[S.mgcost]}`;
  M.update({ values: Object.fromEntries(D.COUNTRIES.map(c => [c, D.get(c, S.grid, S.mgcost, S.tier, S.metric)])), fmt: mfmt, breaks: BREAKS[S.metric], selected: S.country });
  renderExplorerCharts();
}
function renderExplorerCharts() {
  const c = S.country, scope = c ? D.NAMES[c] : "All four countries", [mname, mfmt] = METRICS[S.metric];
  const val = k => c ? D.get(c, S.grid, S.mgcost, S.tier, k) : D.sum(S.grid, S.mgcost, S.tier, k);
  const newPeople = ["grid_densification", "grid_extension", "minigrid", "standalone"].reduce((a, k) => a + (val(k) || 0), 0);
  $("#kpis").innerHTML = [["People to connect by 2030", P(newPeople)], ["Mini-grid capacity", MW(val("mg_capacity_mw"))], ["Battery capacity", MWH(val("battery_mwh"))], ["Value of storage", USD(val("vos_usd_m"))]]
    .map(([l, v]) => `<div class="kpi"><b>${v}</b><span>${l}, ${scope}</span></div>`).join("");
  $("#kpi-note").textContent = c ? "" : "Table 11 sums to 172 million people across the four countries; the report's figure is 171 million.";
  $("#mix").innerHTML = `<h3>New connections by technology, ${TIERS[S.tier - 1]} · ${D.FAMILY_LABEL[S.grid]} · ${D.FAMILY_LABEL[S.mgcost]}</h3><div id="mix-chart"></div>`;
  C.bar({ el: $("#mix-chart"), label: "New connections by technology and country", cats: D.COUNTRIES.map(x => D.NAMES[x]), stacked: true, fmt: P, series: Object.keys(TECH).map(k => ({ name: TECH[k][0], color: TECH[k][1], values: D.COUNTRIES.map(x => D.get(x, S.grid, S.mgcost, S.tier, k)) })) });
  const trend = (id, title, k, fmt) => { $(id).innerHTML = `<h3>${title} by demand tier</h3><div class="ch"></div>`; C.line({ el: $(id + " .ch"), label: `${title} by demand tier`, x: TIERS, fmt, series: (c ? [c] : D.COUNTRIES).map(x => ({ name: D.NAMES[x], color: D.COLORS[x], values: D.byTier(x, S.grid, S.mgcost, k) })) }); };
  trend("#trend-battery", "Battery capacity", "battery_mwh", MWH); trend("#trend-vos", "Value of storage", "vos_usd_m", USD); trend("#trend-cap", "Mini-grid capacity", "mg_capacity_mw", MW);
  C.heat({ el: $("#heat"), title: `${mname}, all 20 scenarios · ${scope}`, fmt: mfmt,
    rows: [1, 2, 3, 4, 5].map(t => ({ key: t, label: TIERS[t - 1] })), cols: D.FAMILIES.map(([g, m]) => ({ key: g + "|" + m, label: `${D.FAMILY_LABEL[g]}<br><small>${D.FAMILY_LABEL[m]}</small>` })),
    values: (r, col) => { const [g, m] = col.key.split("|"); return c ? D.get(c, g, m, r.key, S.metric) : D.sum(g, m, r.key, S.metric); }, current: [S.tier, S.grid + "|" + S.mgcost] });
  const exp = document.createElement("button"); exp.className = "btn"; exp.textContent = "Export data (per country, CSV)"; $("#heat").appendChild(exp);
  exp.addEventListener("click", () => { const lines = ["tier,grid,mgcost,country,metric,value"]; D.FAMILIES.forEach(([g, m]) => [1, 2, 3, 4, 5].forEach(t => (c ? [c] : D.COUNTRIES).forEach(x => lines.push([t, g, m, x, S.metric, D.get(x, g, m, t, S.metric) ?? ""].join(",")))));
    const url = URL.createObjectURL(new Blob([lines.join("\n")], { type: "text/csv" })); const a = document.createElement("a"); a.href = url; a.download = `battery_dashboard_${S.metric}.csv`; a.click(); setTimeout(() => URL.revokeObjectURL(url), 1000); });
  renderSensitivity();
}
const SENS_VIEWS = { battery_leverage: ["Battery investment leverage ratio", v => D.fmt(v, "ratio"), "USD avoided diesel per USD of battery"], lcoe_hybrid_usd_kwh: ["Hybrid mini-grid LCOE", v => v === null ? "—" : v.toFixed(3) + " USD/kWh", "USD/kWh"], fuel_exposure_pct: ["Fuel exposure ratio (no batteries)", v => D.fmt(v, "pct"), "share of investment at risk"], vos_usd_m: ["Value of storage", USD, "USD million"], battery_mwh: ["Battery capacity", MWH, "MWh"] };
let sensView = "battery_leverage";
function renderSensitivity() {
  const Sn = DATA.sensitivity, mult = [...new Set(Sn.map(r => r.multiplier))].sort((a, b) => a - b);
  const rc = T.reference_case, pp = T.pump_prices_usd_l;
  $("#sensitivity").innerHTML = `<h3>Diesel-price sensitivity (Appendix V, Table A11)</h3>
    <p class="note">The controls above do not change this panel. Appendix V models one reference case: Tier 3 demand (${rc.kwh_hh_yr} kWh per household per year), ${rc.grid} and the ${rc.mgcost}. ${rc.note} Baseline pump prices from ${pp.source.split(",")[0]}: ${D.COUNTRIES.map(k => `${D.NAMES[k]} USD ${pp[k].toFixed(2)}/l`).join(", ")}.</p>
    <div class="subtabs" role="group" aria-label="Sensitivity metric">${Object.keys(SENS_VIEWS).map(k => `<button data-v="${k}" aria-pressed="${k === sensView}" class="${k === sensView ? "on" : ""}">${SENS_VIEWS[k][0]}</button>`).join("")}</div><div class="ch ch-wide"></div>`;
  $("#sensitivity .subtabs").addEventListener("click", e => { if (e.target.dataset.v) { sensView = e.target.dataset.v; renderSensitivity(); } });
  const [title, fmt, ylabel] = SENS_VIEWS[sensView];
  C.line({ el: $("#sensitivity .ch"), label: `${title} by diesel price increase and country`, width: 720, height: 300, x: mult.map(multLabel), fmt, ylabel, xlabel: "diesel pump price vs baseline",
    series: (S.country ? [S.country] : D.COUNTRIES).map(c => ({ name: D.NAMES[c], color: D.COLORS[c], values: mult.map(m => { const r = Sn.find(x => x.country === c && x.multiplier === m && x.metric === sensView); return r ? r.value : null; }) })) });
}
renderNow();

/* ---------- countries ---------- */
let curCountry = "BFA";
$("#country-tabs").innerHTML = D.COUNTRIES.map(c => `<button data-c="${c}" aria-pressed="${c === curCountry}" class="${c === curCountry ? "on" : ""}">${D.NAMES[c]}</button>`).join("");
$("#country-tabs").addEventListener("click", e => { if (e.target.dataset.c) { curCountry = e.target.dataset.c; renderCountry(); } });
const NUTSHELL = {
  BFA: "Burkina Faso's least-cost mix depends on how far the grid can expand and on what mini-grids cost. The report finds that 15–22 million people are best served by grid expansion, densification and extension together, under least-cost conditions, with a large off-grid share if the grid is constrained. In the scenario data, stand-alone systems serve about 20 million people at Tier 1. New grid extension grows from about 8 million people at Tier 2 to 14–18 million at Tiers 4–5, in addition to about 3 million reached by densification.",
  MLI: "Population and infrastructure are concentrated in the south-west. Under least-cost grid expansion with optimistic mini-grid costs, mini-grids serve 2.4–2.7 million people across Tiers 2–5; the report gives 2–3 million, or 7–11% of new connections. Mali has the highest baseline diesel pump price of the four countries, USD 0.98 per litre in Table A9, and the highest battery investment leverage when diesel doubles, USD 5.89 avoided per dollar invested in Table A11.",
  NGA: "Nigeria needs a portfolio. About 127 million people are to be connected by 2030, 71% of the four-country total, and the mix is set mainly by grid expansion policy and by what mini-grids will cost. Under restricted grid expansion at Tiers 3–5, Nigeria accounts for 74–80% of the four-country mini-grid capacity and 61–74% of the value of storage, derived from Tables 13 and 14.",
  SEN: "Senegal had 74.2% access in 2023, 96.1% in towns and 56.5% in rural areas, so the remaining gap is rural. Under least-cost grid expansion with optimistic mini-grid costs, mini-grids serve 1.4–2.4 million people across Tiers 2–5; the report gives 1–2.3 million. The value of storage is several times lower than in Burkina Faso or Mali because far fewer people remain to be connected."
};
function renderCountry() {
  const c = curCountry; document.querySelectorAll("#country-tabs button").forEach(b => { const on = b.dataset.c === c; b.classList.toggle("on", on); b.setAttribute("aria-pressed", on); });
  const a = T.access[c], facts = [["Electrification rate, 2023", a.rate_2023, "Table 1, p. 21"], ["2030 target", a.target_2030, "Table 1, p. 21"], ["Urban access", a.urban, T.access_urban_rural_source], ["Rural access", a.rural, T.access_urban_rural_source], ...T.national[c]];
  $("#country-body").innerHTML = `<h2>${D.NAMES[c]}</h2><div class="facts">${facts.map(([k, v, s]) => `<div title="${s || ""}"><span>${k}</span><b>${v}</b></div>`).join("")}</div><p class="src"><b>Sources:</b> access rates from Table 1 and Table A6 (Tracking SDG 7), national targets from Section 1.2. Hover a row to see its table and page in the report.</p><p>${nb(NUTSHELL[c])}</p>
    <h2>New connections by technology and demand tier</h2><div class="row row-4" id="c-mix"></div>
    <h2>Battery capacity and value of storage by demand tier</h2><div class="row row-2"><div class="panel" id="c-bat"></div><div class="panel" id="c-vos"></div></div>`;
  D.FAMILIES.forEach(([g, m]) => { const d = document.createElement("div"); d.className = "panel"; d.innerHTML = `<h3>${D.FAMILY_LABEL[g]}<br><small>${D.FAMILY_LABEL[m]}</small></h3><div class="ch"></div>`; $("#c-mix").appendChild(d);
    C.bar({ el: d.querySelector(".ch"), label: `New connections by technology and tier, ${D.NAMES[c]}, ${D.FAMILY_LABEL[g]}, ${D.FAMILY_LABEL[m]}`, cats: TIERS, stacked: true, fmt: P, height: 220, series: Object.keys(TECH).map(k => ({ name: TECH[k][0], color: TECH[k][1], values: D.byTier(c, g, m, k) })) }); });
  const fam = D.FAMILIES.map(([g, m]) => ({ name: `${D.FAMILY_LABEL[g]}<br>${m} costs`, color: D.FAMILY_COLOR(g, m), g, m }));
  $("#c-bat").innerHTML = "<h3>Battery capacity</h3><div class='ch'></div>"; C.line({ el: $("#c-bat .ch"), label: `Battery capacity by demand tier, ${D.NAMES[c]}`, x: TIERS, fmt: MWH, legendCols: 4, series: fam.map(f => ({ ...f, values: D.byTier(c, f.g, f.m, "battery_mwh") })) });
  $("#c-vos").innerHTML = "<h3>Value of storage</h3><div class='ch'></div>"; C.line({ el: $("#c-vos .ch"), label: `Value of storage by demand tier, ${D.NAMES[c]}`, x: TIERS, fmt: USD, legendCols: 4, series: fam.map(f => ({ ...f, values: D.byTier(c, f.g, f.m, "vos_usd_m") })) });
}
renderCountry();

/* ---------- method & data ---------- */
const ex = DATA.example, exKeys = Object.keys(ex), EX_COLOR = { Investment: "#0073AE", "O&M": "#8F8085", Fuel: "#7C5521" };
const cnt = n => n ? D.nfmt(n) : "—";  // counts of settlements: thin-space thousands, "—" for none (as printed in Table 9)
$("#method-body").innerHTML = nb(`
<h2>Three levers, twenty scenarios per country</h2>
<p>The first lever is <b>demand</b>: five levels of the World Bank Multi-Tier Framework, applied to the whole population. The second is the <b>grid expansion outlook</b>. Under <i>least-cost grid expansion</i> the grid is chosen wherever it gives the lowest LCOE; under <i>restricted grid expansion</i> new grid connections are capped at 2.5% of the population a year, the World Bank Global Electrification Platform convention, which matches historical growth in sub-Saharan Africa. The third is <b>mini-grid costs</b>, either <i>optimistic</i> (2030 projections) or <i>pessimistic</i> (costs surveyed today). Grid connections are reported in two parts: <i>grid densification</i>, meaning new connections inside settlements the grid already reaches, driven by population growth and rising demand, and <i>grid extension</i>, meaning first-time connections of settlements the network has not yet reached.</p>
<div class="tbl"><table class="plain"><thead><tr><th>Tier</th><th>Typical energy services</th><th>Annual demand (kWh/household/year)</th></tr></thead><tbody>${T.mtf.map(r => `<tr><td>${r.tier}</td><td>${r.services}</td><td>${r.kwh_hh_yr}</td></tr>`).join("")}</tbody></table></div><p class="src"><b>Source:</b> Table 7 of the report (World Bank Multi-Tier Framework).</p>
<h2>Mini-grid cost assumptions (2030)</h2>
<div class="tbl"><table class="plain"><thead><tr><th>Component</th><th>Optimistic</th><th>Pessimistic</th></tr></thead><tbody>${T.mg_costs.map(r => `<tr><td>${r.component}</td><td>${r.optimistic}</td><td>${r.pessimistic}</td></tr>`).join("")}</tbody></table></div><p class="src"><b>Source:</b> Table 8 of the report, based on Agenbroad et al. (2018) and ESMAP (2019).</p>
<h2>Value of storage</h2>
<p>The value of storage is the life-cycle cost of a PV/diesel mini-grid minus that of a hybrid PV/diesel/battery mini-grid serving the same demand. It sets the avoided fuel and O&amp;M against the extra battery and PV investment, with capital, operations and maintenance, fuel and salvage costs discounted over the 2023–2030 modelling horizon at a real 10% rate. Diesel delivery cost varies with distance (Szabó et al., 2011), so remote and landlocked settlements pay more per litre.</p>
<div class="panel" style="max-width:520px"><h3>Example: a community of about 500 people at Tier 3 in 2030 (USD over the system life)</h3><div id="ex-chart"></div><p class="src"><b>Source:</b> Figure 11 of the report (Figure S1 in the summary).</p></div>
<h2>Maximum mini-grid potential by technology across scenarios, excluding micro-grid PV below 10 kW (Table 9)</h2>
<div class="tbl"><table class="plain"><thead><tr><th></th><th>Solar PV</th><th>Hydro</th><th>Wind</th></tr></thead><tbody>${D.COUNTRIES.map(c => { const p = T.mg_potential; return `<tr><td>${D.NAMES[c]} (people / settlements)</td>${["pv", "hydro", "wind"].map(k => `<td>${P(p.connections[c][k])} / ${cnt(p.settlements[c][k])}</td>`).join("")}</tr>`; }).join("")}</tbody></table></div><p class="src"><b>Source:</b> Table 9 of the report; counts of people and settlements, maximum across scenarios.</p>
<h2>Tools and data</h2>
<p><b>OnSSET</b> (Open-Source Spatial Electrification Tool) selects, for each settlement, the least-cost option among grid densification, grid extension, mini-grids (PV hybrid, hydro, wind) and stand-alone systems, from settlement population and location (GRID3, WorldPop), existing HV/MV lines (OpenStreetMap, energydata.info), resource maps and national targets. A <b>mini-grid optimisation tool</b> sizes PV, battery and diesel generator per settlement by Particle Swarm Optimisation on hourly dispatch, minimising LCOE; it is run with and without batteries to obtain the value of storage. The diesel-price sensitivity re-runs the optimiser for six pump-price levels (baseline to +100%).</p>
<p>Population comes from the UNDESA World Population Prospects, GRID3 and WorldPop; access rates from Tracking SDG 7 (IEA, IRENA, UNSD, World Bank and WHO, 2024 and 2025 editions). The mini-grid cost assumptions in Table 8 follow Agenbroad et al. (2018, Rocky Mountain Institute) and ESMAP (2019). Grid network costs and the 2.5% connection cap follow the World Bank Global Electrification Platform, and diesel pump prices the World Bank World Development Indicators. Installed mini-grid capacity in Africa is from IRENA, <i>Off-grid renewable energy statistics 2025</i>; the 93% fall in battery costs between 2010 and 2024, from USD 2 571 to USD 192 per kWh, is from IRENA, <i>Renewable power generation costs in 2024</i>. Full references are listed below.</p>`);
function drawExample() { C.bar({ el: $("#ex-chart"), label: "Life-cycle cost with and without batteries, example community", cats: ["With batteries", "Without batteries"], stacked: true, fmt: v => "USD " + D.nfmt(v), series: exKeys.map(k => ({ name: k, color: EX_COLOR[k] || "#999", values: ["With Batteries", "Without Batteries"].map(c => ex[k][c]) })) }); }
drawExample();

/* initial tab from the URL hash */
showTab(location.hash.slice(1) || "findings");
