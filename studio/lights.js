// THE LIGHTS MACHINE'S RUNTIME (Lloyd, 2026-09-05): the Lights machine is a machine in the rack
// like any other, but its notes are cues rather than sounds. This file turns those cues plus the
// operator's live presses into the STATE the hall reads (look, palette, level, hit), builds the
// FRAME (where the music is: beat, bar, bands) and posts both to the sim iframe once per rAF.
//
// Two sources fight over the state and the newer one wins: the timeline (cues in the song or the
// looping pattern) and the operator's fingers (a pad press right now). A press is stamped with the
// step it happened on, so a cue further along the timeline takes the state back. That is how a
// desk behaves: you can grab a look mid-song and the next programmed cue still lands.
//
// LAYERS (2026-09-05): the rack may hold up to six Lights machines, one per layer. Each is its own
// look, palette and gain, and each may be SYNCED to another machine: `m.sync = 'grid'` keeps the
// beat grid, `m.sync = <machine id>` makes that machine's notes the layer's triggers, so a chase
// steps on the kicks and a wave launches on the bass notes. The state carries the whole stack;
// layer 0 is mirrored into state.look/palette so anything written for one layer still works.
(function(){
'use strict';
const Studio=window.Studio=window.Studio||{};

const clamp=(x,a,b)=>x<a?a:x>b?b:x;
const LOOKS=()=>(window.NGVShow&&window.NGVShow.LOOK_NAMES)||[];
const PALS=()=>(window.NGVShow&&window.NGVShow.PALETTE_NAMES)||[];
const famOf=(look)=>(window.NGVShow&&window.NGVShow.lookFamily)?window.NGVShow.lookFamily(look):'base';
const MAX_LAYERS=6;

Studio.createLights=function(opts){
 opts=opts||{};
 const getProject=opts.project||(()=>null);
 const getEngine=opts.engine||(()=>null);
 const getIframe=opts.iframe||(()=>null);

 const show=window.NGVShow?window.NGVShow.createShow():null;
 // the frame we hand the hall. Kept as one object and mutated: a new object per rAF is garbage
 // the sim does not need, and postMessage copies it anyway.
 const frame={t:0,bpm:124,beatN:0,beatPhase:0,barPhase:0,bass:0,mid:0,high:0,rms:0,onset:0};
 const state={look:LOOKS()[0]||'pulse', palette:PALS()[0]||'helix', level:1, hitAt:-9, layers:[]};
 const bands={bass:0,mid:0,high:0,rms:0,onset:0};

 // live presses, one set per layer: the value plus the step it was pressed on. stepAt -1 means
 // "older than any cue", which is what a loop wrap resets it to so the programmed cues take over.
 const live=[]; const liveOf=i=>live[i]||(live[i]={look:null,lookAt:-1, palette:null,palAt:-1});
 const liveLevel={level:null,lvlAt:-1};
 let record=false, quant=1;
 // cached flattens and timeline, thrown away by invalidate() on every edit
 let cache=null, cacheMode='', tl=null;
 // hit bookkeeping: the last step the playhead had crossed, so a hit fires once and not per tick
 let lastStep=-1, lastPosT=0, clock=0, rafN=0, lastMode='', warnedNoShow=false;

 function project(){ return getProject(); }
 function engine(){ return getEngine(); }

 // every Lights machine, in layer order, capped at six. The cap is the compositor's: a seventh
 // layer costs a full pass over every pixel and adds nothing a human can see.
 function lightsMachines(){ const p=project(); if(!p)return [];
  const out=p.machines.filter(m=>m.type==='lights');
  out.sort((a,b)=>((a.layer|0)-(b.layer|0))||0);
  return out.slice(0,MAX_LAYERS);
 }
 function lightsMachine(){ return lightsMachines()[0]||null; }

 function timeline(){ const p=project(); if(!p)return null;
  if(!tl&&Studio.timeline)tl=Studio.timeline(p); return tl; }

 // one flatten per mode, sliced per machine, plus the trigger step list of every machine a layer
 // is synced to. All of it dies on invalidate(), which the studio calls on any edit.
 function flat(){
  const p=project(), eng=engine(); if(!p)return {cues:new Map(),level:[],trig:new Map(),notes:[]};
  const mode=(eng&&eng.mode)||'song';
  if(cache&&cacheMode===mode)return cache;
  const notes=Studio.flatten(p,mode);
  const cues=new Map();
  for(const m of lightsMachines())cues.set(m.id,notes.filter(x=>x.mid===m.id));
  cacheMode=mode; cache={cues, level:Studio.flattenLevel(p,mode), trig:new Map(), notes};
  return cache;
 }

 // the steps a synced layer fires on: that machine's flattened note steps, deduped and sorted,
 // plus the length of the pattern they repeat on so the layer's cue cycle can wrap with it.
 function triggers(mid){
  const f=flat(); if(f.trig.has(mid))return f.trig.get(mid);
  const p=project(), eng=engine(), mode=(eng&&eng.mode)||'song';
  const m=p&&p.machines.find(x=>x.id===mid);
  let steps=[], len=0, base=0;
  if(m){
   const seen=new Set();
   for(const x of f.notes){ if(x.mid!==mid)continue; if(seen.has(x.s))continue; seen.add(x.s); steps.push(x.s); }
   steps.sort((a,b)=>a-b);
   if(mode==='pattern'){ const pat=m.patterns[m.curPat]; len=pat?Studio.patternSteps(pat):0; base=0; }
   else { const tr=Studio.track(p,m.id), b=tr[0];   // the first block is where the layer's cycle starts
    const pat=b&&m.patterns[b.pat]; const T=timeline();
    len=pat?Studio.patternSteps(pat):0; base=b?(T?T.barStep(b.bar):b.bar*Studio.STEPS_PER_BAR):0; }
  }
  const out={steps, len:len>0?len:0, base};
  f.trig.set(mid,out);
  return out;
 }

 function pos(){ const eng=engine();
  if(eng&&eng.pos){ try{ return eng.pos(); }catch(e){} }
  return {step:0,t:0,bar:0,beat:0,stepInBar:0,loopSteps:16};
 }

 // one layer's state at this step: its own cues, then the operator's press on top of them
 function resolveLayer(m,idx,step){
  const L=state.layers[idx]||(state.layers[idx]={look:LOOKS()[0]||'pulse', palette:PALS()[0]||'helix',
   gain:1, family:'base', trigN:0, trigPhase:0, cyclePhase:0, sync:'grid'});
  const sync=m.sync||'grid';
  const T=sync!=='grid'?triggers(sync):null;
  // a synced layer reads its cues on the synced pattern's cycle, so an 8-step drum loop repeats the
  // layer's cues every 8 steps instead of letting them run off down the song
  let look=step;
  if(T&&T.len>0&&step>=T.base)look=T.base+((step-T.base)%T.len);
  const cues=flat().cues.get(m.id)||[];
  let lookAt=-1, palAt=-1;
  for(const c of cues){
   if(c.s>look)break;
   const k=Studio.LIGHT_KEYS[c.n]; if(!k)continue;
   if(k.kind==='look'&&c.s>=lookAt){ lookAt=c.s; L.look=k.val; }
   else if(k.kind==='palette'&&c.s>=palAt){ palAt=c.s; L.palette=k.val; }
  }
  const lv=liveOf(idx);
  if(lv.look!=null&&lv.lookAt>=lookAt)L.look=lv.look;
  if(lv.palette!=null&&lv.palAt>=palAt)L.palette=lv.palette;
  // gain is the layer's own Level knob (the builder writes energy into it); the level LANE is the
  // hall master and lives on state.level, so a riser ramps every layer at once
  const g=(m.params&&m.params.level!=null?m.params.level:1)*(m.gain!=null?m.gain:1);
  L.gain=clamp(g,0,1);
  L.family=m.family||famOf(L.look);
  L.sync=sync;

  // where the layer is in its own cycle: triggers if it is synced, the beat grid if it is not
  if(T&&T.steps.length){
   const s=T.steps; let lo=0,hi=s.length; while(lo<hi){ const md=(lo+hi)>>1; if(s[md]<=look)lo=md+1; else hi=md; }
   const i=lo-1;
   if(i<0){ L.trigN=-1; L.trigPhase=1; }
   else { L.trigN=i;
    const next=i+1<s.length?s[i+1]:(T.len>0?T.base+T.len+(s[0]-T.base):s[i]+4);
    const span=Math.max(1e-6,next-s[i]);
    L.trigPhase=clamp((look-s[i])/span,0,1);
   }
   L.cyclePhase=T.len>0?clamp(((look-T.base)%T.len+T.len)%T.len/T.len,0,1):frame.barPhase;
  } else {
   L.trigN=frame.beatN; L.trigPhase=frame.beatPhase; L.cyclePhase=frame.barPhase;
  }
  return L;
 }

 // the state the timeline asks for at this step, then the operator's presses on top
 function resolve(p){
  p=p||pos();
  const step=p.step||0, f=flat();
  const bpm=(project()&&project().bpm)||124;
  const sec=p.stepSec||Studio.stepSeconds(bpm);
  const machs=lightsMachines();
  state.layers.length=machs.length;
  for(let i=0;i<machs.length;i++)resolveLayer(machs[i],i,step);
  // layer 0 mirrored into the flat state, so a v1 painter and the compositor agree
  if(state.layers[0]){ state.look=state.layers[0].look; state.palette=state.layers[0].palette; }

  // the level LANE is the hall master: every Lights machine writes into the same lane, last wins
  let lvlAt=-1; state.level=1;
  for(const l of f.level){ if(l.s>step)break; if(l.s>=lvlAt){ lvlAt=l.s; state.level=clamp(l.v,0,1); } }
  if(liveLevel.level!=null&&liveLevel.lvlAt>=lvlAt)state.level=clamp(liveLevel.level,0,1);

  // hits: every hit cue the playhead has just crossed, stamped in the frame's clock so the hall's
  // flash decays from the right moment. A wrap (loop or seek back) rearms without firing the lot.
  if(step<lastStep){ lastStep=-1; liveLevel.lvlAt=-1; for(const lv of live)if(lv){ lv.lookAt=-1; lv.palAt=-1; } }
  if(step>lastStep){
   for(const m of machs){ for(const c of (f.cues.get(m.id)||[])){
    if(c.s<=lastStep)continue; if(c.s>step)break;
    const k=Studio.LIGHT_KEYS[c.n];
    if(k&&k.kind==='hit')state.hitAt=clock-(step-c.s)*sec;
   } }
   lastStep=step;
  }
  return state;
 }

 // one press from a pad, a key or the level slider, on a chosen layer (0 unless the UI says else).
 // With record armed and the transport running it also lands in that layer's pattern, quantised,
 // which is how Caustic records a performance.
 function press(kind,val,layerIdx){
  const p=pos(), step=p.step||0, idx=Math.max(0,Math.min(MAX_LAYERS-1,layerIdx|0));
  const lv=liveOf(idx);
  if(kind==='look'){ lv.look=val; lv.lookAt=step; if(state.layers[idx])state.layers[idx].look=val; if(idx===0)state.look=val; }
  else if(kind==='palette'){ lv.palette=val; lv.palAt=step; if(state.layers[idx])state.layers[idx].palette=val; if(idx===0)state.palette=val; }
  else if(kind==='level'){ liveLevel.level=clamp(val,0,1); liveLevel.lvlAt=step; state.level=liveLevel.level; }
  else if(kind==='hit'){ state.hitAt=clock; }
  else return null;

  const eng=engine(), mach=lightsMachines()[idx]||lightsMachine();
  if(!record||!eng||!eng.playing||!mach)return null;
  const pat=mach.patterns[mach.curPat]; if(!pat)return null;
  const steps=Studio.patternSteps(pat), q=quant>0?quant:1;
  let s=Math.round(step/q)*q; s=((s%steps)+steps)%steps;
  if(kind==='level'){ if(!pat.level)pat.level=new Array(steps).fill(null); pat.level[s]=clamp(val,0,1); invalidate(); return {s,level:clamp(val,0,1)}; }
  const n=Studio.lightKeyIndex(kind,val); if(n<0)return null;
  const note=Studio.addNote(pat,{s,n,v:1,l:1});
  invalidate();
  return note;
 }

 function setRecord(on,quantiseSteps){ record=!!on; quant=quantiseSteps>0?(quantiseSteps|0):1; }
 function invalidate(){ cache=null; cacheMode=''; tl=null; }

 // once per rAF from the UI. Stopped, the hall still needs frames or it paints nothing, so we keep
 // posting at a quarter of the rate with the clock frozen: the last state simply holds.
 function tick(){
  const eng=engine(), playing=!!(eng&&eng.playing);
  rafN++;
  if(!playing&&(rafN&3)!==0)return;
  const p=pos(), proj=project(), bpm=(proj&&proj.bpm)||124;

  // a monotonic clock: eng.pos().t restarts on a pattern loop and the looks read t as time, not
  // as position, so a jump back would stutter the sparkle and the helix
  const t=p.t||0;
  if(playing)clock+=t>=lastPosT?Math.min(t-lastPosT,0.25):Studio.stepSeconds(bpm);
  lastPosT=t;
  if(eng&&eng.mode&&eng.mode!==lastMode){ lastMode=eng.mode; invalidate(); }

  if(playing&&eng&&eng.analyser&&eng.analyser.read){ eng.analyser.read(bands); }
  else { bands.bass*=0.85; bands.mid*=0.85; bands.high*=0.85; bands.rms*=0.85; bands.onset=0; }

  const step=p.step||0, mode=(eng&&eng.mode)||'song';
  frame.t=clock; frame.bpm=bpm;
  // beat and bar come from the timeline, so a 7/8 section beats in sevens. The engine already
  // hands them over when it can; pattern mode stays a plain 16-step 4/4 bar at the project tempo.
  if(p.beatN!=null&&p.beatPhase!=null&&p.barPhase!=null){
   frame.beatN=p.beatN|0; frame.beatPhase=p.beatPhase; frame.barPhase=p.barPhase;
  } else {
   const T=mode==='pattern'?null:timeline();
   if(T&&T.at){ const A=T.at(step); frame.beatN=A.beatN|0; frame.beatPhase=A.beatPhase; frame.barPhase=A.barPhase; frame.bpm=A.bpm||bpm; }
   else { frame.beatN=Math.floor(step/4); frame.beatPhase=(step/4)-frame.beatN; frame.barPhase=((step%16)+16)%16/16; }
  }
  frame.bass=bands.bass; frame.mid=bands.mid; frame.high=bands.high; frame.rms=bands.rms; frame.onset=bands.onset;

  resolve(p);

  // a local copy of the show keeps the studio's own desk preview honest against the hall
  if(show){ Object.assign(show.frame,frame); Object.assign(show.state,state); show.on=true; }
  else if(!warnedNoShow){ warnedNoShow=true; console.warn('lights: show/lightshow.js is not loaded'); }

  const el=getIframe();
  const w=el&&el.contentWindow;
  if(w)try{ w.postMessage({t:'show',frame,state,on:true},'*'); }catch(e){}
 }

 const L={ show, state, frame, resolve, press, setRecord, tick, invalidate, lightsMachines,
  get record(){ return record; }, get quantise(){ return quant; },
  // the UI lights its pads from these
  looks:LOOKS(), palettes:PALS(), maxLayers:MAX_LAYERS };
 return L;
};
})();
