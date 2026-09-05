// =============================================================================================
// presets.drums.js - Studio.PRESETS_DRUMS
// Twenty drum templates (10 for the Drums kit, 10 for the Percussion kit) plus expand(), which
// turns a template into a real pattern for a given meter, energy and seed.
//
// A template never stores absolute steps. It stores hits per ROLE, and each meter says which of
// its groups plays which role, so one template gives a musical backbeat in 4/4, 3/4, 5/4, 6/8,
// 7/8 and 12/8 without being rewritten. Pads (Studio.MACHINE_TYPES.beatbox.pads):
// 0 kick, 1 snare, 2 clap, 3 closed hat, 4 open hat, 5 tom, 6 rim, 7 crash.
// =============================================================================================
'use strict';
(function(){
const Studio=window.Studio=window.Studio||{};

// Meters as groups of 16th steps. The sum is always Studio.barSteps(meter).
const GROUPS={'4/4':[4,4,4,4],'3/4':[4,4,4],'5/4':[4,4,4,4,4],'6/8':[6,6],'7/8':[4,4,6],'12/8':[6,6,6,6]};

// Which group carries which role. down = the downbeat, back = the backbeat, up = the lift
// between them. A role that a meter has no group for falls back to the last group.
const ROLES={'4/4':['down','back','up','back'],'3/4':['down','up','back'],'5/4':['down','up','back','up','back'],
 '6/8':['down','back'],'7/8':['down','up','back'],'12/8':['down','back','up','back']};

const clamp=(x,a,b)=>x<a?a:x>b?b:x;

// Seeded PRNG (mulberry32). Same seed in, same notes out.
function mulberry32(a){ return function(){ a=a+0x6D2B79F5|0; let t=Math.imul(a^a>>>15,1|a);
 t=t+Math.imul(t^t>>>7,61|t)^t; return ((t^t>>>14)>>>0)/4294967296; }; }
// Mix the template id into the seed so two templates on the same seed do not jitter identically.
function hashId(s){ let h=2166136261; s=String(s||''); for(let i=0;i<s.length;i++){ h^=s.charCodeAt(i); h=Math.imul(h,16777619); } return h|0; }

function meterKey(meter){ if(!meter)return '4/4'; if(typeof meter==='string')return meter;
 return ((meter.beats||4)+'/'+(meter.div||4)); }

// A hit is written on a 4-step group. In a 6-step group (compound meters) the same position is
// stretched, so at 0/2 land on the two dotted-beat halves instead of bunching at the start.
function scaleAt(at,glen){ at=at|0; if(glen===4)return clamp(at,0,3); return clamp(Math.round(at*glen/4),0,glen-1); }

// Hat density: the spec ladder (4 below 0.2, 2 below 0.6, 1 above) scaled by the template's own
// base division, so a sparse template stays sparse and a trap template stays fast.
function hatDiv(base,e,feel){ const ladder=e<0.2?4:e<0.6?2:1; let d=Math.round((base||2)*ladder/2);
 if(feel==='double')d=Math.round(d/2); return clamp(d,1,8); }

function expand(preset,meter,energy,seed,opts){
 opts=opts||{};
 const key=meterKey(meter), groups=GROUPS[key]||GROUPS['4/4'], roles=ROLES[key]||ROLES['4/4'];
 const starts=[]; let acc=0; for(let i=0;i<groups.length;i++){ starts.push(acc); acc+=groups[i]; }
 const spb=acc, last=groups.length-1;
 const bars=Math.max(1,preset.bars||1);
 const e=clamp(energy==null?0.6:energy,0,1);
 const vs=0.55+0.45*e;                       // velocity scaling, straight from the spec
 const feel=opts.feel||'straight';
 const rnd=mulberry32((seed|0)^hashId(preset.id));

 const byRole={}; roles.forEach((r,i)=>{ (byRole[r]=byRole[r]||[]).push(i); });
 // Half feel: the 'up' hits go, and the backbeat collapses onto the last group that carries it.
 function groupsFor(role){ let gs=byRole[role]; if(!gs||!gs.length)gs=[last];
  if(feel==='half'){ if(role==='up')return []; if(role==='back')gs=[gs[gs.length-1]]; }
  return gs; }

 // One note per (step, pad); a later write wins, exactly like Studio.addNote.
 const map=new Map();
 const put=(s,n,v)=>{ if(s<0||s>=spb*bars)return; map.set(s+':'+n,{s:s,l:1,n:n,v:clamp(v,0.05,1)}); };
 const dropAt=(s,pads)=>{ for(const n of pads)map.delete(s+':'+n); };
 const openAt=new Set();                     // steps where an open hat sits, so no closed hat doubles it
 const hatN=preset.every?preset.every.n:-1;  // only the hat lane gets out of the open hat's way

 for(let b=0;b<bars;b++){
  const b0=b*spb;

  // --- role hits -----------------------------------------------------------------------------
  for(const role of ['down','up','back']){
   const hits=preset.roles&&preset.roles[role]; if(!hits)continue;
   for(const gi of groupsFor(role)){
    const glen=groups[gi], g0=b0+starts[gi];
    for(const h of hits){
     if(h.bar!=null&&h.bar!==b)continue;
     if(h.minEnergy!=null&&e<h.minEnergy)continue;
     put(g0+scaleAt(h.at,glen),h.n,h.v*vs);
    }
   }
  }

  // --- ghosts: extra detail that only shows up once the section has some energy ---------------
  if(e>=0.4&&preset.ghost){
   for(const g of preset.ghost){
    if(g.bar!=null&&g.bar!==b)continue;
    for(const gi of groupsFor(g.role||'back')){
     const glen=groups[gi], g0=b0+starts[gi];
     put(g0+scaleAt(g.at,glen),g.n,g.v*vs*(0.9+0.2*rnd()));
    }
   }
  }

  // --- open hat: one per group once the energy allows it -------------------------------------
  if(preset.open&&e>=(preset.open.minEnergy||0)){
   for(let gi=0;gi<groups.length;gi++){
    const s=b0+starts[gi]+scaleAt(preset.open.at,groups[gi]);
    put(s,preset.open.n,preset.open.v*vs); openAt.add(s);
   }
  }

  // --- the hat lane ---------------------------------------------------------------------------
  const ev=preset.every;
  if(ev&&e>=(ev.minEnergy||0)){
   const div=hatDiv(ev.div,e,feel);
   for(let gi=0;gi<groups.length;gi++){
    const glen=groups[gi], g0=b0+starts[gi];
    for(let i=0;i<glen;i+=div){
     if(i===0&&ev.skipFirst)continue;                       // house/techno: leave the downbeat to the kick
     const s=g0+i; if(openAt.has(s))continue;               // never stack a closed hat on an open one
     const v=(i===0?ev.v:ev.offV)*vs*(0.93+0.14*rnd());     // seeded shimmer so the lane is not machine-flat
     put(s,ev.n,v);
    }
   }
  }

  // --- rolls in the last group (spec: above 0.85, or wherever the template asks) ---------------
  const rl=preset.roll;
  if(rl&&e>=(rl.minEnergy==null?0.85:rl.minEnergy)){
   const gi=rl.group==null||rl.group<0?last:Math.min(rl.group,last);
   const glen=groups[gi], g0=b0+starts[gi], div=Math.max(1,rl.div||1);
   const count=Math.ceil(glen/div);
   for(let k=0;k<count;k++){ const s=g0+k*div; if(rl.n===hatN&&openAt.has(s))continue;
    put(s,rl.n,(rl.v||0.55)*vs*(0.55+0.45*(count<2?1:k/(count-1)))); }
  }
 }

 // --- the fill, last bar only, steps counted back from the end of that bar --------------------
 if(opts.fill&&preset.fill&&preset.fill.length){
  const f0=(bars-1)*spb;
  for(const f of preset.fill){
   const s=f0+spb-Math.max(1,f.fromEnd|0);
   if(s<f0)continue;
   dropAt(s,[0,1,5,2]);                       // clear the groove's own drums so the fill reads cleanly
   put(s,f.n,f.v*vs);
  }
 }

 let notes=Array.from(map.values());

 // --- backstops ------------------------------------------------------------------------------
 // Every pattern has to speak at step 0 of bar 1 (the solo audit listens exactly there).
 if(!notes.some(x=>x.s===0)){
  const d=preset.roles&&preset.roles.down&&preset.roles.down[0];
  put(0,d?d.n:(preset.every?preset.every.n:0),(d?d.v:0.5)*vs);
  notes=Array.from(map.values());
 }
 // A groove template must land a kick or a snare in every bar, whatever the feel did to it.
 if(!preset.sparse){
  const d=(preset.roles&&preset.roles.down&&preset.roles.down[0])||{at:0,n:0,v:1};
  for(let b=0;b<bars;b++){
   const lo=b*spb, hi=lo+spb;
   if(!notes.some(x=>x.s>=lo&&x.s<hi&&(x.n===0||x.n===1))){ put(lo,d.n===0||d.n===1?d.n:0,(d.v||1)*vs); notes=Array.from(map.values()); }
  }
 }

 notes.sort((a,b)=>a.s-b.s||a.n-b.n);
 return { bars:bars, spb:spb, notes:notes };
}

// =============================================================================================
// The templates. Ten grooves for the Drums kit, ten complements for the Percussion kit.
// Percussion leans on shakers (closed hat), rims, toms and claps, and stays off the main snare.
// =============================================================================================
const list=[
 // ---- Drums ---------------------------------------------------------------------------------
 { id:'drums.dnb', inst:'drums', name:'Rolled break', style:'dnb', minEnergy:0.25, bars:2,
   // Written half-time at 124: the break's snare sits on beat 3, not on 2 and 4.
   roles:{ down:[{at:0,n:0,v:1.0},{at:3,n:0,v:0.7,bar:1}],
           up:[{at:0,n:1,v:1.0},{at:2,n:0,v:0.8}],
           back:[{at:2,n:1,v:0.45}] },
   every:{ n:3, div:2, v:0.5, offV:0.3 },
   open:{ at:2, n:4, v:0.45, minEnergy:0.7 },
   ghost:[{role:'down',at:3,n:1,v:0.35},{role:'back',at:1,n:6,v:0.3},{role:'up',at:3,n:1,v:0.3,bar:1}],
   roll:{ n:1, div:1, v:0.5, minEnergy:0.9 },
   fill:[{fromEnd:6,n:1,v:0.7},{fromEnd:4,n:5,v:0.8},{fromEnd:2,n:5,v:0.85},{fromEnd:1,n:1,v:0.95}] },

 { id:'drums.hiphop', inst:'drums', name:'Boom bap', style:'hiphop', minEnergy:0.1,
   roles:{ down:[{at:0,n:0,v:1.0}], up:[{at:2,n:0,v:0.7}], back:[{at:0,n:1,v:0.95}] },
   every:{ n:3, div:2, v:0.55, offV:0.35 },
   open:{ at:3, n:4, v:0.4, minEnergy:0.75 },
   ghost:[{role:'back',at:3,n:1,v:0.35},{role:'up',at:3,n:6,v:0.3}],
   fill:[{fromEnd:4,n:1,v:0.7},{fromEnd:3,n:1,v:0.5},{fromEnd:2,n:5,v:0.8},{fromEnd:1,n:5,v:0.9}] },

 { id:'drums.house', inst:'drums', name:'Four to the floor', style:'house', minEnergy:0.1,
   // A kick on every group start is what makes this four to the floor in any meter.
   roles:{ down:[{at:0,n:0,v:1.0}], up:[{at:0,n:0,v:1.0}],
           back:[{at:0,n:0,v:1.0},{at:0,n:1,v:0.85},{at:0,n:2,v:0.6}] },
   every:{ n:3, div:2, v:0.5, offV:0.5, skipFirst:true },
   open:{ at:2, n:4, v:0.5, minEnergy:0.6 },
   ghost:[{role:'up',at:2,n:6,v:0.35}],
   fill:[{fromEnd:4,n:2,v:0.7},{fromEnd:3,n:2,v:0.7},{fromEnd:2,n:1,v:0.8},{fromEnd:1,n:1,v:0.9}] },

 { id:'drums.techno', inst:'drums', name:'Driving floor', style:'techno', minEnergy:0.15,
   roles:{ down:[{at:0,n:0,v:1.0}], up:[{at:0,n:0,v:1.0}],
           back:[{at:0,n:0,v:1.0},{at:0,n:2,v:0.55}] },
   every:{ n:3, div:2, v:0.45, offV:0.5, skipFirst:true },
   open:{ at:2, n:4, v:0.45, minEnergy:0.5 },
   ghost:[{role:'up',at:3,n:6,v:0.3},{role:'back',at:3,n:6,v:0.3}],
   roll:{ n:3, div:1, v:0.45, minEnergy:0.85 },
   fill:[{fromEnd:4,n:5,v:0.7},{fromEnd:2,n:5,v:0.8},{fromEnd:1,n:2,v:0.9}] },

 { id:'drums.trap', inst:'drums', name:'Trap knock', style:'trap', minEnergy:0.2,
   roles:{ down:[{at:0,n:0,v:1.0}], up:[{at:0,n:1,v:0.95},{at:3,n:0,v:0.75}], back:[{at:2,n:0,v:0.6}] },
   every:{ n:3, div:1, v:0.5, offV:0.3 },
   open:{ at:3, n:4, v:0.4, minEnergy:0.65 },
   ghost:[{role:'back',at:0,n:6,v:0.3}],
   roll:{ n:3, div:1, v:0.45, minEnergy:0.4 },        // the hat roll is the signature, so it comes in early
   fill:[{fromEnd:4,n:1,v:0.6},{fromEnd:3,n:1,v:0.7},{fromEnd:2,n:1,v:0.8},{fromEnd:1,n:1,v:0.95}] },

 { id:'drums.breakbeat', inst:'drums', name:'Chopped break', style:'breakbeat', minEnergy:0.2, bars:2,
   roles:{ down:[{at:0,n:0,v:1.0},{at:2,n:0,v:0.6,bar:1}],
           up:[{at:2,n:0,v:0.7},{at:0,n:1,v:0.5,bar:1}],
           back:[{at:0,n:1,v:0.95}] },
   every:{ n:3, div:2, v:0.5, offV:0.35 },
   open:{ at:3, n:4, v:0.4, minEnergy:0.6 },
   ghost:[{role:'up',at:1,n:1,v:0.3},{role:'back',at:3,n:1,v:0.35}],
   fill:[{fromEnd:6,n:5,v:0.7},{fromEnd:4,n:1,v:0.75},{fromEnd:2,n:5,v:0.8},{fromEnd:1,n:1,v:0.95}] },

 { id:'drums.halftime', inst:'drums', name:'Wide halftime', style:'halftime', minEnergy:0.15,
   roles:{ down:[{at:0,n:0,v:1.0},{at:3,n:0,v:0.55}], up:[{at:0,n:1,v:1.0}], back:[{at:2,n:6,v:0.35}] },
   every:{ n:3, div:2, v:0.4, offV:0.3 },
   open:{ at:2, n:4, v:0.4, minEnergy:0.7 },
   ghost:[{role:'back',at:1,n:1,v:0.3}],
   fill:[{fromEnd:4,n:5,v:0.7},{fromEnd:2,n:5,v:0.8},{fromEnd:1,n:1,v:0.95}] },

 { id:'drums.dubstep', inst:'drums', name:'Half-time weight', style:'dubstep', minEnergy:0.2,
   // Also written half-time at 124: kick on 1, snare on 3, and a lot of air in between.
   roles:{ down:[{at:0,n:0,v:1.0}], up:[{at:0,n:1,v:1.0}], back:[{at:2,n:0,v:0.7}] },
   every:{ n:3, div:2, v:0.35, offV:0.25 },
   open:{ at:2, n:4, v:0.45, minEnergy:0.6 },
   ghost:[{role:'up',at:3,n:6,v:0.3}],
   fill:[{fromEnd:5,n:1,v:0.6},{fromEnd:3,n:5,v:0.75},{fromEnd:1,n:1,v:0.95}] },

 { id:'drums.ambient', inst:'drums', name:'Distant pulse', style:'ambient', minEnergy:0, sparse:true,
   roles:{ down:[{at:0,n:0,v:0.6}], back:[{at:0,n:6,v:0.35}] },
   every:{ n:3, div:4, v:0.25, offV:0.2, minEnergy:0.4 },
   open:{ at:2, n:4, v:0.25, minEnergy:0.8 },
   ghost:[{role:'back',at:2,n:6,v:0.25}],
   fill:[{fromEnd:2,n:5,v:0.5},{fromEnd:1,n:7,v:0.6}] },

 { id:'drums.abstract', inst:'drums', name:'Odd placements', style:'abstract', minEnergy:0.1,
   // Hits sit off the obvious slots and the hat division is a 3 against the meter's 4.
   roles:{ down:[{at:0,n:0,v:1.0},{at:3,n:6,v:0.4}],
           up:[{at:1,n:1,v:0.6},{at:2,n:5,v:0.5}],
           back:[{at:0,n:2,v:0.7},{at:3,n:0,v:0.5}] },
   every:{ n:3, div:3, v:0.4, offV:0.3 },
   open:{ at:1, n:4, v:0.35, minEnergy:0.7 },
   ghost:[{role:'down',at:2,n:6,v:0.3},{role:'up',at:3,n:6,v:0.3}],
   fill:[{fromEnd:5,n:5,v:0.6},{fromEnd:3,n:6,v:0.7},{fromEnd:2,n:5,v:0.8},{fromEnd:1,n:2,v:0.9}] },

 // ---- Percussion ----------------------------------------------------------------------------
 // The perc kit is tuned up (see the instrument table), so pad 0 reads as a woodblock tick,
 // pad 1 as a timbale crack and pad 5 as a conga. These sit around the drum grooves, never on
 // top of the main snare.
 { id:'perc.dnb', inst:'perc', name:'Break shaker', style:'dnb', minEnergy:0.3, bars:2,
   roles:{ down:[{at:0,n:6,v:0.55}], up:[{at:1,n:6,v:0.45},{at:3,n:5,v:0.45}],
           back:[{at:1,n:1,v:0.4},{at:3,n:6,v:0.4,bar:1}] },
   every:{ n:3, div:1, v:0.4, offV:0.28 },
   open:{ at:3, n:4, v:0.3, minEnergy:0.8 },
   ghost:[{role:'down',at:2,n:5,v:0.3},{role:'back',at:2,n:6,v:0.3}],
   fill:[{fromEnd:4,n:5,v:0.6},{fromEnd:2,n:5,v:0.7},{fromEnd:1,n:2,v:0.8}] },

 { id:'perc.hiphop', inst:'perc', name:'Rim pocket', style:'hiphop', minEnergy:0.2,
   roles:{ down:[{at:2,n:6,v:0.5}], up:[{at:0,n:5,v:0.45},{at:3,n:6,v:0.35}],
           back:[{at:2,n:2,v:0.5}] },
   every:{ n:3, div:2, v:0.4, offV:0.3 },
   open:{ at:3, n:4, v:0.3, minEnergy:0.75 },
   ghost:[{role:'up',at:1,n:6,v:0.3},{role:'back',at:1,n:0,v:0.35}],
   fill:[{fromEnd:3,n:5,v:0.6},{fromEnd:2,n:5,v:0.7},{fromEnd:1,n:2,v:0.8}] },

 { id:'perc.house', inst:'perc', name:'Conga swing', style:'house', minEnergy:0.2,
   // Congas answer the four to the floor on the offbeats; the shaker rides between them.
   roles:{ down:[{at:2,n:5,v:0.55}], up:[{at:2,n:5,v:0.45},{at:0,n:6,v:0.4}],
           back:[{at:2,n:5,v:0.5},{at:3,n:6,v:0.35}] },
   every:{ n:3, div:2, v:0.35, offV:0.35, skipFirst:true },
   open:{ at:1, n:4, v:0.3, minEnergy:0.7 },
   ghost:[{role:'down',at:3,n:6,v:0.3},{role:'up',at:1,n:0,v:0.35}],
   fill:[{fromEnd:4,n:5,v:0.6},{fromEnd:3,n:5,v:0.65},{fromEnd:2,n:5,v:0.7},{fromEnd:1,n:2,v:0.85}] },

 { id:'perc.techno', inst:'perc', name:'Metal ticks', style:'techno', minEnergy:0.25,
   roles:{ down:[{at:1,n:6,v:0.45}], up:[{at:3,n:6,v:0.4},{at:1,n:0,v:0.4}],
           back:[{at:1,n:6,v:0.45},{at:3,n:2,v:0.4}] },
   every:{ n:3, div:1, v:0.3, offV:0.25, skipFirst:true },
   open:{ at:2, n:4, v:0.3, minEnergy:0.65 },
   ghost:[{role:'up',at:2,n:6,v:0.28},{role:'back',at:2,n:6,v:0.28}],
   roll:{ n:6, div:1, v:0.35, minEnergy:0.9 },
   fill:[{fromEnd:3,n:6,v:0.6},{fromEnd:2,n:6,v:0.7},{fromEnd:1,n:5,v:0.8}] },

 { id:'perc.trap', inst:'perc', name:'Tick roll', style:'trap', minEnergy:0.25,
   roles:{ down:[{at:0,n:6,v:0.45}], up:[{at:2,n:2,v:0.45}], back:[{at:1,n:1,v:0.35},{at:3,n:6,v:0.35}] },
   every:{ n:3, div:1, v:0.3, offV:0.22 },
   open:{ at:1, n:4, v:0.28, minEnergy:0.8 },
   ghost:[{role:'down',at:3,n:6,v:0.28},{role:'up',at:1,n:6,v:0.28}],
   roll:{ n:6, div:1, v:0.35, minEnergy:0.5 },
   fill:[{fromEnd:4,n:6,v:0.5},{fromEnd:3,n:6,v:0.6},{fromEnd:2,n:6,v:0.7},{fromEnd:1,n:2,v:0.85}] },

 { id:'perc.breakbeat', inst:'perc', name:'Tambourine break', style:'breakbeat', minEnergy:0.2, bars:2,
   roles:{ down:[{at:2,n:6,v:0.5}], up:[{at:0,n:5,v:0.45},{at:2,n:6,v:0.35,bar:1}],
           back:[{at:2,n:2,v:0.45}] },
   every:{ n:3, div:2, v:0.4, offV:0.32 },
   open:{ at:3, n:4, v:0.32, minEnergy:0.65 },
   ghost:[{role:'up',at:3,n:6,v:0.3},{role:'down',at:1,n:0,v:0.3}],
   fill:[{fromEnd:4,n:5,v:0.6},{fromEnd:2,n:5,v:0.75},{fromEnd:1,n:2,v:0.85}] },

 { id:'perc.halftime', inst:'perc', name:'Wide toms', style:'halftime', minEnergy:0.2,
   roles:{ down:[{at:2,n:5,v:0.6}], up:[{at:2,n:5,v:0.5}], back:[{at:0,n:6,v:0.4},{at:2,n:1,v:0.35}] },
   every:{ n:3, div:4, v:0.3, offV:0.25, minEnergy:0.35 },
   open:{ at:2, n:4, v:0.3, minEnergy:0.75 },
   ghost:[{role:'down',at:1,n:6,v:0.28}],
   fill:[{fromEnd:4,n:5,v:0.6},{fromEnd:2,n:5,v:0.75},{fromEnd:1,n:5,v:0.85}] },

 { id:'perc.dubstep', inst:'perc', name:'Sparse rims', style:'dubstep', minEnergy:0.2,
   roles:{ down:[{at:3,n:6,v:0.45}], up:[{at:2,n:6,v:0.4}], back:[{at:0,n:1,v:0.4},{at:3,n:5,v:0.4}] },
   every:{ n:3, div:4, v:0.28, offV:0.22, minEnergy:0.45 },
   open:{ at:1, n:4, v:0.3, minEnergy:0.7 },
   ghost:[{role:'up',at:0,n:6,v:0.28},{role:'back',at:2,n:6,v:0.28}],
   fill:[{fromEnd:3,n:5,v:0.6},{fromEnd:1,n:2,v:0.8}] },

 { id:'perc.ambient', inst:'perc', name:'Wind shaker', style:'ambient', minEnergy:0, sparse:true,
   roles:{ down:[{at:0,n:3,v:0.3}], back:[{at:2,n:6,v:0.28}] },
   every:{ n:3, div:4, v:0.22, offV:0.18, minEnergy:0.5 },
   open:{ at:2, n:4, v:0.22, minEnergy:0.85 },
   ghost:[{role:'back',at:1,n:5,v:0.25}],
   fill:[{fromEnd:2,n:5,v:0.45},{fromEnd:1,n:6,v:0.5}] },

 { id:'perc.abstract', inst:'perc', name:'Scatter', style:'abstract', minEnergy:0.15,
   roles:{ down:[{at:1,n:6,v:0.5},{at:3,n:5,v:0.4}], up:[{at:0,n:2,v:0.45}],
           back:[{at:2,n:6,v:0.4},{at:3,n:1,v:0.35}] },
   every:{ n:3, div:3, v:0.32, offV:0.26 },
   open:{ at:3, n:4, v:0.3, minEnergy:0.7 },
   ghost:[{role:'down',at:2,n:0,v:0.3},{role:'up',at:2,n:6,v:0.28}],
   fill:[{fromEnd:5,n:6,v:0.55},{fromEnd:3,n:5,v:0.65},{fromEnd:2,n:6,v:0.7},{fromEnd:1,n:2,v:0.85}] }
];

Studio.PRESETS_DRUMS={ GROUPS:GROUPS, ROLES:ROLES, list:list, expand:expand, meterKey:meterKey };
})();
