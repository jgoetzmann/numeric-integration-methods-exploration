/* Build-time check for docs/demo.html.
 *
 * The demo page re-implements the Q15 integrator in JavaScript. This script loads the
 * published page, stubs just enough DOM for it to run headless, and drives its own
 * self-check: every (method, problem, rounding) case in the embedded fixture is
 * recomputed in JavaScript and compared, bit for bit, against the final int16 state
 * that rk_harness.simulate.solve_q15 produced. It also confirms the three charts and
 * both generated sentences render non-empty, so a page that throws never ships.
 *
 * It then drives the ranking and the cost chart through their own handlers: the keyboard,
 * a tap, and a tap away. After each it reads the markup the page wrote back: which mark
 * holds focus and the tab stop, where the readout box sits against the mark it describes,
 * what the live region says, and which method the trajectory has loaded.
 *
 *   node tools/check_demo.js [path/to/demo.html]
 *
 * Exit 0 when every case matches and every region rendered; exit 1 otherwise.
 */
"use strict";
const fs = require("fs");
const path = require("path");

const page = process.argv[2] ||
  path.join(__dirname, "..", "docs", "demo.html");
const html = fs.readFileSync(page, "utf8");

const scripts = [...html.matchAll(/<script>([\s\S]*?)<\/script>/g)].map(m => m[1]);
if (scripts.length !== 2) {
  console.error(`FAIL: expected 2 inline scripts in ${page}, found ${scripts.length}`);
  process.exit(1);
}

/* ------------------------------------------------------------------ DOM stub
 * Chart markup is parsed back into mark objects with a regular expression, so the handlers
 * are driven against the attributes the page actually wrote. Setting a host's innerHTML
 * drops focus from any mark inside it, the way a browser does, so a redraw that forgets to
 * put focus back shows up here rather than being covered by a stub that remembers. */
