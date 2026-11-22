/* q15.js: the Q15 integrator of the harness, in JavaScript.

   The arithmetic below (from "Q15 primitives" to "run cache") is the demo engine of the old
   rk-overview site, unchanged. It mirrors harness/rk_harness/fixedpoint.py, problems.py and
   simulate.py (solve_q15), and it reproduces the Python evaluator bit for bit on the 154
   stored cases in analysis/tools/demo_data.json. app.js draws the page; this file only
   computes. It exposes window.Q15. */
(function(){
"use strict";
var PD = document.getElementById("page-data");
var D = PD ? JSON.parse(PD.textContent).demo : null;
if(!D){ return; }
var BUD = D.budget_cycles;

/* ---------------------------------------------------------------- Q15 primitives
   Mirrors rk_harness/fixedpoint.py. Products reach 2^30, so every shift is a
   Math.floor division rather than JavaScript's 32-bit >> operator. */
var QMIN=-32768, QMAX=32767, QONE=32768;
var POW=[], HALF=[];
for(var i=0;i<=22;i++){ POW[i]=Math.pow(2,i); HALF[i]=i>0?Math.pow(2,i-1):0; }

function chk(v){ if(v<QMIN||v>QMAX) throw new RangeError("q15 overflow"); return v; }
function rhe(x){                       /* Python round(): half to even */
  var f=Math.floor(x), d=x-f;
  if(d>0.5) return f+1;
  if(d<0.5) return f;
  return (f%2===0)?f:f+1;
}
function fromFloat(x){
  if(!isFinite(x)) throw new RangeError("non-finite");
  return chk(rhe(x*QONE));
}
function shFloor(v,k){ return Math.floor(v/POW[k]); }
function shNear(v,k){ return k===0?v:Math.floor((v+HALF[k])/POW[k]); }

/* ---------------------------------------------------------------- right-hand sides
   Operation order matches rk_harness/problems.py term for term, because float64 is
   only reproducible if the associativity is. */
var ZETA=0.1, OMEGA=1.0, MU=0.5, RR=2.0, LL=0.5, KE=0.1, KT=0.1, BB=0.02, JJ=0.02, VV=1.0;
var WX=0.3, WY=0.2, WZ=0.5;
var RCA=[[-11.0,10.0,0.0],[5.0,-6.0,1.0],[0.0,2.0,-2.0]];
var RHS={
  dahlquist:function(t,y){ return [-y[0]]; },
  damped_osc:function(t,y){ return [y[1], -2.0*ZETA*OMEGA*y[1] - OMEGA*OMEGA*y[0]]; },
  vanderpol_mild:function(t,y){ return [y[1], MU*(1.0-y[0]*y[0])*y[1] - y[0]]; },
  pendulum:function(t,y){ return [y[1], -Math.sin(y[0])]; },
  dc_motor:function(t,y){ return [(-RR*y[0]-KE*y[1]+VV)/LL, (KT*y[0]-BB*y[1])/JJ]; },
  rc_thermal:function(t,y){
    var o=[0,0,0];
    for(var r=0;r<3;r++){ o[r]=RCA[r][0]*y[0]+RCA[r][1]*y[1]+RCA[r][2]*y[2]; }
    return o;
  },
  quaternion:function(t,y){
    var q0=y[0],q1=y[1],q2=y[2],q3=y[3];
    return [0.5*(-WX*q1-WY*q2-WZ*q3), 0.5*(WX*q0+WZ*q2-WY*q3),
            0.5*(WY*q0-WZ*q1+WX*q3), 0.5*(WZ*q0+WY*q1-WX*q2)];
  }
};
var E0PEND = 1.0 - Math.cos(1.0);

function toPhys(yq, scale){
  var o=new Array(yq.length);
  for(var i=0;i<yq.length;i++){ o[i]=yq[i]/32768.0/scale; }
  return o;
}
function makeRhs(p){
  var f=RHS[p.name], sc=p.scale, ds=p.deriv_scale;
  return function(t,yq){
    var y=toPhys(yq,sc), d=f(t,y), o=new Array(d.length);
    for(var i=0;i<d.length;i++){ o[i]=fromFloat(d[i]*sc*ds); }
    return o;
  };
}

/* ---------------------------------------------------------------- the integrator
   rk_harness/simulate.py solve_q15, with the shift rule as a parameter. */
function solve(meth,p,n,mode,sampleEvery){
  var h=p.t_end/n;
  var hq=fromFloat(h/p.deriv_scale);
  var sh = (mode==="floor")?shFloor:shNear;
  var s=meth.b.length, ns=p.n_states, A=meth.A, b=meth.b, c=meth.c;
  var f=makeRhs(p);
  var y=p.y0.slice(), hk=new Array(s);
  var samples=[[0,y.slice()]];
  var peak=0, m, i, j;
  for(m=0;m<ns;m++){ if(Math.abs(y[m])>peak) peak=Math.abs(y[m]); }
  for(var step=0;step<n;step++){
    var tk=step*h;
    for(i=0;i<s;i++){
      var acc=y, row=A[i];
      for(j=0;j<i;j++){
        var rep=row[j];
        if(!rep) continue;
        var na=new Array(ns), hkj=hk[j];
        for(m=0;m<ns;m++){ na[m]=chk(acc[m]+chk(sh(hkj[m]*rep[0],rep[1]))); }
        acc=na;
      }
      for(m=0;m<ns;m++){ if(Math.abs(acc[m])>peak) peak=Math.abs(acc[m]); }
      var ki=f(tk+c[i]*h, acc), v=new Array(ns);
      for(m=0;m<ns;m++){ v[m]=chk(sh(ki[m]*hq,15)); }
      hk[i]=v;
    }
    var yn=y;
    for(i=0;i<s;i++){
      var rb=b[i];
      if(!rb) continue;
      var nv=new Array(ns), hki=hk[i];
      for(m=0;m<ns;m++){ nv[m]=chk(yn[m]+chk(sh(hki[m]*rb[0],rb[1]))); }
      yn=nv;
    }
    y=yn;
    for(m=0;m<ns;m++){ if(Math.abs(y[m])>peak) peak=Math.abs(y[m]); }
    if(sampleEvery>0 && ((step+1)%sampleEvery===0 || step===n-1)){
      samples.push([(step+1)*h, y.slice()]);
    }
  }
  return {final:y, samples:samples, peak:peak};
}

function errorOf(p, q){
  var y=toPhys(q,p.scale), s=0, i;
  if(p.metric==="energy"){
    var e=0.5*y[1]*y[1]+(1.0-Math.cos(y[0]));
    return Math.abs(e-E0PEND)/E0PEND;
  }
  if(p.metric==="norm1"){
    for(i=0;i<y.length;i++){ s+=y[i]*y[i]; }
    return Math.abs(Math.sqrt(s)-1.0);
  }
  for(i=0;i<y.length;i++){ var d=y[i]-p.ref_end[i]; s+=d*d; }
  return Math.sqrt(s)/p.peak;
}
function stepsFor(meth,p){
  var cyc=meth.cycles.m0plus_fast[String(p.n_states)];
  return cyc>0?Math.floor(BUD/cyc):0;
}
function cyclesFor(meth,p){ return meth.cycles.m0plus_fast[String(p.n_states)]; }

/* ---------------------------------------------------------------- run cache */
var CACHE={};
function run(mk,pk,mode,sample){
  var key=mk+"|"+pk+"|"+mode+"|"+(sample||0);
  if(CACHE[key]) return CACHE[key];
  var meth=METH[mk], p=PROB[pk], n=stepsFor(meth,p), out;
  if(n<=0){ out={status:"no_steps",steps:0}; }
  else{
    try{
      var r=solve(meth,p,n,mode,sample||0);
      out={status:"ok",steps:n,final:r.final,samples:r.samples,
           error:errorOf(p,r.final),
           headroom:r.peak>0?32767/r.peak:Infinity};
    }catch(e){ out={status:"overflow",steps:n}; }
  }
  CACHE[key]=out;
  return out;
}

var METH={}, PROB={};
D.methods.forEach(function(m){ METH[m.key]=m; });
D.problems.forEach(function(p){ PROB[p.name]=p; });

/* Run every stored case again and compare with the Python result. Calls back with
   progress so the page stays responsive. */
function check(progress){
  var rows=D.expected, idx=0, pass=0, fail=[];
  function chunk(){
    var t0=Date.now();
    while(idx<rows.length && Date.now()-t0<40){
      var e=rows[idx++], got=run(e.m,e.p,e.mode,0);
      var same = got.status===e.status && got.steps===e.steps &&
                 (e.status!=="ok" || (got.final.length===e.final.length &&
                  got.final.every(function(v,i){ return v===e.final[i]; })));
      if(same) pass++; else fail.push(e.m+"/"+e.p+"/"+e.mode);
    }
    var done=idx>=rows.length;
    progress({done:done, checked:idx, total:rows.length, pass:pass, fail:fail});
    if(!done) setTimeout(chunk,0);
  }
  chunk();
}

window.Q15 = {D:D, METH:METH, PROB:PROB, run:run, stepsFor:stepsFor, cyclesFor:cyclesFor, check:check};
})();
