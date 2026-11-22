/* Build-time check for the landing widget in docs/index.html.
 *
 * The widget ranks eleven methods under both rounding modes from data reduced out of
 * demo_data.json. This loads the published page headless, drives every problem button
 * and every hover, and confirms the chart and its sentence render without NaN, empty
 * output or an SVG coordinate a browser would drop. It also re-derives the ranking in
 * plain JavaScript and checks the widget agrees, so a chart that silently mis-sorts
 * fails the build.
 *
 * It then drives the pin: a tap, a tap away, and the keyboard, reading the aria-live
 * readout after each against the ranking it re-derived. Last, it runs the staleness badge
 * under a mocked clock on both sides of its threshold and with the clock behind the date.
 *
 *   node tools/check_hero.js [path/to/index.html]
 */
"use strict";
const fs = require("fs"), path = require("path"), vm = require("vm");
const page = process.argv[2] || path.join(__dirname, "..", "docs", "index.html");
const html = fs.readFileSync(page, "utf8");
const scripts = [...html.matchAll(/<script>([\s\S]*?)<\/script>/g)].map(m => m[1]);
if (scripts.length !== 2) {
  console.error(`FAIL: expected 2 inline scripts in ${page}, found ${scripts.length}`);
  process.exit(1);
}

const nodes = new Map();
const mk = id => ({
  id, innerHTML: "", className: "", hidden: true, handlers: {},
  addEventListener(t, f) { this.handlers[t] = f; },
  setAttribute(k, v) { this.attrs = this.attrs || {}; this.attrs[k] = v; },
  getAttribute(k) { return (this.attrs || {})[k] ?? this.dataV ?? null; },
  querySelectorAll() { return []; },
});
const el = id => (nodes.has(id) ? nodes.get(id) : (nodes.set(id, mk(id)), nodes.get(id)));
let onReady = null;
const docHandlers = {};
global.window = {};
global.document = {
  getElementById: el,
  querySelectorAll() { return []; },
  addEventListener(n, f) { if (n === "DOMContentLoaded") onReady = f; else docHandlers[n] = f; },
};
try {
  vm.runInThisContext(scripts[0], { filename: "flip-data" });
  vm.runInThisContext(scripts[1], { filename: "flip-js" });
} catch (e) { console.error("FAIL: hero script threw on load:", e && e.message); process.exit(1); }
if (typeof onReady !== "function") { console.error("FAIL: no DOMContentLoaded handler"); process.exit(1); }
try { onReady(); } catch (e) { console.error("FAIL: hero threw on first render:", e && e.stack); process.exit(1); }

const H = global.window.__RKFLIP__;
const bad = [];
const strip = s => s.replace(/<[^>]+>/g, " ");
/* A click is dispatched the way a browser orders it: the document's capture-phase handler
 * sees it before the target's own. Each fake target answers closest() only for the
 * selector its real element would match. */
const click = v => {
  const ev = { target: { closest: s => (s === "button" ? { getAttribute: () => v } : null) } };
  if (docHandlers.click) docHandlers.click(ev);
  el("flipseg").handlers.click(ev);
};
const hover = k => el("flip").handlers.mouseover({ target: { closest: () => (k ? { getAttribute: () => k } : null) } });

/* Independent ranking, so the chart is checked against something rather than itself. */
function expectRank(prob, mode) {
  const xs = H.methods.map((m, i) => ({ k: m.key, e: H.err[prob][mode][i] }))
    .filter(z => z.e !== null && isFinite(z.e) && z.e > 0)
    .sort((a, b) => a.e - b.e || (a.k < b.k ? -1 : 1));
  let prev = null, r = 0;
  xs.forEach((z, i) => { if (prev === null || z.e !== prev) { r = i + 1; prev = z.e; } z.r = r; });
  return xs;
}
const label = Object.fromEntries(H.methods.map(m => [m.key, m.label]));

