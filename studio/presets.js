// THE PRESET CORE (Lloyd, 2026-09-05): the part of the jam that turns MUSIC into a studio project.
// Everything an author writes elsewhere is abstract: a drum template that has no meter, a pitched
// pattern written in chord tones and scale degrees, a light pattern written in cues. This file is
// where those become a real `Studio` project: notes at real midi pitches, patterns at the section's
// steps per bar, blocks on the song grid, automation, and one Lights machine per light layer.
//
// STYLE GUIDE, pinned, every preset author obeys it:
//   A minor, root midi 57 (A3). Default chord cycle Am F C G, one chord per bar, 4 bar cycle.
//   Project tempo 124; dnb and dubstep are written half time at 124 (snare on 3), never at 174.
//   Velocities: accent 1.0, normal 0.7, ghost 0.4. Pattern lengths 1, 2 or 4 bars, never 3.
//   One instrument per frequency slot in any stack: sub, low, mid-low, mid, high, top, drums, perc.
//   Every pattern must sound on its own at step 0 of bar 1 (the solo audit listens there).
//   Styles, exactly these ids: dnb hiphop house techno trap breakbeat halftime dubstep ambient abstract.
//
// The four preset fragments (presets.drums.js, presets.pitch.js, presets.lights.js) are written by
// other owners and merged here by `refresh()`. This file works without them: it carries a fallback
// drum expander so a template still renders when presets.drums.js is absent.
(function(){
'use strict';
const Studio=window.Studio=window.Studio||{};

const clamp=(x,a,b)=>x<a?a:x>b?b:x;
const round2=(x)=>Math.round(x*100)/100;

// ---- seeded randomness ------------------------------------------------------------------------
// A share link must replay identically, so nothing here ever calls Math.random. Every choice among
// equals and every humanise jitter comes out of this 32 bit generator.
function rng(seed){ let a=(seed|0)||1; return function(){ a|=0; a=a+0x6D2B79F5|0; let t=Math.imul(a^a>>>15,1|a); t=t+Math.imul(t^t>>>7,61|t)^t; return ((t^t>>>14)>>>0)/4294967296; }; }
Studio.rng=rng;
// a stable integer from a string, so a preset id can seed its own jitter
function hash(s,seed){ let h=(seed|0)||2166136261; for(let i=0;i<String(s).length;i++){ h^=String(s).charCodeAt(i); h=Math.imul(h,16777619); } return h>>>0; }

// ---- harmony ----------------------------------------------------------------------------------
// Chord cycles are named moods, not roman numerals, because the jam's chord control is a five way
// chip. All five start on the tonic so a section change never lands on a stranger.
const NOTE_PC={C:0,D:2,E:4,F:5,G:7,A:9,B:11};
const QUAL={ '':[0,4,7], 'm':[0,3,7], '7':[0,4,7,10], 'm7':[0,3,7,10], 'maj7':[0,4,7,11], 'M7':[0,4,7,11],
 'dim':[0,3,6], 'aug':[0,4,8], 'sus2':[0,2,7], 'sus4':[0,5,7], '6':[0,4,7,9], 'm6':[0,3,7,9], '9':[0,4,7,10,14] };
const SCALES={ minor:[0,2,3,5,7,8,10], major:[0,2,4,5,7,9,11], dorian:[0,2,3,5,7,9,10], phrygian:[0,1,3,5,7,8,10] };
const DEFAULT_KEY={root:57,scale:'minor'};

const harmony=Studio.harmony={};
harmony.CYCLES={
 neutral:['Am','F','C','G'],
 dark:['Am','Dm','Em','Am'],
 lift:['Am','F','G','Em'],
 pull:['Am','F','E7','E7'],
 bright:['Am','D','F','G'],
};
harmony.CYCLE_NAMES=Object.keys(harmony.CYCLES);
harmony.key=(k)=>({ root:(k&&k.root!=null)?k.root:DEFAULT_KEY.root, scale:(k&&k.scale)||DEFAULT_KEY.scale });
// The cycles above are written in A minor. A section in another key shifts every chord by the same
// interval, so the mood of a cycle survives a transpose of the whole song.
harmony.chord=function(name,key){
 const K=harmony.key(key), shift=((K.root-DEFAULT_KEY.root)%12+12)%12;
 const s=String(name||'Am');
 const m=/^([A-Ga-g])([#b]?)(.*)$/.exec(s.trim());
 if(!m)return { root:(9+shift)%12, tones:[(9+shift)%12,(0+shift)%12,(4+shift)%12], quality:'m', name:s };
 let pc=NOTE_PC[m[1].toUpperCase()]; if(m[2]==='#')pc++; else if(m[2]==='b')pc--;
 const q=QUAL[m[3]]!==undefined?m[3]:(QUAL[m[3].toLowerCase()]!==undefined?m[3].toLowerCase():'');
 const iv=QUAL[q]||QUAL[''];
 const root=((pc+shift)%12+12)%12;
 return { root, tones:iv.map(i=>(root+i)%12), quality:q, name:s };
};
harmony.scale=function(key){ const K=harmony.key(key), iv=SCALES[K.scale]||SCALES.minor, r=((K.root%12)+12)%12;
 return iv.map(i=>(r+i)%12); };
// the chord live at a bar of a section, for the render and for the tests
harmony.chordAt=function(bar,chords,cycleBars,key){ const cs=(chords&&chords.length?chords:harmony.CYCLES.neutral);
 const cb=Math.max(1,cycleBars|0||1); return harmony.chord(cs[Math.floor(bar/cb)%cs.length],key); };

// ---- the instruments --------------------------------------------------------------------------
// Ten machine instances with fixed voicing. Each owns exactly one frequency slot, which is how a
// stack stays legible: the ladder never puts two things in the same part of the spectrum.
// Osc codes come from machines.js (A.WAVES = sine, triangle, sawtooth, square), so sine is 0 and
// sawtooth is 2. The spec table's 3 and 1 were written against a different order; these are right.
//
// LEVELS. Each machine has TWO gains: the machine's `vol` in the mixer and the synth's own `vol`
// parameter. Two places to turn a thing down is how a pad ends up 26 dB under the kick, which the
// balance audit measured on the spec's numbers. So the synth `vol` is pinned at 1 everywhere and
// the mixer `vol` below is the only level control, re-fitted twice against the real 100 pattern
// library: nothing in a full stack of eight is now more than 19 dB under the loudest part, and a
// ten part stack peaks under 0.9 rather than clipping the master limiter, and the Percussion was
// lifted a third time because the trap kit is loud enough to push its own percussion 22 dB down.
// That is the one
// deliberate change to the spec's vol column, and the measurements are in test-presets.html.
//
// The Arp also gets a longer tail than the spec's voicing (decay 0.16, release 0.18 rather than
// 0.12 and 0.1). At the spec's numbers the two sparse two bar arps, Glass and Stride, bounced
// under the audit's rms floor: a 0.22 s pluck six times in two bars is not enough signal.
const SLOTS=['sub','low','mid-low','mid','high','top','drums','perc'];
const INSTRUMENTS=[
 { id:'drums', type:'beatbox', name:'Drums', slot:'drums', vol:0.62, send:{reverb:0.05},
   params:{ drive:0.15, vol:1 } },
 { id:'perc', type:'beatbox', name:'Percussion', slot:'perc', vol:0.66, send:{delay:0.15},
   params:{ kickTune:0.8, kickDecay:0.12, snareTone:0.8, snareDecay:0.09, hatDecay:0.03, tomTune:0.7, drive:0.05, vol:1 } },
 { id:'bass', type:'bassline', name:'Bass', slot:'low', vol:0.5, send:{}, register:[33,52],
   params:{ cutoff:0.35, res:0.55, envmod:0.6, decay:0.25, dist:0.15, vol:1 } },
 { id:'sub', type:'subsynth', name:'Sub', slot:'sub', vol:0.58, send:{}, register:[24,45],
   params:{ osc1:0, osc2:0, mix:0, cutoff:0.25, res:0, fenv:0, attack:0.01, decay:0.2, sustain:1, release:0.15, vol:1 } },
 { id:'pad', type:'padsynth', name:'Pad', slot:'mid-low', vol:1, send:{reverb:0.35}, register:[48,72],
   params:{ voices:5, spread:18, width:0.7, cutoff:0.4, attack:0.5, release:1.5, lfoAmt:0.25, vol:1 } },
 { id:'chords', type:'padsynth', name:'Chords', slot:'mid-low', vol:0.9, send:{delay:0.2,reverb:0.15}, register:[52,76],
   params:{ voices:3, spread:10, width:0.4, cutoff:0.55, attack:0.01, release:0.25, vol:1 } },
 { id:'keys', type:'fmsynth', name:'Keys', slot:'mid', vol:0.68, send:{reverb:0.2}, register:[55,79],
   params:{ ratio:2, index:3, idecay:0.3, attack:0.005, decay:0.6, sustain:0.3, release:0.5, vol:1 } },
 { id:'lead', type:'subsynth', name:'Lead', slot:'high', vol:0.72, send:{delay:0.3,reverb:0.2}, register:[64,88],
   params:{ osc1:2, osc2:2, mix:0.5, detune:10, oct2:0, cutoff:0.55, res:0.25, fenv:0.4, fdecay:0.25, attack:0.01, decay:0.3, sustain:0.5, release:0.3, glide:0.05, vol:1 } },
 { id:'arp', type:'subsynth', name:'Arp', slot:'high', vol:0.8, send:{delay:0.35}, register:[67,91],
   params:{ osc1:2, osc2:3, mix:0.4, cutoff:0.6, res:0.3, fenv:0.5, fdecay:0.12, attack:0.002, decay:0.16, sustain:0, release:0.18, vol:1 } },
 { id:'fx', type:'fmsynth', name:'FX', slot:'top', vol:0.6, send:{reverb:0.5}, register:[60,84],
   params:{ ratio:1.5, index:8, idecay:1.5, attack:0.2, decay:2, sustain:0.6, release:1.5, feedback:0.3, vol:1 } },
];
const INST_BY_ID={}; INSTRUMENTS.forEach(i=>INST_BY_ID[i.id]=i);
const INST_IDS=INSTRUMENTS.map(i=>i.id);
// the density ladder's order: what survives when energy is low
const PRIORITY=['sub','drums','pad','perc','bass','chords','keys','lead','arp','fx'];
const STYLES=['dnb','hiphop','house','techno','trap','breakbeat','halftime','dubstep','ambient','abstract'];
const LIGHT_FAMILIES=['base','movement','accent','strobe','texture','colour'];
const PADS={ kick:0, snare:1, clap:2, hat:3, ohat:4, tom:5, rim:6, crash:7 };

// ---- the registry -----------------------------------------------------------------------------
// The four fragment files each publish a flat list. They may load in any order and may be missing
// entirely (the studio loads presets.js on its own), so the merge is lazy and re-runs when a
// fragment appears.
const P=Studio.PRESETS={};
P.SLOTS=SLOTS; P.STYLES=STYLES; P.PRIORITY=PRIORITY; P.LIGHT_FAMILIES=LIGHT_FAMILIES; P.PADS=PADS;
P.instruments=INSTRUMENTS; P.INSTRUMENT_IDS=INST_IDS;
P.instrument=(id)=>INST_BY_ID[id]||null;
P.list=[]; P.lightList=[]; P.byId={};
let sig='';
function sourceSig(){ const s=[]; for(const k of ['PRESETS_DRUMS','PRESETS_PITCH','PRESETS_LIGHTS']){ const m=Studio[k]; s.push(k+':'+(m&&m.list?m.list.length:-1)); } return s.join('|'); }
P.refresh=function(force){
 const now=sourceSig(); if(!force&&now===sig&&P.list.length)return P;
 sig=now; P.list=[]; P.lightList=[]; P.byId={};
 for(const k of ['PRESETS_DRUMS','PRESETS_PITCH']){ const m=Studio[k]; if(m&&m.list)for(const p of m.list){ P.list.push(p); P.byId[p.id]=p; } }
 const L=Studio.PRESETS_LIGHTS; if(L&&L.list)for(const p of L.list){ P.lightList.push(p); P.byId[p.id]=p; }
 return P;
};
P.all=()=>{ P.refresh(); return P.list; };
P.lights=()=>{ P.refresh(); return P.lightList; };
P.get=(id)=>{ P.refresh(); return P.byId[id]||null; };
P.forInst=(inst)=>{ P.refresh(); return P.list.filter(p=>p.inst===inst); };
P.forFamily=(fam)=>{ P.refresh(); return P.lightList.filter(p=>p.family===fam); };
// how far an energy sits outside a pattern's window, for picking the nearest when none fits
const eDist=(p,e)=>!p.energy?0:Math.max(0,p.energy[0]-e,e-p.energy[1]);
const styleHit=(p,style)=>!style?true:Array.isArray(p.style)?p.style.indexOf(style)>=0:p.style===style;
P.styleHit=styleHit;

// ---- the drum fallback expander ---------------------------------------------------------------
// RHYTHM owns `Studio.PRESETS_DRUMS.expand`. This stands in when presets.drums.js is absent so a
// template still renders, and it follows the same energy rules so the two do not drift in feel.
const GROUPS_DEF={'4/4':[4,4,4,4],'3/4':[4,4,4],'5/4':[4,4,4,4,4],'6/8':[6,6],'7/8':[4,4,6],'12/8':[6,6,6,6]};
const ROLES_DEF={'4/4':['down','back','up','back'],'3/4':['down','up','back'],'5/4':['down','up','back','up','back'],
 '6/8':['down','back'],'7/8':['down','up','back'],'12/8':['down','back','up','back']};
function meterKey(meter){ const m=meter||{beats:4,div:4}; return (m.beats||4)+'/'+(m.div||4); }
function groupsFor(meter){ const D=Studio.PRESETS_DRUMS; const G=(D&&D.GROUPS)||GROUPS_DEF; const k=meterKey(meter);
 if(G[k])return G[k].slice();
 const spb=Studio.barSteps(meter), out=[]; let left=spb; while(left>0){ const n=Math.min(4,left); out.push(n); left-=n; } return out; }
function rolesFor(meter){ const k=meterKey(meter); const D=Studio.PRESETS_DRUMS; const R=(D&&D.ROLES)||ROLES_DEF;
 return (R[k]||['down','back','up','back']).slice(); }
P.groupsFor=groupsFor; P.rolesFor=rolesFor;

function expandFallback(preset,meter,energy,seed,opts){
 opts=opts||{};
 const spb=Studio.barSteps(meter), groups=groupsFor(meter), roles=rolesFor(meter);
 const e=clamp(energy==null?0.6:energy,0,1), R=rng(hash(preset.id,seed));
 const vs=0.55+0.45*e, feel=opts.feel||'straight';
 const notes=[], seen={};
 const put=(s,n,v)=>{ if(s<0||s>=spb)return; const k=s+':'+n; const val=clamp(v*vs,0.05,1);
  if(seen[k]!=null){ if(val<=seen[k])return; notes.splice(notes.findIndex(x=>x.s===s&&x.n===n),1); }
  seen[k]=val; notes.push({s,l:1,n,v:round2(val)}); };
 // group starts
 const starts=[]; let at=0; for(const g of groups){ starts.push(at); at+=g; }
 const lastG=groups.length-1;
 for(let g=0;g<groups.length;g++){
  let role=roles[g%roles.length];
  // half time: the 'up' hits go, and the backbeat waits for the last group
  if(feel==='half'){ if(role==='up')continue; if(role==='back'&&g!==lastG)continue;
   if(g===lastG&&roles[g%roles.length]!=='back')role='back'; }
  const hits=(preset.roles&&preset.roles[role])||[];
  for(const h of hits)put(starts[g]+(h.at||0),h.n|0,h.v==null?0.8:h.v);
 }
 // hats: one every `div` steps, density on the energy ladder
 if(preset.every){
  let d=e<0.2?4:e<0.6?2:1;
  if(preset.every.div)d=Math.max(1,Math.round(d*(preset.every.div/2)));
  if(feel==='double')d=Math.max(1,Math.round(d/2));
  if(feel==='half')d=d*2;
  for(let g=0;g<groups.length;g++)for(let i=0;i<groups[g];i+=d){
   const s=starts[g]+i, on=(i===0);
   put(s,preset.every.n|0,on?(preset.every.v==null?0.55:preset.every.v):(preset.every.offV==null?0.35:preset.every.offV));
  }
 }
 if(preset.open&&e>=(preset.open.minEnergy==null?0.6:preset.open.minEnergy)){
  for(let g=0;g<groups.length;g++)put(starts[g]+(preset.open.at||0),preset.open.n|0,preset.open.v==null?0.5:preset.open.v);
 }
 // ghosts from 0.4; the seed decides which of the equals survive at the bottom of that range
 if(e>=0.4&&preset.ghost)for(const gh of preset.ghost){
  const keep=e>=0.65||R()<0.5+((e-0.4)*2);
  if(!keep)continue;
  for(let g=0;g<groups.length;g++)if(roles[g%roles.length]===gh.role)put(starts[g]+(gh.at||0),gh.n|0,gh.v==null?0.4:gh.v);
 }
 // rolls in the last group when it is loud
 if(e>0.85){ const n=(preset.every&&preset.every.n)||PADS.hat;
  for(let i=0;i<groups[lastG];i++)put(starts[lastG]+i,n,0.35+0.3*R()); }
 // the fill replaces the tail of the bar; steps are counted back from the bar end
 if(opts.fill&&preset.fill)for(const f of preset.fill)put(spb-(f.fromEnd|0),f.n|0,f.v==null?0.8:f.v);
 notes.sort((a,b)=>a.s-b.s||a.n-b.n);
 return { bars:1, spb, notes };
}
P.expandDrums=function(preset,meter,energy,seed,opts){
 const D=Studio.PRESETS_DRUMS;
 if(D&&typeof D.expand==='function')return D.expand(preset,meter,energy,seed,opts);
 return expandFallback(preset,meter,energy,seed,opts);
};

// ---- rendering a preset into a pattern --------------------------------------------------------
// ctx = {key, chords, cycleBars, transpose, spb, meter, energy, seed, humanise, feel, fill}
// The result is a NORMAL studio pattern: {bars, spb, notes:[{s,l,n,v}]}, plus `src` for provenance
// which the studio ignores. Nothing downstream needs to know a preset existed.
function foldPitch(pc,lo,hi,oct){
 const mid=Math.round((lo+hi)/2);
 let n=lo+(((pc-lo)%12)+12)%12;                       // lowest pitch at or above lo with that class
 while(n+12<=hi&&Math.abs(n+12-mid)<Math.abs(n-mid))n+=12;   // sit near the middle of the window
 n+=12*(oct||0);
 while(n<lo)n+=12; while(n>hi)n-=12;                  // the register is a hard window
 return n;
}
// how many bars a pitched pattern must be so the chord cycle actually turns inside it
function gcd(a,b){ while(b){ const t=a%b; a=b; b=t; } return a; }
function renderBars(preset,chords,cycleBars){
 const pb=Math.max(1,preset.bars||1), cyc=Math.max(1,(chords&&chords.length||4)*Math.max(1,cycleBars||1));
 const l=pb*cyc/gcd(pb,cyc);
 return Math.min(Studio.MAX_BARS,Math.max(pb,l));
}
P.renderBars=renderBars;

function renderPitched(preset,ctx){
 const key=harmony.key(ctx.key), spb=ctx.spb||Studio.STEPS_PER_BAR;
 const chords=(ctx.chords&&ctx.chords.length?ctx.chords:harmony.CYCLES.neutral);
 const cycleBars=Math.max(1,ctx.cycleBars||preset.cycleBars||1);
 const bars=renderBars(preset,chords,cycleBars);
 const reg=preset.register||(INST_BY_ID[preset.inst]&&INST_BY_ID[preset.inst].register)||[48,72];
 const scale=harmony.scale(key);
 const e=ctx.energy==null?1:clamp(ctx.energy,0,1), vs=0.55+0.45*e;
 const hum=clamp(ctx.humanise==null?0:ctx.humanise,0,1);
 const R=rng(hash(preset.id,ctx.seed||1));
 const tr=ctx.transpose|0;
 const out=[], seen={};
 for(let b=0;b<bars;b++){
  const ch=harmony.chordAt(b,chords,cycleBars,key);
  for(const nt of (preset.notes||[])){
   const inBar=nt.s|0; if(inBar>=spb)continue;                    // an odd meter clips the tail
   const s=b*spb+inBar;
   let pc;
   let oct=nt.oct|0;
   if(nt.ct!=null){ const ci=nt.ct|0;
    if(ci<ch.tones.length)pc=ch.tones[ci];
    else { pc=ch.tones[0]; oct+=1; }                              // no seventh: the octave stands in
   } else { const d=Math.max(1,Math.min(scale.length,nt.deg|0||1)); pc=scale[d-1]; }
   const n=clamp(foldPitch(pc,reg[0],reg[1],oct)+tr,0,127);
   let l=Math.max(1,nt.l||1); l=Math.min(l,spb-inBar);            // never spill past the bar end
   let v=(nt.v==null?0.7:nt.v)*vs;
   if(hum)v*=1+(R()*2-1)*0.15*hum;
   v=clamp(v,0.05,1);
   const k=s+':'+n; if(seen[k]!=null){ if(v<=seen[k])continue; out.splice(out.findIndex(x=>x.s===s&&x.n===n),1); }
   seen[k]=v; out.push({s,l,n,v:round2(v)});
  }
 }
 out.sort((a,b)=>a.s-b.s||a.n-b.n);
 return { bars, spb, notes:out, src:preset.id };
}

function renderDrums(preset,ctx){
 const meter=ctx.meter||{beats:4,div:4};
 const p=P.expandDrums(preset,meter,ctx.energy==null?0.6:ctx.energy,ctx.seed||1,{fill:!!ctx.fill,feel:ctx.feel||'straight'});
 const spb=ctx.spb||p.spb||Studio.barSteps(meter);
 const hum=clamp(ctx.humanise==null?0:ctx.humanise,0,1);
 const R=rng(hash(preset.id+':h',ctx.seed||1));
 const notes=(p.notes||[]).filter(n=>n.s<spb*(p.bars||1)).map(n=>({ s:n.s, l:n.l||1, n:n.n,
  v:round2(clamp(hum?n.v*(1+(R()*2-1)*0.15*hum):n.v,0.05,1)) }));
 return { bars:p.bars||1, spb, notes, src:preset.id };
}

// A light pattern is cues on the same grid. Authors write them on 16 step bars; an odd meter keeps
// the position inside the bar and drops whatever falls past its end.
// Fifteen of the light patterns name a look that lives in looks2.js, and up to two of those may
// never be written. A cue can only be encoded as a note if the look has an index in
// Studio.LIGHT_KEYS, which model.js builds from NGVShow.LOOK_NAMES at load. So a missing look
// falls back to the pattern's own `fallbackLook` (one of the original 12), and the pattern loses
// its flavour rather than its existence.
function lookAvailable(name){
 if(Studio.lightKeyIndex('look',name)>=0)return true;
 const NS=window.NGVShow;
 return !!(NS&&NS.PAINT&&NS.PAINT[name]&&Studio.lightKeyIndex('look',name)>=0);
}
P.lookAvailable=lookAvailable;
function renderLightPattern(preset,ctx){
 const spb=ctx.spb||Studio.STEPS_PER_BAR, bars=Math.max(1,preset.bars||1);
 const n=bars*spb, level=new Array(n).fill(null), notes=[], seen={};
 let swapped=0;
 for(const c of (preset.cues||[])){
  const st=c[0]|0, kind=c[1];
  let val=c[2];
  const b=Math.floor(st/Studio.STEPS_PER_BAR), inBar=st%Studio.STEPS_PER_BAR;
  if(b>=bars||inBar>=spb)continue;
  if(kind==='look'&&!lookAvailable(val)){
   if(preset.fallbackLook&&lookAvailable(preset.fallbackLook)){ val=preset.fallbackLook; swapped++; }
   else continue;
  }
  const idx=Studio.lightKeyIndex(kind,val); if(idx<0)continue;
  const s=b*spb+inBar, k=s+':'+idx; if(seen[k])continue; seen[k]=1;
  notes.push({s,l:1,n:idx,v:1});
 }
 if(preset.level&&preset.level.length){
  for(let b=0;b<bars;b++)for(let i=0;i<spb;i++){ const src=preset.level[b*Studio.STEPS_PER_BAR+i];
   if(src!=null)level[b*spb+i]=clamp(src,0,1); }
 }
 notes.sort((a,b)=>a.s-b.s||a.n-b.n);
 return { bars, spb, notes, level, src:preset.id, swapped };
}

// the one entry point: it works out which kind of preset it was handed
P.render=function(preset,ctx){
 ctx=ctx||{};
 if(!preset)return null;
 if(preset.cues||preset.family)return renderLightPattern(preset,ctx);
 if(preset.roles||preset.every||preset.kind==='beatTemplate')return renderDrums(preset,ctx);
 return renderPitched(preset,ctx);
};

// ---- energy ------------------------------------------------------------------------------------
// One place decides what a section's energy MEANS, so the stack, the song and the jam UI agree.
// The ladder runs over a fixed priority and enforces one instrument per frequency slot, which is
// why a stack never ends up with a pad and a chords part fighting for the same octave.
P.applyEnergy=function(section,jam){
 const e=clamp(section&&section.energy==null?0.6:section.energy,0,1);
 const picksIn=(section&&section.picks)||{};
 const n=Math.round(2+8*e);
 const picks={}, dropped=[], slotTaken={};
 let used=0;
 for(const id of PRIORITY){
  const pid=picksIn[id]; if(!pid)continue;
  const pr=P.get(pid);
  if(!pr){ dropped.push({inst:id,why:'unknown'}); continue; }
  if((pr.minEnergy||0)>e+1e-9){ dropped.push({inst:id,why:'minEnergy'}); continue; }
  const slot=(INST_BY_ID[id]||{}).slot||id;
  if(slotTaken[slot]){ dropped.push({inst:id,why:'slot'}); continue; }
  if(used>=n){ dropped.push({inst:id,why:'density'}); continue; }
  picks[id]=pid; slotTaken[slot]=id; used++;
 }
 // lights: gain rides the energy, and the strobe family is only allowed when it is earned
 const trans=(section&&section.transition)||'none';
 const allowStrobe=e>0.85||trans==='riser'||trans==='fill';
 const layers=[];
 for(const L of ((section&&section.lights)||[])){
  const lp=P.get(L.id); if(!lp)continue;
  if(lp.family==='strobe'&&!allowStrobe)continue;
  // LIGHTS composites a layer at machine.params.level * machine.gain, so the two must MULTIPLY to
  // the layer gain and neither may carry all of it. The static half (the pattern's gain and the
  // user's fader) goes on machine.gain; the energy half rides params.level, the only one of the
  // two that automation can reach, so a section change moves the layer without a rack rebuild.
  const sg=clamp((L.gain==null?1:L.gain)*(lp.gain==null?1:lp.gain),0,1), lvl=round2(0.15+0.85*e);
  layers.push({ id:L.id, preset:lp, sync:L.sync||lp.sync||'grid', family:lp.family||'base',
   staticGain:round2(sg), level:lvl, gain:round2(clamp(sg*lvl,0,1)) });
 }
 return {
  energy:e, density:n, picks, dropped, layers, allowStrobe,
  vel:round2(0.55+0.45*e),                 // velocity scale, applied inside render
  cutoff:round2(0.25+0.65*e),              // filter macro, written as automation
  sendMul:round2((0.35-0.25*e)/0.35),      // more energy, drier: the instrument defaults are scaled
  lightGain:round2(0.15+0.85*e),
  humanise:clamp((jam&&jam.humanise)||0,0,1),
 };
};
const CUTOFF_INSTS=['pad','chords','lead','arp','bass'];
P.CUTOFF_INSTS=CUTOFF_INSTS;

// ---- sections and jams -------------------------------------------------------------------------
P.newSection=function(over){
 const s={ bars:8, energy:0.6, feel:'straight', meter:{beats:4,div:4}, cycle:'neutral', transpose:0,
  transition:'none', cycleBars:1, bpm:null,
  picks:{ drums:null, perc:null, bass:null, sub:null, pad:null, chords:null, keys:null, lead:null, arp:null, fx:null },
  lights:[] };
 return Object.assign(s,over||{});
};
P.newJam=function(over){
 return Object.assign({ name:'jam', bpm:124, swing:0, humanise:0.3, seed:1,
  key:{root:57,scale:'minor'}, sections:[] },over||{});
};
// the energy curve the Arc button writes: build, lift, breathe, climb, land
const ARC=[0.15,0.45,0.9,0.3,0.6,1.0,0.2];
P.ARC=ARC;
P.arc=function(n){ n=n|0; if(n<=0)return []; if(n===1)return [0.6];
 const out=[]; for(let i=0;i<n;i++){ const t=i*(ARC.length-1)/(n-1), i0=Math.floor(t), f=t-i0;
  out.push(round2(ARC[i0]+((ARC[Math.min(ARC.length-1,i0+1)]-ARC[i0])*f))); }
 return out; };

// one tap on a style chip: a full stack that plays, one instrument per slot and three light layers
P.starter=function(style,energy){
 P.refresh();
 const e=energy==null?0.6:clamp(energy,0,1);
 const s=P.newSection({ energy:e });
 const bySlot={};
 for(const id of PRIORITY){
  const I=INST_BY_ID[id]; if(!I)continue;
  if(bySlot[I.slot])continue;
  const cand=P.list.filter(p=>p.inst===id&&(p.minEnergy||0)<=e);
  const hit=cand.filter(p=>styleHit(p,style))[0]||cand.filter(p=>styleHit(p,'house'))[0]||cand[0];
  if(!hit)continue;
  s.picks[id]=hit.id; bySlot[I.slot]=hit.id;
 }
 // three layers that read as one show: a bed, something moving, something hitting. A family whose
 // energy windows all miss falls back to its nearest pattern rather than leaving the row empty,
 // because a hall with no base layer looks broken, not quiet.
 const want=['base','movement','accent'];
 for(const fam of want){
  const fml=P.lightList.filter(p=>p.family===fam); if(!fml.length)continue;
  const inRange=fml.filter(p=>!p.energy||(e>=p.energy[0]&&e<=p.energy[1]));
  const near=fml.slice().sort((a,b)=>eDist(a,e)-eDist(b,e));
  const cand=inRange.length?inRange:near;
  const hit=cand.filter(p=>styleHit(p,style))[0]||cand[0];
  s.lights.push({ id:hit.id, sync:hit.sync||'grid', gain:1 });
 }
 s.style=style||null;
 return s;
};

// ---- building a project -------------------------------------------------------------------------
function machineFor(proj,instId,cache){
 if(cache[instId])return cache[instId];
 const I=INST_BY_ID[instId]; if(!I)return null;
 const m=Studio.newMachine(I.type,I.name);
 Object.assign(m.params,I.params||{});
 m.vol=I.vol==null?0.8:I.vol;
 m.send={ delay:(I.send&&I.send.delay)||0, reverb:(I.send&&I.send.reverb)||0 };
 m.inst=instId; m.slot=I.slot;
 m.patterns={}; m.curPat='';
 proj.machines.push(m); cache[instId]=m; return m;
}
// A light layer becomes a Lights machine. Layers are keyed by family plus sync, because a machine
// carries one sync for the whole song; two sections that sync the same family differently would
// otherwise fight. The compositor caps at six, so extra combinations fold back into their family.
function lightMachineFor(proj,fam,sync,cache,order){
 const key=fam+'|'+sync;
 if(cache[key])return cache[key];
 const famOnly=Object.keys(cache).filter(k=>k.indexOf(fam+'|')===0);
 if(order.n>=6&&famOnly.length)return cache[famOnly[0]];
 const m=Studio.newMachine('lights',fam.charAt(0).toUpperCase()+fam.slice(1)+(sync!=='grid'?' / '+sync:''));
 m.layer=Math.min(5,order.n++);
 m.sync=sync; m.family=fam;
 m.patterns={}; m.curPat='';
 proj.machines.push(m); cache[key]=m; return m;
}
function addPattern(m,pat){
 const names=Studio.PATTERN_NAMES;
 const i=Object.keys(m.patterns).length;
 const name=names[i%names.length]+(i>=names.length?'-'+i:'');
 m.patterns[name]=pat; if(!m.curPat)m.curPat=name;
 return name;
}
// a ramp is pre-expanded here so the engine only ever has to set a value
function rampAutom(list,mid,param,s0,s1,v0,v1,steps){
 const n=Math.max(2,steps||8);
 for(let i=0;i<n;i++){ const f=i/(n-1); list.push({ mid, param, s:Math.round(s0+(s1-s0)*f), v:round2(v0+(v1-v0)*f) }); }
}
P.rampAutom=rampAutom;
// a drop takes the kit and the bassline out; the pad and everything above it hold the section up
const DROP_OUT=['drums','bass'];
P.DROP_OUT=DROP_OUT;
// the last n bars of a pattern, moved to the front, so a 2 bar fill can be placed on its own
function lastBars(p,n){
 if(n>=p.bars)return p;
 const off=(p.bars-n)*p.spb;
 return { bars:n, spb:p.spb, src:p.src,
  notes:p.notes.filter(x=>x.s>=off).map(x=>({s:x.s-off,l:x.l,n:x.n,v:x.v})) };
}
// one bar of a pattern with its final beat emptied: the silence before a downbeat
function gapBarOf(p,barIdx,beat){
 const off=(barIdx%p.bars)*p.spb, cut=p.spb-beat;
 return { bars:1, spb:p.spb, src:p.src,
  notes:p.notes.filter(x=>x.s>=off&&x.s<off+cut).map(x=>({s:x.s-off,l:Math.min(x.l,cut-(x.s-off)),n:x.n,v:x.v})) };
}

// the section context every renderer reads: one object so bass, keys and arp land on the same grid
function sectionCtx(section,jam,plan,idx){
 const key=harmony.key(jam&&jam.key);
 const meter=(section&&section.meter)||{beats:4,div:4};
 return {
  key, meter, spb:Studio.barSteps(meter),
  chords:harmony.CYCLES[(section&&section.cycle)||'neutral']||harmony.CYCLES.neutral,
  cycleBars:Math.max(1,(section&&section.cycleBars)||1),
  transpose:(section&&section.transpose)|0,
  energy:plan.energy, humanise:plan.humanise, feel:(section&&section.feel)||'straight',
  seed:((jam&&jam.seed)||1)+idx*101,
 };
}
P.sectionCtx=sectionCtx;

// THE LIVE STACK: one section, pattern mode, no transitions. The jam rebuilds this on every tile
// tap, so it must be cheap and must never place a block.
P.buildStack=function(section,jam){
 P.refresh();
 jam=jam||P.newJam();
 section=section||P.newSection();
 const plan=P.applyEnergy(section,jam);
 const ctx=sectionCtx(section,jam,plan,0);
 const proj=Studio.newProject((jam.name||'jam')+' stack');
 proj.bpm=jam.bpm||124; proj.swing=clamp(jam.swing||0,0,1);
 // headroom: a full stack of ten hits the master limiter, and a limiter that is always working
 // squashes the transients the drums are made of. 0.8 leaves the peak near 0.9 with ten parts.
 proj.master.vol=0.68;
 proj.song.sections=[]; proj.song.bars=Math.max(1,section.bars||8);
 const cache={};
 for(const id of PRIORITY){
  const pid=plan.picks[id]; if(!pid)continue;
  const pr=P.get(pid); const m=machineFor(proj,id,cache); if(!m||!pr)continue;
  const pat=P.render(pr,Object.assign({},ctx,{fill:false}));
  m.curPat=addPattern(m,pat);
  if(CUTOFF_INSTS.indexOf(id)>=0&&m.params.cutoff!=null)m.params.cutoff=plan.cutoff;
  m.send.delay=round2(m.send.delay*plan.sendMul); m.send.reverb=round2(m.send.reverb*plan.sendMul);
 }
 const lcache={}, order={n:0};
 for(const L of plan.layers){
  const m=lightMachineFor(proj,L.family,L.sync,lcache,order); if(!m)continue;
  const pat=P.render(L.preset,ctx);
  m.curPat=addPattern(m,pat);
  m.gain=L.staticGain; m.params.level=L.level;   // the product is the layer gain; setting both to it squared it
 }
 proj.jam={ mode:'stack', section:Studio.clone(section) };
 return proj;
};

// THE SONG: every section rendered, blocks placed, automation written, transitions applied.
P.buildSong=function(jam){
 P.refresh();
 jam=jam||P.newJam();
 const secs=(jam.sections&&jam.sections.length?jam.sections:[P.newSection()]);
 const proj=Studio.newProject(jam.name||'jam');
 proj.bpm=jam.bpm||124; proj.swing=clamp(jam.swing||0,0,1);
 proj.master.vol=0.68;
 const key=harmony.key(jam.key);
 const autom=proj.song.autom=[];
 proj.song.sections=[];   // newProject has no sections: a jam always has at least one
 const cache={}, lcache={}, order={n:0};
 const sendAcc={};        // sends cannot be automated (they are not machine params), so they are
 const sendCount={};      // set once from the mean energy of the sections an instrument plays in
 const plans=[], ctxs=[], starts=[];

 // 1) the section list first, so the timeline is right before any bar maths happens
 let bar=0;
 secs.forEach((S,i)=>{
  const len=Math.max(1,S.bars||8);
  const plan=P.applyEnergy(S,jam);
  const ctx=sectionCtx(S,jam,plan,i);
  proj.song.sections.push({ bar, len, meter:ctx.meter, bpm:S.bpm||jam.bpm||124, feel:S.feel||'straight',
   key, chords:ctx.chords.slice(), cycleBars:ctx.cycleBars, transpose:ctx.transpose,
   energy:plan.energy, transition:S.transition||'none', seed:ctx.seed });
  plans.push(plan); ctxs.push(ctx); starts.push(bar);
  bar+=len;
 });
 proj.song.bars=Math.max(1,bar);
 // the sections alone fix every bar's step, so the timeline is final before a single block exists
 const tl=Studio.timeline(proj);

 // 2) the parts
 secs.forEach((S,i)=>{
  const plan=plans[i], ctx=ctxs[i], b0=starts[i], len=Math.max(1,S.bars||8);
  const trans=S.transition||'none';
  const gapBar=(trans==='gap'&&len>1)?1:0;                      // the last bar is its own block
  const fillBar=(trans==='fill'&&len>1)?1:0;
  const dropBars=trans==='drop'?(len>=16?8:Math.min(4,len-1)):0;
  for(const id of PRIORITY){
   const pid=plan.picks[id]; if(!pid)continue;
   const pr=P.get(pid); const m=machineFor(proj,id,cache); if(!m||!pr)continue;
   const pat=P.render(pr,Object.assign({},ctx,{fill:false}));
   const name=addPattern(m,pat);
   // drop: the drums and the bass stop early, everything else holds the section up
   let end=len;
   if(dropBars&&DROP_OUT.indexOf(id)>=0)end=Math.max(1,len-dropBars);
   if(fillBar&&id==='drums'&&end>1){
    // a drum template may be two bars, and expand puts the fill on the LAST bar it returns, so
    // the fill block has to be that long or the fill never plays
    const fp=P.render(pr,Object.assign({},ctx,{fill:true}));
    const fb=Math.min(fp.bars,end-1);
    Studio.placeBlock(proj,m.id,b0,name,end-fb);
    Studio.placeBlock(proj,m.id,b0+end-fb,addPattern(m,lastBars(fp,fb)),fb);
   } else if(gapBar&&end>1){
    Studio.placeBlock(proj,m.id,b0,name,end-1);
    // the closing bar is whichever bar of the pattern would have landed there, minus its last beat
    const beat=Math.max(1,Math.round(16/((ctx.meter.div)||4)));
    Studio.placeBlock(proj,m.id,b0+end-1,addPattern(m,gapBarOf(pat,(end-1)%pat.bars,beat)),1);
   } else {
    Studio.placeBlock(proj,m.id,b0,name,end);
   }
   if(CUTOFF_INSTS.indexOf(id)>=0&&m.params.cutoff!=null)autom.push({ mid:m.id, param:'cutoff', s:tl.barStep(b0), v:plan.cutoff });
   sendAcc[id]=(sendAcc[id]||0)+plan.sendMul; sendCount[id]=(sendCount[id]||0)+1;
  }

  // 3) the light layers
  for(const L of plan.layers){
   const m=lightMachineFor(proj,L.family,L.sync,lcache,order); if(!m)continue;
   const pat=P.render(L.preset,ctx);
   const name=addPattern(m,pat);
   Studio.placeBlock(proj,m.id,b0,name,len);
   // the first section that uses a layer fixes machine.gain; a later section whose static gain
   // differs folds that difference into its level, so the product is always the layer's gain
   if(m.gain==null){ m.gain=L.staticGain; m.params.level=L.level; }
   autom.push({ mid:m.id, param:'level', s:tl.barStep(b0), v:round2(clamp(m.gain>0?L.gain/m.gain:L.level,0,1)) });
  }
 });

 // 4) transitions, written against the same timeline
 secs.forEach((S,i)=>{
  const plan=plans[i], ctx=ctxs[i], b0=starts[i], len=Math.max(1,S.bars||8), trans=S.transition||'none';
  const endBar=b0+len;
  if(trans==='fill'){
   // the crash lands on the NEXT downbeat, inside the next section's own drum pattern
   const dm=cache.drums;
   if(dm){
    const nextBlock=Studio.track(proj,dm.id).find(b=>b.bar===endBar);
    if(nextBlock&&dm.patterns[nextBlock.pat]){ Studio.addNote(dm.patterns[nextBlock.pat],{s:0,n:PADS.crash,v:0.9,l:1}); }
    else { const cp={ bars:1, spb:ctx.spb, notes:[{s:0,l:1,n:PADS.crash,v:0.9}] };
     if(endBar<proj.song.bars)Studio.placeBlock(proj,dm.id,endBar,addPattern(dm,cp),1); }
   }
  }
  if(trans==='riser'){
   const fx=machineFor(proj,'fx',cache);
   if(fx){
    const bars=Math.min(2,len), rb=endBar-bars;
    const spb=ctx.spb, note={ bars, spb, notes:[{s:0,l:bars*spb-1,n:clamp(69+ctx.transpose,0,127),v:0.8}] };
    Studio.placeBlock(proj,fx.id,rb,addPattern(fx,note),bars);
    // fmsynth has no cutoff; the mod index is the knob that opens the same way
    const param=(Studio.MACHINE_TYPES[fx.type].params.cutoff?'cutoff':'index');
    const lo=param==='cutoff'?0.2:1, hi=param==='cutoff'?1:16;
    rampAutom(autom,fx.id,param,tl.barStep(rb),tl.barStep(endBar)-1,lo,hi,8);
    for(const k in lcache){ const lm=lcache[k];
     rampAutom(autom,lm.id,'level',tl.barStep(rb),tl.barStep(endBar)-1,0.4,1,8); }
   }
  }
  if(trans==='gap'){
   const beat=Math.max(1,Math.round(16/((ctx.meter.div)||4)));
   const s=tl.barStep(endBar)-beat;
   for(const k in lcache){ const lm=lcache[k];
    autom.push({ mid:lm.id, param:'level', s, v:0 });
    autom.push({ mid:lm.id, param:'level', s:tl.barStep(endBar), v:plan.lightGain }); }
  }
  if(trans==='drop'){
   // the pad is what holds the drop up, so its level is nudged back rather than cut
   const pd=cache.pad;
   if(pd&&pd.params.cutoff!=null){ const db=endBar-(len>=16?8:Math.min(4,len-1));
    autom.push({ mid:pd.id, param:'cutoff', s:tl.barStep(db), v:round2(clamp(plan.cutoff*0.75,0.05,1)) }); }
   for(const k in lcache){ const lm=lcache[k]; const db=endBar-(len>=16?8:Math.min(4,len-1));
    autom.push({ mid:lm.id, param:'level', s:tl.barStep(db), v:round2(clamp(plan.lightGain*0.5,0,1)) }); }
  }
 });

 // 5) sends, once, from the mean of the sections each instrument plays in
 for(const id in cache){
  const m=cache[id], I=INST_BY_ID[id]; if(!I)continue;
  const mul=sendCount[id]?sendAcc[id]/sendCount[id]:1;
  m.send.delay=round2(clamp(((I.send&&I.send.delay)||0)*mul,0,1));
  m.send.reverb=round2(clamp(((I.send&&I.send.reverb)||0)*mul,0,1));
 }
 autom.sort((a,b)=>a.s-b.s);
 proj.song.bars=Math.max(1,bar);   // placeBlock raised it from newProject's default of 16
 proj.jam={ mode:'song', jam:Studio.clone(Object.assign({},jam,{sections:secs})) };
 return proj;
};

// the first thing the jam shows: a house stack across four sections with the arc on it
P.demoJam=function(style){
 P.refresh();
 const j=P.newJam({ name:'jam' });
 const e=P.arc(4);
 const base=P.starter(style||'house',0.6);
 e.forEach((en,i)=>{
  const s=Studio.clone(base);
  s.energy=en; s.bars=8;
  s.cycle=['neutral','lift','pull','neutral'][i%4];
  s.transition=i<e.length-1?(e[i+1]-en>0.2?'riser':'fill'):'none';
  j.sections.push(s);
 });
 return j;
};
})();
