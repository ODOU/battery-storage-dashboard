/* Minimal SVG charts. Global: C */
const C = (() => {
  const NS = "http://www.w3.org/2000/svg"; /* XML namespace identifier, not a network request -- whitelisted in build.py's check_no_external_urls() */
  const el = (n, a = {}, txt) => { const e = document.createElementNS(NS, n); for (const k in a) e.setAttribute(k, a[k]); if (txt !== undefined) e.textContent = txt; return e; };
  const tip = document.createElement("div"); tip.className = "tooltip"; tip.setAttribute("role", "status"); tip.setAttribute("aria-live", "polite"); document.body.appendChild(tip);
  const showTip = (ev, html) => {
    tip.innerHTML = html; tip.style.display = "block";
    let x = ev.clientX + 12, y = ev.clientY + 12;                       // keep the tooltip inside the viewport
    if (x + tip.offsetWidth > window.innerWidth - 4) x = ev.clientX - tip.offsetWidth - 12;
    if (y + tip.offsetHeight > window.innerHeight - 4) y = ev.clientY - tip.offsetHeight - 12;
    tip.style.left = Math.max(2, x) + "px"; tip.style.top = Math.max(2, y) + "px";
  };
  const hideTip = () => { tip.style.display = "none"; };
  const hover = (node, html) => { node.addEventListener("mousemove", e => showTip(e, html)); node.addEventListener("mouseleave", hideTip); node.appendChild(el("title", {}, html.replace(/<[^>]+>/g, " ").replace(/\s+/g, " ").trim())); };
  /* Axis ceiling: 1 / 2 / 2.5 / 3 / 4 / 5 / 7.5 / 10 steps so that a series is never squeezed into the bottom half of its panel. */
  const nice = max => { if (!(max > 0)) return 1; const p = Math.pow(10, Math.floor(Math.log10(max))); const f = max / p; const steps = [1, 2, 2.5, 3, 4, 5, 7.5, 10]; return steps.find(s => f <= s + 1e-9) * p; };
  const svg = (w, h, label) => { const s = el("svg", { viewBox: `0 0 ${w} ${h}`, preserveAspectRatio: "xMidYMid meet", width: "100%", role: "img" }); if (label) { s.setAttribute("aria-label", label); s.appendChild(el("title", {}, label)); } return s; };
  const TICK_PX = 6.2;  // average glyph width of the 11 px tick font, used to size the left margin to the widest label
  const tickLabels = (top, fmt) => [1, 2, 3, 4].map(i => fmt(top * i / 4));
  /* Draw at the container's own width so that tick text keeps its CSS size instead of being scaled down with the viewBox. */
  const fitW = (o, fallback = 480) => o.width || (o.el.clientWidth > 200 ? Math.round(o.el.clientWidth) : fallback);
  const frame = (o, top) => {
    const W = fitW(o), H = o.height || Math.round(Math.max(200, Math.min(300, W * 0.5)));
    const widest = top === undefined ? 0 : Math.max(...tickLabels(top, o.fmt || String).map(s => s.length));
    const m = { t: 12 + (o.ylabel ? 14 : 0), r: 12, b: 34, l: Math.max(48, Math.ceil(widest * TICK_PX) + 10) };
    const s = svg(W, H, o.label); o.el.innerHTML = ""; o.el.appendChild(s);
    return { s, W, H, m, iw: W - m.l - m.r, ih: H - m.t - m.b };
  };
  const yAxis = (f, top, fmt) => { for (let i = 0; i <= 4; i++) { const v = top * i / 4, y = f.m.t + f.ih - f.ih * i / 4; f.s.appendChild(el("line", { x1: f.m.l, x2: f.W - f.m.r, y1: y, y2: y, stroke: "#e3e6ea" })); f.s.appendChild(el("text", { x: f.m.l - 4, y: y + 3, "text-anchor": "end", class: "tick" }, i === 0 ? "0" : fmt(v))); } };
  const xTicks = (f, cats, band) => cats.forEach((c, i) => f.s.appendChild(el("text", { x: f.m.l + band * (i + .5), y: f.H - f.m.b + 14, "text-anchor": "middle", class: "tick" }, c)));
  const labels = (f, o) => { if (o.ylabel) f.s.appendChild(el("text", { x: f.m.l - 4, y: 10, class: "tick" }, o.ylabel)); if (o.xlabel) f.s.appendChild(el("text", { x: f.m.l + f.iw / 2, y: f.H - 2, "text-anchor": "middle", class: "tick" }, o.xlabel)); };
  const posMax = vals => Math.max(0, ...vals.filter(v => v !== null && v !== undefined && !Number.isNaN(v)));
  const bar = (o) => {
    const n = o.cats.length, fmt = o.fmt || String;
    const tot = o.cats.map((_, i) => o.stacked ? o.series.reduce((a, s) => a + Math.max(0, s.values[i] || 0), 0) : posMax(o.series.map(s => s.values[i])));
    const top = nice(Math.max(...tot, o.refLine ? o.refLine.value : 0));
    const f = frame(o, top), band = f.iw / n; yAxis(f, top, fmt); xTicks(f, o.cats, band);
    const y = v => f.m.t + f.ih - f.ih * v / top;
    o.cats.forEach((c, i) => { let acc = 0; o.series.forEach((s, j) => { const v = s.values[i]; if (v === null || v === undefined) return;
      const w = o.stacked ? band * .7 : band * .7 / o.series.length, x = f.m.l + band * i + band * .15 + (o.stacked ? 0 : w * j);
      const y0 = o.stacked ? y(acc + v) : y(v), h = o.stacked ? y(acc) - y(acc + v) : f.m.t + f.ih - y(v);
      const r = el("rect", { x, y: y0, width: w, height: Math.max(0, h), fill: s.color }); hover(r, `<b>${s.name}</b><br>${c}: ${fmt(v)}`); f.s.appendChild(r); if (o.stacked) acc += v; }); });
    if (o.refLine) { const yy = y(o.refLine.value); f.s.appendChild(el("line", { x1: f.m.l, x2: f.W - f.m.r, y1: yy, y2: yy, stroke: "#b00020", "stroke-dasharray": "4 3" })); f.s.appendChild(el("text", { x: f.W - f.m.r, y: yy - 4, "text-anchor": "end", class: "lbl", fill: "#b00020" }, o.refLine.label)); }
    labels(f, o);
    if (o.series.length > 1) legend(o.el, o.series, o.legendCols);
  };
  const hbar = (o) => { const H = 24 * o.cats.length + 20, W = fitW(o), ml = 80, iw = W - ml - 60, fmt = o.fmt || String; const max = nice(Math.max(...o.values));
    const s = svg(W, H, o.label); o.el.innerHTML = ""; o.el.appendChild(s);
    o.cats.forEach((c, i) => { const y = 8 + i * 24, w = iw * (o.values[i] || 0) / max; s.appendChild(el("text", { x: ml - 6, y: y + 12, "text-anchor": "end", class: "lbl" }, c)); const r = el("rect", { x: ml, y, width: w, height: 16, fill: o.color }); hover(r, `${c}: ${fmt(o.values[i])}`); s.appendChild(r); s.appendChild(el("text", { x: ml + w + 4, y: y + 12, class: "lbl" }, fmt(o.values[i]))); }); };
  const line = (o) => {
    const n = o.x.length, fmt = o.fmt || String; const top = nice(posMax(o.series.flatMap(s => s.values)));
    const f = frame(o, top), band = f.iw / n; yAxis(f, top, fmt); xTicks(f, o.x, band);
    const px = i => f.m.l + band * (i + .5), py = v => f.m.t + f.ih - f.ih * v / top;
    o.series.forEach(s => {
      let run = [];  // one polyline per run of consecutive values: a missing point breaks the line instead of being bridged
      const flush = () => { if (run.length > 1) f.s.appendChild(el("polyline", { points: run.join(" "), fill: "none", stroke: s.color, "stroke-width": 2 })); run = []; };
      s.values.forEach((v, i) => { if (v === null || v === undefined) flush(); else run.push(`${px(i)},${py(v)}`); }); flush();
      s.values.forEach((v, i) => { if (v === null || v === undefined) return; const c = el("circle", { cx: px(i), cy: py(v), r: 3.5, fill: s.color }); hover(c, `<b>${s.name}</b><br>${o.x[i]}: ${fmt(v)}`); f.s.appendChild(c); }); });
    labels(f, o); legend(o.el, o.series, o.legendCols); };
  const area = (o) => {
    const n = o.x.length, fmt = o.fmt || String; const tot = o.x.map((_, i) => o.series.reduce((a, s) => a + (s.values[i] || 0), 0)); const top = nice(Math.max(...tot));
    const f = frame(o, top), band = f.iw / n; yAxis(f, top, fmt); xTicks(f, o.x, band);
    const px = i => f.m.l + band * (i + .5), py = v => f.m.t + f.ih - f.ih * v / top; let base = o.x.map(() => 0);
    o.series.forEach(s => { const upper = base.map((b, i) => b + (s.values[i] || 0)); const d = upper.map((v, i) => `${px(i)},${py(v)}`).join(" ") + " " + base.map((v, i) => `${px(i)},${py(v)}`).reverse().join(" "); f.s.appendChild(el("polygon", { points: d, fill: s.color, opacity: .85 })); base = upper; });
    // Hover bands per category carry the values of every series (the polygons themselves have no single value).
    o.x.forEach((c, i) => { const r = el("rect", { x: f.m.l + band * i, y: f.m.t, width: band, height: f.ih, fill: "transparent" });
      hover(r, `<b>${c}</b><br>` + o.series.map(s => `${s.name}: ${fmt(s.values[i] || 0)}`).join("<br>") + `<br>Total: ${fmt(tot[i])}`); f.s.appendChild(r); });
    labels(f, o); legend(o.el, o.series); };
  const legend = (container, series, cols) => { const d = document.createElement("div"); d.className = "legend"; if (cols) { d.classList.add("cols"); d.style.gridTemplateColumns = `repeat(${cols}, minmax(0, 1fr))`; } series.forEach(s => { const i = document.createElement("span"); i.innerHTML = `<i style="background:${s.color}"></i>${s.name}`; d.appendChild(i); }); container.appendChild(d); };
  const heat = (o) => { const vals = o.rows.flatMap(r => o.cols.map(c => o.values(r, c))).filter(v => v); const max = Math.max(...vals, 0);
    const shade = v => !v ? "#fff" : `rgba(0,115,174,${0.12 + 0.68 * v / max})`, ink = v => v && v / max > .85 ? "#fff" : "#222";  // white ink only on the darkest tints (contrast)
    o.el.innerHTML = `<h3>${o.title}</h3><div class="heat"><table><caption class="sr">${o.title}</caption><thead><tr><th scope="col">Demand tier</th>${o.cols.map(c => `<th scope="col">${c.label}</th>`).join("")}</tr></thead><tbody>` +
      o.rows.map(r => `<tr><th scope="row">${r.label}</th>${o.cols.map(c => { const v = o.values(r, c); const cur = o.current && o.current[0] === r.key && o.current[1] === c.key; return `<td class="${cur ? "cur" : ""}"${cur ? ' aria-current="true"' : ""} style="background:${shade(v)};color:${ink(v)}">${o.fmt(v)}</td>`; }).join("")}</tr>`).join("") + "</tbody></table></div>"; };
  return { svg, bar, hbar, line, area, tip, el, heat, hover };
})();