let checked = 0, ranksChecked = 0;
for (const prob of H.problems) {
  click(prob);
  for (const k of [null, ...H.methods.map(m => m.key)]) {
    hover(k);
    checked++;
    for (const id of ["flip", "flipsay"]) {
      const h = el(id).innerHTML;
      if (!h || h.length < 20) bad.push(`${prob}/${k}: ${id} empty`);
      const junk = strip(h).match(/NaN|undefined|Infinity/);
      if (junk) bad.push(`${prob}/${k}: ${id} rendered ${junk[0]}`);
      if (/(?:\bx|\by|cx|cy|width|height)="(?:NaN|-?Infinity)/.test(h)) {
        bad.push(`${prob}/${k}: ${id} invalid SVG coordinate`);
      }
    }
  }
  // The left column must read in the ranking order the data implies, label for label.
  const want = expectRank(prob, "floor").map(z => `${z.r} ${label[z.k]}`);
  const shown = [...el("flip").innerHTML.matchAll(
    /<text class="fn[^"]*"[^>]*text-anchor="end">(\d+)\s+(.*?)\s+<tspan/g)]
    .map(m => `${m[1]} ${m[2]}`);
  if (shown.length !== want.length) {
    bad.push(`${prob}: left column drew ${shown.length} rows, data implies ${want.length}`);
  } else if (shown.join("|") !== want.join("|")) {
    bad.push(`${prob}: left column order is ${shown.join(", ")}; data implies ${want.join(", ")}`);
  } else {
    ranksChecked += shown.length;
  }
}
hover(null);

/* The paragraph above the chart says a line can be tapped and that the arrow keys reach
 * the same highlight. A hover handler satisfies neither, and that is what the page shipped
 * while the sentence claimed otherwise, so both paths are driven here rather than read off
 * the source: the sentence cannot outlive its handlers.
 */
const flip = el("flip");
const visible = strip(html.replace(/<script>[\s\S]*?<\/script>/g, " "));
const tap = k => {
  const ev = { target: { closest: s => (k && /g\[data-k\]/.test(s) ? { getAttribute: () => k } : null) } };
  if (docHandlers.click) docHandlers.click(ev);
  flip.handlers.click(ev);
};
const press = k => flip.handlers.keydown({ key: k, preventDefault() {} });
const lit = () => (el("flip").innerHTML.match(/class="f[ln](?: up| dn)? on"/g) || []).length;
// A lit method lights a group in each column, so the keys are deduplicated.
const litKeys = () => [...new Set([...el("flip").innerHTML.matchAll(
  /<g class="hot" data-k="([^"]*)">(?:(?!<\/g>)[\s\S])*?class="f[ln](?: up| dn)? on"/g)].map(m => m[1]))];
// Inline tags only, so they are removed rather than spaced: "<b>x</b>:" renders as "x:".
const inline = s => s.replace(/<[^>]+>/g, "").replace(/\s+/g, " ").trim();
const read = () => inline(el("flipread").innerHTML);

if (/\btap\b/i.test(visible) && !flip.handlers.click) {
  bad.push("the hero paragraph says tap and #flip has no click handler");
}
if (/\barrow keys\b/i.test(visible) && !flip.handlers.keydown) {
  bad.push("the hero paragraph names the arrow keys and #flip has no keydown handler");
}
if (!/id="flip"[^>]*tabindex="0"/.test(html)) {
  bad.push('#flip has no tabindex="0", so its keydown handler cannot be reached');
}
if (!/<p id="flipread"[^>]*aria-live="polite"/.test(html)) {
  bad.push("#flipread is missing or carries no aria-live, so a pinned line is announced to nobody");
}
if (!docHandlers.click) {
  bad.push("no document click handler, so a tap away from the chart cannot hide the readout");
}

/* What the readout must say for method k: its own name, then both ranks as the data
 * implies them. Checked by prefix and by fragment, never against the widget's own text. */
function readoutFaults(prob, k, where) {
  const text = read(), out = [];
  const f = expectRank(prob, "floor"), n = expectRank(prob, "nearest");
  const a = f.find(z => z.k === k), b = n.find(z => z.k === k);
  if (!text.startsWith(`${label[k]} on ${prob}:`)) out.push(`${where}: readout does not open with ${label[k]} (reads "${text}")`);
  if (a && !text.includes(`rank ${a.r} of ${f.length} under floor`)) out.push(`${where}: readout lacks floor rank ${a.r} of ${f.length} (reads "${text}")`);
  if (b && !text.includes(`rank ${b.r} of ${n.length} under round-to-nearest`)) out.push(`${where}: readout lacks round-to-nearest rank ${b.r} of ${n.length} (reads "${text}")`);
  if (/NaN|undefined|Infinity/.test(text)) out.push(`${where}: readout rendered junk: "${text}"`);
  return out;
}

let readouts = 0;
if (flip.handlers.click && flip.handlers.keydown && docHandlers.click) {
  for (const prob of H.problems) {
    click(prob);
    press("Escape");
    const order = expectRank(prob, "floor").map(z => z.k);
    if (order.length < 2) continue;
    const first = order[0], last = order[order.length - 1];

    tap(first);
    if (litKeys().join() !== first) bad.push(`${prob}: a tap on ${first} lit [${litKeys()}]`);
    bad.push(...readoutFaults(prob, first, `${prob} tap`)); readouts++;

    const said = read();
    hover(last);
    if (read() !== said) bad.push(`${prob}: hovering ${last} rewrote the readout; only a pin should`);
    hover(null);

    tap(null);
    if (litKeys().join() !== first) bad.push(`${prob}: a tap away changed the lit line to [${litKeys()}]; it should keep ${first}`);
    if (read() !== "") bad.push(`${prob}: a tap away left the readout showing "${read()}"`);

    press("ArrowDown");
    if (litKeys().join() !== order[1]) bad.push(`${prob}: ArrowDown lit [${litKeys()}], want ${order[1]}`);
    bad.push(...readoutFaults(prob, order[1], `${prob} ArrowDown`)); readouts++;

    press("End");
    if (litKeys().join() !== last) bad.push(`${prob}: End lit [${litKeys()}], want ${last}`);
    bad.push(...readoutFaults(prob, last, `${prob} End`)); readouts++;

    press("Escape");
    if (lit() !== 0) bad.push(`${prob}: Escape left a line highlighted`);
    if (read() !== "") bad.push(`${prob}: Escape left the readout showing "${read()}"`);

    press("Enter");
    if (litKeys().join() !== first) bad.push(`${prob}: Enter with nothing pinned lit [${litKeys()}], want ${first}`);
    bad.push(...readoutFaults(prob, first, `${prob} Enter`)); readouts++;
    press("Escape");
  }
}

/* The staleness badge. The threshold is read from the script and held to the decision
 * that set it; the page's own data-asof date is the origin, and the clock is mocked to
 * land an hour past midday on each day tested. The second script is run again for each
 * clock, which re-registers the hero's DOMContentLoaded handler and changes nothing else.
 */
const asofM = /<p[^>]*id="stale"[^>]*data-asof="(\d{4}-\d{2}-\d{2})"/.exec(html);
const thrM = /var STALE_DAYS=(\d+);/.exec(scripts[1]);
if (!asofM) bad.push("the staleness badge has no data-asof date to count from");
if (!thrM) bad.push("the badge script defines no STALE_DAYS threshold");
else if (Number(thrM[1]) !== 7) bad.push(`STALE_DAYS is ${thrM[1]}; the recorded decision sets 7`);
if (!/\.stale\.old\{/.test(html)) bad.push("no .stale.old rule, so the stale state has no styling of its own");
let clocks = 0;
if (asofM && thrM) {
  const asof = asofM[1], T = Number(thrM[1]);
  const origin = Date.parse(asof + "T12:00:00Z");
  const badge = days => {
    const n = el("stale");
    n.attrs = { "data-asof": asof }; n.hidden = true; n.innerHTML = ""; n.className = "stale";
    const realNow = Date.now;
    Date.now = () => origin + days * 86400000 + 3600000;
    try { vm.runInThisContext(scripts[1], { filename: "flip-js-clock" }); }
    catch (e) { bad.push(`badge script threw with the clock at ${days} days: ${e && e.message}`); }
    finally { Date.now = realNow; }
    clocks++;
    return { hidden: n.hidden, cls: n.className, state: (n.attrs || {})["data-state"],
             text: inline(n.innerHTML), html: n.innerHTML };
  };
  const PAUSED = "a snapshot cannot tell a paused run from a broken build";
  for (const [d, want] of [[0, "fresh"], [T, "fresh"], [T + 1, "stale"], [T + 30, "stale"]]) {
    const b = badge(d);
    if (b.hidden) { bad.push(`badge at ${d} days stayed hidden`); continue; }
    if (b.state !== want) bad.push(`badge at ${d} days is in state ${b.state}, want ${want}`);
    if ((want === "stale") !== /(?:^|\s)old(?:\s|$)/.test(b.cls)) bad.push(`badge at ${d} days has class "${b.cls}"`);
    if (!b.text.includes(d === 0 ? "from today" : `${d} days old`)) bad.push(`badge at ${d} days reads "${b.text}"`);
    if (!b.text.includes(PAUSED)) bad.push(`badge at ${d} days does not say ${PAUSED}`);
    if (!/href="https:\/\/[^"]+\/rk-findings\/"/.test(b.html) || !b.text.includes("build stamp")) {
      bad.push(`badge at ${d} days does not point to the findings site's build stamp`);
    }
    if (want === "stale" && !b.text.startsWith("Stale.")) bad.push(`badge at ${d} days does not open with "Stale."`);
    if (want === "stale" && !b.text.includes(`${T}-day limit`)) bad.push(`badge at ${d} days does not name the ${T}-day limit`);
    if (want === "fresh" && /Stale|limit/.test(b.text)) bad.push(`badge at ${d} days talks about staleness while fresh`);
    if (/NaN|undefined|Infinity/.test(b.text)) bad.push(`badge at ${d} days rendered junk: "${b.text}"`);
  }
  if (!badge(-2).hidden) bad.push("with the reader's clock behind the archive date, the badge still showed an age");
}

console.log(`hero: ${H.methods.length} methods x ${H.problems.length} problems, ` +
            `${checked} render passes, ${ranksChecked} ranked rows matched against the data`);
if (bad.length) { bad.slice(0, 10).forEach(b => console.error("FAIL:", b)); process.exit(1); }
console.log("hero render: no empty output, no NaN, no invalid coordinates");
console.log("hero input: pointer, tap and arrow-key paths all move the highlight; a tap away " +
            "hides the readout and keeps the pinned line");
console.log(`hero readout: ${readouts} aria-live readouts matched both re-derived ranks`);
console.log(`staleness badge: ${clocks} mocked clocks; fresh through ${thrM[1]} days, stale ` +
            "past it, hidden when the clock is behind the archive date");
