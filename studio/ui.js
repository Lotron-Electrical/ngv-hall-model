// THE STUDIO'S UI (Lloyd, 2026-09-05): the Caustic 3 surface, built phone first.
//
// A phone gets one transport row, a bottom nav of six tabs (the sixth is the hall itself), and a
// play drawer it can collapse out of the way. A desktop gets the same surface with the tabs moved
// into the top bar and the hall docked on the right. Everything that is not needed to make the
// next decision lives behind the "more" sheet or a card's "..." menu, because the first phone pass
// was four rows of chrome before a single knob (Lloyd, 2026-09-05: "way too much going on here").
//
// This file owns no sound and no light maths. It edits the model, tells the engine the model moved
// (eng.invalidate) and asks the lights runtime for a frame once per rAF. If the engine or the
// lights runtime is missing it falls back to the stub, so a view always draws.
(function(){
'use strict';
const Studio=window.Studio;
if(!Studio){ document.body.innerHTML='<p style="padding:20px;color:#d8433c">studio/model.js did not load.</p>'; return; }
const SPB=Studio.STEPS_PER_BAR, MT=Studio.MACHINE_TYPES, FXT=Studio.FX_TYPES;
const NGV=window.NGVShow||{LOOK_NAMES:[],PALETTE_NAMES:[],PALETTES:{},LOOKS:[]};

/* ------------------------------------------------------------------ helpers */
const $=(id)=>document.getElementById(id);
const el=(tag,cls,txt)=>{ const e=document.createElement(tag); if(cls)e.className=cls; if(txt!=null)e.textContent=txt; return e; };
const clamp=(x,a,b)=>x<a?a:x>b?b:x;
const fix=(v,d)=>Number(v).toFixed(d==null?2:d);
const mq=(q)=>window.matchMedia&&window.matchMedia(q).matches;
const isPhone=()=>window.innerWidth<900;
const isTouch=()=>mq('(hover: none)');

function hsvCss(c){ const s=(c.s==null?1:c.s), v=(c.v==null?1:c.v);
 return 'hsl('+c.h+','+Math.round(s*100)+'%,'+Math.round((1-s/2)*v*100)+'%)'; }
function palCss(name){ const p=NGV.PALETTES[name]; if(!p)return '#333';
 return 'linear-gradient(120deg,'+hsvCss(p.A)+' 0%,'+hsvCss(p.A)+' 45%,'+hsvCss(p.B)+' 100%)'; }
function palSolid(name){ const p=NGV.PALETTES[name]; return p?hsvCss(p.A):'#555'; }
const NOTE_NAMES=['C','C#','D','D#','E','F','F#','G','G#','A','A#','B'];
const isBlack=(n)=>[1,3,6,8,10].indexOf(((n%12)+12)%12)>=0;
const noteName=(n)=>NOTE_NAMES[((n%12)+12)%12]+(Math.floor(n/12)-1);

// small line icons, drawn rather than typed: the page is ASCII and a glyph font may not have loaded
const SV=(inner,s)=>'<svg width="'+(s||20)+'" height="'+(s||20)+'" viewBox="0 0 20 20" aria-hidden="true">'+inner+'</svg>';
const ICON={
 stop:SV('<rect x="4" y="4" width="12" height="12" rx="2" fill="currentColor"/>',14),
 rec:SV('<circle cx="10" cy="10" r="6" fill="currentColor"/>',14),
 menu:SV('<g fill="currentColor"><rect x="2" y="4" width="16" height="2" rx="1"/><rect x="2" y="9" width="16" height="2" rx="1"/><rect x="2" y="14" width="16" height="2" rx="1"/></g>',18),
 up:SV('<path d="M5 12l5-5 5 5" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/>',18),
 down:SV('<path d="M5 8l5 5 5-5" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/>',18),
 rack:SV('<g fill="currentColor"><rect x="2" y="3" width="16" height="4" rx="1.5"/><rect x="2" y="9" width="16" height="4" rx="1.5" opacity=".75"/><rect x="2" y="15" width="16" height="3" rx="1.5" opacity=".5"/></g>'),
 pattern:SV('<g fill="currentColor"><rect x="2" y="3" width="4" height="4" rx="1"/><rect x="8" y="3" width="4" height="4" rx="1" opacity=".45"/><rect x="14" y="3" width="4" height="4" rx="1"/><rect x="2" y="8" width="4" height="4" rx="1" opacity=".45"/><rect x="8" y="8" width="4" height="4" rx="1"/><rect x="14" y="8" width="4" height="4" rx="1" opacity=".45"/><rect x="2" y="13" width="4" height="4" rx="1"/><rect x="8" y="13" width="4" height="4" rx="1" opacity=".45"/><rect x="14" y="13" width="4" height="4" rx="1"/></g>'),
 song:SV('<g fill="currentColor"><rect x="2" y="4" width="11" height="3" rx="1.5"/><rect x="5" y="9" width="13" height="3" rx="1.5" opacity=".7"/><rect x="2" y="14" width="8" height="3" rx="1.5" opacity=".5"/></g>'),
 mixer:SV('<g stroke="currentColor" stroke-width="2" stroke-linecap="round"><path d="M5 3v14M10 3v14M15 3v14"/></g><g fill="currentColor"><rect x="2" y="11" width="6" height="3" rx="1.5"/><rect x="7" y="5" width="6" height="3" rx="1.5"/><rect x="12" y="9" width="6" height="3" rx="1.5"/></g>'),
 fx:SV('<path d="M2 10c2-6 4-6 6 0s4 6 6 0 3-3 4-1" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round"/>'),
 hall:SV('<path d="M3 17V8l7-5 7 5v9" fill="none" stroke="currentColor" stroke-width="2" stroke-linejoin="round"/><circle cx="10" cy="11" r="2.5" fill="currentColor"/>'),
};

let toastTimer=0;
function say(text,hold){ const t=$('toast'); if(!text){ t.hidden=true; return; }
 t.textContent=text; t.hidden=false; clearTimeout(toastTimer);
 toastTimer=setTimeout(()=>{ t.hidden=true; },hold||2800); }

/* ------------------------------------------------------------------ state */
const LSKEY='ngv.studio.project', LSDRAWER='ngv.studio.drawer';
let proj=loadStored()||Studio.demoProject();
let view='rack';
let selId=(proj.machines[0]||{}).id||null;
let record=false, quant=1, octave=0, velocity=0.8;
let clipboard=null, selBlock=null;
const flash={}, held={};

function loadStored(){ try{ const s=localStorage.getItem(LSKEY); if(!s)return null; const p=JSON.parse(s);
  return (p&&p.machines)?p:null; }catch(e){ return null; } }
let saveTimer=0;
function autosave(){ clearTimeout(saveTimer); saveTimer=setTimeout(()=>{
  try{ localStorage.setItem(LSKEY,JSON.stringify(proj)); }catch(e){} },500); }

const machine=(id)=>proj.machines.find(m=>m.id===id)||null;
const sel=()=>machine(selId)||proj.machines[0]||null;
const kindOf=(m)=>m?MT[m.type].kind:'synth';
function commit(){ try{ eng.invalidate&&eng.invalidate(); }catch(e){} try{ L.invalidate&&L.invalidate(); }catch(e){} autosave(); }

/* ------------------------------------------------------------------ engine and lights */
function nullEngine(){
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

/* ------------------------------------------------------------------ sheets */
// one presentation for every menu and dialog: a bottom sheet on a phone, a centred card on a
// desktop. Rows are 44 px so a thumb can hit them, and the actions read as sentences.
let sheetOpen=false;
function openSheet(title,build,noClose){
 const box=$('sheet'); box.textContent='';
 if(title)box.appendChild(el('h3',null,title));
 build(box);
 if(!noClose){ const c=el('button','sact','Close'); c.addEventListener('click',closeSheet); box.appendChild(c); }
 $('veil').hidden=false; sheetOpen=true; box.scrollTop=0;
}
function closeSheet(){ $('veil').hidden=true; sheetOpen=false; }
function sAct(box,label,fn,cls){ const b=el('button','sact'+(cls?' '+cls:''),label);
 b.addEventListener('click',()=>{ closeSheet(); fn(); }); box.appendChild(b); return b; }
function sRow(box,label,node){ const r=el('div','srow');
 if(label)r.appendChild(el('label',null,label));
 if(node){ node.classList.add('grow'); r.appendChild(node); }
 box.appendChild(r); return r; }
function sToggle(box,label,get,set){ const b=el('button',null,get()?'On':'Off');
 b.setAttribute('aria-pressed',get()?'true':'false');
 b.addEventListener('click',()=>{ set(!get()); b.textContent=get()?'On':'Off'; b.setAttribute('aria-pressed',get()?'true':'false'); });
 sRow(box,label,b); return b; }
function sSeg(box,label,options,get,set){ const seg=el('div','seg');
 const paint=()=>seg.querySelectorAll('button').forEach(b=>b.setAttribute('aria-pressed',b.dataset.v===String(get())?'true':'false'));
 for(const [v,t] of options){ const b=el('button',null,t); b.dataset.v=String(v);
  b.addEventListener('click',()=>{ set(v); paint(); }); seg.appendChild(b); }
 paint(); sRow(box,label,seg); return seg; }

/* ------------------------------------------------------------------ knob and fader */
// both are pointer driven with the pointer captured and touch-action none, so a vertical drag
// never turns into a page scroll on a touch screen
function knob(spec){
 const wrap=el('div','knobwrap');
 const k=el('div','knob'); k.tabIndex=0; k.setAttribute('role','slider'); k.setAttribute('aria-label',spec.name);
 k.appendChild(el('span','needle'));
 const lbl=el('div','klbl',spec.name); lbl.title=spec.name;
 const val=el('div','kval');
 wrap.appendChild(k); wrap.appendChild(lbl); wrap.appendChild(val);
 const span=spec.max-spec.min, dp=spec.step&&spec.step>=1?0:(span>20?1:2);
 function paint(){ const v=spec.get(); const p=span?clamp((v-spec.min)/span,0,1):0;
  k.style.setProperty('--pct',p); k.setAttribute('aria-valuenow',fix(v,dp));
  val.textContent=(spec.fmt?spec.fmt(v):fix(v,dp))+(spec.unit||''); }
 function set(v){ if(spec.step)v=Math.round(v/spec.step)*spec.step; spec.set(clamp(v,spec.min,spec.max)); paint(); }
 k.addEventListener('pointerdown',(e)=>{ e.preventDefault(); k.setPointerCapture(e.pointerId);
  const y0=e.clientY, v0=spec.get(), travel=e.pointerType==='mouse'?140:180;
  const mv=(ev)=>{ const f=ev.shiftKey?0.25:1; set(v0+(y0-ev.clientY)/travel*span*f); };
  const up=()=>{ k.removeEventListener('pointermove',mv); k.removeEventListener('pointerup',up); k.removeEventListener('pointercancel',up); };
  k.addEventListener('pointermove',mv); k.addEventListener('pointerup',up); k.addEventListener('pointercancel',up); });
 k.addEventListener('dblclick',()=>{ if(spec.def!=null)set(spec.def); });
 k.addEventListener('wheel',(e)=>{ e.preventDefault(); set(spec.get()+(e.deltaY<0?1:-1)*span/60); },{passive:false});
 k.addEventListener('keydown',(e)=>{ const st=span/50;
  if(e.key==='ArrowUp'||e.key==='ArrowRight'){ e.preventDefault(); set(spec.get()+st); }
  else if(e.key==='ArrowDown'||e.key==='ArrowLeft'){ e.preventDefault(); set(spec.get()-st); } });
 paint(); return wrap;
}
function intParam(p){ return Number.isInteger(p.min)&&Number.isInteger(p.max)&&Number.isInteger(p.def)&&
 (p.max-p.min>=2||p.def===p.min); }
function paramKnobs(table,params,onChange,cls){
 const box=el('div','knobs '+(cls||'wrap'));
 for(const key in table){ const p=table[key];
  box.appendChild(knob({name:p.name,min:p.min,max:p.max,def:p.def,unit:p.unit?' '+p.unit:'',step:intParam(p)?1:0,
   get:()=>params[key]==null?p.def:params[key], set:(v)=>{ params[key]=v; onChange&&onChange(key,v); }})); }
 return box;
}
function fader(spec){
 const f=el('div','fader'); f.tabIndex=0; f.setAttribute('role','slider'); f.setAttribute('aria-label',spec.name);
 const fill=el('div','fill'), cap=el('div','cap'); f.appendChild(fill); f.appendChild(cap);
 function paint(){ const p=clamp((spec.get()-spec.min)/(spec.max-spec.min),0,1);
  fill.style.height=(p*100)+'%'; cap.style.bottom=(p*100)+'%'; f.setAttribute('aria-valuenow',fix(spec.get())); }
 function set(v){ spec.set(clamp(v,spec.min,spec.max)); paint(); spec.after&&spec.after(); }
 function fromY(cy){ const r=f.getBoundingClientRect(); return spec.min+(1-clamp((cy-r.top)/r.height,0,1))*(spec.max-spec.min); }
 f.addEventListener('pointerdown',(e)=>{ e.preventDefault(); f.setPointerCapture(e.pointerId); set(fromY(e.clientY));
  const mv=(ev)=>set(fromY(ev.clientY));
  const up=()=>{ f.removeEventListener('pointermove',mv); f.removeEventListener('pointerup',up); f.removeEventListener('pointercancel',up); };
  f.addEventListener('pointermove',mv); f.addEventListener('pointerup',up); f.addEventListener('pointercancel',up); });
 f.addEventListener('keydown',(e)=>{ const st=(spec.max-spec.min)/40;
  if(e.key==='ArrowUp'){ e.preventDefault(); set(spec.get()+st); } else if(e.key==='ArrowDown'){ e.preventDefault(); set(spec.get()-st); } });
 paint(); return f;
}

/* ------------------------------------------------------------------ RACK */
function renderRack(){
 const box=$('racklist'); box.textContent='';
 proj.machines.forEach((m,i)=>{
  const T=MT[m.type];
  const card=el('div','rackcard'+(m.id===selId?' on':''));
  const hd=el('div','rackhd');
  const badge=el('span','badge',T.name); badge.style.background=T.color; hd.appendChild(badge);
  hd.appendChild(el('span','nm',m.name));
  const mb=el('button','sm','M'); mb.title='Mute'; mb.setAttribute('aria-pressed',m.mute?'true':'false');
  mb.addEventListener('click',(e)=>{ e.stopPropagation(); m.mute=!m.mute; eng.setMixer&&eng.setMixer(m.id); commit(); renderRack(); renderMixer(); });
  const sb=el('button','sm go','S'); sb.title='Solo'; sb.setAttribute('aria-pressed',m.solo?'true':'false');
  sb.addEventListener('click',(e)=>{ e.stopPropagation(); m.solo=!m.solo; eng.setMixer&&eng.setMixer(m.id); commit(); renderRack(); renderMixer(); });
  const dots=el('button','sm dots','...'); dots.title='More'; dots.setAttribute('aria-label','More for '+m.name);
  dots.addEventListener('click',(e)=>{ e.stopPropagation(); machineMenu(m,i); });
  hd.appendChild(mb); hd.appendChild(sb); hd.appendChild(dots);
  card.appendChild(hd);
  const body=el('div','rackbody');
  body.appendChild(paramKnobs(T.params,m.params,(key,v)=>{ eng.setParam&&eng.setParam(m.id,key,v); commit(); },'knobrow'));
  card.appendChild(body);
  // selecting a card must NOT rebuild the rack: the rebuild detached the "..." button between its
  // own pointerdown and click, so the menu needed two taps on any card that was not already selected
  card.addEventListener('pointerdown',()=>{ if(selId===m.id)return; selId=m.id;
   box.querySelectorAll('.rackcard').forEach((c,j)=>c.classList.toggle('on',proj.machines[j]&&proj.machines[j].id===selId));
   renderChips(); renderStrip(); });
  box.appendChild(card);
 });
 if(!proj.machines.length)box.appendChild(el('p','muted','The rack is empty. Add a machine.'));
}
function machineMenu(m,i){
 openSheet(m.name,(box)=>{
  sAct(box,'Edit pattern',()=>{ selId=m.id; setView('pattern'); renderAll(); });
  sAct(box,'Rename',()=>renameMachine(m));
  if(i>0)sAct(box,'Move up',()=>{ proj.machines.splice(i-1,0,proj.machines.splice(i,1)[0]); commit(); renderAll(); });
  if(i<proj.machines.length-1)sAct(box,'Move down',()=>{ proj.machines.splice(i+1,0,proj.machines.splice(i,1)[0]); commit(); renderAll(); });
  sAct(box,'Remove machine',()=>{ if(!confirm('Remove '+m.name+'?'))return;
   const at=proj.machines.indexOf(m); if(at>=0)proj.machines.splice(at,1);
   delete proj.song.tracks[m.id]; if(selId===m.id)selId=(proj.machines[0]||{}).id||null;
   eng.rebuild&&eng.rebuild(); commit(); renderAll(); },'danger');
 });
}
function renameMachine(m){
 openSheet('Rename',(box)=>{
  const inp=el('input'); inp.type='text'; inp.value=m.name; inp.spellcheck=false;
  sRow(box,'Name',inp);
  sAct(box,'Save',()=>{ m.name=inp.value.trim()||m.name; commit(); renderAll(); });
  setTimeout(()=>{ inp.focus(); inp.select(); },40);
 });
}
function addMachineSheet(){
 openSheet('Add machine',(box)=>{
  for(const type of Studio.MACHINE_ORDER)sAct(box,MT[type].name,()=>{
   const m=Studio.newMachine(type); proj.machines.push(m); selId=m.id;
   eng.rebuild&&eng.rebuild(); commit(); renderAll(); say(MT[type].name+' added'); });
 });
}

/* ------------------------------------------------------------------ PATTERN */
let gridEls=null;
const stepW=()=>isPhone()?26:22;
const labW=()=>isPhone()?62:74;
function rowHFor(kind){ const ph=isPhone();
 if(kind==='drum')return ph?40:26;
 if(kind==='lights')return ph?32:18;
 return ph?20:14; }
function rowsFor(m){
 const kind=kindOf(m);
 if(kind==='drum')return MT[m.type].pads.map((p,i)=>({n:i,label:p})).reverse();
 if(kind==='lights')return Studio.LIGHT_KEYS.map((k,i)=>({n:i,label:k.kind==='hit'?'HIT':k.val,
   swatch:k.kind==='palette'?palSolid(k.val):null, band:k.kind==='palette'?'#151318':(k.kind==='hit'?'#1d1418':null)}));   // looks at the top in pad order: a phone shows the first lanes only (Lloyd, 2026-09-05)
 const out=[]; for(let n=96;n>=24;n--)out.push({n,label:noteName(n),black:isBlack(n),c:(n%12===0)});
 return out;
}
const noteLen=()=>parseInt($('notelen').value,10)||1;

function renderPatternHead(){
 const m=sel(), badge=$('patmach'), selp=$('patsel'), bank=$('bank');
 if(!m){ badge.textContent='-'; badge.style.background='#333'; return; }
 badge.textContent=m.name; badge.style.background=MT[m.type].color; badge.title=m.name+' - '+MT[m.type].name;
 selp.textContent='';
 for(const name of Studio.PATTERN_NAMES){ const p=m.patterns[name];
  const o=el('option',null,name+(p&&p.notes.length?' *':'')); o.value=name; selp.appendChild(o); }
 selp.value=m.curPat;
 bank.textContent='';
 for(const name of Studio.PATTERN_NAMES){ const p=m.patterns[name];
  const b=el('button','sm'+(p&&p.notes.length?' has':''),name);
  b.setAttribute('aria-pressed',m.curPat===name?'true':'false');
  b.title='Pattern '+name+(p?' ('+p.bars+' bar'+(p.bars>1?'s':'')+', '+p.notes.length+' notes)':' (empty)');
  b.addEventListener('click',()=>pickPattern(name)); bank.appendChild(b); }
 $('bars').value=String(m.patterns[m.curPat].bars);
}
function pickPattern(name){ const m=sel(); if(!m)return;
 if(!m.patterns[name])m.patterns[name]=Studio.newPattern(m.type,1);
 m.curPat=name; commit(); renderPatternHead(); renderPattern(); renderSong(); }
function stepPattern(d){ const m=sel(); if(!m)return;
 const i=Studio.PATTERN_NAMES.indexOf(m.curPat);
 pickPattern(Studio.PATTERN_NAMES[clamp(i+d,0,Studio.PATTERN_NAMES.length-1)]); }

function renderPattern(){
 const wrap=$('patwrap'), m=sel();
 const keep=gridEls?{l:gridEls.scroll.scrollLeft,t:gridEls.scroll.scrollTop,id:gridEls.mid}:null;
 wrap.textContent=''; gridEls=null;
 if(!m){ wrap.appendChild(el('p','muted','Add a machine in the RACK view first.')); return; }
 const pat=m.patterns[m.curPat];
 const kind=kindOf(m), rows=rowsFor(m), ROWH=rowHFor(kind), STEPW=stepW(), LW=labW();
 const steps=Studio.patternSteps(pat), W=steps*STEPW, H=rows.length*ROWH;

 const top=el('div','gridtop'); const cor=el('div','corner'); cor.style.width=LW+'px'; top.appendChild(cor);
 const ruler=el('div','ruler'); const rin=el('div','rin'); rin.style.width=W+'px';
 for(let s=0;s<steps;s+=4){ const b=el('div','bl'+(s%SPB===0?' bar':'')); b.style.left=(s*STEPW)+'px';
  if(s%SPB===0)b.textContent=String(s/SPB+1); rin.appendChild(b); }
 ruler.appendChild(rin); top.appendChild(ruler); wrap.appendChild(top);

 const mid=el('div','gridmid');
 const lbls=el('div','rowlbls'); lbls.style.width=LW+'px';
 const lin=el('div','rin'); lin.style.height=H+'px';
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
 const head=el('div','playhead'); gin.appendChild(head);
 scroll.appendChild(gin); mid.appendChild(scroll); wrap.appendChild(mid);

 const lane=el('div','lanewrap');
 const lcor=el('div','corner',kind==='lights'?'Level':'Vel'); lcor.style.width=LW+'px'; lane.appendChild(lcor);
 const lscroll=el('div','lanescroll'); const lanein=el('div','lanein'); lanein.style.width=W+'px';
 lscroll.appendChild(lanein); lane.appendChild(lscroll); wrap.appendChild(lane);

 const rowIndex=(n)=>rows.findIndex(r=>r.n===n);
 function drawNotes(){ notesLayer.textContent='';
  for(const q of pat.notes){ const i=rowIndex(q.n); if(i<0)continue;
   const d=el('div','note'); d.style.left=(q.s*STEPW)+'px'; d.style.top=(i*ROWH)+'px';
   d.style.width=Math.max(5,q.l*STEPW-1)+'px'; d.style.height=(ROWH-1)+'px';
   const k=Studio.LIGHT_KEYS[q.n];
   d.style.background=kind==='lights'?(k&&k.kind==='palette'?palSolid(k.val):MT[m.type].color):MT[m.type].color;
   const v=el('div','vbar'); v.style.width=Math.round(clamp(q.v,0,1)*100)+'%'; d.appendChild(v);
   d.title=(kind==='synth'?noteName(q.n):rows[i].label)+'  step '+(q.s+1)+'  vel '+fix(q.v);
   notesLayer.appendChild(d); } }
 function drawLane(){ lanein.textContent='';
  for(let s=0;s<=steps;s+=4){ const t=el('div','lanetick'+(s%SPB===0?' bar':'')); t.style.left=(s*STEPW)+'px'; lanein.appendChild(t); }
  if(kind==='lights'){ const lv=pat.level||[];
   for(let s=0;s<steps;s++){ const v=lv[s]; if(v==null)continue;
    const b=el('div','lanebar'); b.style.left=(s*STEPW+1)+'px'; b.style.width=(STEPW-2)+'px';
    b.style.height=Math.max(2,clamp(v,0,1)*100)+'%'; lanein.appendChild(b); } }
  else { const byStep={}; for(const q of pat.notes)byStep[q.s]=Math.max(byStep[q.s]||0,q.v);
   for(const s in byStep){ const b=el('div','lanebar'); b.style.left=(s*STEPW+1)+'px'; b.style.width=(STEPW-2)+'px';
    b.style.background='var(--accent)'; b.style.height=Math.max(3,byStep[s]*100)+'%'; lanein.appendChild(b); } } }
 drawNotes(); drawLane();

 scroll.addEventListener('scroll',()=>{ lin.style.transform='translateY('+(-scroll.scrollTop)+'px)';
  rin.style.transform='translateX('+(-scroll.scrollLeft)+'px)'; lanein.style.transform='translateX('+(-scroll.scrollLeft)+'px)'; });

 const at=(e)=>{ const r=gin.getBoundingClientRect();
  return { s:Math.floor((e.clientX-r.left)/STEPW), x:e.clientX-r.left, i:Math.floor((e.clientY-r.top)/ROWH) }; };
 const canLen=(kind==='synth');
 const toggleAt=(p)=>{ if(p.i<0||p.i>=rows.length||p.s<0||p.s>=steps)return null;
  const n=rows[p.i].n; const hit=pat.notes.find(q=>q.n===n&&p.s>=q.s&&p.s<q.s+q.l);
  if(hit){ Studio.removeNote(pat,hit.s,hit.n); commit(); drawNotes(); drawLane(); return null; }
  const note=Studio.addNote(pat,{s:p.s,n,v:velocity,l:canLen?noteLen():1});
  commit(); drawNotes(); drawLane(); return note; };
 scroll.addEventListener('contextmenu',(e)=>{ e.preventDefault(); const p=at(e);
  if(p.i<0||p.i>=rows.length)return; const n=rows[p.i].n;
  const hit=pat.notes.find(q=>q.n===n&&p.s>=q.s&&p.s<q.s+q.l);
  if(hit){ Studio.removeNote(pat,hit.s,hit.n); commit(); drawNotes(); drawLane(); } });
 // touch taps toggle a step and leave the two-way scroll alone; a mouse also drags note lengths
 scroll.addEventListener('pointerdown',(e)=>{
  if(e.pointerType!=='mouse'){ const sx=e.clientX, sy=e.clientY;
   const up=(ev)=>{ scroll.removeEventListener('pointerup',up); scroll.removeEventListener('pointercancel',up);
    if(Math.abs(ev.clientX-sx)<9&&Math.abs(ev.clientY-sy)<9)toggleAt(at(ev)); };
   scroll.addEventListener('pointerup',up); scroll.addEventListener('pointercancel',up); return; }
  if(e.button!==0)return;
  const p=at(e); if(p.i<0||p.i>=rows.length||p.s<0||p.s>=steps)return;
  const n=rows[p.i].n; const hit=pat.notes.find(q=>q.n===n&&p.s>=q.s&&p.s<q.s+q.l);
  if(hit){ const edge=(hit.s+hit.l)*STEPW;
   if(canLen&&p.x>edge-8){ dragLength(hit); return; }
   if(e.shiftKey){ dragVel(hit); return; }
   Studio.removeNote(pat,hit.s,hit.n); commit(); drawNotes(); drawLane(); return; }
  const note=Studio.addNote(pat,{s:p.s,n,v:velocity,l:canLen?noteLen():1});
  commit(); drawNotes(); drawLane(); if(canLen&&note)dragLength(note); });
 function dragLength(note){ const mv=(ev)=>{ const p=at(ev); note.l=clamp(p.s-note.s+1,1,steps-note.s); drawNotes(); };
  const up=()=>{ document.removeEventListener('pointermove',mv); document.removeEventListener('pointerup',up); commit(); };
  document.addEventListener('pointermove',mv); document.addEventListener('pointerup',up); }
 function dragVel(note){ const start=note.v; let base=null;
  const mv=(ev)=>{ if(base==null)base=ev.clientY; note.v=clamp(start+(base-ev.clientY)/120,0.05,1); drawNotes(); drawLane(); };
  const up=()=>{ document.removeEventListener('pointermove',mv); document.removeEventListener('pointerup',up); commit(); };
  document.addEventListener('pointermove',mv); document.addEventListener('pointerup',up); }

 function laneSet(e){ const r=lanein.getBoundingClientRect(); const s=Math.floor((e.clientX-r.left)/STEPW);
  if(s<0||s>=steps)return; const v=clamp(1-(e.clientY-r.top)/r.height,0,1);
  if(kind==='lights'){ if(!pat.level)pat.level=new Array(steps).fill(null); pat.level[s]=e.altKey?null:v; }
  else { let any=false; for(const q of pat.notes)if(q.s===s){ q.v=Math.max(0.05,v); any=true; } if(!any)return; }
  commit(); drawLane(); drawNotes(); }
 lscroll.addEventListener('pointerdown',(e)=>{ e.preventDefault(); lscroll.setPointerCapture(e.pointerId); laneSet(e);
  const mv=(ev)=>laneSet(ev);
  const up=()=>{ lscroll.removeEventListener('pointermove',mv); lscroll.removeEventListener('pointerup',up); lscroll.removeEventListener('pointercancel',up); };
  lscroll.addEventListener('pointermove',mv); lscroll.addEventListener('pointerup',up); lscroll.addEventListener('pointercancel',up); });

 gridEls={scroll,head,gin,drawNotes,drawLane,steps,ROWH,rows,mid:m.id,STEPW};
 if(keep&&keep.id===m.id){ scroll.scrollLeft=keep.l; scroll.scrollTop=keep.t; }
 else if(kind==='synth')scroll.scrollTop=Math.max(0,(96-72)*ROWH-40);
 scroll.dispatchEvent(new Event('scroll'));
}

/* ------------------------------------------------------------------ SONG */
const BARW=()=>isPhone()?34:28;
let songEls=null;
function renderSong(){
 const wrap=$('songwrap'); wrap.textContent=''; songEls=null;
 const BW=BARW();
 const bars=Math.max(Studio.songLengthBars(proj),proj.song.bars||1)+8;
 const laneW=bars*BW, nameW=110, rowW=nameW+laneW;
 const top=el('div','songtop'); const cor=el('div','corner'); cor.style.width=nameW+'px'; top.appendChild(cor);
 const ruler=el('div','ruler'); const rin=el('div','rin'); rin.style.width=laneW+'px';
 for(let b=0;b<bars;b++){ if(b%4)continue; const d=el('div','bl bar');
  d.style.left=(b*BW)+'px'; d.textContent=String(b+1); rin.appendChild(d); }
 ruler.appendChild(rin); top.appendChild(ruler); wrap.appendChild(top);

 const scroll=el('div','songscroll'); const sin=el('div','songin'); sin.style.width=rowW+'px';
 const laneBg='repeating-linear-gradient(90deg,#22262c 0 1px,transparent 1px '+(BW*4)+'px),'+
  'repeating-linear-gradient(90deg,#16181c 0 1px,transparent 1px '+BW+'px)';
 proj.machines.forEach((m)=>{
  const row=el('div','songrow'); row.style.width=rowW+'px';
  const nm=el('div','songname'); const dot=el('span','dot'); dot.style.background=MT[m.type].color;
  nm.appendChild(dot); const t=el('span',null,m.name); t.title=m.name+' - '+MT[m.type].name; nm.appendChild(t);
  nm.addEventListener('pointerdown',()=>{ selId=m.id; renderChips(); renderStrip(); renderSong(); });
  row.appendChild(nm);
  const lane=el('div','songlane'); lane.style.width=laneW+'px'; lane.style.backgroundImage=laneBg;
  for(const b of Studio.track(proj,m.id)){
   const d=el('div','block'+(selBlock&&selBlock.mid===m.id&&selBlock.bar===b.bar?' sel':''));
   d.style.left=(b.bar*BW+1)+'px'; d.style.width=(b.len*BW-2)+'px'; d.style.background=MT[m.type].color;
   d.appendChild(document.createTextNode(b.pat));
   d.title=m.name+'  pattern '+b.pat+'  bar '+(b.bar+1)+'  '+b.len+' bars';
   const grip=el('div','grip'); d.appendChild(grip);
   grip.addEventListener('pointerdown',(e)=>{ e.stopPropagation(); e.preventDefault(); grip.setPointerCapture(e.pointerId);
    const r=lane.getBoundingClientRect();
    const mv=(ev)=>{ const bar=Math.floor((ev.clientX-r.left)/BW); b.len=Math.max(1,bar-b.bar+1);
     proj.song.bars=Math.max(proj.song.bars,b.bar+b.len); d.style.width=(b.len*BW-2)+'px'; };
    const up=()=>{ grip.removeEventListener('pointermove',mv); grip.removeEventListener('pointerup',up); commit(); renderSong(); };
    grip.addEventListener('pointermove',mv); grip.addEventListener('pointerup',up); });
   d.addEventListener('pointerdown',(e)=>{ e.stopPropagation(); selId=m.id; selBlock={mid:m.id,bar:b.bar}; renderSong(); renderChips(); });
   d.addEventListener('dblclick',(e)=>{ e.stopPropagation(); selId=m.id; m.curPat=b.pat; setView('pattern'); renderAll(); });
   lane.appendChild(d); }
  lane.addEventListener('pointerdown',(e)=>{ if(e.target!==lane)return;
   const r=lane.getBoundingClientRect(); const bar=Math.floor((e.clientX-r.left)/BW);
   const p=m.patterns[m.curPat]; if(!p)return;
   Studio.placeBlock(proj,m.id,bar,m.curPat,p.bars); selId=m.id; selBlock={mid:m.id,bar};
   commit(); renderSong(); renderChips(); });
  row.appendChild(lane); sin.appendChild(row);
 });
 if(!proj.machines.length)sin.appendChild(el('p','muted','No machines yet.'));
 const head=el('div','playhead'); head.style.left=nameW+'px'; sin.appendChild(head);
 scroll.appendChild(sin); wrap.appendChild(scroll);
 scroll.addEventListener('scroll',()=>{ rin.style.transform='translateX('+(-scroll.scrollLeft)+'px)'; });
 ruler.addEventListener('pointerdown',(e)=>{ const r=rin.getBoundingClientRect();
  eng.seek&&eng.seek(Math.max(0,(e.clientX-r.left)/BW)*SPB); });
 songEls={scroll,head,nameW,BW};
}
function deleteBlock(){ if(!selBlock){ say('Tap a block first'); return; }
 Studio.removeBlock(proj,selBlock.mid,selBlock.bar); selBlock=null; commit(); renderSong(); }

/* ------------------------------------------------------------------ MIXER */
function renderMixer(){
 const wrap=$('mixwrap'); wrap.textContent='';
 for(const m of proj.machines){
  const s=el('div','strip'+(m.id===selId?' on':''));
  const t=el('div','striptype',MT[m.type].name); t.style.background=MT[m.type].color; s.appendChild(t);
  const nm=el('div','stripname',m.name); nm.title=m.name; s.appendChild(nm);
  const vv=el('div','kval',fix(m.vol));
  s.appendChild(fader({name:m.name+' volume',min:0,max:1,get:()=>m.vol,set:(v)=>{ m.vol=v; vv.textContent=fix(v); },
   after:()=>{ eng.setMixer&&eng.setMixer(m.id); commit(); }}));
  s.appendChild(vv);
  const pk=el('div','knobs');
  pk.appendChild(knob({name:'Pan',min:-1,max:1,def:0,get:()=>m.pan,set:(v)=>{ m.pan=v; eng.setMixer&&eng.setMixer(m.id); commit(); },
   fmt:(v)=>Math.abs(v)<0.02?'C':(v<0?'L':'R')+Math.round(Math.abs(v)*100)}));
  s.appendChild(pk);
  const row=el('div','mrow');
  const mb=el('button',null,'Mute'); mb.setAttribute('aria-pressed',m.mute?'true':'false');
  mb.addEventListener('click',()=>{ m.mute=!m.mute; eng.setMixer&&eng.setMixer(m.id); commit(); renderMixer(); renderRack(); });
  const sb=el('button','go','Solo'); sb.setAttribute('aria-pressed',m.solo?'true':'false');
  sb.addEventListener('click',()=>{ m.solo=!m.solo; eng.setMixer&&eng.setMixer(m.id); commit(); renderMixer(); renderRack(); });
  row.appendChild(mb); row.appendChild(sb); s.appendChild(row);
  const sends=el('div','knobs');
  sends.appendChild(knob({name:'Delay',min:0,max:1,def:0,get:()=>m.send.delay,set:(v)=>{ m.send.delay=v; eng.setMixer&&eng.setMixer(m.id); commit(); }}));
  sends.appendChild(knob({name:'Reverb',min:0,max:1,def:0,get:()=>m.send.reverb,set:(v)=>{ m.send.reverb=v; eng.setMixer&&eng.setMixer(m.id); commit(); }}));
  s.appendChild(sends);
  s.addEventListener('pointerdown',()=>{ if(selId===m.id)return; selId=m.id;
   wrap.querySelectorAll('.strip').forEach((c,j)=>c.classList.toggle('on',proj.machines[j]&&proj.machines[j].id===selId));
   renderChips(); renderStrip(); });
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

/* ------------------------------------------------------------------ FX */
function renderFx(){
 const wrap=$('fxwrap'); wrap.textContent=''; const m=sel(), badge=$('fxmach');
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
  wrap.appendChild(box);
 });
 const mb=el('div','fxslot'); mb.appendChild(el('h3',null,'Master sends'));
 mb.appendChild(el('label',null,'Delay bus'));
 mb.appendChild(paramKnobs(FXT.delay.params,proj.master.delay.params,()=>{ eng.setFx&&eng.setFx(null,'delay'); commit(); }));
 mb.appendChild(el('label',null,'Reverb bus'));
 mb.appendChild(paramKnobs(FXT.reverb.params,proj.master.reverb.params,()=>{ eng.setFx&&eng.setFx(null,'reverb'); commit(); }));
 wrap.appendChild(mb);
}

/* ------------------------------------------------------------------ the play drawer */
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
const BASE=48;
let keyMap={}, keyLetter={};
function rebuildKeyMap(){ const kind=kindOf(sel()); keyMap={}; keyLetter={};
 if(kind==='synth'){ WHITE_KEYS.forEach((k,i)=>keyMap[k]=BASE+octave*12+WHITE_OFF[i]);
  BLACK_KEYS.forEach((k,i)=>keyMap[k]=BASE+octave*12+BLACK_OFF[i]);
  WHITE2_KEYS.forEach((k,i)=>keyMap[k]=BASE+octave*12+WHITE2_OFF[i]);
  BLACK2_KEYS.forEach((k,i)=>keyMap[k]=BASE+octave*12+BLACK2_OFF[i]); }
 else if(kind==='drum')WHITE_KEYS.slice(0,8).forEach((k,i)=>keyMap[k]=i);
 for(const k in keyMap)keyLetter[keyMap[k]]=k; }

function renderChips(){
 const box=$('machtabs'); box.textContent='';
 for(const m of proj.machines){ const b=el('button');
  const d=el('span','dot'); d.style.background=MT[m.type].color; b.appendChild(d);
  b.appendChild(document.createTextNode(m.name));
  b.setAttribute('aria-pressed',m.id===selId?'true':'false');
  b.addEventListener('click',()=>{ selId=m.id; renderChips(); renderStrip();
   if(view==='pattern'){ renderPatternHead(); renderPattern(); }
   if(view==='fx')renderFx(); if(view==='rack')renderRack(); if(view==='mixer')renderMixer(); });
  box.appendChild(b); }
}
function setDrawer(open){
 document.body.classList.toggle('drawer-shut',!open);
 $('drawertog').setAttribute('aria-expanded',open?'true':'false');
 $('drawertog').innerHTML=open?ICON.down:ICON.up;
 $('drawertog').title=open?'Hide the keys':'Show the keys';
 try{ localStorage.setItem(LSDRAWER,open?'open':'shut'); }catch(e){}
 if(open)renderStrip();
}
const drawerOpen=()=>!document.body.classList.contains('drawer-shut');

function renderStrip(){
 rebuildKeyMap();
 const host=$('stripplay'); host.textContent='';
 const m=sel(), kind=kindOf(m);
 $('octbox').style.display=kind==='synth'?'':'none';
 document.body.classList.toggle('lightsdesk',kind==='lights');   // the light pads want a taller drawer
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
 const b=BASE+octave*12;
 // a phone gets one octave with big keys and the octave stepper; a desktop gets three
 const lo=isPhone()?b:b-12, hi=isPhone()?b+11:b+25;
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
 kb.addEventListener('pointerdown',(e)=>{ const t=e.target.closest('[data-n]'); if(!t)return; e.preventDefault();
  const n=+t.dataset.n; pressNote(n);
  const up=()=>{ releaseNote(n); kb.removeEventListener('pointerup',up); kb.removeEventListener('pointercancel',up); };
  kb.addEventListener('pointerup',up); kb.addEventListener('pointercancel',up); });
}
function buildPads(host,m){
 const g=el('div','padgrid padabs'); g.style.gridTemplateColumns=isPhone()?'repeat(2,1fr)':'repeat(4,1fr)';
 MT[m.type].pads.forEach((name,i)=>{ const b=el('button','pad',name); b.dataset.n=i;
  b.appendChild(el('span','k',(WHITE_KEYS[i]||'').toUpperCase()));
  b.addEventListener('pointerdown',(e)=>{ e.preventDefault(); pressNote(i); setTimeout(()=>releaseNote(i),60); });
  g.appendChild(b); });
 host.appendChild(g);
}
// the light pads: side by side on a desktop, one scrolling stack on a phone (three narrow columns
// on a 390 px screen left every pad label truncated)
function buildLights(host){
 if(isPhone())return buildLightsPhone(host);
 const cols=el('div','lightcols');
 const c1=el('div','lightcol'); c1.appendChild(el('label',null,'Look'));
 const lg=el('div','padgrid'); lg.style.gridTemplateColumns=isPhone()?'repeat(2,1fr)':'repeat(3,1fr)';
 NGV.LOOK_NAMES.forEach((name,i)=>{ const b=el('button','pad',name);
  const desc=(NGV.LOOKS[i]||[])[1]; if(desc)b.title=desc;
  b.dataset.look=name; b.setAttribute('aria-pressed',L.state.look===name?'true':'false');
  b.appendChild(el('span','k',(LOOK_KEYS[i]||'').toUpperCase()));
  b.addEventListener('click',()=>lightPress('look',name)); lg.appendChild(b); });
 c1.appendChild(lg); cols.appendChild(c1);
 const c2=el('div','lightcol'); c2.appendChild(el('label',null,'Palette'));
 const pg=el('div','padgrid'); pg.style.gridTemplateColumns=isPhone()?'repeat(2,1fr)':'repeat(5,1fr)';
 NGV.PALETTE_NAMES.forEach((name,i)=>{ const b=el('button','palpad'); b.style.background=palCss(name);
  b.dataset.pal=name; b.setAttribute('aria-pressed',L.state.palette===name?'true':'false');
  b.appendChild(el('span',null,name)); b.appendChild(el('b',null,(PAL_KEYS[i]||'').toUpperCase()));
  b.addEventListener('click',()=>lightPress('palette',name)); pg.appendChild(b); });
 c2.appendChild(pg); cols.appendChild(c2);
 const c3=el('div','lightside');
 const lv=el('label'); lv.innerHTML='Level <span class="val" id="lvlval">'+fix(L.state.level)+'</span>'; c3.appendChild(lv);
 const r=el('input'); r.type='range'; r.id='lvl'; r.min=0; r.max=1; r.step=0.01; r.value=L.state.level;
 r.addEventListener('input',()=>lightPress('level',parseFloat(r.value)));
 c3.appendChild(r);
 const hb=el('button',null,'HIT'); hb.id='hitbtn'; hb.title='Space';
 hb.addEventListener('pointerdown',(e)=>{ e.preventDefault(); lightPress('hit',true);
  hb.classList.add('hit'); setTimeout(()=>hb.classList.remove('hit'),140); });
 c3.appendChild(hb); cols.appendChild(c3);
 host.appendChild(cols);
}
function buildLightsPhone(host){
 const stack=el('div','lightstack');
 const row=el('div','hitrow');
 const lv=el('label'); lv.innerHTML='Level <span class="val" id="lvlval">'+fix(L.state.level)+'</span>';
 const r=el('input'); r.type='range'; r.id='lvl'; r.min=0; r.max=1; r.step=0.01; r.value=L.state.level;
 r.addEventListener('input',()=>lightPress('level',parseFloat(r.value)));
 const col=el('div','lvlcol'); col.appendChild(lv); col.appendChild(r);
 const hb=el('button',null,'HIT'); hb.id='hitbtn';
 hb.addEventListener('pointerdown',(e)=>{ e.preventDefault(); lightPress('hit',true);
  hb.classList.add('hit'); setTimeout(()=>hb.classList.remove('hit'),140); });
 row.appendChild(col); row.appendChild(hb); stack.appendChild(row);
 stack.appendChild(el('label',null,'Look'));
 const lg=el('div','padgrid'); lg.style.gridTemplateColumns='repeat(3,1fr)';
 NGV.LOOK_NAMES.forEach((name)=>{ const b=el('button','pad',name); b.dataset.look=name;
  b.setAttribute('aria-pressed',L.state.look===name?'true':'false');
  b.addEventListener('click',()=>lightPress('look',name)); lg.appendChild(b); });
 stack.appendChild(lg);
 stack.appendChild(el('label',null,'Palette'));
 const pg=el('div','padgrid'); pg.style.gridTemplateColumns='repeat(3,1fr)';
 NGV.PALETTE_NAMES.forEach((name)=>{ const b=el('button','palpad'); b.style.background=palCss(name);
  b.dataset.pal=name; b.setAttribute('aria-pressed',L.state.palette===name?'true':'false');
  b.appendChild(el('span',null,name));
  b.addEventListener('click',()=>lightPress('palette',name)); pg.appendChild(b); });
 stack.appendChild(pg);
 host.appendChild(stack);
}
function refreshLightPads(){
 const host=$('stripplay');
 host.querySelectorAll('[data-look]').forEach(b=>b.setAttribute('aria-pressed',L.state.look===b.dataset.look?'true':'false'));
 host.querySelectorAll('[data-pal]').forEach(b=>b.setAttribute('aria-pressed',L.state.palette===b.dataset.pal?'true':'false'));
 const lv=$('lvlval'), r=$('lvl'); if(lv)lv.textContent=fix(L.state.level); if(r&&document.activeElement!==r)r.value=L.state.level;
}
function lightPress(kind,val){
 let wrote=null;
 try{ wrote=L.press(kind,val); }catch(e){}
 if(L.stub||!wrote){ if(record&&eng.playing){ if(kind==='level')recordLightLevel(val); else recordLightCue(kind,val); } }
 refreshLightPads(); const m=sel(); if(view==='pattern'&&m&&m.type==='lights')renderPattern();
}
function lightsMachine(){ return proj.machines.find(m=>m.type==='lights')||null; }
function recordLightCue(kind,val){ const m=lightsMachine(); if(!m)return; const p=patternForWrite(m); if(!p)return;
 const n=Studio.lightKeyIndex(kind,val); if(n<0)return; Studio.addNote(p.pat,{s:p.step,n,v:1,l:1}); commit(); }
function recordLightLevel(v){ const m=lightsMachine(); if(!m)return; const p=patternForWrite(m); if(!p||!p.pat.level)return;
 p.pat.level[p.step]=v; commit(); }

/* ------------------------------------------------------------------ live play and record */
function patternForWrite(m){
 let step=0, pat=m.patterns[m.curPat];
 let p; try{ p=eng.pos(); }catch(e){ p={step:0}; }
 if(eng.mode==='song'){
  const bar=Math.floor(p.step/SPB);
  const blk=Studio.track(proj,m.id).find(b=>bar>=b.bar&&bar<b.bar+b.len);
  if(blk){ pat=m.patterns[blk.pat]; step=p.step-blk.bar*SPB; } else step=p.step;
 } else step=p.step;
 if(!pat)return null;
 const n=Studio.patternSteps(pat), q=quant||1;
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
  if(w&&w.pat===h.pat){ const ps=Studio.patternSteps(h.pat); const len=((w.step-h.start)%ps+ps)%ps;
   h.note.l=Math.max(1,Math.min(len||1,ps-h.note.s)); commit(); if(view==='pattern')renderPatternNotes(); } }
 delete held[n]; paintHeld();
}
function renderPatternNotes(){ if(gridEls&&gridEls.mid===selId){ gridEls.drawNotes(); gridEls.drawLane(); } else renderPattern(); }
function paintHeld(){ $('stripplay').querySelectorAll('.piano [data-n]').forEach(d=>d.classList.toggle('held',held[+d.dataset.n]!=null)); }

/* ------------------------------------------------------------------ transport */
function setPlaying(on){ $('play').textContent=on?'Pause':'Play'; $('play').setAttribute('aria-pressed',on?'true':'false'); }
function doPlay(){
 try{ eng.init&&eng.init(); }catch(e){ say('Audio could not start: '+e.message,5000); }
 if(eng.playing)eng.pause(); else eng.play({mode:eng.mode||'pattern'});
 setPlaying(!!eng.playing);
}
function doStop(){ try{ eng.stop(); }catch(e){} setPlaying(false); }
function setMode(mode){ eng.mode=mode; const was=eng.playing; try{ eng.stop(); }catch(e){}
 $('modebtn').textContent=mode==='pattern'?'Pattern':'Song';
 commit(); if(was){ try{ eng.play({mode}); }catch(e){} } setPlaying(!!eng.playing); }
function setRecord(on){ record=on; $('rec').setAttribute('aria-pressed',on?'true':'false');
 try{ L.setRecord&&L.setRecord(on,quant); }catch(e){} }
function setBpm(v){ proj.bpm=clamp(Math.round(v)||124,60,200); $('bpmval').textContent=String(proj.bpm); commit(); }
function setQuant(v){ quant=+v||1; $('quant').value=String(quant); try{ L.setRecord&&L.setRecord(record,quant); }catch(e){} }
function setOctave(o){ octave=clamp(o,-2,2); $('octval').textContent=(octave>0?'+':'')+octave; renderStrip(); }

/* ------------------------------------------------------------------ views and nav */
const VIEWS=[['rack','Rack'],['pattern','Pattern'],['song','Song'],['mixer','Mixer'],['fx','FX']];
function setView(v){
 if(v==='hall'){ document.body.classList.add('hallview'); view='hall'; paintNav(); return; }
 document.body.classList.remove('hallview'); view=v;
 VIEWS.forEach(([n])=>$('view-'+n).classList.toggle('on',n===v));
 paintNav();
 if(v==='pattern'){ renderPatternHead(); renderPattern(); }
 else if(v==='song')renderSong(); else if(v==='mixer')renderMixer();
 else if(v==='fx')renderFx(); else renderRack();
}
function paintNav(){
 document.querySelectorAll('#nav button,#tabs button').forEach(b=>b.setAttribute('aria-pressed',b.dataset.v===view?'true':'false'));
}
function buildNav(){
 const nav=$('nav'); nav.textContent='';
 for(const [v,label] of VIEWS.concat([['hall','Hall']])){
  const b=el('button'); b.dataset.v=v; b.innerHTML=ICON[v==='hall'?'hall':v];
  b.appendChild(el('span',null,label)); b.title=label;
  b.addEventListener('click',()=>setView(v)); nav.appendChild(b); }
 const tabs=$('tabs'); tabs.textContent='';
 for(const [v,label] of VIEWS){ const b=el('button',null,label.toUpperCase()); b.dataset.v=v;
  b.addEventListener('click',()=>setView(v)); tabs.appendChild(b); }
}

/* ------------------------------------------------------------------ the more sheet */
function moreSheet(){
 openSheet('Studio',(box)=>{
  const nm=el('input'); nm.type='text'; nm.value=proj.name; nm.spellcheck=false;
  nm.addEventListener('input',()=>{ proj.name=nm.value; $('namebtn').firstChild.textContent=nm.value||'untitled'; autosave(); });
  sRow(box,'Project',nm);
  sSeg(box,'Play',[['pattern','Pattern'],['song','Song']],()=>eng.mode||'pattern',(v)=>setMode(v));
  sToggle(box,'Loop',()=>!!eng.loop,(v)=>{ eng.loop=v; $('loop').setAttribute('aria-pressed',v?'true':'false'); });
  const sw=el('input'); sw.type='range'; sw.min=0; sw.max=1; sw.step=0.01; sw.value=proj.swing||0;
  const swv=el('span','val',Math.round((proj.swing||0)*100)+'%');
  sw.addEventListener('input',()=>{ proj.swing=+sw.value; swv.textContent=Math.round(proj.swing*100)+'%'; commit(); });
  const swr=sRow(box,'Swing',sw); swr.appendChild(swv);
  const q=el('select'); [[1,'1/16'],[2,'1/8'],[4,'1/4 (beat)']].forEach(([v,t])=>{ const o=el('option',null,t); o.value=v; q.appendChild(o); });
  q.value=String(quant); q.addEventListener('change',()=>setQuant(q.value));
  sRow(box,'Quantise',q);
  if(!isPhone())sToggle(box,'Hall panel',()=>!document.body.classList.contains('simoff'),
   (v)=>document.body.classList.toggle('simoff',!v));
  sAct(box,'Save project',doSave);
  sAct(box,'Load project',doLoad);
  sAct(box,'Export show',doExport);
 });
}
function bpmSheet(){
 openSheet('Tempo',(box)=>{
  const inp=el('input'); inp.type='number'; inp.min=60; inp.max=200; inp.step=1; inp.value=proj.bpm;
  inp.addEventListener('input',()=>setBpm(+inp.value));
  sRow(box,'BPM',inp);
  const r=el('div','seg');
  [-10,-1,1,10].forEach(d=>{ const b=el('button',null,(d>0?'+':'')+d);
   b.addEventListener('click',()=>{ setBpm(proj.bpm+d); inp.value=proj.bpm; }); r.appendChild(b); });
  sRow(box,'Nudge',r);
  setTimeout(()=>inp.focus(),40);
 });
}

/* ------------------------------------------------------------------ save, load, export */
async function doSave(){
 proj.name=(proj.name||'').trim()||'untitled';
 if(!Studio.saveProject){ autosave(); say('Saved to this browser'); return; }
 try{ await Studio.saveProject(proj); say('Saved '+proj.name); }catch(e){ say('Save failed: '+e.message,5000); }
 autosave();
}
async function doLoad(){
 openSheet('Load a project',(box)=>{
  const list=el('div','list'); list.appendChild(el('p','muted','Looking...')); box.appendChild(list);
  (async()=>{ let names=[];
   try{ const r=await fetch('show/shows.json',{cache:'no-store'}); if(r.ok)names=await r.json(); }catch(e){}
   list.textContent='';
   if(!names.length){ list.appendChild(el('p','muted','Nothing saved yet.')); return; }
   for(const n of names){ const b=el('button','sact',n);
    b.addEventListener('click',async()=>{
     if(!Studio.loadProject){ say('export.js is not loaded'); return; }
     try{ const p=await Studio.loadProject(n); if(!p){ say('No project file for '+n); return; }
      proj=p; selId=(proj.machines[0]||{}).id||null; selBlock=null;
      eng.rebuild&&eng.rebuild(); commit(); closeSheet(); renderAll(); say('Loaded '+n);
     }catch(e){ say('Load failed: '+e.message,5000); } });
    list.appendChild(b); } })();
 });
}
async function doExport(){
 proj.name=(proj.name||'').trim()||'untitled';
 if(!Studio.exportShow){ say('export.js is not loaded',5000); return; }
 openSheet('Export',(box)=>{
  const txt=el('p','muted','Starting...'); box.appendChild(txt);
  const bar=el('div'); bar.id='pbar'; const fill=el('div'); fill.id='pbarfill'; bar.appendChild(fill); box.appendChild(bar);
  const done=el('div'); box.appendChild(done);
  (async()=>{ try{
    const res=await Studio.exportShow(proj,eng,proj.name,(t,p)=>{ txt.textContent=t; fill.style.width=Math.round((p||0)*100)+'%'; });
    fill.style.width='100%'; txt.textContent='Done.';
    const url=res&&res.url?res.url:('index.html?show='+encodeURIComponent(proj.name));
    const a=el('a',null,url); a.href=url; a.target='_blank'; a.style.color='var(--accent)';
    done.appendChild(el('p',null,'Play it in the hall:')); done.appendChild(a);
   }catch(e){ txt.textContent='Export failed: '+e.message; } })();
 });
}

/* ------------------------------------------------------------------ keyboard */
function typing(){ const a=document.activeElement; if(!a)return false;
 const t=a.tagName; return t==='INPUT'||t==='SELECT'||t==='TEXTAREA'||a.isContentEditable; }
document.addEventListener('keydown',(e)=>{
 if(e.key==='Escape'){ if(sheetOpen){ closeSheet(); return; } doStop(); return; }
 if(e.key==='Enter'&&!typing()){ e.preventDefault(); doPlay(); return; }
 if(typing()||sheetOpen)return;
 if(e.key==='R'&&e.shiftKey){ e.preventDefault(); setRecord(!record); return; }
 if((e.key==='Delete'||e.key==='Backspace')&&view==='song'){ e.preventDefault(); deleteBlock(); return; }
 if(e.repeat)return;
 const m=sel(); if(!m)return; const kind=kindOf(m), k=e.key.toLowerCase();
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
 if(kind==='synth'){ if(k==='['){ e.preventDefault(); setOctave(octave-1); return; }
  if(k===']'){ e.preventDefault(); setOctave(octave+1); return; } }
 const n=keyMap[k];
 if(n!=null){ e.preventDefault(); pressNote(n); }
});
document.addEventListener('keyup',(e)=>{ if(typing())return; const n=keyMap[e.key.toLowerCase()]; if(n!=null)releaseNote(n); });

/* ------------------------------------------------------------------ frame loop */
let frames=0;
function loop(){
 requestAnimationFrame(loop); frames++;
 let p; try{ p=eng.pos(); }catch(e){ p={step:0,t:0}; }
 $('pos').textContent=(Math.floor(p.step/SPB)+1)+':'+(Math.floor(p.step/4)%4+1);
 if(eng.playing!==($('play').textContent==='Pause'))setPlaying(!!eng.playing);
 let rms=0; try{ if(eng.analyser){ const o={}; eng.analyser.read(o); rms=o.rms||0; } }catch(e){}
 $('meterfill').style.width=Math.round(clamp(rms,0,1)*100)+'%';
 if(view==='pattern'&&gridEls){ const m=machine(gridEls.mid);
  if(m){ const pat=m.patterns[m.curPat]; const n=pat?Studio.patternSteps(pat):SPB;
   gridEls.head.style.left=((p.step%n)*gridEls.STEPW)+'px'; } }
 if(view==='song'&&songEls)songEls.head.style.left=(songEls.nameW+(p.step/SPB)*songEls.BW)+'px';
 if(L.tick&&(eng.playing||frames%4===0)){ try{ L.tick(); }catch(e){} }
 if(frames%6===0){ const st=L.state||{};
  $('simstate').textContent=(st.look||'-')+' / '+(st.palette||'-')+' / '+fix(st.level==null?1:st.level,2);
  const m=sel(); if(m&&kindOf(m)==='lights'&&drawerOpen())refreshLightPads(); }
 if(frames%2===0&&drawerOpen())paintFlashes();
}
function paintFlashes(){
 const m=sel(); if(!m)return; const now=performance.now(), host=$('stripplay'), kind=kindOf(m);
 if(kind==='drum')host.querySelectorAll('.pad[data-n]').forEach(b=>{
  b.classList.toggle('hit',(now-(flash[m.id+':'+b.dataset.n]||-1e9))<130); });
 else if(kind==='synth')host.querySelectorAll('.piano [data-n]').forEach(d=>{
  const n=+d.dataset.n; d.classList.toggle('held',held[n]!=null||(now-(flash[m.id+':'+n]||-1e9))<130); });
}

/* ------------------------------------------------------------------ boot */
function renderAll(){
 renderRack(); renderChips(); renderStrip();
 if(view==='pattern'){ renderPatternHead(); renderPattern(); }
 if(view==='song')renderSong(); if(view==='mixer')renderMixer(); if(view==='fx')renderFx();
 $('namebtn').firstChild.textContent=proj.name||'untitled';
 $('bpmval').textContent=String(proj.bpm);
}
function boot(){
 $('stop').innerHTML=ICON.stop; $('rec').innerHTML=ICON.rec; $('menubtn').innerHTML=ICON.menu;
 buildNav();
 const bars=$('bars'); for(let i=1;i<=Studio.MAX_BARS;i++){ const o=el('option',null,i+' bar'+(i>1?'s':'')); o.value=i; bars.appendChild(o); }
 bars.addEventListener('change',()=>{ const m=sel(); if(!m)return;
  Studio.resizePattern(m.patterns[m.curPat],+bars.value); commit(); renderPattern(); renderSong(); });
 const nl=$('notelen'); [[1,'1/16'],[2,'1/8'],[4,'1/4'],[8,'1/2'],[16,'1 bar']].forEach(([v,t])=>{ const o=el('option',null,t); o.value=v; nl.appendChild(o); });
 nl.value='1';
 const q=$('quant'); [[1,'1/16'],[2,'1/8'],[4,'1/4 (beat)']].forEach(([v,t])=>{ const o=el('option',null,t); o.value=v; q.appendChild(o); });
 q.value='1'; q.addEventListener('change',()=>setQuant(q.value));

 $('play').addEventListener('click',doPlay);
 $('stop').addEventListener('click',doStop);
 $('rec').addEventListener('click',()=>setRecord(!record));
 $('modebtn').addEventListener('click',()=>setMode((eng.mode||'pattern')==='pattern'?'song':'pattern'));
 $('loop').addEventListener('click',()=>{ eng.loop=!eng.loop; $('loop').setAttribute('aria-pressed',eng.loop?'true':'false'); });
 $('bpmval').addEventListener('click',bpmSheet);
 $('bpmdn').addEventListener('click',()=>setBpm(proj.bpm-1));
 $('bpmup').addEventListener('click',()=>setBpm(proj.bpm+1));
 $('namebtn').addEventListener('click',moreSheet);
 $('menubtn').addEventListener('click',moreSheet);
 $('veil').addEventListener('pointerdown',(e)=>{ if(e.target.id==='veil')closeSheet(); });

 $('addmach').addEventListener('click',addMachineSheet);
 $('patsel').addEventListener('change',()=>pickPattern($('patsel').value));
 $('patprev').addEventListener('click',()=>stepPattern(-1));
 $('patnext').addEventListener('click',()=>stepPattern(1));
 $('pattools').addEventListener('click',()=>openSheet('Pattern',(box)=>{
  sAct(box,'Clear pattern',()=>{ const m=sel(); if(!m)return; const p=m.patterns[m.curPat];
   p.notes=[]; if(p.level)p.level.fill(null); commit(); renderPatternHead(); renderPattern(); });
  sAct(box,'Copy pattern',()=>{ const m=sel(); if(!m)return; clipboard=Studio.clone(m.patterns[m.curPat]); say('Pattern copied'); });
  sAct(box,'Paste pattern',()=>{ const m=sel(); if(!m||!clipboard)return;
   m.patterns[m.curPat]=Studio.clone(clipboard); commit(); renderPatternHead(); renderPattern(); renderSong(); say('Pattern pasted'); });
 }));
 $('songtools').addEventListener('click',()=>openSheet('Arrange',(box)=>{
  box.appendChild(el('p','muted','Tap a bar to drop the current pattern. Drag a block right edge to stretch it.'));
  sAct(box,'Delete selected block',deleteBlock);
  sAct(box,'Clear the arrangement',()=>{ if(!confirm('Clear the whole arrangement?'))return;
   proj.song.tracks={}; selBlock=null; commit(); renderSong(); },'danger');
 }));

 $('velo').addEventListener('input',()=>{ velocity=+$('velo').value; $('veloval').textContent=fix(velocity); });
 $('octdn').addEventListener('click',()=>setOctave(octave-1));
 $('octup').addEventListener('click',()=>setOctave(octave+1));
 $('drawertog').addEventListener('click',()=>setDrawer(!drawerOpen()));
 $('simhandle').addEventListener('pointerdown',(e)=>{ e.preventDefault(); $('simhandle').setPointerCapture(e.pointerId);
  const mv=(ev)=>{ $('simpanel').style.width=clamp(window.innerWidth-ev.clientX,220,window.innerWidth-420)+'px'; };
  const up=()=>{ $('simhandle').removeEventListener('pointermove',mv); $('simhandle').removeEventListener('pointerup',up); };
  $('simhandle').addEventListener('pointermove',mv); $('simhandle').addEventListener('pointerup',up); });

 // a breakpoint change moves the tabs, the hall and the grid row heights, so redraw on the flip
 let wasPhone=isPhone();
 window.addEventListener('resize',()=>{ const now=isPhone();
  if(now!==wasPhone){ wasPhone=now;
   if(!now&&view==='hall')setView('rack'); else { renderStrip(); if(view==='pattern')renderPattern(); if(view==='song')renderSong(); } } });

 setMode('pattern'); setRecord(false); setOctave(0); setQuant(1);
 $('loop').setAttribute('aria-pressed',eng.loop?'true':'false');
 let open=false; try{ open=localStorage.getItem(LSDRAWER)==='open'; }catch(e){}
 setDrawer(open);
 renderAll(); setView('rack');
 if(eng.stub)say('No audio engine: the studio is on the stub clock.',5000);
 requestAnimationFrame(loop);
}
if(document.readyState==='loading')document.addEventListener('DOMContentLoaded',boot); else boot();

// a handful of internals the verification pages poke at
Studio.ui={ get project(){ return proj; }, get engine(){ return eng; }, get lights(){ return L; },
 setView, renderAll, setDrawer, openSheet:moreSheet, select(id){ selId=id; renderAll(); } };
})();