let active = null;
const nodes = new Map();
function parseMarks(host) {
  if (host._marks) return host._marks;
  const out = [];
  const re = /<g class="hot"((?:\s+[\w-]+="[^"]*")*)>([\s\S]*?)<\/g>/g;
  let m;
  while ((m = re.exec(host._html))) {
    const attrs = {};
    for (const a of m[1].matchAll(/([\w-]+)="([^"]*)"/g)) attrs[a[1]] = a[2];
    out.push({
      host, attrs, inner: m[2],
      getAttribute(k) { return Object.prototype.hasOwnProperty.call(this.attrs, k) ? this.attrs[k] : null; },
      focus() { active = this; },
      closest(sel) { return /g\[data-meth\]/.test(sel) ? this : null; },
    });
  }
  host._marks = out;
  return out;
}
function el(id) {
  if (nodes.has(id)) return nodes.get(id);
  const n = {
    id, className: "", textContent: "", _html: "", _marks: null,
    style: {},
    parentNode: { style: {} },
    handlers: {},
    get innerHTML() { return this._html; },
    set innerHTML(v) {
      this._html = String(v);
      this._marks = null;
      if (active && active.host === this) active = null;
    },
    addEventListener(type, fn) { this.handlers[type] = fn; },
    setAttribute() {},
    getAttribute() { return null; },
    querySelectorAll(sel) { return sel === "g[data-meth]" ? parseMarks(this) : []; },
  };
  nodes.set(id, n);
  return n;
}
let onReady = null;
const docCapture = {};
global.window = {};
global.document = {
  getElementById: el,
  get activeElement() { return active; },
  addEventListener(name, fn, capture) {
    if (name === "DOMContentLoaded") onReady = fn;
    else if (capture) docCapture[name] = fn;
  },
};

/* ------------------------------------------------------------------ run */
const runInThisContext = require("vm").runInThisContext;
try {
  runInThisContext(scripts[0], { filename: "demo-data" });
  runInThisContext(scripts[1], { filename: "demo-js" });
} catch (e) {
  console.error("FAIL: demo script threw on load:", e && e.message);
  process.exit(1);
}
if (typeof onReady !== "function") {
  console.error("FAIL: demo never registered a DOMContentLoaded handler");
  process.exit(1);
}

const t0 = Date.now();
try {
  onReady();
} catch (e) {
  console.error("FAIL: demo threw during first render:", e && e.stack);
  process.exit(1);
}

const REGIONS = ["board", "traj", "readout", "pareto", "rankline", "paretoline"];
const problems = [];
for (const id of REGIONS) {
  if (!el(id).innerHTML || el(id).innerHTML.length < 20) {
    problems.push(`region '${id}' rendered ${el(id).innerHTML.length} chars`);
  }
}

/* A click reaches the document's capture-phase handler before the target's own, as it
 * does in a browser. */
const dispatchClick = (hostId, target) => {
  const ev = { target };
  if (docCapture.click) docCapture.click(ev);
  if (el(hostId).handlers.click) el(hostId).handlers.click(ev);
};

/* Drive every control combination a visitor can reach and make sure none of them throws,
 * renders an empty region, leaks NaN/undefined into the page, or emits an SVG coordinate
 * a browser would silently drop. */
const data = global.window.__RKDEMO__;
const click = (host, v) =>
  dispatchClick(host, { closest: s => (s === "button" ? { getAttribute: () => v } : null) });
const strip = s => s.replace(/<[^>]+>/g, " ").replace(/\s+/g, " ");
let combos = 0;
for (const mode of ["floor", "nearest"]) {
  for (const p of data.problems) {
    for (const m of data.methods) {
      try {
        click("modeseg", mode);
        click("probseg", p.name);
        click("methseg", m.key);
      } catch (e) {
        problems.push(`${mode}/${p.name}/${m.key} threw: ${e && e.message}`);
        continue;
      }
      combos++;
      for (const id of REGIONS) {
        const h = el(id).innerHTML;
        if (!h || h.length < 20) problems.push(`${mode}/${p.name}/${m.key}: ${id} empty`);
        const junk = strip(h).match(/NaN|undefined|Infinity/);
        if (junk) problems.push(`${mode}/${p.name}/${m.key}: ${id} rendered ${junk[0]}`);
        if (/(?:\bx|\by|cx|cy|width|height)="(?:NaN|-?Infinity)/.test(h)) {
          problems.push(`${mode}/${p.name}/${m.key}: ${id} has an invalid SVG coordinate`);
        }
      }
    }
  }
}

/* ------------------------------------------------------------------ chart input
 * Both charts owe a keyboard path, a live readout, a readout pinned at its mark, focus
 * that survives a redraw, and a tap away that hides the readout without unloading the
 * method. Each is driven through the page's handlers, on every problem under both modes.
 */
const label = Object.fromEntries(data.methods.map(m => [m.key, m.label]));
const marksOf = id => el(id).querySelectorAll("g[data-meth]");
const keysOf = id => marksOf(id).map(g => g.getAttribute("data-meth"));
const markFor = (id, k) => marksOf(id).find(g => g.getAttribute("data-meth") === k);
const press = key => {
  if (active) active.host.handlers.keydown({ key, target: active, preventDefault() {} });
};
const loadedKey = () => {
  const m = /<dt>method<\/dt><dd>(.*?) \u00b7 order/.exec(el("readout").innerHTML);
  const hit = m && data.methods.find(x => x.label === m[1]);
  return hit ? hit.key : null;
};
const focusKey = () => (active ? active.getAttribute("data-meth") : null);
const focusLive = id => Boolean(active) && marksOf(id).includes(active);

let pinned = 0, restores = 0, walks = 0;
/* The tab stop a chart should offer: the last mark used on it, then the loaded method, then
 * the top mark. Tracked here from the inputs this script drives, not read off the page. */
const lastUsed = { board: null, pareto: null };
const wantStop = (id, keys, loaded) =>
  (keys.includes(lastUsed[id]) ? lastUsed[id] : keys.includes(loaded) ? loaded : keys[0]);
function pinnedAt(id, key, where) {
  const h = el(id).innerHTML;
  const c = /<g class="callout" data-for="([^"]*)"[^>]*>([\s\S]*?)<\/g>/.exec(h);
  if (!c) { problems.push(`${where}: ${id} drew no readout for ${key}`); return; }
  if (c[1] !== key) { problems.push(`${where}: ${id} readout is for ${c[1]}, want ${key}`); return; }
  const r = /<rect x="([-\d.]+)" y="([-\d.]+)" width="([\d.]+)" height="([\d.]+)"/.exec(c[2]);
  const t = /<text[^>]*>([\s\S]*?)<\/text>/.exec(c[2]);
  const vb = /viewBox="0 0 ([\d.]+) ([\d.]+)"/.exec(h);
  const g = markFor(id, key);
  if (!r || !vb || !g) { problems.push(`${where}: ${id} readout or mark for ${key} did not parse`); return; }
  // The mark's drawn extent: the bar for a row, the circle's bounding box for a dot.
  let m0;
  if (id === "board") {
    const b = /<rect class="bar[^"]*" x="([\d.]+)" y="([\d.]+)" width="([\d.]+)" height="([\d.]+)"/.exec(g.inner);
    m0 = [Number(b[1]), Number(b[2]), Number(b[1]) + Number(b[3]), Number(b[2]) + Number(b[4])];
  } else {
    const d = /<circle[^>]*cx="([\d.]+)" cy="([\d.]+)" r="([\d.]+)"/.exec(g.inner);
    const cx = Number(d[1]), cy = Number(d[2]), cr = Number(d[3]);
    m0 = [cx - cr, cy - cr, cx + cr, cy + cr];
  }
  const [x, y, w, hh] = r.slice(1).map(Number);
  const gap = Math.hypot(Math.max(m0[0] - (x + w), 0, x - m0[2]), Math.max(m0[1] - (y + hh), 0, y - m0[3]));
  if (gap > 12) problems.push(`${where}: ${id} readout box sits ${gap.toFixed(0)} px from the mark it describes`);
  if (w > 330) problems.push(`${where}: ${id} readout box is ${w} px wide, too wide for a phone's view of the chart`);
  if (x < 0 || y < 0 || x + w > Number(vb[1]) || y + hh > Number(vb[2])) {
    problems.push(`${where}: ${id} readout box runs outside the chart`);
  }
  const text = t ? t[1].replace(/<\/tspan>\s*<tspan[^>]*>/g, " ").replace(/<[^>]+>/g, "") : "";
  if (!text.startsWith(label[key] + ":")) problems.push(`${where}: ${id} readout box does not name ${label[key]}`);
  const live = el(id + "live").textContent;
  if (!live.startsWith(label[key] + ":") || /NaN|undefined|Infinity/.test(live)) {
    problems.push(`${where}: ${id} live readout reads "${live}"`);
  }
  pinned++;
}
function hidden(id, where) {
  if (/class="callout"/.test(el(id).innerHTML)) problems.push(`${where}: ${id} readout box still drawn`);
  if (el(id + "live").textContent !== "") problems.push(`${where}: ${id} live readout still says "${el(id + "live").textContent}"`);
}
function expectFocus(id, key, where) {
  if (focusKey() !== key) problems.push(`${where}: focus is on ${focusKey()}, want ${key}`);
  else if (!focusLive(id)) problems.push(`${where}: focus is on a mark the redraw removed`);
  else restores++;
}

