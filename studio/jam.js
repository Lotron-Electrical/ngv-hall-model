// THE JAM (Lloyd, 2026-09-05): the simple end of the studio, built for a thumb. The whole document
// the user edits is a JAM: a name, a tempo and a list of SECTIONS. A section is a stack of picks,
// one preset per instrument and up to six light layers, plus the knobs that move energy.
//
// The surface rule is that COLOUR carries the meaning and words are the exception. Every instrument
// owns a colour, its patterns are tiles in that colour, and a tile is either filled (on) or an
// outline (off). Nothing is captioned, nothing is summarised in a sentence, and there are only two
// type sizes. If a control needs explaining it goes in a sheet, not on the surface.
//
// Two projects exist at any moment and only one is live. The STACK is the current section built as
// a one-bar loop in pattern mode, which is what every tap rebuilds and hot-swaps under a running
// transport. The SONG is every section rendered and placed on the timeline, built on demand for
// song play and export. `proj` points at the live one; the engine and the lights runtime read it
// through a closure, so swapping is one assignment plus a rebuild.
//
// This file never authors music: it picks preset ids, hands them to Studio.PRESETS, and draws what
// comes back.
(function(){
'use strict';
const Studio=window.Studio=window.Studio||{};

// ---------------------------------------------------------------- small helpers
const $=(id)=>document.getElementById(id);
const el=(tag,cls,txt)=>{ const e=document.createElement(tag); if(cls)e.className=cls; if(txt!=null)e.textContent=txt; return e; };
const clamp=(x,a,b)=>x<a?a:x>b?b:x;
const fix=(x,n)=>Number(x||0).toFixed(n);
const pct=(x)=>Math.round(clamp(x,0,1)*100)+'%';
const cut=(s,n)=>{ s=String(s||''); return s.length>n?s.slice(0,n-1)+'…':s; };
const svg=(w,h,vb,body)=>'<svg width="'+w+'" height="'+h+'" viewBox="'+vb+'" aria-hidden="true">'+body+'</svg>';

const LSKEY='ngv.jam';
const STUDIO_KEY='ngv.studio.project';       // the key studio/ui.js restores from
const FAMILIES=['base','movement','accent','strobe','texture','colour'];
const INST_ORDER=['drums','perc','bass','sub','pad','chords','keys','lead','arp','fx'];
const METERS=['4/4','3/4','5/4','6/8','7/8','12/8'];
const CYCLE_NAMES=['neutral','dark','lift','pull','bright'];
const TRANSITIONS=['none','fill','riser','drop','gap'];
const FEELS=['straight','half','double'];
const STYLES=['dnb','hiphop','house','techno','trap','breakbeat','halftime','dubstep','ambient','abstract'];
const BARS=[4,8,16];

// the palette. One colour per instrument and per light family, which is the whole vocabulary of
// the interface: if you can see it you do not need to read it.
const INST_COLOUR={ drums:'#ffd166', perc:'#ff8a3d', bass:'#ff5c5c', sub:'#c0392b', pad:'#b78cff',
 chords:'#8e5bff', keys:'#5fd4a8', lead:'#4fa3ff', arp:'#7fd3ff', fx:'#ff5db1' };
const FAM_COLOUR={ base:'#ffb020', movement:'#35e0e0', accent:'#a8e63a', strobe:'#ffffff',
 texture:'#ff4fd8', colour:'#ff9ad6' };     // colour's tiles paint a rainbow, this is its text
const STYLE_COLOUR={ dnb:'#ff5c5c', hiphop:'#ff8a3d', house:'#ffd166', techno:'#a8e63a',
 trap:'#5fd4a8', breakbeat:'#35e0e0', halftime:'#4fa3ff', dubstep:'#b78cff', ambient:'#ff5db1',
 abstract:'#cbd2dc' };
// short names, because a row is 66 px wide and "Percussion" is not a word anyone needs spelled out
const SHORT={ drums:'Drums', perc:'Perc', bass:'Bass', sub:'Sub', pad:'Pad', chords:'Chords',
 keys:'Keys', lead:'Lead', arp:'Arp', fx:'FX' };
// energy as a temperature: cool at rest, hot at full. The only place a number becomes a colour.
const heat=(e)=>'hsl('+Math.round(210-210*clamp(e,0,1))+' 82% 56%)';

const ICON={
 play:svg(20,22,'0 0 20 22','<path d="M3 2l15 9-15 9z" fill="currentColor"/>'),
 pause:svg(18,22,'0 0 18 22','<rect x="1" y="1" width="5.5" height="20" rx="1.2" fill="currentColor"/><rect x="11.5" y="1" width="5.5" height="20" rx="1.2" fill="currentColor"/>'),
 jam:svg(22,22,'0 0 22 22','<g fill="none" stroke="currentColor" stroke-width="1.9" stroke-linecap="round"><path d="M2 6h18M2 11h18M2 16h18"/></g><g fill="currentColor"><circle cx="7" cy="6" r="2.6"/><circle cx="14" cy="11" r="2.6"/><circle cx="6" cy="16" r="2.6"/></g>'),
 song:svg(22,22,'0 0 22 22','<g fill="currentColor"><rect x="2" y="7" width="4.5" height="8" rx="1.2"/><rect x="8.7" y="3" width="4.5" height="16" rx="1.2"/><rect x="15.4" y="9" width="4.5" height="4" rx="1.2"/></g>'),
 hall:svg(22,22,'0 0 22 22','<g fill="none" stroke="currentColor" stroke-width="1.9" stroke-linecap="round"><path d="M2 19h18"/><path d="M4 19V8l7-5 7 5v11"/><path d="M9 19v-5.5a2 2 0 0 1 4 0V19"/></g>'),
 dots:svg(4,16,'0 0 4 16','<circle cx="2" cy="2.4" r="1.6" fill="currentColor"/><circle cx="2" cy="8" r="1.6" fill="currentColor"/><circle cx="2" cy="13.6" r="1.6" fill="currentColor"/>'),
 caret:svg(12,8,'0 0 12 8','<path d="M1.5 1.5L6 6l4.5-4.5" fill="none" stroke="currentColor" stroke-width="1.7" stroke-linecap="round"/>')
};

let toastT=0;
function say(text,hold){ const t=$('toast'); if(!text){ t.hidden=true; return; }
 t.textContent=text; t.hidden=false; clearTimeout(toastT); toastT=setTimeout(()=>{ t.hidden=true; },hold||2000); }

let sheetOpen=false;
function openSheet(title,build){
 const s=$('sheet'); s.innerHTML='';
 s.appendChild(el('h3',null,title));
 build(s);
 const close=el('button','sact','Close'); close.addEventListener('click',closeSheet); s.appendChild(close);
 $('veil').hidden=false; sheetOpen=true; s.scrollTop=0;
 s.setAttribute('aria-label',title);
}
function closeSheet(){ $('veil').hidden=true; sheetOpen=false; }
function sheetRow(parent,label,node){ const r=el('div','srow'); if(label)r.appendChild(el('label',null,label));
 if(node){ node.classList.add('grow'); r.appendChild(node); } parent.appendChild(r); return r; }
function seg(values,curVal,onPick,labels){
 const w=el('div','seg');
 values.forEach((v,i)=>{ const b=el('button',null,labels?labels[i]:String(v));
  b.setAttribute('aria-pressed',v===curVal?'true':'false');
  b.addEventListener('click',()=>onPick(v)); w.appendChild(b); });
 return w;
}
// a press held on a tile opens its sheet, the same as the corner button. Cancelled by any drag,
// because the strips scroll under the finger and a scroll must never be read as a hold.
function longPress(node,fn){
 let t=0, x=0, y=0;
 const clear=()=>{ if(t){ clearTimeout(t); t=0; } };
 node.addEventListener('pointerdown',(e)=>{ x=e.clientX; y=e.clientY; clear();
  t=setTimeout(()=>{ t=0; fn(); },450); });
 node.addEventListener('pointermove',(e)=>{ if(t&&(Math.abs(e.clientX-x)>10||Math.abs(e.clientY-y)>10))clear(); });
 for(const ev of ['pointerup','pointercancel','pointerleave'])node.addEventListener(ev,clear);
 node.addEventListener('contextmenu',(e)=>e.preventDefault());
}

// ---------------------------------------------------------------- the preset banks
function P(){ return Studio.PRESETS||null; }
function banksReady(){ const p=P(); return !!(p&&p.buildStack&&p.buildSong&&p.starter&&p.arc); }
let patCache=null;
function allPatterns(){
 if(patCache)return patCache;
 const out=[];
 for(const b of [Studio.PRESETS_DRUMS,Studio.PRESETS_PITCH]) if(b&&Array.isArray(b.list))out.push.apply(out,b.list);
 const p=P(); if(!out.length&&p&&Array.isArray(p.patterns))out.push.apply(out,p.patterns);
 patCache=out; return out;
}
function patternsFor(inst){ return allPatterns().filter(x=>x.inst===inst); }
function lightPatterns(){ const b=Studio.PRESETS_LIGHTS; return (b&&Array.isArray(b.list))?b.list:[]; }
function lightsFor(family){ return lightPatterns().filter(x=>x.family===family); }
function lxById(id){ return lightPatterns().find(x=>x.id===id)||null; }
function patById(id){ return allPatterns().find(x=>x.id===id)||null; }
function instruments(){
 const p=P();
 if(p&&Array.isArray(p.instruments)&&p.instruments.length)return p.instruments;
 const seen={}, out=[];
 for(const id of INST_ORDER){ if(patternsFor(id).length){ seen[id]=1; out.push({id,name:id}); } }
 for(const x of allPatterns())if(!seen[x.inst]){ seen[x.inst]=1; out.push({id:x.inst,name:x.inst}); }
 return out;
}

// ---------------------------------------------------------------- the jam document
let jam=null, cur=0;
let stackProj=null, songProj=null, proj=null, mode='pattern';
let view='jam', hallLoaded=false;

function section(){ return (jam&&jam.sections&&jam.sections[cur])||null; }
// the shapes are CORE's, so a section this page writes is one presets.js reads back untranslated
function emptySection(){
 const p=P();
 if(p&&p.newSection)return p.newSection();
 const picks={}; for(const i of instruments())picks[i.id]=null;
 return { bars:8, energy:0.6, feel:'straight', meter:{beats:4,div:4}, cycle:'neutral', transpose:0,
  transition:'none', cycleBars:1, bpm:null, picks, lights:[] };
}
function emptyJam(){
 const p=P();
 if(p&&p.newJam)return p.newJam();
 return { name:'jam', bpm:124, swing:0, humanise:0.3, seed:1, key:{root:57,scale:'minor'}, sections:[] };
}
function freshJam(){
 const j=emptyJam(); j.sections=[];
 if(banksReady()){
  const arc=P().arc(4);
  for(let i=0;i<4;i++){ const s=P().starter('house',arc[i])||emptySection(); s.energy=arc[i]; s.style='house'; j.sections.push(s); }
 } else { j.sections.push(emptySection()); }
 return j;
}
// what comes back from a share link or from storage may be an older shape, or nonsense
function sane(j){
 if(!j||typeof j!=='object'||!Array.isArray(j.sections)||!j.sections.length)return null;
 j.name=String(j.name||'jam').slice(0,60);
 j.bpm=clamp(+j.bpm||124,60,200); j.swing=clamp(+j.swing||0,0,0.6);
 j.humanise=clamp(j.humanise==null?0.3:+j.humanise,0,1); j.seed=(+j.seed||1)|0;
 if(!j.key||typeof j.key!=='object')j.key={root:57,scale:'minor'};
 j.sections=j.sections.slice(0,32).map(s=>{
  const out=emptySection();
  out.bars=BARS.indexOf(+s.bars)>=0?+s.bars:8;
  if(typeof s.style==='string')out.style=s.style;
  if(s.cycleBars===2)out.cycleBars=2;
  if(s.bpm)out.bpm=clamp(+s.bpm,60,200);
  out.energy=clamp(s.energy==null?0.6:+s.energy,0,1);
  out.feel=FEELS.indexOf(s.feel)>=0?s.feel:'straight';
  out.meter={beats:clamp((s.meter&&+s.meter.beats)||4,1,16),div:((s.meter&&+s.meter.div)===8)?8:4};
  out.cycle=CYCLE_NAMES.indexOf(s.cycle)>=0?s.cycle:'neutral';
  out.transpose=clamp((+s.transpose)|0,-12,12);
  out.transition=TRANSITIONS.indexOf(s.transition)>=0?s.transition:'none';
  if(s.picks)for(const k in out.picks)if(typeof s.picks[k]==='string')out.picks[k]=s.picks[k];
  if(Array.isArray(s.lights))out.lights=s.lights.slice(0,6)
   .filter(x=>x&&typeof x.id==='string')
   .map(x=>({id:x.id, sync:typeof x.sync==='string'?x.sync:'grid', gain:clamp(x.gain==null?1:+x.gain,0,1)}));
  return out;
 });
 return j;
}
let saveT=0;
function autosave(){ clearTimeout(saveT); saveT=setTimeout(()=>{
 try{ localStorage.setItem(LSKEY,JSON.stringify(jam)); }catch(e){} },400); }

// ---------------------------------------------------------------- the engine and the lights
function nullEngine(){ return { playing:false, mode:'pattern', stub:true,
 pos:()=>({step:0,t:0,bar:0,beat:0,stepInBar:0,loopSteps:16}),
 play(){}, pause(){}, stop(){}, seek(){}, rebuild(){}, invalidate(){}, init(){} }; }
const eng=(Studio.createEngine?Studio.createEngine({project:()=>proj}):nullEngine());
const L=Studio.createLights?Studio.createLights({project:()=>proj,engine:()=>eng,iframe:()=>$('sim')})
 :{state:{},tick(){},invalidate(){},stub:true};

// eng.rebuild swaps the rig without touching the transport, so a tap while playing changes the
// sound on the next step and never stops the music
function buildStack(){
 if(!banksReady()||!section())return;
 try{ stackProj=P().buildStack(Studio.clone(section()),jamHeader()); }
 catch(e){ console.error('buildStack failed',e); say('That stack could not be built'); return; }
 if(mode!=='song'){ proj=stackProj; hot(); }
}
function buildSongProject(){
 if(!banksReady())return null;
 try{ songProj=P().buildSong(Studio.clone(jamHeader(true))); return songProj; }
 catch(e){ console.error('buildSong failed',e); say('That song could not be built'); return null; }
}
function jamHeader(withSections){
 const h={ name:jam.name, bpm:jam.bpm, swing:jam.swing, humanise:jam.humanise, seed:jam.seed,
  key:jam.key||{root:57,scale:'minor'} };
 h.sections=withSections?jam.sections:[section()];
 return h;
}
function hot(){
 try{ eng.rebuild&&eng.rebuild(); }catch(e){}
 try{ eng.invalidate&&eng.invalidate(); }catch(e){}
 try{ L.invalidate&&L.invalidate(); }catch(e){}
 autosave();
}
// the Jam view always edits the stack, so a tap there drops out of song playback first
function toStack(){
 if(mode!=='song')return;
 mode='pattern'; buildStack(); proj=stackProj; hot();
 $('songplay').setAttribute('aria-pressed','false');
 if(eng.playing)try{ eng.play({mode:'pattern',fromStep:0}); }catch(e){}
}

// ---------------------------------------------------------------- the Jam view
// One tap on a style pill is a whole stack. The section's own shape (bars, meter, feel, chords,
// ending, transpose, energy) is kept, because a starter is a sound and not an arrangement.
function renderStyles(){
 const host=$('stylerow'); if(!host)return;
 host.innerHTML='';
 const sec=section();
 for(const style of STYLES){
  const b=el('button',null,style); b.type='button';
  b.style.setProperty('--c',STYLE_COLOUR[style]||'#cbd2dc');
  b.setAttribute('aria-pressed',(sec&&sec.style===style)?'true':'false');
  b.addEventListener('click',()=>{
   if(!banksReady())return say('No presets loaded');
   const s=section(); if(!s)return;
   toStack();
   let starter=null;
   try{ starter=P().starter(style,s.energy); }catch(e){ console.error(e); }
   if(!starter)return say('No '+style+' starter');
   s.picks=starter.picks; s.lights=starter.lights||[]; s.style=style;
   orderLights(s);
   songProj=null; buildStack(); renderJam(); renderSong(); autosave();
  });
  host.appendChild(b);
 }
}

// a row is a coloured dot, a short name, and a scrolling strip of tiles. Nothing else.
function makeRow(colour,name,extraClass){
 const r=el('div','jrow'+(extraClass?' '+extraClass:''));
 r.style.setProperty('--c',colour);
 r.appendChild(el('span','jdot'));
 r.appendChild(el('span','jrn',name));
 const strip=el('div','jstrip');
 r.appendChild(strip);
 return {jrow:r, strip};
}
function makeTile(colour,label,on,aria){
 const t=el('button','jtile'); t.type='button';
 t.style.setProperty('--c',colour);
 t.setAttribute('aria-pressed',on?'true':'false');
 t.setAttribute('aria-label',aria);
 t.title=aria;
 t.appendChild(el('span','jtn',cut(label,14)));
 return t;
}

function renderJam(){
 renderStyles();
 const body=$('jambody');
 const scroll={}, top=body.scrollTop;
 body.querySelectorAll('.jstrip[data-key]').forEach(s=>{ scroll[s.dataset.key]=s.scrollLeft; });
 body.innerHTML='';

 if(!banksReady()){
  const m=el('div','jblockhd','No presets loaded'); body.appendChild(m); return;
 }
 const sec=section(); if(!sec)return;

 for(const inst of instruments()){
  const colour=INST_COLOUR[inst.id]||'#cbd2dc';
  const pick=sec.picks[inst.id]||null;
  const r=makeRow(colour,SHORT[inst.id]||inst.name||inst.id);
  r.strip.dataset.key='i:'+inst.id;
  for(const p of patternsFor(inst.id)){
   const on=pick===p.id;
   const t=makeTile(colour,p.name||p.id,on,(SHORT[inst.id]||inst.id)+': '+(p.name||p.id));
   if((p.minEnergy||0)>sec.energy)t.classList.add('jlocked');
   t.addEventListener('click',()=>{ toStack();
    sec.picks[inst.id]=on?null:p.id;
    songProj=null; buildStack(); renderJam(); autosave(); });
   r.strip.appendChild(t);
  }
  body.appendChild(r.jrow);
 }

 // one Lights block, six short rows inside it. Six families means at most six layers stack.
 const jblock=el('div','jblock');
 jblock.appendChild(el('div','jblockhd','Lights'));
 for(const fam of FAMILIES){
  const colour=FAM_COLOUR[fam];
  const entry=sec.lights.find(x=>{ const p=lxById(x.id); return p&&p.family===fam; })||null;
  const r=makeRow(colour,fam.charAt(0).toUpperCase()+fam.slice(1),fam==='colour'?'jfam-colour':'');
  r.strip.dataset.key='l:'+fam;
  for(const p of lightsFor(fam)){
   const on=!!entry&&entry.id===p.id;
   const t=makeTile(colour,p.name||p.id,on,fam+' light: '+(p.name||p.id));
   t.classList.add('jlx');
   t.addEventListener('click',()=>{ toStack();
    sec.lights=sec.lights.filter(x=>{ const q=lxById(x.id); return !q||q.family!==fam; });
    if(!on)sec.lights.push({id:p.id, sync:(p.sync||'grid'), gain:(p.gain==null?1:p.gain)});
    orderLights(sec);
    songProj=null; buildStack(); renderJam(); autosave(); });
   // the active tile carries its own controls: a jdot in the colour of whatever it follows, and a
   // corner that opens the sheet. A held press anywhere on the jtile opens the same sheet.
   if(on){
    if(entry.sync&&entry.sync!=='grid'){
     const d=el('span','jsyncdot');
     d.style.setProperty('--s',INST_COLOUR[entry.sync]||'#0e0f11');
     d.title='Following '+(SHORT[entry.sync]||entry.sync);
     t.insertBefore(d,t.firstChild);
    }
    const jmore=el('button','jmore'); jmore.type='button';
    jmore.innerHTML=ICON.dots;
    jmore.setAttribute('aria-label',fam+' layer settings');
    jmore.title='Sync and gain';
    jmore.addEventListener('click',(e)=>{ e.stopPropagation(); layerSheet(fam,entry); });
    t.appendChild(jmore);
    longPress(t,()=>layerSheet(fam,entry));
   }
   r.strip.appendChild(t);
  }
  jblock.appendChild(r.jrow);
 }
 body.appendChild(jblock);

 // put each strip back where the finger left it, and on a first draw scroll the chosen tile into
 // view: a row whose only marker is a filled tile is useless if that tile is off the right edge
 body.querySelectorAll('.jstrip[data-key]').forEach(s=>{
  if(scroll[s.dataset.key]!=null)s.scrollLeft=scroll[s.dataset.key];
  const on=s.querySelector('.jtile[aria-pressed="true"]');
  if(!on)return;
  // only when the chosen tile is off the edge, so a tap leaves the strip where the finger put it
  // but changing section walks each row to its new pick. Rect maths, not offsetLeft: a tile's
  // offsetParent is the positioned .view, so offsetLeft carries the row's dot and name too.
  const a=on.getBoundingClientRect(), b=s.getBoundingClientRect();
  if(a.left<b.left-1||a.right>b.right+1)s.scrollLeft=Math.max(0,s.scrollLeft+(a.left-b.left)-6);
 });
 body.scrollTop=top;
}
// layers stack in family order so the compositor sees base first and strobe last
function orderLights(sec){
 sec.lights.sort((a,b)=>{ const pa=lxById(a.id), pb=lxById(b.id);
  return FAMILIES.indexOf(pa?pa.family:'') - FAMILIES.indexOf(pb?pb.family:''); });
}
function syncOptions(sec){
 const out=['grid'];
 for(const i of instruments())if(sec.picks[i.id])out.push(i.id);
 return out;
}
// everything a light layer can be told, kept off the surface and put here
function layerSheet(fam,entry){
 const sec=section(); if(!sec||!entry)return;
 const preset=lxById(entry.id);
 openSheet(preset?preset.name:fam,(s)=>{
  s.appendChild(el('p','muted','What this layer follows.'));
  const opts=syncOptions(sec);
  const g=el('div','jsheetgrid');
  for(const o of opts){
   const b=el('button',null,o==='grid'?'Beat':(SHORT[o]||o)); b.type='button';
   b.setAttribute('aria-pressed',entry.sync===o?'true':'false');
   if(o!=='grid')b.style.color=INST_COLOUR[o]||'';
   b.addEventListener('click',()=>{ toStack(); entry.sync=o;
    g.querySelectorAll('button').forEach(x=>x.setAttribute('aria-pressed','false'));
    b.setAttribute('aria-pressed','true');
    songProj=null; buildStack(); renderJam(); autosave(); });
   g.appendChild(b);
  }
  s.appendChild(g);
  const i=document.createElement('input'); i.type='range'; i.min='0'; i.max='1'; i.step='0.05';
  i.value=String(entry.gain==null?1:entry.gain); i.setAttribute('aria-label','Layer gain');
  i.style.accentColor=FAM_COLOUR[fam]||'';
  const v=el('span','val',fix(entry.gain==null?1:entry.gain,2));
  i.addEventListener('input',()=>{ entry.gain=+i.value; v.textContent=fix(entry.gain,2); });
  i.addEventListener('change',()=>{ toStack(); songProj=null; buildStack(); autosave(); });
  sheetRow(s,'Gain',i).appendChild(v);
  const off=el('button','sact danger','Turn this layer off');
  off.addEventListener('click',()=>{ toStack();
   sec.lights=sec.lights.filter(x=>x!==entry);
   songProj=null; buildStack(); renderJam(); closeSheet(); autosave(); });
  s.appendChild(off);
 });
}

// ---------------------------------------------------------------- the Song view
// The song is a strip of coloured blocks, hot where the energy is. Tapping one selects it; the one
// card below is that section and nothing else, with everything but energy behind More.
function renderSong(){
 renderStrip();
 const body=$('songbody');
 const wasMore=!!body.querySelector('.jseccard.jmore');
 body.innerHTML='';
 const s=section(); if(!s)return;

 const card=el('div','jseccard'); if(wasMore)card.classList.add('jmore');
 card.style.setProperty('--c',heat(s.energy));

 const top=el('div','jcardtop');
 const sw=el('span','jswatch'); top.appendChild(sw);
 const e=document.createElement('input'); e.type='range'; e.min='0'; e.max='1'; e.step='0.05';
 e.value=String(s.energy); e.setAttribute('aria-label','Energy');
 const ev=el('span','val',pct(s.energy));
 e.addEventListener('input',()=>{ s.energy=+e.value; ev.textContent=pct(s.energy);
  card.style.setProperty('--c',heat(s.energy)); paintStrip(); });
 e.addEventListener('change',()=>{ songProj=null; buildStack(); renderJam(); autosave(); });
 top.appendChild(e); top.appendChild(ev);
 card.appendChild(top);

 const mb=el('button','jmorebtn'); mb.type='button';
 mb.appendChild(el('span',null,'More'));
 const cv=el('span',null); cv.innerHTML=ICON.caret; mb.appendChild(cv);
 mb.setAttribute('aria-expanded',wasMore?'true':'false');
 mb.addEventListener('click',()=>{ const on=card.classList.toggle('jmore');
  mb.setAttribute('aria-expanded',on?'true':'false'); });
 card.appendChild(mb);

 const mo=el('div','jmorebody');
 const jmrow=(label,node)=>{ const r=el('div','jmrow'); r.appendChild(el('label',null,label));
  r.appendChild(node); mo.appendChild(r); return r; };
 jmrow('Bars',seg(BARS,s.bars,(v)=>{ s.bars=v; touched(); }));
 jmrow('Feel',seg(FEELS,s.feel,(v)=>{ s.feel=v; touched(); },['Straight','Half','Double']));
 jmrow('Meter',seg(METERS,s.meter.beats+'/'+s.meter.div,(v)=>{
  const p=v.split('/'); s.meter={beats:+p[0],div:+p[1]}; touched(); }));
 jmrow('Chords',seg(CYCLE_NAMES,s.cycle,(v)=>{ s.cycle=v; touched(); }));
 jmrow('Ending',seg(TRANSITIONS,s.transition,(v)=>{ s.transition=v; touched(); }));
 const tr=el('div','jmrow'); tr.appendChild(el('label',null,'Key'));
 const dn=el('button',null,'−'); dn.setAttribute('aria-label','Down a semitone');
 const tv=el('span','val',(s.transpose>0?'+':'')+s.transpose);
 const up=el('button',null,'+'); up.setAttribute('aria-label','Up a semitone');
 dn.addEventListener('click',()=>{ s.transpose=clamp(s.transpose-1,-12,12); tv.textContent=(s.transpose>0?'+':'')+s.transpose; touched(true); });
 up.addEventListener('click',()=>{ s.transpose=clamp(s.transpose+1,-12,12); tv.textContent=(s.transpose>0?'+':'')+s.transpose; touched(true); });
 tr.appendChild(dn); tr.appendChild(tv); tr.appendChild(up); mo.appendChild(tr);
 card.appendChild(mo);

 const acts=el('div','jsecacts');
 const dup=el('button',null,'Copy');
 dup.addEventListener('click',()=>{ jam.sections.splice(cur+1,0,JSON.parse(JSON.stringify(s)));
  cur++; songProj=null; renderSong(); autosave(); });
 const lf=el('button',null,'‹'); lf.setAttribute('aria-label','Move earlier'); lf.disabled=cur===0;
 lf.addEventListener('click',()=>move(-1));
 const rt=el('button',null,'›'); rt.setAttribute('aria-label','Move later'); rt.disabled=cur===jam.sections.length-1;
 rt.addEventListener('click',()=>move(1));
 const rm=el('button','danger','Delete'); rm.disabled=jam.sections.length<2;
 rm.addEventListener('click',()=>{ jam.sections.splice(cur,1); cur=clamp(cur,0,jam.sections.length-1);
  songProj=null; buildStack(); renderJam(); renderSong(); autosave(); });
 for(const x of [dup,lf,rt,rm])acts.appendChild(x);
 card.appendChild(acts);

 body.appendChild(card);
}
// the blocks themselves: colour is energy, the ring is what you are editing, green is what plays
function renderStrip(){
 const host=$('secstrip'); if(!host||!jam)return;
 host.innerHTML='';
 jam.sections.forEach((s,i)=>{
  const b=el('button','jsecblock',String(i+1)); b.type='button';
  b.style.setProperty('--c',heat(s.energy));
  b.setAttribute('aria-pressed',i===cur?'true':'false');
  b.setAttribute('aria-label','Section '+(i+1)+', energy '+pct(s.energy));
  b.title='Section '+(i+1)+', energy '+pct(s.energy);
  b.addEventListener('click',()=>{ cur=i; buildStack(); renderJam(); renderSong(); });
  host.appendChild(b);
 });
 const add=el('button','jsecadd','+'); add.type='button';
 add.setAttribute('aria-label','Add a section');
 add.title='Add a section';
 add.addEventListener('click',()=>{
  const s=JSON.parse(JSON.stringify(section()||emptySection()));
  jam.sections.splice(cur+1,0,s); cur++; songProj=null;
  renderSong(); renderJam(); autosave();
 });
 host.appendChild(add);
}
// only the colours change while the energy slider moves, so the strip is not rebuilt under the finger
function paintStrip(){
 const host=$('secstrip'); if(!host||!jam)return;
 const blocks=host.querySelectorAll('.jsecblock');
 jam.sections.forEach((s,i)=>{ if(blocks[i])blocks[i].style.setProperty('--c',heat(s.energy)); });
}
function move(d){
 const j=cur+d; if(j<0||j>=jam.sections.length)return;
 const t=jam.sections[cur]; jam.sections[cur]=jam.sections[j]; jam.sections[j]=t;
 cur=j; songProj=null; renderSong(); autosave();
}
// an edit to the current section invalidates the song and rebuilds the live stack
function touched(keepCard){
 songProj=null; buildStack(); renderJam(); autosave();
 if(!keepCard)renderSong();
}

// ---------------------------------------------------------------- views and the transport
function setView(v){
 view=v;
 for(const name of ['jam','song','hall']){
  const s=$('view-'+name); if(s)s.classList.toggle('on',name===v);
 }
 document.querySelectorAll('#nav button,#tabs button').forEach(b=>{
  b.setAttribute('aria-pressed',b.dataset.view===v?'true':'false'); });
 if(v==='hall'&&!hallLoaded){ hallLoaded=true; $('sim').src='index.html?embed=1&show=live&bare=1'; }
}
function setPlaying(on){
 const b=$('play');
 b.innerHTML=on?ICON.pause:ICON.play;
 b.setAttribute('aria-label',on?'Pause':'Play');
 b.title=on?'Pause':'Play';
 b.setAttribute('aria-pressed',on?'true':'false');
}
function playPause(){
 if(!proj)buildStack();
 if(eng.playing){ eng.pause(); setPlaying(false); return; }
 try{ eng.play({mode:mode}); }catch(e){ console.error(e); say('No audio'); }
 setPlaying(!!eng.playing);
}
function stopAll(){ try{ eng.stop(); }catch(e){} setPlaying(false); }
function playSong(){
 if(!banksReady())return say('No presets loaded');
 const p=songProj||buildSongProject(); if(!p)return;
 mode='song'; proj=p; hot();
 $('songplay').setAttribute('aria-pressed','true');
 try{ eng.play({mode:'song',fromStep:0}); }catch(e){ console.error(e); }
 setPlaying(!!eng.playing);
}

// ---------------------------------------------------------------- share, export, hand-off
function b64url(bytes){
 let s=''; const CH=0x8000;
 for(let i=0;i<bytes.length;i+=CH)s+=String.fromCharCode.apply(null,bytes.subarray(i,i+CH));
 return btoa(s).replace(/\+/g,'-').replace(/\//g,'_').replace(/=+$/,'');
}
function unb64url(str){
 const s=str.replace(/-/g,'+').replace(/_/g,'/'), pad=s.length%4?'===='.slice(s.length%4):'';
 const bin=atob(s+pad), out=new Uint8Array(bin.length);
 for(let i=0;i<bin.length;i++)out[i]=bin.charCodeAt(i);
 return out;
}
// the jam in the hash. j1 is deflate-raw, j0 is plain JSON for a browser without CompressionStream,
// so a link made on one machine always opens on another.
async function encodeJam(j){
 const bytes=new TextEncoder().encode(JSON.stringify(j));
 if(typeof CompressionStream==='function'){
  try{
   const cs=new CompressionStream('deflate-raw');
   const ab=await new Response(new Blob([bytes]).stream().pipeThrough(cs)).arrayBuffer();
   return 'j1.'+b64url(new Uint8Array(ab));
  }catch(e){}
 }
 return 'j0.'+b64url(bytes);
}
async function decodeJam(hash){
 const s=String(hash||'').replace(/^#/,'');
 if(!s)return null;
 try{
  if(s.indexOf('j0.')===0)return JSON.parse(new TextDecoder().decode(unb64url(s.slice(3))));
  if(s.indexOf('j1.')===0){
   if(typeof DecompressionStream!=='function')return null;
   const ds=new DecompressionStream('deflate-raw');
   const ab=await new Response(new Blob([unb64url(s.slice(3))]).stream().pipeThrough(ds)).arrayBuffer();
   return JSON.parse(new TextDecoder().decode(new Uint8Array(ab)));
  }
 }catch(e){ console.warn('share link would not decode',e); }
 return null;
}
async function shareLink(){
 const h=await encodeJam(jam);
 const url=location.origin+location.pathname+'#'+h;
 try{ history.replaceState(null,'','#'+h); }catch(e){}
 let copied=false;
 try{ if(navigator.clipboard&&navigator.clipboard.writeText){ await navigator.clipboard.writeText(url); copied=true; } }catch(e){}
 openSheet('Share',(s)=>{
  s.appendChild(el('p','muted',copied?'Copied. The link is in the address bar too.':'Copy this link.'));
  const box=document.createElement('input'); box.type='text'; box.value=url; box.readOnly=true;
  box.setAttribute('aria-label','Share link'); box.className='grow';
  const r=el('div','srow'); r.appendChild(box); s.appendChild(r);
  box.addEventListener('focus',()=>box.select());
  const c=el('button','sact','Copy again');
  c.addEventListener('click',()=>{ box.select();
   try{ navigator.clipboard.writeText(url); say('Copied'); }catch(e){ say('Copy it by hand'); } });
  s.appendChild(c);
 });
 return url;
}
function download(blob,name){
 const u=URL.createObjectURL(blob), a=document.createElement('a');
 a.href=u; a.download=name; a.style.display='none';
 document.body.appendChild(a); a.click();
 setTimeout(()=>{ URL.revokeObjectURL(u); a.remove(); },4000);
}
// the site is a static host, so the studio's POST-to-disk export is no use here: the same render
// and cue-file code comes back through Studio.exportFiles and lands as two browser downloads.
async function exportShow(){
 if(typeof Studio.exportFiles!=='function')return say('Export is not in this build yet',3000);
 const p=buildSongProject(); if(!p)return;
 let fill=null;
 openSheet('Export',(s)=>{
  s.appendChild(el('p','muted','Rendering the song. Two files land in your downloads.'));
  const bar=el('div',null); bar.id='jbar'; fill=el('div',null); fill.id='jbarfill';
  bar.appendChild(fill); s.appendChild(bar);
 });
 const name=(Studio.safeName?Studio.safeName(jam.name):String(jam.name||'jam'));
 try{
  eng.init&&eng.init();
  const r=await Studio.exportFiles(p,eng,name,(text,f)=>{ if(fill)fill.style.width=Math.round(clamp(f||0,0,1)*100)+'%'; });
  const wav=r.wavBlob instanceof Blob?r.wavBlob:new Blob([r.wavBlob],{type:'audio/wav'});
  const cues=typeof r.cuesJson==='string'?new Blob([r.cuesJson],{type:'application/json'})
   :new Blob([JSON.stringify(r.cuesJson)],{type:'application/json'});
  download(wav,name+'.wav'); download(cues,name+'.cues.json');
  closeSheet(); say('Exported');
  return {wav:wav.size, cues:cues.size};
 }catch(e){ console.error('export failed',e); closeSheet(); say('Export failed',3500); return null; }
}
// the studio restores whatever is under this key on boot, so handing a jam over is one write
function openInStudio(){
 const p=buildSongProject(); if(!p)return;
 p.name=jam.name||'jam';
 try{ localStorage.setItem(STUDIO_KEY,JSON.stringify(p)); }
 catch(e){ return say('Too big to hand over'); }
 location.href='studio.html';
}

// ---------------------------------------------------------------- the sheets
function menuSheet(){
 openSheet('Jam',(s)=>{
  const n=document.createElement('input'); n.type='text'; n.value=jam.name; n.maxLength=60;
  n.setAttribute('aria-label','Jam name');
  n.addEventListener('change',()=>{ jam.name=n.value.trim()||'jam'; autosave(); });
  sheetRow(s,'Name',n);
  const share=el('button','sact','Share a link'); share.addEventListener('click',()=>{ shareLink(); });
  const exp=el('button','sact','Export the audio'); exp.addEventListener('click',()=>{ exportShow(); });
  const st=el('button','sact','Open in the studio'); st.addEventListener('click',openInStudio);
  const nu=el('button','sact danger','Start again');
  nu.addEventListener('click',()=>{ jam=freshJam(); cur=0; songProj=null;
   try{ history.replaceState(null,'',location.pathname); }catch(e){}
   buildStack(); renderJam(); renderSong(); closeSheet(); autosave(); });
  for(const b of [share,exp,st,nu])s.appendChild(b);
 });
}
function tempoSheet(){
 openSheet('Tempo',(s)=>{
  const mk=(label,min,max,step,val,onSet,fmt)=>{
   const i=document.createElement('input'); i.type='range'; i.min=String(min); i.max=String(max);
   i.step=String(step); i.value=String(val); i.setAttribute('aria-label',label);
   const v=el('span','val',fmt(val));
   i.addEventListener('input',()=>{ v.textContent=fmt(+i.value); });
   i.addEventListener('change',()=>{ onSet(+i.value); });
   sheetRow(s,label,i).appendChild(v);
  };
  mk('Tempo',70,180,1,jam.bpm,(v)=>{ jam.bpm=v; $('bpmval').textContent=String(v); apply(); },(v)=>String(Math.round(v)));
  mk('Swing',0,0.6,0.01,jam.swing,(v)=>{ jam.swing=v; apply(); },(v)=>fix(v,2));
  mk('Loose',0,1,0.05,jam.humanise,(v)=>{ jam.humanise=v; apply(); },(v)=>fix(v,2));
  function apply(){ songProj=null; buildStack(); autosave(); }
 });
}

// ---------------------------------------------------------------- the frame loop
let frames=0, fpsWindow=[], lastT=0, lastPlayingSec=-1;
function loop(ts){
 requestAnimationFrame(loop); frames++;
 if(lastT){ const dt=ts-lastT; if(dt>0&&dt<500){ fpsWindow.push(dt); if(fpsWindow.length>120)fpsWindow.shift(); } }
 lastT=ts;
 if(eng.playing!==($('play').getAttribute('aria-pressed')==='true'))setPlaying(!!eng.playing);
 if(L.tick&&(eng.playing||frames%4===0)){ try{ L.tick(); }catch(e){} }
 // the section strip is the only playhead the jam shows: the jblock that is sounding goes green
 if(view==='song'&&frames%6===0){
  let si=-1;
  if(mode==='song'&&eng.playing&&songProj&&songProj.song&&songProj.song.sections){
   let p=null; try{ p=eng.pos(); }catch(e){}
   if(p){ const T=Studio.timeline?Studio.timeline(songProj):null;
    const bar=T?T.stepBar(p.step):Math.floor(p.step/16);
    songProj.song.sections.forEach((s,i)=>{ if(bar>=s.bar&&bar<s.bar+s.len)si=i; }); }
  }
  if(si!==lastPlayingSec){ lastPlayingSec=si;
   const blocks=$('secstrip').querySelectorAll('.jsecblock');
   blocks.forEach((b,i)=>b.classList.toggle('jplaying',i===si)); }
 }
}
function fps(){ if(!fpsWindow.length)return 0;
 const mean=fpsWindow.reduce((a,b)=>a+b,0)/fpsWindow.length; return Math.round(1000/mean); }

// ---------------------------------------------------------------- boot
function navButtons(){
 const defs=[['jam','Jam',ICON.jam],['song','Song',ICON.song],['hall','Hall',ICON.hall]];
 for(const host of [$('nav'),$('tabs')]){
  if(!host)continue;
  host.innerHTML='';
  for(const d of defs){
   const b=el('button',null); b.type='button'; b.dataset.view=d[0];
   const ic=el('span',null); ic.innerHTML=d[2]; b.appendChild(ic);
   b.appendChild(el('span',null,d[1]));
   b.setAttribute('aria-pressed',d[0]===view?'true':'false');
   b.addEventListener('click',()=>setView(d[0]));
   host.appendChild(b);
  }
 }
}

async function boot(){
 // a share link beats storage, storage beats a fresh house starter
 let j=null;
 if(location.hash&&location.hash.length>3)j=sane(await decodeJam(location.hash));
 if(!j){ try{ const s=localStorage.getItem(LSKEY); if(s)j=sane(JSON.parse(s)); }catch(e){} }
 if(!j)j=freshJam();
 jam=j; cur=0;

 navButtons();
 setPlaying(false);
 $('bpmval').textContent=String(jam.bpm);
 $('play').addEventListener('click',playPause);
 $('stop').addEventListener('click',stopAll);
 $('bpmval').addEventListener('click',tempoSheet);
 $('menubtn').addEventListener('click',menuSheet);
 $('veil').addEventListener('click',(e)=>{ if(e.target===$('veil'))closeSheet(); });
 document.addEventListener('keydown',(e)=>{ if(e.key==='Escape'&&sheetOpen){ e.preventDefault(); closeSheet(); } });

 $('arcbtn').addEventListener('click',()=>{
  if(!banksReady())return say('No presets loaded');
  const a=P().arc(jam.sections.length);
  jam.sections.forEach((s,i)=>{ s.energy=clamp(a[i]==null?s.energy:a[i],0,1); });
  songProj=null; buildStack(); renderSong(); renderJam(); autosave();
 });
 $('songplay').addEventListener('click',playSong);

 buildStack();
 renderJam(); renderSong(); setView('jam');
 if(!banksReady())say('No presets loaded. Add ?stub for the stand-in bank.',5000);
 requestAnimationFrame(loop);
}
if(document.readyState==='loading')document.addEventListener('DOMContentLoaded',boot); else boot();

// what the verification pages poke at
Studio.jam={
 get jam(){ return jam; }, get project(){ return proj; }, get engine(){ return eng; }, get lights(){ return L; },
 get section(){ return section(); }, get mode(){ return mode; }, get view(){ return view; },
 setView, renderJam, renderSong, playSong, playPause, stopAll, shareLink, exportShow, openInStudio,
 menuSheet, tempoSheet, layerSheet, encodeJam, decodeJam, fps, banksReady,
 buildSong:buildSongProject,
 setCur(i){ cur=clamp(i|0,0,jam.sections.length-1); buildStack(); renderJam(); renderSong(); },
 load(j){ const s=sane(j); if(!s)return false; jam=s; cur=0; songProj=null;
  buildStack(); renderJam(); renderSong(); return true; }
};
})();
