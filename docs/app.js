/* app.js: the interactive parts of the page. No libraries. The numbers come from the
   page-data block, which site/build.py writes from data/*.json. */
(function(){
"use strict";
var PD = JSON.parse(document.getElementById("page-data").textContent);
var NS = "http://www.w3.org/2000/svg";

function $(s, r){ return (r||document).querySelector(s); }
function $$(s, r){ return Array.prototype.slice.call((r||document).querySelectorAll(s)); }
function el(tag, attrs, text){
  var e = document.createElementNS(NS, tag);
  for (var k in attrs) e.setAttribute(k, attrs[k]);
  if (text != null) e.textContent = text;
  return e;
}
function fmt(v){
  if (v === 0) return "0";
  var a = Math.abs(v);
  if (a >= 1e4 || a < 1e-3) return v.toExponential(2).replace("e-", "e−");
  return String(+v.toPrecision(3));
}
function lg(v){ return Math.log(v) / Math.LN10; }

/* A radio group made of buttons: <div class="seg" role="radiogroup"> */
function seg(host, onPick){
  host.addEventListener("click", function(ev){
    var b = ev.target.closest("button");
    if (!b || !host.contains(b)) return;
    $$("button", host).forEach(function(x){ x.setAttribute("aria-checked", x === b ? "true" : "false"); });
    onPick(b);
  });
}
function picked(host, attr){
  var b = $('button[aria-checked="true"]', host);
  return b ? b.getAttribute(attr) : null;
}

/* Charts draw at the width of their box (at most 720), so the text stays readable on a phone. */
function chartWidth(host){ return Math.max(300, Math.min(720, Math.round(host.clientWidth || 720))); }
var resizers = [], lastW = window.innerWidth;
window.addEventListener("resize", function(){
  if (Math.abs(window.innerWidth - lastW) < 40) return;
  lastW = window.innerWidth;
  resizers.forEach(function(f){ f(); });
});
function onResize(f){ resizers.push(f); }

/* ---------------------------------------------------------------- tooltip */
var tip = document.createElement("div");
tip.className = "tip"; tip.hidden = true; tip.setAttribute("role", "status");
document.body.appendChild(tip);
function showTip(text, x, y){
  tip.textContent = text; tip.hidden = false;
  var w = tip.offsetWidth, h = tip.offsetHeight;
  var left = Math.min(Math.max(8, x - w / 2), window.innerWidth - w - 8);
  tip.style.left = left + "px";
  tip.style.top = Math.max(8, y - h - 12) + "px";
}
function hideTip(){ tip.hidden = true; }
function hoverable(node, text){
  node.setAttribute("tabindex", "0");
  node.setAttribute("aria-label", text);
  node.addEventListener("mouseenter", function(ev){ showTip(text, ev.clientX, ev.clientY); });
  node.addEventListener("mousemove", function(ev){ showTip(text, ev.clientX, ev.clientY); });
  node.addEventListener("mouseleave", hideTip);
  node.addEventListener("focus", function(){
    var r = node.getBoundingClientRect(); showTip(text, r.left + r.width / 2, r.top);
  });
  node.addEventListener("blur", hideTip);
}

/* ---------------------------------------------------------------- the Q15 demo */
var PROBLEM_TEXT = {
  dahlquist: "Exponential decay, y′ = −y. A search problem.",
  damped_osc: "A damped oscillator. A search problem.",
  vanderpol_mild: "A mild Van der Pol oscillator. A search problem.",
  pendulum: "A pendulum. The error is the drift in energy. A held-out problem.",
  dc_motor: "A DC motor, current and speed. A held-out problem.",
  rc_thermal: "A stiff RC thermal network with three nodes. A held-out problem.",
  quaternion: "A rotating quaternion. The error is the drift from unit length. A held-out problem."
};

function demo(){
  if (!window.Q15) return;
  var Q = window.Q15, sel = $("#d-prob"), modes = $("#demo .seg");
  Q.D.problems.forEach(function(p){
    var o = document.createElement("option");
    o.value = p.name; o.textContent = p.name + (p.set === "heldout" ? " (held-out)" : "");
    sel.appendChild(o);
  });
  sel.value = "damped_osc";
  function draw(){
    var pk = sel.value, mode = picked(modes, "data-mode");
    var p = Q.PROB[pk];
    $("#d-desc").textContent = (PROBLEM_TEXT[pk] || "") + " Time span 0 to " + p.t_end + ".";
    var rows = Q.D.methods.map(function(m){
      var r = Q.run(m.key, pk, mode, 0);
      return {m: m, r: r, cyc: Q.cyclesFor(m, p)};
    });
    rows.sort(function(a, b){
      var ea = a.r.status === "ok" ? a.r.error : Infinity, eb = b.r.status === "ok" ? b.r.error : Infinity;
      return ea - eb;
    });
    var ok = rows.filter(function(z){ return z.r.status === "ok" && z.r.error > 0; });
    var lo = Math.min.apply(null, ok.map(function(z){ return z.r.error; }));
    var hi = Math.max.apply(null, ok.map(function(z){ return z.r.error; }));
    var l0 = Math.floor(lg(lo)), l1 = Math.ceil(lg(hi));
    if (l1 === l0) l1 = l0 + 1;
    var W = chartWidth($("#d-chart")), narrow = W < 520;
    var rowH = 26, top = 8, left = narrow ? 96 : 132, right = narrow ? 64 : 150, H = top + rows.length * rowH + 30;
    var svg = el("svg", {viewBox: "0 0 " + W + " " + H, role: "img",
      "aria-label": "Final error of each method on " + pk + ", " + (mode === "floor" ? "floor rounding" : "round to nearest")});
    var span = W - left - right;
    function X(v){ return left + (lg(v) - l0) / (l1 - l0) * span; }
    for (var d = l0; d <= l1; d++){
      var gx = left + (d - l0) / (l1 - l0) * span;
      svg.appendChild(el("line", {x1: gx, x2: gx, y1: top, y2: H - 24, "class": "grid"}));
      svg.appendChild(el("text", {x: gx, y: H - 8, "class": "axis", "text-anchor": "middle"}, "1e" + d));
    }
    rows.forEach(function(z, i){
      var y = top + i * rowH, g = el("g", {"class": "bar " + (z.m.origin === "discovered" ? "disc" : "class")});
      var name = z.m.origin === "discovered" ? z.m.key + (z.m.key === PD.champion.hash ? " ★" : "") : z.m.label;
      g.appendChild(el("text", {x: left - 8, y: y + rowH / 2 + 4, "text-anchor": "end", "class": "lab"}, name));
      var text;
      if (z.r.status === "ok"){
        var w = Math.max(2, X(Math.max(z.r.error, Math.pow(10, l0))) - left);
        g.appendChild(el("rect", {x: left, y: y + 4, width: w, height: rowH - 8, rx: 3}));
        g.appendChild(el("text", {x: left + w + 6, y: y + rowH / 2 + 4, "class": "val"},
          narrow ? fmt(z.r.error) : fmt(z.r.error) + "  ·  " + z.r.steps.toLocaleString() + " steps"));
        text = name + (z.m.origin === "discovered" ? " (discovered" + (z.m.key === PD.champion.hash ? ", the champion)" : ")") : "") + ": error " + fmt(z.r.error) + ", " + z.r.steps.toLocaleString() + " steps of " + z.cyc + " cycles, " + z.m.stages + " stages, order " + z.m.order;
      } else {
        g.setAttribute("class", "bar over");
        g.appendChild(el("rect", {x: left, y: y + 4, width: span, height: rowH - 8, rx: 3}));
        g.appendChild(el("text", {x: left + 8, y: y + rowH / 2 + 4, "class": "val inv"}, "overflow at " + (z.r.steps || 0).toLocaleString() + " steps"));
        text = name + ": overflow. A value went outside the Q15 range.";
      }
      hoverable(g, text);
      svg.appendChild(g);
    });
    var host = $("#d-chart"); host.innerHTML = ""; host.appendChild(svg);
  }
  sel.addEventListener("change", draw);
  seg(modes, draw);
  onResize(draw);
  draw();

  var btn = $("#d-check"), out = $("#d-check-out");
  btn.addEventListener("click", function(){
    btn.disabled = true;
    Q.check(function(s){
      if (!s.done){ out.textContent = "Checking: " + s.checked + " of " + s.total + "..."; return; }
      btn.disabled = false;
      out.className = s.fail.length ? "bad" : "good";
      out.textContent = s.fail.length
        ? s.pass + " of " + s.total + " agree. Different: " + s.fail.slice(0, 4).join(", ")
        : s.pass + " of " + s.total + " cases agree with the Python harness, bit for bit. Your browser ran the same arithmetic that scored the archive.";
    });
  });
}

/* ---------------------------------------------------------------- the result chart */
function frontier(){
  var host = $("#f-chart"); if (!host) return;
  var F = PD.frontier, pts = [];
  F.classical.forEach(function(c){ pts.push({x: c.cycles, y: c.heldout_error, kind: "class", name: c.name}); });
  F.discovered.forEach(function(d){
    pts.push({x: d.cycles, y: d.heldout_error, kind: d.is_champion ? "champ" : "disc",
              name: d.is_champion ? "champion " + PD.champion.hash : "discovered", d: d});
  });
  var xs = pts.map(function(p){ return p.x; }), ys = pts.map(function(p){ return p.y; });
  var x0 = 0, x1 = Math.ceil(Math.max.apply(null, xs) / 10) * 10 + 5;
  var l0 = lg(Math.min.apply(null, ys)) - 0.12, l1 = lg(Math.max.apply(null, ys)) + 0.25;
  var W = chartWidth(host), H = W < 520 ? 320 : 380, L = 58, R = 16, T = 16, B = 46;
  var svg = el("svg", {viewBox: "0 0 " + W + " " + H, role: "img",
    "aria-label": "Held-out error against cycles per step for classical and discovered methods"});
  function X(v){ return L + (v - x0) / (x1 - x0) * (W - L - R); }
  function Y(v){ return T + (l1 - lg(v)) / (l1 - l0) * (H - T - B); }
  [0.01, 0.02, 0.05, 0.1, 0.2, 0.5, 1].forEach(function(v){
    if (lg(v) > l0 && lg(v) < l1){
      svg.appendChild(el("line", {x1: L, x2: W - R, y1: Y(v), y2: Y(v), "class": "grid" + (v === 0.1 || v === 1 ? "" : " minor")}));
      svg.appendChild(el("text", {x: L - 8, y: Y(v) + 4, "class": "axis", "text-anchor": "end"}, String(v)));
    }
  });
  for (var c = 0; c <= x1; c += 10){
    svg.appendChild(el("line", {x1: X(c), x2: X(c), y1: T, y2: H - B, "class": "grid minor"}));
    svg.appendChild(el("text", {x: X(c), y: H - B + 18, "class": "axis", "text-anchor": "middle"}, String(c)));
  }
  svg.appendChild(el("text", {x: (L + W - R) / 2, y: H - 6, "class": "axis title", "text-anchor": "middle"}, "analytic cycles per step (cheaper to the left)"));
  svg.appendChild(el("text", {x: 14, y: (T + H - B) / 2, "class": "axis title", "text-anchor": "middle",
    transform: "rotate(-90 14 " + (T + H - B) / 2 + ")"}, "held-out error (lower is better)"));
  pts.sort(function(a, b){ return (a.kind === "champ") - (b.kind === "champ"); });
  pts.forEach(function(p){
    var g = el("g", {"class": "pt " + p.kind}), cx = X(p.x), cy = Y(p.y);
    if (p.kind === "class"){
      g.appendChild(el("circle", {cx: cx, cy: cy, r: 6}));
      if (p.name === "euler") g.appendChild(el("text", {x: cx + 10, y: cy + 4, "class": "plab"}, p.name));
      else if (p.name === "midpoint") g.appendChild(el("text", {x: cx - 9, y: cy + 4, "class": "plab", "text-anchor": "end"}, p.name));
      else if (W >= 520) g.appendChild(el("text", {x: cx + 3, y: cy - 10, "class": "plab", transform: "rotate(-55 " + (cx + 3) + " " + (cy - 10) + ")"}, p.name));
    } else {
      var s = p.kind === "champ" ? 9 : 6;
      g.appendChild(el("path", {d: "M" + cx + " " + (cy - s) + "L" + (cx + s) + " " + cy + "L" + cx + " " + (cy + s) + "L" + (cx - s) + " " + cy + "Z"}));
      if (p.kind === "champ") g.appendChild(el("text", {x: cx + 12, y: cy + 4, "class": "plab strong"}, "champion"));
    }
    var t = p.kind === "class"
      ? p.name + " (classical): error " + fmt(p.y) + " at " + p.x + " cycles per step"
      : (p.kind === "champ" ? "Champion " + PD.champion.hash : "Discovered elite") + ": error " + fmt(p.y) + " at " + p.x +
        " cycles per step, " + p.d.stages + " stages, order " + p.d.order + ", first seen in cycle " + p.d.first_cycle;
    hoverable(g, t);
    svg.appendChild(g);
  });
  host.innerHTML = "";
  host.appendChild(svg);
}

/* ---------------------------------------------------------------- the lead selector */
var BASIS_TEXT = {
  analytic: "Analytic cost counts only the coefficient arithmetic of a step. All archived scores use it.",
  traced_whole_step: "Traced whole-step cost counts every instruction of the compiled step, except the body of the derivative function."
};
var WEIGHT_TEXT = {
  magnitude: "Magnitude weighting is the published one. It is a plain RMS of the four errors, so a problem with large errors has a large effect.",
  equal_reference_norm: "Reference-norm weighting divides each error by the zero-state error of its problem. It gives more weight to rc_thermal.",
  equal_median_anchor: "Median-anchor weighting divides each error by the median classical error of its problem. The four problems then have equal weight."
};
function lead(){
  var b = $("#cf-basis"), w = $("#cf-weight"); if (!b) return;
  function draw(){
    var basis = picked(b, "data-v"), weight = picked(w, "data-v");
    var c = PD.cells.filter(function(z){ return z.basis === basis && z.weighting === weight; })[0];
    $("#cf-ratio").textContent = (+c.ratio.toPrecision(3)) + "x";
    $("#cf-ratio").className = c.ratio >= 1 ? "good" : "bad";
    $("#cf-loo").textContent = c.champion_still_leads ? "Yes" : "No";
    $("#cf-loo").className = c.champion_still_leads ? "good" : "bad";
    $("#cf-low").textContent = "(lowest: " + (+c.lowest_leave_one_out_ratio.toPrecision(3)) + "x)";
    var note = BASIS_TEXT[basis] + " " + WEIGHT_TEXT[weight];
    if (basis === "traced_whole_step" && weight === "equal_median_anchor")
      note += " This low value comes from pendulum, which this weighting magnifies. It does not mean that the champion loses by this factor.";
    $("#cf-note").textContent = note;
  }
  seg(b, draw); seg(w, draw); draw();
}

/* ---------------------------------------------------------------- how it works */
function pipe(){
  var host = $("#pipe"); if (!host) return;
  host.addEventListener("click", function(ev){
    var btn = ev.target.closest("button"); if (!btn) return;
    var k = btn.getAttribute("data-step");
    $$("button", host).forEach(function(x){ x.setAttribute("aria-pressed", x === btn ? "true" : "false"); });
    $$(".steps .step").forEach(function(s){ s.hidden = s.getAttribute("data-step") !== k; });
  });
}

/* ---------------------------------------------------------------- claims */
function claims(){
  var f = $("#cl-filter"); if (!f) return;
  var segHost = $(".seg", f), head = $("#cl-head"), openBtn = $("#cl-open");
  function apply(){
    var proj = picked(segHost, "data-f"), onlyHead = head.checked;
    $$(".claim").forEach(function(c){
      var show = (proj === "all" || c.getAttribute("data-project") === proj) &&
                 (!onlyHead || $(".star", c));
      c.hidden = !show;
    });
  }
  seg(segHost, apply);
  head.addEventListener("change", apply);
  openBtn.addEventListener("click", function(){
    var open = openBtn.textContent === "Open all";
    $$(".claim").forEach(function(c){ if (!c.hidden) c.open = open; });
    openBtn.textContent = open ? "Close all" : "Open all";
  });
  function fromHash(){
    var id = decodeURIComponent(location.hash.slice(1));
    var c = id && document.getElementById(id);
    if (c && c.classList.contains("claim")){
      c.hidden = false; c.open = true;
      setTimeout(function(){ c.scrollIntoView({block: "start"}); }, 0);
    }
  }
  window.addEventListener("hashchange", fromHash);
  fromHash();
}

/* ---------------------------------------------------------------- copy */
function copy(){
  $$("button.copy").forEach(function(b){
    b.addEventListener("click", function(){
      var t = document.getElementById(b.getAttribute("data-copy")).textContent;
      (navigator.clipboard ? navigator.clipboard.writeText(t) : Promise.reject()).then(
        function(){ b.textContent = "Copied"; setTimeout(function(){ b.textContent = "Copy"; }, 1500); },
        function(){ b.textContent = "Select the text"; });
    });
  });
}

demo(); frontier(); onResize(frontier); lead(); pipe(); claims(); copy();
})();