if (!/id="boardlive"[^>]*aria-live="polite"/.test(html) || !/id="paretolive"[^>]*aria-live="polite"/.test(html)) {
  problems.push("a chart has no aria-live readout element in the page markup");
}
if (!docCapture.click) problems.push("no capture-phase document click handler, so a tap away cannot hide a readout");

for (const mode of ["floor", "nearest"]) {
  for (const p of data.problems) {
    click("modeseg", mode);
    click("probseg", p.name);
    for (const id of ["board", "pareto"]) {
      const W = `${mode}/${p.name}/${id}`;
      if (!el(id).handlers.keydown) { problems.push(`${W}: no keydown handler`); continue; }
      if (!/<svg[^>]*role="group"/.test(el(id).innerHTML)) {
        problems.push(`${W}: the chart is not role="group"; an img role hides the buttons inside it`);
      }
      const ms = marksOf(id), was = loadedKey();
      if (ms.length < 2) continue;
      const stops = ms.filter(g => g.getAttribute("tabindex") === "0");
      if (stops.length !== 1) problems.push(`${W}: ${stops.length} marks carry tabindex="0"; a roving tab stop has one`);
      for (const g of ms) {
        const k = g.getAttribute("data-meth"), al = g.getAttribute("aria-label") || "";
        if (!["0", "-1"].includes(g.getAttribute("tabindex"))) problems.push(`${W}: ${k} has no tabindex`);
        if (g.getAttribute("role") !== "button") problems.push(`${W}: ${k} has role ${g.getAttribute("role")}`);
        if (!al.startsWith(label[k]) || /NaN|undefined|Infinity/.test(al)) problems.push(`${W}: ${k} aria-label "${al}"`);
        if (g.getAttribute("aria-pressed") !== (k === was ? "true" : "false")) {
          problems.push(`${W}: ${k} aria-pressed is ${g.getAttribute("aria-pressed")} with ${was} loaded`);
        }
      }
      const keys = keysOf(id);
      const stopWant = wantStop(id, keys, was);
      if (stops[0] && stops[0].getAttribute("data-meth") !== stopWant) {
        problems.push(`${W}: the tab stop is on ${stops[0].getAttribute("data-meth")}, want ${stopWant}`);
      }
      const start = stops[0] || ms[0], s = keys.indexOf(start.getAttribute("data-meth"));
      start.focus();

      press("ArrowDown");
      const down = keys[(s + 1) % keys.length];
      expectFocus(id, down, `${W} ArrowDown`);
      pinnedAt(id, down, `${W} ArrowDown`);
      // The trajectory panel is not redrawn by a chart-only redraw, so the marks' own
      // pressed state is what shows whether an arrow key changed the loaded method.
      const pressed = marksOf(id).filter(g => g.getAttribute("aria-pressed") === "true")
        .map(g => g.getAttribute("data-meth"));
      if (loadedKey() !== was || pressed.join() !== (keys.includes(was) ? was : "")) {
        problems.push(`${W}: ArrowDown changed the loaded method (pressed: [${pressed}], was ${was}); only Enter or a tap should`);
      }
      const stop = marksOf(id).filter(g => g.getAttribute("tabindex") === "0");
      if (stop.length !== 1 || stop[0].getAttribute("data-meth") !== down) problems.push(`${W}: the tab stop did not follow focus`);

      press("End");
      expectFocus(id, keys[keys.length - 1], `${W} End`);
      pinnedAt(id, keys[keys.length - 1], `${W} End`);
      press("Home");
      expectFocus(id, keys[0], `${W} Home`);
      pinnedAt(id, keys[0], `${W} Home`);
      press("ArrowUp");
      expectFocus(id, keys[keys.length - 1], `${W} ArrowUp from the top`);

      const target = focusKey();
      press("Enter");
      if (loadedKey() !== target) problems.push(`${W}: Enter did not load ${target}`);
      expectFocus(id, target, `${W} Enter`);
      pinnedAt(id, target, `${W} Enter`);
      if (markFor(id, target) && markFor(id, target).getAttribute("aria-pressed") !== "true") {
        problems.push(`${W}: after Enter ${target} is not marked pressed`);
      }

      press("Escape");
      hidden(id, `${W} Escape`);
      expectFocus(id, target, `${W} Escape`);
      if (loadedKey() !== target) problems.push(`${W}: Escape unloaded ${target}`);

      const other = keysOf(id).find(k => k !== target);
      active = null;                       // a touch tap moves no focus
      dispatchClick(id, markFor(id, other));
      if (loadedKey() !== other) problems.push(`${W}: a tap on ${other} did not load it`);
      pinnedAt(id, other, `${W} tap`);

      dispatchClick(id, { closest: () => null });
      hidden(id, `${W} tap away`);
      if (loadedKey() !== other) problems.push(`${W}: a tap away unloaded ${other}`);
      if (markFor(id, other) && markFor(id, other).getAttribute("aria-pressed") !== "true") {
        problems.push(`${W}: after a tap away ${other} is no longer marked pressed`);
      }
      lastUsed[id] = other;
      walks++;
    }
    // A readout open on one chart closes when a mark on the other chart is tapped.
    const bk = keysOf("board")[0], pk = keysOf("pareto")[0];
    if (bk && pk) {
      dispatchClick("board", markFor("board", bk));
      pinnedAt("board", bk, `${mode}/${p.name} tap on the ranking`);
      dispatchClick("pareto", markFor("pareto", pk));
      hidden("board", `${mode}/${p.name} tap on the cost chart`);
      pinnedAt("pareto", pk, `${mode}/${p.name} tap on the cost chart`);
      dispatchClick("pareto", { closest: () => null });
      hidden("pareto", `${mode}/${p.name} tap away from both`);
      lastUsed.board = bk; lastUsed.pareto = pk;
    }
  }
}

