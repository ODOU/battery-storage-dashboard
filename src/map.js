/* Four-country SVG map. Global: M */
const M = (() => {
  const RAMP = ["#d6e8f3", "#a9cfe6", "#6fb0d5", "#2f8bc0", "#0073AE"], NONE = "#e6e9ee", OUTSIDE = "#f3f4f6";
  /* Label anchors (lon, lat) chosen by eye so that each label sits inside its country; the vertex
     mean of a coastline-heavy polygon does not. */
  const ANCHOR = { BFA: [-1.6, 12.4], MLI: [-3.2, 17.4], NGA: [8.0, 9.4], SEN: [-14.6, 14.6] };
  let svg, paths = {}, labels = {}, onSelect = () => {}, proj, legendEl;
  const rings = g => g.type === "Polygon" ? [g.coordinates] : g.coordinates;
  const init = (el, o) => {
    onSelect = o.onSelect || onSelect; legendEl = o.legend || null;
    const feats = DATA.geo.features, focus = feats.filter(f => f.properties.focus);
    let x0 = 180, x1 = -180, y0 = 90, y1 = -90;
    focus.forEach(f => rings(f.geometry).forEach(poly => poly[0].forEach(([x, y]) => { x0 = Math.min(x0, x); x1 = Math.max(x1, x); y0 = Math.min(y0, y); y1 = Math.max(y1, y); })));
    x0 -= 1; x1 += 1; y0 -= 1; y1 += 1;
    const k = Math.cos((y0 + y1) / 2 * Math.PI / 180);            // equirectangular with the east–west scale corrected at the mid-latitude
    const W = 480, H = Math.round(W * (y1 - y0) / ((x1 - x0) * k));
    proj = ([x, y]) => [(x - x0) / (x1 - x0) * W, (y1 - y) / (y1 - y0) * H];
    svg = C.svg(W, H, "Map of Burkina Faso, Mali, Nigeria and Senegal shaded by the selected metric"); el.innerHTML = ""; el.appendChild(svg);
    feats.forEach(f => { const d = rings(f.geometry).map(poly => poly.map(ring => "M" + ring.map(p => proj(p).map(v => v.toFixed(1)).join(",")).join("L") + "Z").join("")).join("");
      const p = C.el("path", { d, class: "country" + (f.properties.focus ? " focus" : ""), fill: f.properties.focus ? NONE : OUTSIDE, "fill-rule": "evenodd" }); svg.appendChild(p);
      if (f.properties.focus) {
        const iso = f.properties.iso3; paths[iso] = p;
        p.setAttribute("tabindex", "0"); p.setAttribute("role", "button"); p.setAttribute("aria-pressed", "false"); p.setAttribute("aria-label", f.properties.name);
        const toggle = () => onSelect(p.classList.contains("selected") ? null : iso);
        p.addEventListener("click", toggle);
        p.addEventListener("keydown", e => { if (e.key === "Enter" || e.key === " ") { e.preventDefault(); toggle(); } });
      } });
    focus.forEach(f => { const [cx, cy] = proj(ANCHOR[f.properties.iso3]);
      const t = C.el("text", { x: cx, y: cy, "text-anchor": "middle", class: "lbl", "pointer-events": "none" }); t.appendChild(C.el("tspan", { x: cx, dy: -2, "font-weight": "600" }, f.properties.name)); t.appendChild(C.el("tspan", { x: cx, dy: 12 }, "")); svg.appendChild(t); labels[f.properties.iso3] = t; });
  };
  /* o.breaks: four ascending thresholds fixed per metric (computed over all scenarios), so that a
     colour means the same value whatever the controls show; o.fmt formats legend values. */
  const update = (o) => {
    const bin = v => o.breaks.filter(b => v >= b).length;
    for (const iso in paths) { const v = o.values[iso]; const p = paths[iso]; const has = v !== null && v !== undefined && v > 0;
      p.setAttribute("fill", has ? RAMP[Math.min(4, bin(v))] : NONE); p.classList.toggle("selected", o.selected === iso); p.setAttribute("aria-pressed", o.selected === iso ? "true" : "false");
      const text = `${D.NAMES[iso]}: ${has ? o.fmt(v) : "no mini-grid deployment in this scenario"}`;
      p.setAttribute("aria-label", text); p.querySelector("title")?.remove(); p.appendChild(C.el("title", {}, text));
      p.onmousemove = e => { C.tip.innerHTML = `<b>${D.NAMES[iso]}</b><br>${has ? o.fmt(v) : "no mini-grid deployment in this scenario"}`; C.tip.style.display = "block"; C.tip.style.left = (e.clientX + 12) + "px"; C.tip.style.top = (e.clientY + 12) + "px"; };
      p.onmouseleave = () => { C.tip.style.display = "none"; }; labels[iso].lastChild.textContent = has ? o.fmt(v) : "—"; }
    if (legendEl) {
      const b = o.breaks, lab = [`< ${o.fmt(b[0])}`, `${o.fmt(b[0])} – ${o.fmt(b[1])}`, `${o.fmt(b[1])} – ${o.fmt(b[2])}`, `${o.fmt(b[2])} – ${o.fmt(b[3])}`, `≥ ${o.fmt(b[3])}`];
      legendEl.innerHTML = RAMP.map((c, i) => `<span><i style="background:${c}"></i>${lab[i]}</span>`).join("") + `<span><i style="background:${NONE}"></i>no mini-grid deployment</span><span><i style="background:${OUTSIDE};border:1px solid #d9dee3"></i>outside the study</span>`;
    }
  };
  return { init, update };
})();
