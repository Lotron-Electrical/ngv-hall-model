// THE LIGHTS MACHINE'S RUNTIME (Lloyd, 2026-09-05): the Lights machine is a machine in the rack
// like any other, but its notes are cues rather than sounds. This file turns those cues plus the
// operator's live presses into the STATE the hall reads (look, palette, level, hit), builds the
// FRAME (where the music is: beat, bar, bands) and posts both to the sim iframe once per rAF.
//
// Two sources fight over the state and the newer one wins: the timeline (cues in the song or the
// looping pattern) and the operator's fingers (a pad press right now). A press is stamped with the
// step it happened on, so a cue further along the timeline takes the state back. That is how a
// desk behaves: you can grab a look mid-song and the next programmed cue still lands.
(function(){
'use strict';
const Studio=window.Studio=window.Studio||{};

const clamp=(x,a,b)=>x<a?a:x>b?b:x;
const LOOKS=()=>(window.NGVShow&&window.NGVShow.LOOK_NAMES)||[];
const PALS=()=>(window.NGVShow&&window.NGVShow.PALETTE_NAMES)||[];

Studio.createLights=function(opts){
 opts=opts||{};
 const getProject=opts.project||(()=>null);
 const getEngine=opts.engine||(()=>null);
 const getIframe=opts.iframe||(()=>null);

 const show=window.NGVShow?window.NGVShow.createShow():null;
 // the frame we hand the hall. Kept as one object and mutated: a new object per rAF is garbage
 // the sim does not need, and postMessage copies it anyway.
 const frame={t:0,bpm:124,beatN:0,beatPhase:0,barPhase:0,bass:0,mid:0,high:0,rms:0,onset:0};
 const state={look:LOOKS()[0]||'pulse', palette:PALS()[0]||'helix', level:1, hitAt:-9};
 const bands={bass:0,mid:0,high:0,rms:0,onset:0};

 // live presses: the value plus the step it was pressed on. stepAt -1 means "older than any cue",
 // which is what a loop wrap resets it to so the programmed cues take the hall back.
 const live={look:null,lookAt:-1, palette:null,palAt:-1, level:null,lvlAt:-1};
 let record=false, quant=1;
 // cached flattens, thrown away by invalidate() on every edit
 let cache=null, cacheMode='';
 // hit bookkeeping: the last step the playhead had crossed, so a hit fires once and not per tick
 let lastStep=-1, lastPosT=0, clock=0, rafN=0, lastMode='', warnedNoShow=false;

 function project(){ return getProject(); }
 function engine(){ return getEngine(); }

 function lightsMachine(){ const p=project(); if(!p)return null;
  for(const m of p.machines)if(m.type==='lights')return m; return null; }

 function flat(){
  const p=project(), eng=engine(); if(!p)return {cues:[],level:[]};
  const mode=(eng&&eng.mode)||'song';
  if(cache&&cacheMode===mode)return cache;
  const mach=lightsMachine();
  const notes=mach?Studio.flatten(p,mode).filter(x=>x.mid===mach.id):[];
  cacheMode=mode; cache={cues:notes, level:Studio.flattenLevel(p,mode)};
  return cache;
 }

 function pos(){ const eng=engine();
  if(eng&&eng.pos){ try{ return eng.pos(); }catch(e){} }
  return {step:0,t:0,bar:0,beat:0,stepInBar:0,loopSteps:16};
 }

 // the state the timeline asks for at this step, then the operator's presses on top
 function resolve(p){
  p=p||pos();
  const step=p.step||0, f=flat(), bpm=(project()&&project().bpm)||124, sec=Studio.stepSeconds(bpm);
  let lookAt=-1, palAt=-1, lvlAt=-1;
  for(const c of f.cues){
   if(c.s>step)break;
   const k=Studio.LIGHT_KEYS[c.n]; if(!k)continue;
   if(k.kind==='look'&&c.s>=lookAt){ lookAt=c.s; state.look=k.val; }
   else if(k.kind==='palette'&&c.s>=palAt){ palAt=c.s; state.palette=k.val; }
  }
  for(const l of f.level){ if(l.s>step)break; if(l.s>=lvlAt){ lvlAt=l.s; state.level=clamp(l.v,0,1); } }
  // the press wins only while no later cue has landed on that kind
  if(live.look!=null&&live.lookAt>=lookAt)state.look=live.look;
  if(live.palette!=null&&live.palAt>=palAt)state.palette=live.palette;
  if(live.level!=null&&live.lvlAt>=lvlAt)state.level=clamp(live.level,0,1);
  { const lm=lightsMachine(); if(lm&&lm.params&&lm.params.level!=null)state.level=clamp(state.level*lm.params.level,0,1); }   // the rack's Level knob scales the lane

  // hits: every hit cue the playhead has just crossed, stamped in the frame's clock so the hall's
  // flash decays from the right moment. A wrap (loop or seek back) rearms without firing the lot.
  if(step<lastStep){ lastStep=-1; live.lookAt=live.palAt=live.lvlAt=-1; }
  if(step>lastStep){
   for(const c of f.cues){
    if(c.s<=lastStep)continue; if(c.s>step)break;
    const k=Studio.LIGHT_KEYS[c.n];
    if(k&&k.kind==='hit')state.hitAt=clock-(step-c.s)*sec;
   }
   lastStep=step;
  }
  return state;
 }

 // one press from a pad, a key or the level slider. With record armed and the transport running it
 // also lands in the pattern, quantised, which is how Caustic records a performance.
 function press(kind,val){
  const p=pos(), step=p.step||0;
  if(kind==='look'){ live.look=val; live.lookAt=step; state.look=val; }
  else if(kind==='palette'){ live.palette=val; live.palAt=step; state.palette=val; }
  else if(kind==='level'){ live.level=clamp(val,0,1); live.lvlAt=step; state.level=live.level; }
  else if(kind==='hit'){ state.hitAt=clock; }
  else return null;

  const eng=engine(), mach=lightsMachine();
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
 function invalidate(){ cache=null; cacheMode=''; }

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

  const step=p.step||0;
  frame.t=clock; frame.bpm=bpm;
  frame.beatN=Math.floor(step/4);
  frame.beatPhase=(step/4)-frame.beatN;
  frame.barPhase=((step%16)+16)%16/16;
  frame.bass=bands.bass; frame.mid=bands.mid; frame.high=bands.high; frame.rms=bands.rms; frame.onset=bands.onset;

  resolve(p);

  // a local copy of the show keeps the studio's own desk preview honest against the hall
  if(show){ Object.assign(show.frame,frame); Object.assign(show.state,state); show.on=true; }
  else if(!warnedNoShow){ warnedNoShow=true; console.warn('lights: show/lightshow.js is not loaded'); }

  const el=getIframe();
  const w=el&&el.contentWindow;
  if(w)try{ w.postMessage({t:'show',frame,state,on:true},'*'); }catch(e){}
 }

 const L={ show, state, frame, resolve, press, setRecord, tick, invalidate,
  get record(){ return record; }, get quantise(){ return quant; },
  // the UI lights its pads from these
  looks:LOOKS(), palettes:PALS() };
 return L;
};
})();