const DEADLINE = Date.now() + 120000;
const check = () => {
  const line = el("selfcheck").innerHTML;
  const done = /<b>(\d+) of (\d+)<\/b>/.exec(line);
  if (!done && Date.now() < DEADLINE) { setTimeout(check, 10); return; }
  const m = done;
  const cases = data.expected.filter(e => e.status === "ok").length;
  let ok = true;
  if (!m) {
    console.error("FAIL: self-check produced no count:", line.slice(0, 200));
    ok = false;
  } else if (m[1] !== m[2]) {
    console.error(`FAIL: only ${m[1]} of ${m[2]} browser runs matched the Python evaluator`);
    ok = false;
  } else {
    console.log(`demo self-check: ${m[1]} of ${m[2]} runs reproduce solve_q15 exactly ` +
                `(${cases} fixture cases, ${Date.now() - t0} ms)`);
  }
  problems.slice(0, 12).forEach(p => console.error("FAIL:", p));
  if (problems.length) ok = false;
  if (problems.length > 12) console.error(`FAIL: ... and ${problems.length - 12} more`);
  if (ok) {
    console.log(`demo render: ${combos} control combinations, ${REGIONS.length} regions ` +
                `each, no empty output and no invalid coordinates`);
    console.log(`demo input: ${walks} chart walks (arrow keys, Home, End, Enter, Escape, tap, ` +
                `tap away); ${pinned} readouts pinned within 12 px of their mark with a matching ` +
                `live region; focus restored after ${restores} redraws`);
  }
  process.exit(ok ? 0 : 1);
};
setTimeout(check, 5);
