// Synthetic map: SVG grid, 1 cell = 1 km (CELL px). No external map provider or API key.
const CELL = 40, W = 800, H = 460, SVGNS = "http://www.w3.org/2000/svg";
const $ = (id) => document.getElementById(id);
const state = { config: null, pos: null, fuel: 0, hours: 0, total: 0, path: [] };
const FUEL_PER_KM = 0.35, AVG_KMH = 28, MIN_HOURS = 0.05; // keep in sync with jde_suite/meters.py

function el(name, attrs, parent) {
  const n = document.createElementNS(SVGNS, name);
  for (const [k, v] of Object.entries(attrs)) n.setAttribute(k, v);
  if (parent) parent.appendChild(n);
  return n;
}
const km = (a, b) => Math.hypot(a.x - b.x, a.y - b.y) / CELL;

function drawGrid(svg) {
  for (let x = 0; x <= W; x += CELL) el("line", { x1: x, y1: 0, x2: x, y2: H, stroke: "#c9d8d2" }, svg);
  for (let y = 0; y <= H; y += CELL) el("line", { x1: 0, y1: y, x2: W, y2: y, stroke: "#c9d8d2" }, svg);
  [["Depot", 80, 80], ["Quarry", 640, 120], ["Fuel bay", 560, 360]].forEach(([t, x, y]) => {
    el("rect", { x: x - 28, y: y - 18, width: 56, height: 36, rx: 6, fill: "#fff", stroke: "#0d6b73" }, svg);
    const tx = el("text", { x, y: y + 4, "text-anchor": "middle", "font-size": 11, fill: "#0d6b73" }, svg);
    tx.textContent = t;
  });
}

function log(title, payload) {
  const d = document.createElement("article");
  d.className = "log-entry";
  d.innerHTML = `<header><span></span><span>${new Date().toLocaleTimeString("en-GB")}</span></header><pre></pre>`;
  d.querySelector("span").textContent = title;
  d.querySelector("pre").textContent = JSON.stringify(payload, null, 2);
  $("eventLog").prepend(d);
}

function render(status) {
  $("fuelReading").textContent = state.fuel.toFixed(2);
  $("hourReading").textContent = state.hours.toFixed(2);
  $("distanceTotal").textContent = state.total.toFixed(2) + " km";
  if (status) $("syncStatus").textContent = status;
}

async function post(url, body) {
  const r = await fetch(url, { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(body) });
  const data = await r.json();
  if (!r.ok) throw new Error(data.error || "Request failed");
  return data;
}

async function moved(to) {
  const d = km(state.pos, to);
  if (d < 0.01) return;
  state.total += d;
  state.fuel += d * FUEL_PER_KM;
  state.hours += Math.max(d / AVG_KMH, MIN_HOURS);
  el("line", { x1: state.pos.x, y1: state.pos.y, x2: to.x, y2: to.y, stroke: "#0d6b73", "stroke-width": 3 }, $("trail"));
  state.pos = to;
  render("Sending readings...");
  const payload = { equipmentNumber: state.config.equipmentNumber, fuelReading: state.fuel, hourReading: state.hours };
  log("Request", payload);
  try {
    log("Response", await post("api/update-meter-readings", payload));
    render("Synced");
  } catch (e) {
    log("Error", { message: e.message });
    render("Sync failed");
  }
}

function setup() {
  const svg = $("map");
  svg.innerHTML = "";
  drawGrid(svg);
  el("g", { id: "trail" }, svg);
  const start = { x: 120, y: 260 };
  state.pos = { ...start };
  const truck = el("g", { cursor: "grab" }, svg);
  el("rect", { x: -18, y: -12, width: 36, height: 24, rx: 5, fill: "#d55d2a", stroke: "#fff", "stroke-width": 2 }, truck);
  el("rect", { x: 6, y: -9, width: 9, height: 12, fill: "#fff" }, truck);
  el("circle", { cx: -9, cy: 13, r: 4, fill: "#222" }, truck);
  el("circle", { cx: 9, cy: 13, r: 4, fill: "#222" }, truck);
  const place = (p) => truck.setAttribute("transform", `translate(${p.x} ${p.y})`);
  place(state.pos);
  let drag = false;
  const toSvg = (e) => {
    const pt = svg.createSVGPoint(); pt.x = e.clientX; pt.y = e.clientY;
    const p = pt.matrixTransform(svg.getScreenCTM().inverse());
    return { x: Math.min(W - 20, Math.max(20, p.x)), y: Math.min(H - 20, Math.max(20, p.y)) };
  };
  truck.addEventListener("pointerdown", (e) => { drag = true; truck.setPointerCapture(e.pointerId); render("Moving..."); });
  truck.addEventListener("pointermove", (e) => { if (drag) place(toSvg(e)); });
  truck.addEventListener("pointerup", (e) => { if (!drag) return; drag = false; const p = toSvg(e); place(p); moved(p); });
  window.__truck = { move: (x, y) => { place({ x, y }); return moved({ x, y }); } }; // lets a test script drive the demo
  $("resetRouteButton").onclick = () => {
    state.total = 0; state.fuel = state.config.initialTelemetry.fuelReading; state.hours = state.config.initialTelemetry.hourReading;
    state.pos = { ...start }; place(state.pos); $("trail").innerHTML = ""; render("Route reset");
  };
  $("clearLogButton").onclick = () => { $("eventLog").innerHTML = ""; };
}

(async () => {
  state.config = await (await fetch("api/config")).json();
  state.fuel = state.config.initialTelemetry.fuelReading;
  state.hours = state.config.initialTelemetry.hourReading;
  $("equipmentNumber").textContent = state.config.equipmentNumber;
  if (state.config.mock) $("mockBadge").classList.remove("hidden");
  setup();
  render("Ready");
})();

// Optional: open /?autodemo=1 to replay a short scripted route (used for the README screenshot).
if (location.search.includes("autodemo")) {
  setTimeout(async () => {
    for (const [x, y] of [[260, 200], [420, 280], [560, 340]]) { await window.__truck.move(x, y); }
  }, 800);
}
