// THE STUDIO'S UI (Lloyd, 2026-09-05): the Caustic 3 surface. Five views over one project - RACK,
// PATTERN, SONG, MIXER, FX - with the transport always on top, the play strip always on the bottom
// and the hall sim docked on the right so the lights are visible while the music is being made.
//
// This file owns no sound and no light maths. It edits the model, tells the engine the model moved
// (eng.invalidate) and asks the lights runtime for a frame once per rAF. If the engine or the
// lights runtime is missing (they are written in parallel) it falls back to the stub so every view
// still draws and the playhead still runs.
(function(){
'use strict';
const Studio=window.Studio;
if(!Studio){ document.body.innerHTML='<p style="padding:20px;color:#d8433c">studio/model.js did not load.</p>'; return; }
const SPB=Studio.STEPS_PER_BAR, MT=Studio.MACHINE_TYPES, FXT=Studio.FX_TYPES;
const NGV=window.NGVShow||{LOOK_NAMES:[],PALETTE_NAMES:[],PALETTES:{},LOOKS:[]};

/* ------------------------------------------------------------------ small helpers */
const $=(id)=>document.getElementById(id);
const el=(tag,cls,txt)=>{ const e=document.createElement(tag); if(cls)e.className=cls; if(txt!=null)e.textContent=txt; return e; };
const clamp=(x,a,b)=>x<a?a:x>b?b:x;
const fix=(v,d)=>Number(v).toFixed(d==null?2:d);
// a palette's A colour as CSS, for swatches and pads (hsv, the same numbers lightshow.js paints with)
function hsvCss(c,mul){ const v=(c.v==null?1:c.v)*(mul==null?1:mul);
 return 'hsl('+c.h+','+Math.round((c.s==null?1:c.s)*100)+'%,'+Math.round((1-(c.s==null?1:c.s)/2)*v*100)+'%)'; }
function palCss(name){ const p=NGV.PALETTES[name]; if(!p)return '#333';
 return 'linear-gradient(120deg,'+hsvCss(p.A)+' 0%,'+hsvCss(p.A)+' 45%,'+hsvCss(p.B)+' 100%)'; }
function palSolid(name){ const p=NGV.PALETTES[name]; return p?hsvCss(p.A):'#555'; }
const NOTE_NAMES=['C','C#','D','D#','E','F','F#','G','G#','A','A#','B'];
const isBlack=(n)=>[1,3,6,8,10].indexOf(((n%12)+12)%12)>=0;
const noteName=(n)=>NOTE_NAMES[((n%12)+12)%12]+(Math.floor(n/12)-1);

let msgTimer=0;
function say(text,hold){ const m=$('msg'); m.textContent=text||''; clearTimeout(msgTimer);
 if(text)msgTimer=setTimeout(()=>{ m.textContent=''; },hold||3200); }

/* ------------------------------------------------------------------ state */
const LSKEY='ngv.studio.project';
let proj=loadStored()||Studio.demoProject();
let view='rack';
let selId=(proj.machines[0]||{}).id||null;
let record=false, quant=1, octave=0, velocity=0.8;
let clipboard=null, selBlock=null, selNote=null;
const flash={};              // machineId+':'+n -> the time the key lit, for the on-screen flashes
const held={};               // keyboard note -> {n, startStep} while a key is down (record needs the length)

function loadStored(){ try{ const s=localStorage.getItem(LSKEY); if(!s)return null; const p=JSON.parse(s);
  return (p&&p.machines)?p:null; }catch(e){ return null; } }
let saveTimer=0;
function autosave(){ clearTimeout(saveTimer); saveTimer=setTimeout(()=>{
  try{ localStorage.setItem(LSKEY,JSON.stringify(proj)); }catch(e){} },500); }

const machine=(id)=>proj.machines.find(m=>m.id===id)||null;
const sel=()=>machine(selId)||proj.machines[0]||null;
const curPat=()=>{ const m=sel(); return m?m.patterns[m.curPat]:null; };
const kindOf=(m)=>m?MT[m.type].kind:'synth';

// every edit lands here: the engine and the lights runtime re-read the project, then we save
function commit(){ try{ eng.invalidate&&eng.invalidate(); }catch(e){} try{ L.invalidate&&L.invalidate(); }catch(e){} autosave(); }

/* ------------------------------------------------------------------ engine and lights */
function nullEngine(){ // last resort: engine.js absent and engine-stub.js not loaded
 const bands={bass:0,mid:0,high:0,rms:0,onset:0};
 return { ac:null, playing:false, mode:'pattern', loop:true, master:null, stub:true,
  analyser:{read(o){ for(const k in bands)o[k]=bands[k]; return o; }},
  init(){}, rebuild(){}, invalidate(){}, play(){}, pause(){}, stop(){}, seek(){},
  noteOn(){}, noteOff(){}, setParam(){}, setMixer(){}, setFx(){},
  pos(){ return {step:0,t:0,bar:0,beat:0,stepInBar:0,loopSteps:SPB}; },
  render(){ return Promise.reject(new Error('no engine')); } };
}
const makeEngine=Studio.createEngine||Studio.createEngineStub||nullEngine;
const eng=makeEngine({ project:()=>proj, onNote:(mid,n,v,time,on)=>{ if(on)flash[mid+':'+n]=performance.now(); } });
eng.loop=true;
const L=Studio.createLights?Studio.createLights({project:()=>proj,engine:()=>eng,iframe:()=>$('sim')})
  :(Studio.createLightsStub?Studio.createLightsStub():{state:{look:'pulse',palette:'helix',level:1,hitAt:-9},stub:true,
    press(k,v){ if(k==='hit')this.state.hitAt=performance.now()/1000; else this.state[k]=v; return null; },
    resolve(){}, invalidate(){}, tick(){}, setRecord(){}});

/* ------------------------------------------------------------------ knob widget */
// a knob is a vertical drag: up raises, Shift is fine, double-click is the default. It draws the
// travel as an arc so the value is readable at a glance without reading the number.
function knob(spec){
 const wrap=el('div','knobwrap');
 const k=el('div','knob'); k.tabIndex=0; k.setAttribute('role','slider');
 k.setAttribute('aria-label',spec.name); k.appendChild(el('span','needle'));
 const lbl=el('div','klbl',spec.name); lbl.title=spec.name;
 const val=el('div','kval');
 wrap.appendChild(k); wrap.appendChild(lbl); wrap.appendChild(val);
 const span=spec.max-spec.min, dp=spec.step&&spec.step>=1?0:(span>20?1:2);
 function paint(){ const v=spec.get(); const p=span?clamp((v-spec.min)/span,0,1):0;
  k.style.setProperty('--pct',p); k.setAttribute('aria-valuenow',fix(v,dp));
  val.textContent=(spec.fmt?spec.fmt(v):fix(v,dp))+(spec.unit||''); }
 function set(v){ if(spec.step)v=Math.round(v/spec.step)*spec.step; spec.set(clamp(v,spec.min,spec.max)); paint(); }
 k.addEventListener('mousedown',(e)=>{ e.preventDefault(); k.focus();
  const y0=e.clientY, v0=spec.get();
  const mv=(ev)=>{ const f=ev.shiftKey?0.25:1; set(v0+(y0-ev.clientY)/140*span*f); };
  const up=()=>{ document.removeEventListener('mousemove',mv); document.removeEventListener('mouseup',up); };
  document.addEventListener('mousemove',mv); document.addEventListener('mouseup',up); });
 k.addEventListener('dblclick',()=>{ if(spec.def!=null)set(spec.def); });
 k.addEventListener('wheel',(e)=>{ e.preventDefault(); set(spec.get()+(e.deltaY<0?1:-1)*span/60); },{passive:false});
 k.addEventListener('keydown',(e)=>{ const st=span/50;
  if(e.key==='ArrowUp'||e.key==='ArrowRight'){ e.preventDefault(); set(spec.get()+st); }
  else if(e.key==='ArrowDown'||e.key==='ArrowLeft'){ e.preventDefault(); set(spec.get()-st); } });
 paint(); wrap.repaint=paint; return wrap;
}
// a parameter counts as whole-numbered when its whole table is integers and its default is not the
// top of the range (that pattern is a 0..1 amount, like the Lights level, not a switch position)
function intParam(p){ return Number.isInteger(p.min)&&Number.isInteger(p.max)&&Number.isInteger(p.def)&&
 (p.max-p.min>=2||p.def===p.min); }
function paramKnobs(table,params,onChange){
 const box=el('div','knobs');
 for(const key in table){ const p=table[key];
  box.appendChild(knob({name:p.name,min:p.min,max:p.max,def:p.def,unit:p.unit?' '+p.unit:'',
   step:intParam(p)?1:0,
   get:()=>params[key]==null?p.def:params[key], set:(v)=>{ params[key]=v; onChange&&onChange(key,v); }})); }
 return box;
}

/* ------------------------------------------------------------------ vertical fader */
function fader(spec){
 const f=el('div','fader'); f.tabIndex=0; f.setAttribute('role','slider'); f.setAttribute('aria-label',spec.name);
 const fill=el('div','fill'), cap=el('div','cap'); f.appendChild(fill); f.appendChild(cap);
 function paint(){ const p=clamp((spec.get()-spec.min)/(spec.max-spec.min),0,1);
  fill.style.height=(p*100)+'%'; cap.style.bottom=(p*100)+'%'; f.setAttribute('aria-valuenow',fix(spec.get())); }
 function set(v){ spec.set(clamp(v,spec.min,spec.max)); paint(); spec.after&&spec.after(); }
 function fromY(cy){ const r=f.getBoundingClientRect(); return spec.min+(1-clamp((cy-r.top)/r.height,0,1))*(spec.max-spec.min); }
 f.addEventListener('mousedown',(e)=>{ e.preventDefault(); f.focus(); set(fromY(e.clientY));
  const mv=(ev)=>set(fromY(ev.clientY));
  const up=()=>{ document.removeEventListener('mousemove',mv); document.removeEventListener('mouseup',up); };
  document.addEventListener('mousemove',mv); document.addEventListener('mouseup',up); });
 f.addEventListener('keydown',(e)=>{ const st=(spec.max-spec.min)/40;
  if(e.key==='ArrowUp'){ e.preventDefault(); set(spec.get()+st); } else if(e.key==='ArrowDown'){ e.preventDefault(); set(spec.get()-st); } });
 paint(); return f;
}

/* ------------------------------------------------------------------ RACK view */
function renderRack(){
 const box=$('racklist'); box.textContent='';
 proj.machines.forEach((m,i)=>{
  const T=MT[m.type];
  const card=el('div','rackcard'+(m.id===selId?' on':''));
  const hd=el('div','rackhd');
  const badge=el('span','badge',T.name); badge.style.background=T.color; hd.appendChild(badge);
  const nm=el('input'); nm.type='text'; nm.value=m.name; nm.spellcheck=false; nm.title='Machine name';
  nm.addEventListener('input',()=>{ m.name=nm.value; commit(); renderStripTabs(); });
  hd.appendChild(nm);
  hd.appendChild(el('span','sp'));
  const mkBtn=(txt,title,fn,pressed)=>{ const b=el('button',null,txt); b.title=title;
   if(pressed!=null)b.setAttribute('aria-pressed',pressed?'true':'false');
   b.addEventListener('click',fn); hd.appendChild(b); return b; };
  mkBtn('Edit','Select this machine and open its pattern',()=>{ selId=m.id; setView('pattern'); renderAll(); });
  mkBtn('M','Mute',()=>{ m.mute=!m.mute; eng.setMixer&&eng.setMixer(m.id); commit(); renderRack(); renderMixer(); },m.mute);
  mkBtn('S','Solo',()=>{ m.solo=!m.solo; eng.setMixer&&eng.setMixer(m.id); commit(); renderRack(); renderMixer(); },m.solo);
  mkBtn('Up','Move up',()=>{ if(i>0){ proj.machines.splice(i-1,0,proj.machines.splice(i,1)[0]); commit(); renderAll(); } });
  mkBtn('Dn','Move down',()=>{ if(i<proj.machines.length-1){ proj.machines.splice(i+1,0,proj.machines.splice(i,1)[0]); commit(); renderAll(); } });
  mkBtn('Remove','Remove this machine',()=>{ if(!confirm('Remove '+m.name+'?'))return;
   proj.machines.splice(i,1); delete proj.song.tracks[m.id]; if(selId===m.id)selId=(proj.machines[0]||{}).id||null;
   eng.rebuild&&eng.rebuild(); commit(); renderAll(); });
  card.appendChild(hd);
  const body=el('div','rackbody');
  body.appendChild(paramKnobs(T.params,m.params,(key,v)=>{ eng.setParam&&eng.setParam(m.id,key,v); commit(); }));
  card.appendChild(body);
  card.addEventListener('mousedown',()=>{ if(selId!==m.id){ selId=m.id; renderRack(); renderStripTabs(); renderStrip(); } });
  box.appendChild(card);
 });
 if(!proj.machines.length)box.appendChild(el('p','muted','The rack is empty. Add a machine below.'));
 const add=$('addbtns'); add.textContent='';
 for(const type of Studio.MACHINE_ORDER){ const b=el('button',null,MT[type].name);
  b.addEventListener('click',()=>{ const m=Studio.newMachine(type); proj.machines.push(m); selId=m.id;
   eng.rebuild&&eng.rebuild(); commit(); renderAll(); });
  add.appendChild(b); }
}

/* ------------------------------------------------------------------ PATTERN view */
const STEPW=22;
let gridEls=null;    // kept so the playhead can move without a full re-render

function rowsFor(m){
 const kind=kindOf(m);
 if(kind==='drum')return MT[m.type].pads.map((p,i)=>({n:i,label:p})).reverse();
 if(kind==='lights')return Studio.LIGHT_KEYS.map((k,i)=>({n:i,label:k.kind==='hit'?'HIT':k.val,
   swatch:k.kind==='palette'?palSolid(k.val):null, band:k.kind==='palette'?'#151318':(k.kind==='hit'?'#1d1418':null)}));   // looks at the top, in pad order: they are the lanes that matter and a short screen showed only the hit and the palettes (integration, 2026-09-05)
 const out=[]; for(let n=96;n>=24;n--)out.push({n,label:noteName(n),black:isBlack(n),c:(n%12===0)});
 return out;
}
const rowHFor=(kind)=>kind==='drum'?26:(kind==='lights'?18:14);

function renderPattern(){
 const wrap=$('patwrap'); const m=sel();
 const keep=gridEls?{l:gridEls.scroll.scrollLeft,t:gridEls.scroll.scrollTop,id:gridEls.mid}:null;
 wrap.textContent=''; gridEls=null;
 // header controls
 const badge=$('patmach'); const bank=$('bank'); bank.textContent='';
 if(!m){ badge.textContent='-'; badge.style.background='#333'; wrap.appendChild(el('p','muted','Add a machine in the RACK view first.')); return; }
 badge.textContent=m.name+' - '+MT[m.type].name; badge.style.background=MT[m.type].color;
 for(const name of Studio.PATTERN_NAMES){ const p=m.patterns[name];
  const b=el('button',(p&&p.notes.length?'has':''),name);
  b.setAttribute('aria-pressed',m.curPat===name?'true':'false'); b.title='Pattern '+name+(p?' ('+p.bars+' bar'+(p.bars>1?'s':'')+', '+p.notes.length+' notes)':' (empty)');
  b.addEventListener('click',()=>{ if(!m.patterns[name])m.patterns[name]=Studio.newPattern(m.type,1);
   m.curPat=name; commit(); renderPattern(); renderSong(); });
  bank.appendChild(b); }
 const pat=m.patterns[m.curPat]; $('bars').value=String(pat.bars);
 const kind=kindOf(m), rows=rowsFor(m), ROWH=rowHFor(kind), steps=Studio.patternSteps(pat);
 const W=steps*STEPW, H=rows.length*ROWH;
 $('pathint').textContent=kind==='synth'?'Click adds a note, drag its right edge to lengthen, click it again or right-click to remove, Shift-drag sets velocity.'
  :(kind==='lights'?'Click a lane to stamp a cue. The level lane below is drawn across with the mouse.':'Click a pad step to toggle it. Shift-drag a hit sets its velocity.');

 // top ruler
 const top=el('div','gridtop'); top.appendChild(el('div','corner'));
 const ruler=el('div','ruler'); const rin=el('div','rin'); rin.style.width=W+'px';
 for(let s=0;s<steps;s+=4){ const b=el('div','bl'+(s%SPB===0?' bar':'')); b.style.left=(s*STEPW)+'px';
  if(s%SPB===0)b.textContent=String(s/SPB+1); rin.appendChild(b); }
 ruler.appendChild(rin); top.appendChild(ruler); wrap.appendChild(top);

 // labels + scrolling grid
 const mid=el('div','gridmid');
 const lbls=el('div','rowlbls'); const lin=el('div','rin'); lin.style.height=H+'px';
 rows.forEach((r,i)=>{ const d=el('div','rowlbl'+(r.black?' black':'')+(r.c?' c':''));
  d.style.top=(i*ROWH)+'px'; d.style.height=ROWH+'px';
  if(r.swatch){ const sw=el('span','swatch'); sw.style.background=r.swatch; d.appendChild(sw); }
  d.appendChild(document.createTextNode(r.label)); d.title=r.label; lin.appendChild(d); });
 lbls.appendChild(lin); mid.appendChild(lbls);

 const scroll=el('div','gridscroll'); const gin=el('div','gridin');
 gin.style.width=W+'px'; gin.style.height=H+'px';
 const bg=el('div','gridbg');
 bg.style.backgroundImage=
  'repeating-linear-gradient(180deg,transparent 0 '+(ROWH-1)+'px,#1b1e24 '+(ROWH-1)+'px '+ROWH+'px),'+
  'repeating-linear-gradient(90deg,#22262c 0 1px,transparent 1px '+(STEPW*SPB)+'px),'+
  'repeating-linear-gradient(90deg,#191c21 0 1px,transparent 1px '+(STEPW*4)+'px),'+
  'repeating-linear-gradient(90deg,#141619 0 1px,transparent 1px '+STEPW+'px)';
 gin.appendChild(bg);
 rows.forEach((r,i)=>{ const c=r.black?'#131519':r.band; if(!c)return;
  const b=el('div','rowband'); b.style.top=(i*ROWH)+'px'; b.style.height=ROWH+'px'; b.style.background=c; gin.appendChild(b); });
 const notesLayer=el('div'); notesLayer.style.position='absolute'; notesLayer.style.inset='0'; gin.appendChild(notesLayer);
 const head=el('div','playhead'); head.style.left='0'; gin.appendChild(head);
 scroll.appendChild(gin); mid.appendChild(scroll); wrap.appendChild(mid);

 // the lane under the grid: velocity for notes, level for the Lights machine
 const lane=el('div','lanewrap'); const lcor=el('div','corner',kind==='lights'?'Level':'Velocity');
 lane.appendChild(lcor);
 const lscroll=el('div','lanescroll'); const lanein=el('div','lanein'); lanein.style.width=W+'px';
 lscroll.appendChild(lanein); lane.appendChild(lscroll); wrap.appendChild(lane);

 const rowIndex=(n)=>rows.findIndex(r=>r.n===n);
 function drawNotes(){
  notesLayer.textContent='';
  for(const q of pat.notes){ const i=rowIndex(q.n); if(i<0)continue;
   const d=el('div','note'+(selNote===q?' sel':'')); d.style.left=(q.s*STEPW)+'px'; d.style.top=(i*ROWH)+'px';
   d.style.width=Math.max(4,q.l*STEPW-1)+'px'; d.style.height=(ROWH-1)+'px';
   const k=Studio.LIGHT_KEYS[q.n];
   d.style.background=kind==='lights'?(k&&k.kind==='palette'?palSolid(k.val):MT[m.type].color):MT[m.type].color;
   const v=el('div','vbar'); v.style.width=Math.round(clamp(q.v,0,1)*100)+'%'; d.appendChild(v);
   d.title=(kind==='synth'?noteName(q.n):(rows[i].label))+'  step '+(q.s+1)+'  vel '+fix(q.v);
   notesLayer.appendChild(d); }
 }
 function drawLane(){
  lanein.textContent='';
  for(let s=0;s<=steps;s+=4){ const t=el('div','lanetick'+(s%SPB===0?' bar':'')); t.style.left=(s*STEPW)+'px'; lanein.appendChild(t); }
  if(kind==='lights'){ const lv=pat.level||[];
   for(let s=0;s<steps;s++){ const v=lv[s]; if(v==null)continue;
    const b=el('div','lanebar'); b.style.left=(s*STEPW+1)+'px'; b.style.width=(STEPW-2)+'px';
    b.style.height=Math.max(2,clamp(v,0,1)*100)+'%'; lanein.appendChild(b); } }
  else { const byStep={}; for(const q of pat.notes)byStep[q.s]=Math.max(byStep[q.s]||0,q.v);
   for(const s in byStep){ const b=el('div','lanebar'); b.style.left=(s*STEPW+1)+'px'; b.style.width=(STEPW-2)+'px';
    b.style.background='var(--accent)'; b.style.height=Math.max(3,byStep[s]*100)+'%'; lanein.appendChild(b); } }
 }
 drawNotes(); drawLane();

 // scrolling: the labels and the two lanes follow the grid
 scroll.addEventListener('scroll',()=>{ lin.style.transform='translateY('+(-scroll.scrollTop)+'px)';
  rin.style.transform='translateX('+(-scroll.scrollLeft)+'px)'; lanein.style.transform='translateX('+(-scroll.scrollLeft)+'px)'; });

 const at=(e)=>{ const r=gin.getBoundingClientRect();
  return { s:Math.floor((e.clientX-r.left)/STEPW), x:e.clientX-r.left, i:Math.floor((e.clientY-r.top)/ROWH) }; };
 const canLen=(kind==='synth');
 scroll.addEventListener('contextmenu',(e)=>{ e.preventDefault(); const p=at(e); if(p.i<0||p.i>=rows.length)return;
  const n=rows[p.i].n; const hit=pat.notes.find(q=>q.n===n&&p.s>=q.s&&p.s<q.s+q.l);
  if(hit){ Studio.removeNote(pat,hit.s,hit.n); commit(); drawNotes(); drawLane(); } });
 scroll.addEventListener('mousedown',(e)=>{
  if(e.button!==0)return; const p=at(e);
  if(p.i<0||p.i>=rows.length||p.s<0||p.s>=steps)return;
  const n=rows[p.i].n; const hit=pat.notes.find(q=>q.n===n&&p.s>=q.s&&p.s<q.s+q.l);
  let target=hit;
  if(hit){
   const edge=(hit.s+hit.l)*STEPW;
   if(canLen&&p.x>edge-7){ dragLength(hit); return; }
   if(e.shiftKey){ dragVel(hit); return; }
   Studio.removeNote(pat,hit.s,hit.n); selNote=null; commit(); drawNotes(); drawLane(); return;
  }
  target=Studio.addNote(pat,{s:p.s,n,v:velocity,l:canLen?noteLen():1});
  selNote=target; commit(); drawNotes(); drawLane();
  if(canLen&&target)dragLength(target);
 });
 function dragLength(note){ const mv=(ev)=>{ const p=at(ev); note.l=clamp(p.s-note.s+1,1,steps-note.s); drawNotes(); };
  const up=()=>{ document.removeEventListener('mousemove',mv); document.removeEventListener('mouseup',up); commit(); };
  document.addEventListener('mousemove',mv); document.addEventListener('mouseup',up); }
 function dragVel(note){ const start=note.v; let base=null;   // shift-drag up is louder
  const mv=(ev)=>{ if(base==null)base=ev.clientY; note.v=clamp(start+(base-ev.clientY)/120,0.05,1); drawNotes(); drawLane(); };
  const up=()=>{ document.removeEventListener('mousemove',mv); document.removeEventListener('mouseup',up); commit(); };
  document.addEventListener('mousemove',mv); document.addEventListener('mouseup',up); }

 // the lane is drawn across: level for Lights, velocity for everything else
 function laneSet(e){ const r=lanein.getBoundingClientRect(); const s=Math.floor((e.clientX-r.left)/STEPW);
  if(s<0||s>=steps)return; const v=clamp(1-(e.clientY-r.top)/r.height,0,1);
  if(kind==='lights'){ if(!pat.level)pat.level=new Array(steps).fill(null); pat.level[s]=e.altKey?null:v; }
  else { let any=false; for(const q of pat.notes)if(q.s===s){ q.v=Math.max(0.05,v); any=true; } if(!any)return; }
  commit(); drawLane(); drawNotes(); }
 lscroll.addEventListener('mousedown',(e)=>{ e.preventDefault(); laneSet(e);
  const mv=(ev)=>laneSet(ev); const up=()=>{ document.removeEventListener('mousemove',mv); document.removeEventListener('mouseup',up); };
  document.addEventListener('mousemove',mv); document.addEventListener('mouseup',up); });

 gridEls={scroll,head,gin,drawNotes,drawLane,steps,ROWH,rows,mid:m.id,W};
 // open on the middle of the range for a synth, otherwise the top
 if(keep&&keep.id===m.id){ scroll.scrollLeft=keep.l; scroll.scrollTop=keep.t; }
 else if(kind==='synth')scroll.scrollTop=Math.max(0,(96-72)*ROWH-40);
 scroll.dispatchEvent(new Event('scroll'));
}
const noteLen=()=>parseInt($('notelen').value,10)||1;

/* ------------------------------------------------------------------ SONG view */
const BARW=28;
let songEls=null;
function renderSong(){
 const wrap=$('songwrap'); wrap.textContent=''; songEls=null;
 const bars=Math.max(Studio.songLengthBars(proj),proj.song.bars||1)+8;
 const laneW=bars*BARW, rowW=130+laneW;
 const top=el('div','songtop'); const cor=el('div','corner'); top.appendChild(cor);
 const ruler=el('div','ruler'); const rin=el('div','rin'); rin.style.width=laneW+'px';
 for(let b=0;b<bars;b++){ if(b%4&&bars>32)continue; const d=el('div','bl'+(b%4===0?' bar':''));
  d.style.left=(b*BARW)+'px'; if(b%4===0)d.textContent=String(b+1); rin.appendChild(d); }
 ruler.appendChild(rin); top.appendChild(ruler); wrap.appendChild(top);

 const scroll=el('div','songscroll'); const sin=el('div','songin'); sin.style.width=rowW+'px';
 const laneBg='repeating-linear-gradient(90deg,#22262c 0 1px,transparent 1px '+(BARW*4)+'px),'+
  'repeating-linear-gradient(90deg,#16181c 0 1px,transparent 1px '+BARW+'px)';
 proj.machines.forEach((m)=>{
  const row=el('div','songrow'); row.style.width=rowW+'px';
  const nm=el('div','songname'); const dot=el('span','dot'); dot.style.background=MT[m.type].color;
  nm.appendChild(dot); const t=el('span',null,m.name); t.title=m.name+' - '+MT[m.type].name; nm.appendChild(t);
  nm.addEventListener('mousedown',()=>{ selId=m.id; renderStripTabs(); renderStrip(); renderSong(); });
  row.appendChild(nm);
  const lane=el('div','songlane'); lane.style.width=laneW+'px'; lane.style.backgroundImage=laneBg;
  for(const b of Studio.track(proj,m.id)){
   const d=el('div','block'+(selBlock&&selBlock.mid===m.id&&selBlock.bar===b.bar?' sel':''));
   d.style.left=(b.bar*BARW+1)+'px'; d.style.width=(b.len*BARW-2)+'px'; d.style.background=MT[m.type].color;
   d.textContent=b.pat; d.title=m.name+'  pattern '+b.pat+'  bar '+(b.bar+1)+'  '+b.len+' bars';
   const grip=el('div','grip'); d.appendChild(grip);
   d.addEventListener('mousedown',(e)=>{ e.stopPropagation(); selId=m.id; selBlock={mid:m.id,bar:b.bar};
    if(e.target===grip){ dragBlock(b,m,lane); } renderSong(); renderStripTabs(); });
   d.addEventListener('dblclick',(e)=>{ e.stopPropagation(); selId=m.id; m.curPat=b.pat; setView('pattern'); renderAll(); });
   lane.appendChild(d); }
  lane.addEventListener('mousedown',(e)=>{ if(e.target!==lane&&!e.target.classList.contains('bg'))return;
   const r=lane.getBoundingClientRect(); const bar=Math.floor((e.clientX-r.left)/BARW);
   const p=m.patterns[m.curPat]; if(!p)return;
   Studio.placeBlock(proj,m.id,bar,m.curPat,p.bars); selId=m.id; selBlock={mid:m.id,bar};
   commit(); renderSong(); renderStripTabs(); });
  row.appendChild(lane); sin.appendChild(row);
 });
 if(!proj.machines.length)sin.appendChild(el('p','muted','No machines yet.'));
 const head=el('div','playhead'); head.style.left='130px'; sin.appendChild(head);
 scroll.appendChild(sin); wrap.appendChild(scroll);
 scroll.addEventListener('scroll',()=>{ rin.style.transform='translateX('+(-scroll.scrollLeft)+'px)'; });
 // click the ruler to seek
 ruler.addEventListener('mousedown',(e)=>{ const r=rin.getBoundingClientRect();
  eng.seek&&eng.seek(Math.max(0,(e.clientX-r.left)/BARW)*SPB); });
 function dragBlock(b,m,lane){ const r=lane.getBoundingClientRect();
  const mv=(ev)=>{ const bar=Math.floor((ev.clientX-r.left)/BARW); b.len=Math.max(1,bar-b.bar+1);
   proj.song.bars=Math.max(proj.song.bars,b.bar+b.len); commit(); renderSong(); };
  const up=()=>{ document.removeEventListener('mousemove',mv); document.removeEventListener('mouseup',up); };
  document.addEventListener('mousemove',mv); document.addEventListener('mouseup',up); }
 songEls={scroll,head};
}
function deleteBlock(){ if(!selBlock)return; Studio.removeBlock(proj,selBlock.mid,selBlock.bar); selBlock=null; commit(); renderSong(); }

/* ------------------------------------------------------------------ MIXER view */
function renderMixer(){
 const wrap=$('mixwrap'); wrap.textContent='';
 for(const m of proj.machines){
  const s=el('div','strip'+(m.id===selId?' on':''));
  const t=el('div','striptype',MT[m.type].name); t.style.background=MT[m.type].color; s.appendChild(t);
  const nm=el('div','stripname',m.name); nm.title=m.name; s.appendChild(nm);
  s.appendChild(fader({name:m.name+' volume',min:0,max:1,get:()=>m.vol,set:(v)=>{ m.vol=v; },
   after:()=>{ eng.setMixer&&eng.setMixer(m.id); commit(); }}));
  const vv=el('div','kval',fix(m.vol)); s.appendChild(vv);
  s.appendChild(knob({name:'Pan',min:-1,max:1,def:0,get:()=>m.pan,set:(v)=>{ m.pan=v; eng.setMixer&&eng.setMixer(m.id); commit(); },
   fmt:(v)=>Math.abs(v)<0.02?'C':(v<0?'L':'R')+Math.round(Math.abs(v)*100)}));
  const row=el('div','mrow');
  const mb=el('button',null,'Mute'); mb.setAttribute('aria-pressed',m.mute?'true':'false');
  mb.addEventListener('click',()=>{ m.mute=!m.mute; eng.setMixer&&eng.setMixer(m.id); commit(); renderMixer(); renderRack(); });
  const sb=el('button','go','Solo'); sb.setAttribute('aria-pressed',m.solo?'true':'false');
  sb.addEventListener('click',()=>{ m.solo=!m.solo; eng.setMixer&&eng.setMixer(m.id); commit(); renderMixer(); renderRack(); });
  row.appendChild(mb); row.appendChild(sb); s.appendChild(row);
  const sends=el('div','knobs'); sends.style.justifyContent='center';
  sends.appendChild(knob({name:'Delay',min:0,max:1,def:0,get:()=>m.send.delay,set:(v)=>{ m.send.delay=v; eng.setMixer&&eng.setMixer(m.id); commit(); }}));
  sends.appendChild(knob({name:'Reverb',min:0,max:1,def:0,get:()=>m.send.reverb,set:(v)=>{ m.send.reverb=v; eng.setMixer&&eng.setMixer(m.id); commit(); }}));
  s.appendChild(sends);
  s.addEventListener('mousedown',()=>{ if(selId!==m.id){ selId=m.id; renderMixer(); renderStripTabs(); renderStrip(); } });
  wrap.appendChild(s);
 }
 const ms=el('div','strip master');
 const mt=el('div','striptype','MASTER'); mt.style.background='var(--accent)'; ms.appendChild(mt);
 ms.appendChild(el('div','stripname','Master out'));
 ms.appendChild(fader({name:'Master volume',min:0,max:1,get:()=>proj.master.vol,set:(v)=>{ proj.master.vol=v; },
  after:()=>{ eng.setMixer&&eng.setMixer(null); commit(); }}));
 ms.appendChild(el('label',null,'Delay return'));
 ms.appendChild(paramKnobs(FXT.delay.params,proj.master.delay.params,()=>{ eng.setFx&&eng.setFx(null,'delay'); commit(); }));
 ms.appendChild(el('label',null,'Reverb return'));
 ms.appendChild(paramKnobs(FXT.reverb.params,proj.master.reverb.params,()=>{ eng.setFx&&eng.setFx(null,'reverb'); commit(); }));
 wrap.appendChild(ms);
}

/* ------------------------------------------------------------------ FX view */
function renderFx(){
 const wrap=$('fxwrap'); wrap.textContent=''; const m=sel();
 const badge=$('fxmach');
 if(!m){ badge.textContent='-'; badge.style.background='#333'; wrap.appendChild(el('p','muted','No machine selected.')); return; }
 badge.textContent=m.name; badge.style.background=MT[m.type].color;
 [0,1].forEach((slot)=>{
  const box=el('div','fxslot'); const hd=el('div','fxhd');
  hd.appendChild(el('label',null,'Insert '+(slot+1)));
  const sels=el('select'); const none=el('option',null,'(empty)'); none.value=''; sels.appendChild(none);
  for(const k in FXT){ const o=el('option',null,FXT[k].name); o.value=k; sels.appendChild(o); }
  sels.value=m.fx[slot]?m.fx[slot].type:'';
  sels.addEventListener('change',()=>{ m.fx[slot]=sels.value?Studio.newFx(sels.value):null;
   eng.setFx&&eng.setFx(m.id,slot); commit(); renderFx(); });
  hd.appendChild(sels);
  if(m.fx[slot]){ const on=el('button','go','On'); on.setAttribute('aria-pressed',m.fx[slot].on?'true':'false');
   on.addEventListener('click',()=>{ m.fx[slot].on=!m.fx[slot].on; eng.setFx&&eng.setFx(m.id,slot); commit(); renderFx(); });
   hd.appendChild(on); }
  box.appendChild(hd);
  if(m.fx[slot])box.appendChild(paramKnobs(FXT[m.fx[slot].type].params,m.fx[slot].params,()=>{ eng.setFx&&eng.setFx(m.id,slot); commit(); }));
  else box.appendChild(el('p','muted','Nothing in this slot. Pick an effect to insert it before the channel fader.'));
  wrap.appendChild(box);
 });
 const mb=el('div','fxslot'); mb.appendChild(el('h3',null,'Master sends'));
 mb.appendChild(el('p','muted','The two buses every machine can send to. Send amounts live on the mixer strips.'));
 mb.appendChild(el('label',null,'Delay bus'));
 mb.appendChild(paramKnobs(FXT.delay.params,proj.master.delay.params,()=>{ eng.setFx&&eng.setFx(null,'delay'); commit(); }));
 mb.appendChild(el('label',null,'Reverb bus'));
 mb.appendChild(paramKnobs(FXT.reverb.params,proj.master.reverb.params,()=>{ eng.setFx&&eng.setFx(null,'reverb'); commit(); }));
 wrap.appendChild(mb);
}

/* ------------------------------------------------------------------ the play strip */
// the computer keyboard map changes with the selected machine, so the strip and the key routing
// are built from the same tables and the on-screen keys always show the letter that fires them.
const WHITE_KEYS=['z','x','c','v','b','n','m',',','.','/'];
const WHITE_OFF =[0,2,4,5,7,9,11,12,14,16];
const BLACK_KEYS=['s','d','g','h','j','l',';'];
const BLACK_OFF =[1,3,6,8,10,13,15];
const WHITE2_KEYS=['q','w','e','r','t','y','u','i','o','p'];
const WHITE2_OFF =[12,14,16,17,19,21,23,24,26,28];
const BLACK2_KEYS=['2','3','5','6','7','9','0'];
const BLACK2_OFF =[13,15,18,20,22,25,27];
const LOOK_KEYS=['1','2','3','4','5','6','7','8','9','0','-','='];
const PAL_KEYS=['q','w','e','r','t','y','u','i','o','p'];
const BASE=48;   // C3 with the octave stepper at 0

function synthKeyMap(){ const map={};
 WHITE_KEYS.forEach((k,i)=>map[k]=BASE+octave*12+WHITE_OFF[i]);
 BLACK_KEYS.forEach((k,i)=>map[k]=BASE+octave*12+BLACK_OFF[i]);
 WHITE2_KEYS.forEach((k,i)=>map[k]=BASE+octave*12+WHITE2_OFF[i]);
 BLACK2_KEYS.forEach((k,i)=>map[k]=BASE+octave*12+BLACK2_OFF[i]);
 return map; }
function drumKeyMap(){ const map={}; WHITE_KEYS.slice(0,8).forEach((k,i)=>map[k]=i); return map; }
let keyMap={}, keyLetter={};
function rebuildKeyMap(){ const m=sel(), kind=kindOf(m); keyMap={}; keyLetter={};
 if(kind==='synth'){ keyMap=synthKeyMap(); } else if(kind==='drum'){ keyMap=drumKeyMap(); }
 for(const k in keyMap)keyLetter[keyMap[k]]=k; }

function renderStripTabs(){
 const box=$('machtabs'); box.textContent='';
 for(const m of proj.machines){ const b=el('button');
  const d=el('span','dot'); d.style.background=MT[m.type].color; b.appendChild(d);
  b.appendChild(document.createTextNode(m.name));
  b.setAttribute('aria-pressed',m.id===selId?'true':'false');
  b.addEventListener('click',()=>{ selId=m.id; renderStripTabs(); renderStrip();
   if(view==='pattern')renderPattern(); if(view==='fx')renderFx(); if(view==='rack')renderRack(); if(view==='mixer')renderMixer(); });
  box.appendChild(b); }
}

function renderStrip(){
 rebuildKeyMap();
 const host=$('stripplay'); host.textContent='';
 const m=sel(); const kind=kindOf(m);
 $('octrow').style.display=kind==='synth'?'':'none';
 if(!m){ host.appendChild(el('p','muted','No machine selected.')); $('hint').textContent=''; return; }
 if(kind==='synth')buildPiano(host);
 else if(kind==='drum')buildPads(host,m);
 else buildLights(host);
 $('hint').innerHTML=kind==='synth'?'Keys <b>z x c v b n m , . /</b> white, <b>s d g h j l ;</b> black, <b>q..p</b> an octave up, <b>[ ]</b> octave.'
  :(kind==='drum'?'Keys <b>z x c v b n m ,</b> fire the eight pads.'
   :'Keys <b>1..9 0 - =</b> looks, <b>q..p</b> palettes, <b>[ ]</b> level, <b>Space</b> HIT.');
}

function buildPiano(host){
 const kb=el('div','piano'); host.appendChild(kb);
 const lo=BASE+octave*12-12, hi=lo+37;                     // three octaves and the top C
 const whites=[]; for(let n=lo;n<=hi;n++)if(!isBlack(n))whites.push(n);
 const w=100/whites.length;
 whites.forEach((n,i)=>{ const d=el('div','w'); d.style.left=(i*w)+'%'; d.style.width=w+'%'; d.dataset.n=n;
  if(keyLetter[n])d.appendChild(el('i',null,keyLetter[n].toUpperCase()));
  else if(n%12===0)d.appendChild(el('i',null,noteName(n)));
  kb.appendChild(d); });
 for(let n=lo;n<=hi;n++){ if(!isBlack(n))continue;
  const left=whites.filter(x=>x<n).length; const d=el('div','b');
  d.style.left=(left*w-w*0.3)+'%'; d.style.width=(w*0.6)+'%'; d.dataset.n=n;
  if(keyLetter[n])d.appendChild(el('i',null,keyLetter[n].toUpperCase()));
  kb.appendChild(d); }
 kb.addEventListener('mousedown',(e)=>{ const t=e.target.closest('[data-n]'); if(!t)return; e.preventDefault();
  const n=+t.dataset.n; pressNote(n);
  const up=()=>{ releaseNote(n); document.removeEventListener('mouseup',up); };
  document.addEventListener('mouseup',up); });
}

function buildPads(host,m){
 const g=el('div','padgrid'); g.style.gridTemplateColumns='repeat(4,1fr)'; g.style.gridTemplateRows='repeat(2,1fr)';
 MT[m.type].pads.forEach((name,i)=>{ const b=el('button','pad',name); b.dataset.n=i;
  const k=el('span','k',(WHITE_KEYS[i]||'').toUpperCase()); b.appendChild(k);
  b.addEventListener('mousedown',(e)=>{ e.preventDefault(); pressNote(i); setTimeout(()=>releaseNote(i),60); });
  g.appendChild(b); });
 host.appendChild(g);
}

function buildLights(host){
 const cols=el('div','lightcols');
 const c1=el('div','lightcol'); c1.appendChild(el('label',null,'Look'));
 const lg=el('div','padgrid'); lg.style.gridTemplateColumns='repeat(3,1fr)';
 NGV.LOOK_NAMES.forEach((name,i)=>{ const b=el('button','pad',name);
  const desc=(NGV.LOOKS[i]||[])[1]; if(desc)b.title=desc;
  b.dataset.look=name; b.setAttribute('aria-pressed',L.state.look===name?'true':'false');
  b.appendChild(el('span','k',(LOOK_KEYS[i]||'').toUpperCase()));
  b.addEventListener('click',()=>lightPress('look',name));
  lg.appendChild(b); });
 c1.appendChild(lg); cols.appendChild(c1);

 const c2=el('div','lightcol'); c2.appendChild(el('label',null,'Palette'));
 const pg=el('div','padgrid'); pg.style.gridTemplateColumns='repeat(5,1fr)';
 NGV.PALETTE_NAMES.forEach((name,i)=>{ const b=el('button','palpad'); b.style.background=palCss(name);
  b.dataset.pal=name; b.setAttribute('aria-pressed',L.state.palette===name?'true':'false');
  b.appendChild(el('span',null,name)); b.appendChild(el('b',null,(PAL_KEYS[i]||'').toUpperCase()));
  b.addEventListener('click',()=>lightPress('palette',name));
  pg.appendChild(b); });
 c2.appendChild(pg); cols.appendChild(c2);

 const c3=el('div','lightside');
 const lv=el('label'); lv.innerHTML='Level <span class="val" id="lvlval">'+fix(L.state.level)+'</span>'; c3.appendChild(lv);
 const r=el('input'); r.type='range'; r.id='lvl'; r.min=0; r.max=1; r.step=0.01; r.value=L.state.level;
 r.addEventListener('input',()=>{ lightPress('level',parseFloat(r.value)); });
 c3.appendChild(r);
 const hb=el('button',null,'HIT'); hb.id='hitbtn'; hb.title='Space';
 hb.addEventListener('mousedown',(e)=>{ e.preventDefault(); lightPress('hit',true); hb.classList.add('hit'); setTimeout(()=>hb.classList.remove('hit'),140); });
 c3.appendChild(hb);
 cols.appendChild(c3);
 host.appendChild(cols);
}

function refreshLightPads(){
 const host=$('stripplay');
 host.querySelectorAll('[data-look]').forEach(b=>b.setAttribute('aria-pressed',L.state.look===b.dataset.look?'true':'false'));
 host.querySelectorAll('[data-pal]').forEach(b=>b.setAttribute('aria-pressed',L.state.palette===b.dataset.pal?'true':'false'));
 const lv=$('lvlval'), r=$('lvl'); if(lv)lv.textContent=fix(L.state.level); if(r&&document.activeElement!==r)r.value=L.state.level;
}
function lightPress(kind,val){
 let wrote=null;
 try{ wrote=L.press(kind,val); }catch(e){ /* the lights runtime may still be being written */ }
 if(L.stub||!wrote){ // keep the studio honest even without lights.js: write the cue ourselves
  if(record&&eng.playing&&kind!=='level')recordLightCue(kind,val);
  else if(record&&eng.playing&&kind==='level')recordLightLevel(val);
 }
 refreshLightPads(); if(view==='pattern')refreshPatternIfLights();
}
function lightsMachine(){ return proj.machines.find(m=>m.type==='lights')||null; }
function recordLightCue(kind,val){ const m=lightsMachine(); if(!m)return; const p=patternForWrite(m); if(!p)return;
 const n=Studio.lightKeyIndex(kind,val); if(n<0)return;
 Studio.addNote(p.pat,{s:p.step,n,v:1,l:1}); commit(); }
function recordLightLevel(v){ const m=lightsMachine(); if(!m)return; const p=patternForWrite(m); if(!p||!p.pat.level)return;
 p.pat.level[p.step]=v; commit(); }
function refreshPatternIfLights(){ const m=sel(); if(m&&m.type==='lights')renderPattern(); }

/* ------------------------------------------------------------------ live play and record */
// where a press lands: the pattern the machine is playing right now, at the quantised step
function patternForWrite(m){
 let step=0, pat=m.patterns[m.curPat];
 let p; try{ p=eng.pos(); }catch(e){ p={step:0}; }
 if(eng.mode==='song'){
  const bar=Math.floor(p.step/SPB);
  const blk=Studio.track(proj,m.id).find(b=>bar>=b.bar&&bar<b.bar+b.len);
  if(blk){ pat=m.patterns[blk.pat]; step=(p.step-blk.bar*SPB); }
  else step=p.step;
 } else step=p.step;
 if(!pat)return null;
 const n=Studio.patternSteps(pat);
 const q=quant||1;
 step=Math.round(step/q)*q; step=((step%n)+n)%n;
 return {pat,step};
}
function pressNote(n){
 const m=sel(); if(!m)return;
 flash[m.id+':'+n]=performance.now();
 try{ eng.init&&eng.init(); }catch(e){}
 try{ eng.noteOn&&eng.noteOn(m.id,n,velocity); }catch(e){}
 paintHeld();
 if(record&&eng.playing){ const w=patternForWrite(m); if(w){
   const note=Studio.addNote(w.pat,{s:w.step,n,v:velocity,l:1});
   held[n]={note,pat:w.pat,start:w.step}; commit(); if(view==='pattern')renderPatternNotes(); } }
}
function releaseNote(n){
 const m=sel(); if(!m)return;
 try{ eng.noteOff&&eng.noteOff(m.id,n); }catch(e){}
 const h=held[n];
 if(h&&kindOf(m)==='synth'){ const w=patternForWrite(m);
  if(w&&w.pat===h.pat){ const len=((w.step-h.start)%Studio.patternSteps(h.pat)+Studio.patternSteps(h.pat))%Studio.patternSteps(h.pat);
   h.note.l=Math.max(1,Math.min(len||1,Studio.patternSteps(h.pat)-h.note.s)); commit(); if(view==='pattern')renderPatternNotes(); } }
 delete held[n]; paintHeld();
}
function renderPatternNotes(){ if(gridEls&&gridEls.mid===selId){ gridEls.drawNotes(); gridEls.drawLane(); } else renderPattern(); }
function paintHeld(){
 const host=$('stripplay');
 host.querySelectorAll('.piano [data-n]').forEach(d=>d.classList.toggle('held',held[+d.dataset.n]!=null));
}

/* ------------------------------------------------------------------ transport */
function setPlaying(on){
 $('play').textContent=on?'Pause':'Play';
 $('play').setAttribute('aria-pressed',on?'true':'false');
}
function doPlay(){
 try{ eng.init&&eng.init(); }catch(e){ say('Audio could not start: '+e.message,6000); }
 if(eng.playing){ eng.pause(); } else { eng.play({mode:eng.mode||'pattern'}); }
 setPlaying(!!eng.playing);
}
function doStop(){ try{ eng.stop(); }catch(e){} setPlaying(false); }
function setMode(mode){ eng.mode=mode; const was=eng.playing; try{ eng.stop(); }catch(e){}
 $('modepat').setAttribute('aria-pressed',mode==='pattern'?'true':'false');
 $('modesong').setAttribute('aria-pressed',mode==='song'?'true':'false');
 commit(); if(was){ try{ eng.play({mode}); }catch(e){} } setPlaying(!!eng.playing); }
function setRecord(on){ record=on; $('rec').setAttribute('aria-pressed',on?'true':'false');
 try{ L.setRecord&&L.setRecord(on,quant); }catch(e){} }

/* ------------------------------------------------------------------ views */
const VIEWS=['rack','pattern','song','mixer','fx'];
function setView(v){ view=v;
 VIEWS.forEach(n=>$('view-'+n).classList.toggle('on',n===v));
 document.querySelectorAll('#tabs button').forEach(b=>b.setAttribute('aria-pressed',b.dataset.v===v?'true':'false'));
 if(v==='pattern')renderPattern(); else if(v==='song')renderSong(); else if(v==='mixer')renderMixer();
 else if(v==='fx')renderFx(); else renderRack();
}
function renderAll(){ renderRack(); renderStripTabs(); renderStrip();
 if(view==='pattern')renderPattern(); if(view==='song')renderSong(); if(view==='mixer')renderMixer(); if(view==='fx')renderFx();
 $('name').value=proj.name; $('bpm').value=proj.bpm; $('swing').value=proj.swing||0;
 $('swingval').textContent=Math.round((proj.swing||0)*100)+'%';
}

/* ------------------------------------------------------------------ save, load, export */
function veil(html){ const v=$('veil'), b=$('veilbox'); b.innerHTML=html; v.hidden=false; return b; }
function unveil(){ $('veil').hidden=true; }
$('veil')&&$('veil').addEventListener('mousedown',(e)=>{ if(e.target.id==='veil')unveil(); });

async function doSave(){
 proj.name=$('name').value.trim()||'untitled';
 if(!Studio.saveProject){ say('export.js is not loaded, saved to this browser only'); autosave(); return; }
 try{ await Studio.saveProject(proj); say('Saved '+proj.name); }catch(e){ say('Save failed: '+e.message,6000); }
 autosave();
}
async function doLoad(){
 const b=veil('<h3>Load a project</h3><p class="muted">Projects saved into show/ by this studio.</p><div class="list" id="loadlist">Looking...</div><button id="loadclose">Close</button>');
 $('loadclose').addEventListener('click',unveil);
 const list=$('loadlist'); list.textContent='';
 let names=[];
 try{ const r=await fetch('show/shows.json',{cache:'no-store'}); if(r.ok)names=await r.json(); }catch(e){}
 if(!names.length){ list.appendChild(el('p','muted','Nothing saved yet.')); }
 for(const n of names){ const btn=el('button',null,n);
  btn.addEventListener('click',async()=>{
   if(!Studio.loadProject){ say('export.js is not loaded'); return; }
   try{ const p=await Studio.loadProject(n); if(!p){ say('No project file for '+n); return; }
    proj=p; selId=(proj.machines[0]||{}).id||null; selBlock=null;
    eng.rebuild&&eng.rebuild(); commit(); renderAll(); unveil(); say('Loaded '+n);
   }catch(e){ say('Load failed: '+e.message,6000); } });
  list.appendChild(btn); }
}
async function doExport(){
 proj.name=$('name').value.trim()||'untitled';
 if(!Studio.exportShow){ say('export.js is not loaded yet',6000); return; }
 const b=veil('<h3>Export</h3><p id="ptxt" class="muted">Starting...</p><div id="pbar"><div id="pbarfill"></div></div><div id="pdone"></div><button id="pclose">Close</button>');
 $('pclose').addEventListener('click',unveil);
 const txt=$('ptxt'), fill=$('pbarfill');
 try{
  const res=await Studio.exportShow(proj,eng,proj.name,(t,p)=>{ txt.textContent=t; fill.style.width=Math.round((p||0)*100)+'%'; });
  fill.style.width='100%'; txt.textContent='Done.';
  const url=res&&res.url?res.url:('index.html?show='+encodeURIComponent(proj.name));
  $('pdone').innerHTML='<p>Play it in the hall: <a href="'+url+'" target="_blank">'+url+'</a></p>';
 }catch(e){ txt.textContent='Export failed: '+e.message; }
}

/* ------------------------------------------------------------------ keyboard routing */
function typing(){ const a=document.activeElement; if(!a)return false;
 const t=a.tagName; return t==='INPUT'||t==='SELECT'||t==='TEXTAREA'||a.isContentEditable; }
document.addEventListener('keydown',(e)=>{
 if(e.key==='Enter'&&!typing()){ e.preventDefault(); doPlay(); return; }
 if(e.key==='Escape'){ if(!$('veil').hidden){ unveil(); return; } doStop(); return; }
 if(typing())return;
 if(e.key==='R'&&e.shiftKey){ e.preventDefault(); setRecord(!record); return; }
 if((e.key==='Delete'||e.key==='Backspace')&&view==='song'){ e.preventDefault(); deleteBlock(); return; }
 if(e.repeat)return;
 const m=sel(); if(!m)return; const kind=kindOf(m); const k=e.key.toLowerCase();
 if(kind==='lights'){
  let i=LOOK_KEYS.indexOf(k);
  if(i>=0&&NGV.LOOK_NAMES[i]){ e.preventDefault(); lightPress('look',NGV.LOOK_NAMES[i]); return; }
  i=PAL_KEYS.indexOf(k);
  if(i>=0&&NGV.PALETTE_NAMES[i]){ e.preventDefault(); lightPress('palette',NGV.PALETTE_NAMES[i]); return; }
  if(k==='['){ e.preventDefault(); lightPress('level',clamp(L.state.level-0.1,0,1)); return; }
  if(k===']'){ e.preventDefault(); lightPress('level',clamp(L.state.level+0.1,0,1)); return; }
  if(e.code==='Space'||k===' '){ e.preventDefault(); lightPress('hit',true); return; }
  return;
 }
 if(kind==='synth'){
  if(k==='['){ e.preventDefault(); setOctave(octave-1); return; }
  if(k===']'){ e.preventDefault(); setOctave(octave+1); return; }
 }
 const n=keyMap[k];
 if(n!=null){ e.preventDefault(); pressNote(n); }
});
document.addEventListener('keyup',(e)=>{ if(typing())return; const n=keyMap[e.key.toLowerCase()];
 if(n!=null)releaseNote(n); });
function setOctave(o){ octave=clamp(o,-2,2); $('octval').textContent=(octave>0?'+':'')+octave; renderStrip(); }

/* ------------------------------------------------------------------ the frame loop */
let frames=0;
function loop(){
 requestAnimationFrame(loop);
 frames++;
 let p; try{ p=eng.pos(); }catch(e){ p={step:0,t:0,bar:0,beat:0,stepInBar:0,loopSteps:SPB}; }
 // clocks
 $('barbeat').textContent=(Math.floor(p.step/SPB)+1)+':'+(Math.floor(p.step/4)%4+1)+':'+(Math.floor(p.step)%4+1);
 const t=p.t||0; $('clock').textContent=Math.floor(t/60)+':'+String(Math.floor(t%60)).padStart(2,'0')+'.'+Math.floor((t%1)*10);
 if(eng.playing!==(($('play').textContent)==='Pause'))setPlaying(!!eng.playing);
 // meter
 let rms=0; try{ if(eng.analyser){ const o={}; eng.analyser.read(o); rms=o.rms||0; } }catch(e){}
 $('meterfill').style.width=Math.round(clamp(rms,0,1)*100)+'%';
 // playheads
 if(view==='pattern'&&gridEls){ const m=machine(gridEls.mid);
  if(m){ const pat=m.patterns[m.curPat]; const n=pat?Studio.patternSteps(pat):SPB;
   const s=eng.mode==='song'?p.step:(p.step%n); gridEls.head.style.left=((s%n)*STEPW)+'px'; } }
 if(view==='song'&&songEls)songEls.head.style.left=(130+(p.step/SPB)*BARW)+'px';
 // the hall: the lights runtime posts a frame to the iframe every rAF (slower when stopped)
 if(L.tick&&(eng.playing||frames%4===0)){ try{ L.tick(); }catch(e){} }
 if(frames%6===0){ const st=L.state||{};
  $('simstate').textContent=(st.look||'-')+' / '+(st.palette||'-')+' / '+fix(st.level==null?1:st.level,2);
  if(sel()&&kindOf(sel())==='lights')refreshLightPads(); }
 // key flashes from the scheduler
 if(frames%2===0)paintFlashes();
}
function paintFlashes(){
 const m=sel(); if(!m)return; const now=performance.now(); const host=$('stripplay');
 const kind=kindOf(m);
 if(kind==='drum'){ host.querySelectorAll('.pad[data-n]').forEach(b=>{
   const on=(now-(flash[m.id+':'+b.dataset.n]||-1e9))<130; b.classList.toggle('hit',on); }); }
 else if(kind==='synth'){ host.querySelectorAll('.piano [data-n]').forEach(d=>{
   const n=+d.dataset.n; const on=held[n]!=null||(now-(flash[m.id+':'+n]||-1e9))<130; d.classList.toggle('held',on); }); }
}

/* ------------------------------------------------------------------ wiring */
function boot(){
 // view tabs
 const tabs=$('tabs');
 for(const v of VIEWS){ const b=el('button',null,v.toUpperCase()); b.dataset.v=v;
  b.setAttribute('aria-pressed',v===view?'true':'false');
  b.addEventListener('click',()=>setView(v)); tabs.appendChild(b); }
 // selects
 const bars=$('bars'); for(let i=1;i<=Studio.MAX_BARS;i++){ const o=el('option',null,i+' bar'+(i>1?'s':'')); o.value=i; bars.appendChild(o); }
 bars.addEventListener('change',()=>{ const m=sel(); if(!m)return; Studio.resizePattern(m.patterns[m.curPat],+bars.value);
  commit(); renderPattern(); renderSong(); });
 const nl=$('notelen'); [[1,'1/16'],[2,'1/8'],[4,'1/4'],[8,'1/2'],[16,'1 bar']].forEach(([v,t])=>{ const o=el('option',null,t); o.value=v; nl.appendChild(o); });
 nl.value='1';
 const q=$('quant'); [[1,'1/16'],[2,'1/8'],[4,'1/4 (beat)']].forEach(([v,t])=>{ const o=el('option',null,t); o.value=v; q.appendChild(o); });
 q.value='1'; q.addEventListener('change',()=>{ quant=+q.value; try{ L.setRecord&&L.setRecord(record,quant); }catch(e){} });
 // transport
 $('play').addEventListener('click',doPlay);
 $('stop').addEventListener('click',doStop);
 $('rec').addEventListener('click',()=>setRecord(!record));
 $('modepat').addEventListener('click',()=>setMode('pattern'));
 $('modesong').addEventListener('click',()=>setMode('song'));
 $('loop').addEventListener('click',()=>{ eng.loop=!eng.loop; $('loop').setAttribute('aria-pressed',eng.loop?'true':'false'); });
 $('bpm').addEventListener('change',()=>{ proj.bpm=clamp(+$('bpm').value||124,60,200); $('bpm').value=proj.bpm; commit(); });
 $('bpmdn').addEventListener('click',()=>{ proj.bpm=clamp(proj.bpm-1,60,200); $('bpm').value=proj.bpm; commit(); });
 $('bpmup').addEventListener('click',()=>{ proj.bpm=clamp(proj.bpm+1,60,200); $('bpm').value=proj.bpm; commit(); });
 $('swing').addEventListener('input',()=>{ proj.swing=+$('swing').value; $('swingval').textContent=Math.round(proj.swing*100)+'%'; commit(); });
 $('name').addEventListener('input',()=>{ proj.name=$('name').value; autosave(); });
 $('velo').addEventListener('input',()=>{ velocity=+$('velo').value; $('veloval').textContent=fix(velocity); });
 $('octdn').addEventListener('click',()=>setOctave(octave-1));
 $('octup').addEventListener('click',()=>setOctave(octave+1));
 // pattern tools
 $('patclear').addEventListener('click',()=>{ const m=sel(); if(!m)return; const p=m.patterns[m.curPat];
  p.notes=[]; if(p.level)p.level.fill(null); commit(); renderPattern(); });
 $('patcopy').addEventListener('click',()=>{ const m=sel(); if(!m)return; clipboard=Studio.clone(m.patterns[m.curPat]); say('Pattern copied'); });
 $('patpaste').addEventListener('click',()=>{ const m=sel(); if(!m||!clipboard)return;
  m.patterns[m.curPat]=Studio.clone(clipboard); commit(); renderPattern(); renderSong(); say('Pattern pasted'); });
 // song tools
 $('songdel').addEventListener('click',deleteBlock);
 $('songclear').addEventListener('click',()=>{ if(!confirm('Clear the whole arrangement?'))return;
  proj.song.tracks={}; selBlock=null; commit(); renderSong(); });
 // files
 $('save').addEventListener('click',doSave);
 $('load').addEventListener('click',doLoad);
 $('export').addEventListener('click',doExport);
 // sim panel
 $('simtoggle').addEventListener('click',()=>{ const on=$('simpanel').classList.toggle('hidden');
  $('simhandle').classList.toggle('hidden',on); $('simtoggle').setAttribute('aria-pressed',on?'false':'true'); });
 $('simhandle').addEventListener('mousedown',(e)=>{ e.preventDefault();
  const mv=(ev)=>{ const w=clamp(window.innerWidth-ev.clientX,200,window.innerWidth-420);
   $('simpanel').style.width=w+'px'; };
  const up=()=>{ document.removeEventListener('mousemove',mv); document.removeEventListener('mouseup',up); };
  document.addEventListener('mousemove',mv); document.addEventListener('mouseup',up); });
 // the whole surface
 setMode('pattern'); setRecord(false); setOctave(0);
 $('loop').setAttribute('aria-pressed',eng.loop?'true':'false');
 renderAll(); setView('rack');
 if(eng.stub)say('No audio engine loaded: the studio is running on the stub clock.',8000);
 requestAnimationFrame(loop);
}
if(document.readyState==='loading')document.addEventListener('DOMContentLoaded',boot); else boot();

// a handful of internals the verification pages poke at
Studio.ui={ get project(){ return proj; }, get engine(){ return eng; }, get lights(){ return L; },
 setView, renderAll, select(id){ selId=id; renderAll(); } };
})();
