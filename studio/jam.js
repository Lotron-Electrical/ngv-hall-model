// THE JAM (Lloyd, 2026-09-05): the simple end of the studio, built for a thumb. The whole document
// the user edits is a JAM: a name, a tempo, a feel and a list of SECTIONS. A section is a stack of
// picks, one preset per instrument and up to six light layers, plus the knobs that move energy
// (energy, feel, meter, chord cycle, transpose, transition, bars).
//
// Two projects exist at any moment and only one is live. The STACK is the current section built as
// a one-bar loop in pattern mode, which is what every tap in the Jam view rebuilds and hot-swaps
// under a running transport. The SONG is every section rendered and placed on the timeline, built
// on demand when the user plays the song or exports. `proj` always points at the live one, and the
// engine and the lights runtime read it through a closure, so swapping is one assignment plus a
// rebuild.
//
// Everything drawable comes from the preset banks (presets.js and the three preset files). This
// file never authors music: it picks ids, hands them to Studio.PRESETS, and draws what comes back.
(function(){
'use strict';
const Studio=window.Studio=window.Studio||{};

// ---------------------------------------------------------------- small helpers
const $=(id)=>document.getElementById(id);
const el=(tag,cls,txt)=>{ const e=document.createElement(tag); if(cls)e.className=cls; if(txt!=null)e.textContent=txt; return e; };
const clamp=(x,a,b)=>x<a?a:x>b?b:x;
const fix=(x,n)=>Number(x||0).toFixed(n);
const pct=(x)=>Math.round(clamp(x,0,1)*100)+'%';

const LSKEY='ngv.jam';
const STUDIO_KEY='ngv.studio.project';       // the key studio/ui.js restores from
const FAMILIES=['base','movement','accent','strobe','texture','colour'];
const INST_ORDER=['drums','perc','bass','sub','pad','chords','keys','lead','arp','fx'];
const METERS=[[4,4],[3,4],[5,4],[6,8],[7,8],[12,8]];
const CYCLE_NAMES=['neutral','dark','lift','pull','bright'];
const TRANSITIONS=['none','fill','riser','drop','gap'];
const FEELS=['straight','half','double'];
const STYLES=['dnb','hiphop','house','techno','trap','breakbeat','halftime','dubstep','ambient','abstract'];
const BARS=[4,8,16];

let toastT=0;
function say(text,hold){ const t=$('toast'); if(!text){ t.hidden=true; return; }
 t.textContent=text; t.hidden=false; clearTimeout(toastT); toastT=setTimeout(()=>{ t.hidden=true; },hold||2200); }

let sheetOpen=false;
function openSheet(title,build){
 const s=$('sheet'); s.innerHTML='';
 const h=el('h3',null,title); s.appendChild(h);
 build(s);
 const close=el('button','sact','Close'); close.addEventListener('click',closeSheet); s.appendChild(close);
 $('veil').hidden=false; sheetOpen=true; s.scrollTop=0;
 s.setAttribute('aria-label',title);
}
function closeSheet(){ $('veil').hidden=true; sheetOpen=false; }

// a labelled row inside a sheet or a card
function row(parent,label,node){ const r=el('div','srow'); if(label)r.appendChild(el('label',null,label));
 if(node){ node.classList.add('grow'); r.appendChild(node); } parent.appendChild(r); return r; }
// a segmented control: values in, the chosen one pressed, a callback out
function seg(values,cur,onPick,labels){
 const w=el('div','seg');
 values.forEach((v,i)=>{ const b=el('button',null,labels?labels[i]:String(v));
  b.setAttribute('aria-pressed',v===cur?'true':'false');
  b.addEventListener('click',()=>onPick(v)); w.appendChild(b); });
 return w;
}

// ---------------------------------------------------------------- the preset banks
// Every read goes through here so a bank that has not landed yet is a quiet empty list rather than
// a page that will not boot.
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
// the instrument table, or the ids the patterns imply if presets.js is not in yet
function instruments(){
 const p=P();
 if(p&&Array.isArray(p.instruments)&&p.instruments.length)return p.instruments;
 const seen={}, out=[];
 for(const id of INST_ORDER){ if(patternsFor(id).length){ seen[id]=1; out.push({id,name:id,slot:id}); } }
 for(const x of allPatterns())if(!seen[x.inst]){ seen[x.inst]=1; out.push({id:x.inst,name:x.inst,slot:x.inst}); }
 return out;
}

// ---------------------------------------------------------------- the jam document
let jam=null, cur=0;
let stackProj=null, songProj=null, proj=null, mode='pattern';
let view='jam', hallLoaded=false;

function section(){ return (jam&&jam.sections&&jam.sections[cur])||null; }
// the shapes are CORE's, so a section this page writes is one presets.js can read back without
// translation. The literals below are only the fallback for a bank that has not loaded.
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
// what comes back from a share link or from storage may be from an older shape or from nowhere
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
 :{state:{look:'-',palette:'-',level:1},tick(){},invalidate(){},stub:true};

// the stack is rebuilt on every tap. eng.rebuild() swaps the rig without touching the transport,
// so a tap while playing changes the sound on the next step and never stops the music.
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
// the jam minus the UI's own bookkeeping, which is all the preset builders want
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
// leaving song playback: the Jam view always edits the stack, so a tap there drops back to it
function toStack(){
 if(mode!=='song')return;
 mode='pattern'; buildStack(); proj=stackProj; hot();
 $('songplay').setAttribute('aria-pressed','false');
 if(eng.playing)try{ eng.play({mode:'pattern',fromStep:0}); }catch(e){}
}

// ---------------------------------------------------------------- the Jam view
// the style chips: one tap is a whole stack. The section's own shape (bars, meter, feel, chords,
// transition, transpose, energy) is deliberately kept, because a starter is a sound, not an
// arrangement, and losing a 7/8 section to a chip tap would be a nasty surprise.
function renderStyles(){
 const host=$('stylerow'); if(!host)return;
 host.innerHTML='';
 const sec=section();
 for(const style of STYLES){
  const b=el('button',null,style); b.type='button';
  b.setAttribute('aria-pressed',(sec&&sec.style===style)?'true':'false');
  b.setAttribute('aria-label','Starter stack: '+style);
  b.addEventListener('click',()=>{
   if(!banksReady())return say('The preset banks are not loaded');
   const s=section(); if(!s)return;
   toStack();
   let starter=null;
   try{ starter=P().starter(style,s.energy); }catch(e){ console.error(e); }
   if(!starter)return say('No starter for '+style);
   s.picks=starter.picks; s.lights=starter.lights||[]; s.style=style;
   orderLights(s);
   songProj=null; buildStack(); renderJam(); renderSong(); autosave();
   say(style+' stack loaded');
  });
  host.appendChild(b);
 }
}
function renderJam(){
 renderStyles();
 const body=$('jambody');
 const scroll={}, top=body.scrollTop;
 body.querySelectorAll('.jstrip[data-key]').forEach(s=>{ scroll[s.dataset.key]=s.scrollLeft; });
 body.innerHTML='';

 if(!banksReady()){
  const w=el('div','jrow'); const b=el('div','jstrip');
  b.appendChild(el('div','empty','The preset banks are not loaded. Add ?stub to the address for the stand-in bank.'));
  w.appendChild(b); body.appendChild(w); return;
 }
 const sec=section(); if(!sec)return;

 // one row per instrument, one tile per preset, at most one tile on
 for(const inst of instruments()){
  const list=patternsFor(inst.id);
  const wrap=el('div','jrow'); const pick=sec.picks[inst.id]||null;
  if(pick)wrap.classList.add('on');
  const hd=el('div','jrhd');
  hd.appendChild(el('span','nm',inst.name||inst.id));
  hd.appendChild(el('span','slot',inst.slot||''));
  const lbl=el('span','pick'+(pick?'':' pick off'),pick?(patById(pick)?patById(pick).name:pick):'off');
  lbl.className='pick'+(pick?'':' off'); hd.appendChild(lbl);
  wrap.appendChild(hd);

  const strip=el('div','jstrip'); strip.dataset.key='i:'+inst.id;
  if(!list.length)strip.appendChild(el('div','empty','no presets yet'));
  for(const p of list){
   const t=el('button','tile'); t.type='button';
   t.appendChild(el('span','tn',p.name||p.id));
   t.appendChild(el('span','ts',p.style||''));
   const on=pick===p.id;
   t.setAttribute('aria-pressed',on?'true':'false');
   t.setAttribute('aria-label',(inst.name||inst.id)+': '+(p.name||p.id)+(p.style?', '+p.style:''));
   if((p.minEnergy||0)>sec.energy)t.classList.add('locked');
   t.addEventListener('click',()=>{ toStack();
    sec.picks[inst.id]=on?null:p.id;
    buildStack(); renderJam(); autosave(); });
   strip.appendChild(t);
  }
  wrap.appendChild(strip);
  body.appendChild(wrap);
 }

 // six light rows, one per family, at most one layer each, so at most six layers stack
 for(const fam of FAMILIES){
  const list=lightsFor(fam);
  const entry=sec.lights.find(x=>{ const p=lxById(x.id); return p&&p.family===fam; })||null;
  const wrap=el('div','jrow'); if(entry)wrap.classList.add('on');
  const hd=el('div','jrhd');
  hd.appendChild(el('span','nm',fam));
  hd.appendChild(el('span','slot','lights'));
  const lbl=el('span','pick',entry?(lxById(entry.id)?lxById(entry.id).name:entry.id):'off');
  if(!entry)lbl.classList.add('off'); hd.appendChild(lbl);
  wrap.appendChild(hd);

  const strip=el('div','jstrip'); strip.dataset.key='l:'+fam;
  if(!list.length)strip.appendChild(el('div','empty','no light patterns yet'));
  for(const p of list){
   const t=el('button','tile'); t.type='button';
   t.appendChild(el('span','tn',p.name||p.id));
   t.appendChild(el('span','ts',fam));
   const on=!!entry&&entry.id===p.id;
   t.setAttribute('aria-pressed',on?'true':'false');
   t.setAttribute('aria-label','Light layer '+fam+': '+(p.name||p.id));
   t.addEventListener('click',()=>{ toStack();
    sec.lights=sec.lights.filter(x=>{ const q=lxById(x.id); return !q||q.family!==fam; });
    if(!on)sec.lights.push({id:p.id, sync:(p.sync||'grid'), gain:(p.gain==null?1:p.gain)});
    orderLights(sec);
    buildStack(); renderJam(); autosave(); });
   strip.appendChild(t);
  }
  wrap.appendChild(strip);

  // the active layer's own controls: what it is quantised to, and how hard it hits
  if(entry){
   const ctl=el('div','lxctl');
   const sync=el('button','syncbtn'); sync.type='button';
   sync.textContent='Sync: '+syncLabel(entry.sync);
   sync.title='What this layer is locked to';
   sync.addEventListener('click',()=>{ toStack();
    const opts=syncOptions(sec); const i=opts.indexOf(entry.sync);
    entry.sync=opts[(i<0?0:i+1)%opts.length];
    sync.textContent='Sync: '+syncLabel(entry.sync);
    buildStack(); autosave(); });
   ctl.appendChild(sync);
   ctl.appendChild(el('label',null,'Gain'));
   const g=document.createElement('input'); g.type='range'; g.min='0'; g.max='1'; g.step='0.05';
   g.value=String(entry.gain==null?1:entry.gain);
   g.setAttribute('aria-label',fam+' layer gain');
   const gv=el('span','gv',fix(entry.gain==null?1:entry.gain,2));
   g.addEventListener('input',()=>{ entry.gain=+g.value; gv.textContent=fix(entry.gain,2); });
   g.addEventListener('change',()=>{ toStack(); buildStack(); autosave(); });
   ctl.appendChild(g); ctl.appendChild(gv);
   wrap.appendChild(ctl);
  }
  body.appendChild(wrap);
 }

 body.querySelectorAll('.jstrip[data-key]').forEach(s=>{ if(scroll[s.dataset.key]!=null)s.scrollLeft=scroll[s.dataset.key]; });
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
function syncLabel(id){
 if(!id||id==='grid')return 'Grid';
 const i=instruments().find(x=>x.id===id);
 return i?(i.name||i.id):id;
}

// ---------------------------------------------------------------- the Song view
function renderSong(){
 const body=$('songbody'), open={};
 body.querySelectorAll('.seccard.open').forEach(c=>{ open[c.dataset.i]=1; });
 body.innerHTML='';
 if(!jam||!jam.sections.length)return;

 jam.sections.forEach((s,i)=>{
  const card=el('div','seccard'); card.dataset.i=String(i);
  if(i===cur)card.classList.add('cur');
  if(open[String(i)])card.classList.add('open');

  const hd=el('button','sechd'); hd.type='button';
  hd.setAttribute('aria-expanded',card.classList.contains('open')?'true':'false');
  hd.appendChild(el('span','no',String(i+1)));
  const meta=el('span','meta', s.bars+' bars, '+s.meter.beats+'/'+s.meter.div+', '+s.feel+', '+s.cycle+
   (s.transition!=='none'?', '+s.transition:'')+(s.transpose?', '+(s.transpose>0?'+':'')+s.transpose:''));
  hd.appendChild(meta);
  const bar=el('span','bar'); const fill=el('i'); fill.style.width=pct(s.energy); bar.appendChild(fill);
  hd.appendChild(bar);
  const cv=el('span','cv');
  cv.innerHTML='<svg width="11" height="7" viewBox="0 0 11 7" aria-hidden="true">'+
   '<path d="M1 1l4.5 4.5L10 1" fill="none" stroke="currentColor" stroke-width="1.6" stroke-linecap="round"/></svg>';
  hd.appendChild(cv);
  hd.addEventListener('click',()=>{ const on=card.classList.toggle('open');
   hd.setAttribute('aria-expanded',on?'true':'false'); });
  card.appendChild(hd);

  const b=el('div','secbody');

  const e=document.createElement('input'); e.type='range'; e.min='0'; e.max='1'; e.step='0.05';
  e.value=String(s.energy); e.setAttribute('aria-label','Section '+(i+1)+' energy');
  const ev=el('span','gv',pct(s.energy));
  e.addEventListener('input',()=>{ s.energy=+e.value; ev.textContent=pct(s.energy); fill.style.width=pct(s.energy); });
  e.addEventListener('change',()=>{ touched(i); });
  const er=row(b,'Energy',e); er.appendChild(ev);

  row(b,'Bars',seg(BARS,s.bars,(v)=>{ s.bars=v; touched(i); renderSong(); }));
  row(b,'Feel',seg(FEELS,s.feel,(v)=>{ s.feel=v; touched(i); renderSong(); },['Straight','Half','Double']));
  row(b,'Meter',seg(METERS.map(m=>m[0]+'/'+m[1]),s.meter.beats+'/'+s.meter.div,(v)=>{
   const p=v.split('/'); s.meter={beats:+p[0],div:+p[1]}; touched(i); renderSong(); }));
  row(b,'Chords',seg(CYCLE_NAMES,s.cycle,(v)=>{ s.cycle=v; touched(i); renderSong(); }));
  row(b,'End',seg(TRANSITIONS,s.transition,(v)=>{ s.transition=v; touched(i); renderSong(); }));

  const tr=el('div','secrow'); tr.appendChild(el('label',null,'Transpose'));
  const dn=el('button',null,'-'); dn.setAttribute('aria-label','Transpose down');
  const tv=el('span','gv',(s.transpose>0?'+':'')+s.transpose);
  const up=el('button',null,'+'); up.setAttribute('aria-label','Transpose up');
  dn.addEventListener('click',()=>{ s.transpose=clamp(s.transpose-1,-12,12); tv.textContent=(s.transpose>0?'+':'')+s.transpose; touched(i); });
  up.addEventListener('click',()=>{ s.transpose=clamp(s.transpose+1,-12,12); tv.textContent=(s.transpose>0?'+':'')+s.transpose; touched(i); });
  tr.appendChild(dn); tr.appendChild(tv); tr.appendChild(up); b.appendChild(tr);

  const acts=el('div','secacts');
  const edit=el('button',null,'Jam this'); edit.addEventListener('click',()=>{ cur=i; mode='pattern';
   buildStack(); renderJam(); renderSong(); setView('jam'); });
  const dup=el('button',null,'Duplicate'); dup.addEventListener('click',()=>{
   jam.sections.splice(i+1,0,JSON.parse(JSON.stringify(s))); if(cur>i)cur++; songProj=null; renderSong(); autosave(); });
  const upB=el('button',null,'Up'); upB.disabled=i===0;
  upB.addEventListener('click',()=>{ move(i,-1); });
  const dnB=el('button',null,'Down'); dnB.disabled=i===jam.sections.length-1;
  dnB.addEventListener('click',()=>{ move(i,1); });
  const rm=el('button','danger','Remove'); rm.disabled=jam.sections.length<2;
  rm.addEventListener('click',()=>{ jam.sections.splice(i,1); cur=clamp(cur>=i?cur-1:cur,0,jam.sections.length-1);
   songProj=null; buildStack(); renderJam(); renderSong(); autosave(); });
  for(const x of [edit,dup,upB,dnB,rm])acts.appendChild(x);
  b.appendChild(acts);

  card.appendChild(b);
  body.appendChild(card);
 });
}
function move(i,d){
 const j=i+d; if(j<0||j>=jam.sections.length)return;
 const t=jam.sections[i]; jam.sections[i]=jam.sections[j]; jam.sections[j]=t;
 if(cur===i)cur=j; else if(cur===j)cur=i;
 songProj=null; renderSong(); autosave();
}
// any edit to a section invalidates the song, and the current one also rebuilds the live stack
function touched(i){ songProj=null; if(i===cur)buildStack(); if(i===cur)renderJam(); autosave(); }

// ---------------------------------------------------------------- views and the transport
function setView(v){
 view=v;
 for(const name of ['jam','song','hall']){
  const s=$('view-'+name); if(s)s.classList.toggle('on',name===v);
 }
 document.querySelectorAll('#nav button,#tabs button').forEach(b=>{
  b.setAttribute('aria-pressed',b.dataset.view===v?'true':'false'); });
 // the hall is heavy: it is only mounted the first time it is asked for
 if(v==='hall'&&!hallLoaded){ hallLoaded=true; $('sim').src='index.html?embed=1&show=live&bare=1'; }
}
function setPlaying(on){
 const b=$('play'); b.textContent=on?'Pause':'Play'; b.setAttribute('aria-pressed',on?'true':'false');
}
function playPause(){
 if(!proj)buildStack();
 if(eng.playing){ eng.pause(); setPlaying(false); return; }
 try{ eng.play({mode:mode}); }catch(e){ console.error(e); say('The audio engine would not start'); }
 setPlaying(!!eng.playing);
}
function stopAll(){ try{ eng.stop(); }catch(e){} setPlaying(false); }
function playSong(){
 if(!banksReady())return say('The preset banks are not loaded');
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
// the jam in the hash. j1 is deflate-raw, j0 is the plain JSON fallback for a browser without
// CompressionStream, so a link made on one machine always opens on another.
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
 openSheet('Share this jam',(s)=>{
  s.appendChild(el('p','muted',copied?'The link is on the clipboard and in the address bar.':'Copy this link:'));
  const box=document.createElement('input'); box.type='text'; box.value=url; box.readOnly=true;
  box.setAttribute('aria-label','Share link'); box.className='grow';
  const r=el('div','srow'); r.appendChild(box); s.appendChild(r);
  box.addEventListener('focus',()=>box.select());
  const c=el('button','sact','Copy again');
  c.addEventListener('click',()=>{ box.select();
   try{ navigator.clipboard.writeText(url); say('Link copied'); }catch(e){ say('Copy it by hand'); } });
  s.appendChild(c);
  s.appendChild(el('p','muted','Link length '+url.length+' characters.'));
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
 if(typeof Studio.exportFiles!=='function')
  return say('Export is not available in this build yet',3200);
 const p=buildSongProject(); if(!p)return;
 let fill=null;
 openSheet('Export',(s)=>{
  s.appendChild(el('p','muted','Rendering the song and measuring the mix. This runs offline and is faster than real time.'));
  const bar=el('div',null); bar.id='jbar'; fill=el('div',null); fill.id='jbarfill'; bar.appendChild(fill); s.appendChild(bar);
  s.appendChild(el('p','muted','Two files land in your downloads: the WAV and the cue JSON.'));
 });
 const name=(Studio.safeName?Studio.safeName(jam.name):String(jam.name||'jam'));
 try{
  eng.init&&eng.init();
  const r=await Studio.exportFiles(p,eng,name,(text,f)=>{ if(fill)fill.style.width=Math.round(clamp(f||0,0,1)*100)+'%'; });
  const wav=r.wavBlob instanceof Blob?r.wavBlob:new Blob([r.wavBlob],{type:'audio/wav'});
  const cues=typeof r.cuesJson==='string'?new Blob([r.cuesJson],{type:'application/json'})
   :new Blob([JSON.stringify(r.cuesJson)],{type:'application/json'});
  download(wav,name+'.wav'); download(cues,name+'.cues.json');
  closeSheet(); say('Exported '+name+'.wav and '+name+'.cues.json',3200);
  return {wav:wav.size, cues:cues.size};
 }catch(e){ console.error('export failed',e); closeSheet(); say('The export failed: '+e.message,4000); return null; }
}
// the studio restores whatever is under this key on boot, so handing a jam over is one write
function openInStudio(){
 const p=buildSongProject(); if(!p)return;
 p.name=jam.name||'jam';
 try{ localStorage.setItem(STUDIO_KEY,JSON.stringify(p)); }
 catch(e){ return say('That song is too big to hand over'); }
 location.href='studio.html';
}

// ---------------------------------------------------------------- the sheets
function menuSheet(){
 openSheet('Jam',(s)=>{
  const n=document.createElement('input'); n.type='text'; n.value=jam.name; n.maxLength=60;
  n.setAttribute('aria-label','Jam name');
  n.addEventListener('change',()=>{ jam.name=n.value.trim()||'jam'; autosave(); });
  row(s,'Name',n);

  const share=el('button','sact','Share link'); share.addEventListener('click',()=>{ shareLink(); });
  const exp=el('button','sact','Export WAV and cues'); exp.addEventListener('click',()=>{ exportShow(); });
  const st=el('button','sact','Open in the studio'); st.addEventListener('click',openInStudio);
  const nu=el('button','sact danger','Start a new jam');
  nu.addEventListener('click',()=>{ jam=freshJam(); cur=0; songProj=null;
   try{ history.replaceState(null,'',location.pathname); }catch(e){}
   buildStack(); renderJam(); renderSong(); closeSheet(); autosave(); say('New jam'); });
  for(const b of [share,exp,st,nu])s.appendChild(b);
  s.appendChild(el('p','muted','Sections: '+jam.sections.length+'. Bars: '+
   jam.sections.reduce((a,x)=>a+x.bars,0)+'.'));
 });
}
function tempoSheet(){
 openSheet('Tempo and feel',(s)=>{
  const mk=(label,min,max,step,val,onSet,fmt)=>{
   const i=document.createElement('input'); i.type='range'; i.min=String(min); i.max=String(max);
   i.step=String(step); i.value=String(val); i.setAttribute('aria-label',label);
   const v=el('span','gv',fmt(val));
   i.addEventListener('input',()=>{ v.textContent=fmt(+i.value); });
   i.addEventListener('change',()=>{ onSet(+i.value); });
   const r=row(s,label,i); r.appendChild(v);
  };
  mk('Tempo',70,180,1,jam.bpm,(v)=>{ jam.bpm=v; $('bpmval').textContent=String(v); apply(); },(v)=>String(Math.round(v)));
  mk('Swing',0,0.6,0.01,jam.swing,(v)=>{ jam.swing=v; apply(); },(v)=>fix(v,2));
  mk('Humanise',0,1,0.05,jam.humanise,(v)=>{ jam.humanise=v; apply(); },(v)=>fix(v,2));
  function apply(){ songProj=null; buildStack(); autosave(); }
 });
}

// ---------------------------------------------------------------- the frame loop
let frames=0, fpsWindow=[], lastT=0;
function loop(ts){
 requestAnimationFrame(loop); frames++;
 if(lastT){ const dt=ts-lastT; if(dt>0&&dt<500){ fpsWindow.push(dt); if(fpsWindow.length>120)fpsWindow.shift(); } }
 lastT=ts;
 let p; try{ p=eng.pos?eng.pos():null; }catch(e){ p=null; }
 if(p){
  const bar=(p.bar!=null?p.bar:Math.floor(p.step/16))+1;
  const beat=(p.beat!=null?p.beat:Math.floor(p.step/4)%4)+1;
  $('pos').textContent=bar+':'+beat;
 }
 if(eng.playing!==($('play').textContent==='Pause'))setPlaying(!!eng.playing);
 if(L.tick&&(eng.playing||frames%4===0)){ try{ L.tick(); }catch(e){} }
 if(view==='hall'&&frames%6===0){ const st=L.state||{};
  $('simstate').textContent=(st.look||'-')+' / '+(st.palette||'-')+' / '+fix(st.level==null?1:st.level,2); }
}
function fps(){ if(!fpsWindow.length)return 0;
 const mean=fpsWindow.reduce((a,b)=>a+b,0)/fpsWindow.length; return Math.round(1000/mean); }

// ---------------------------------------------------------------- boot
function navButtons(){
 const defs=[['jam','Jam'],['song','Song'],['hall','Hall']];
 for(const host of [$('nav'),$('tabs')]){
  if(!host)continue;
  host.innerHTML='';
  for(const d of defs){
   const b=el('button',null); b.type='button'; b.dataset.view=d[0];
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
 $('bpmval').textContent=String(jam.bpm);
 $('play').addEventListener('click',playPause);
 $('stop').addEventListener('click',stopAll);
 $('bpmval').addEventListener('click',tempoSheet);
 $('menubtn').addEventListener('click',menuSheet);
 $('veil').addEventListener('click',(e)=>{ if(e.target===$('veil'))closeSheet(); });
 document.addEventListener('keydown',(e)=>{ if(e.key==='Escape'&&sheetOpen){ e.preventDefault(); closeSheet(); } });

 $('addsec').addEventListener('click',()=>{
  const s=JSON.parse(JSON.stringify(section()||emptySection()));
  jam.sections.splice(cur+1,0,s); cur=cur+1; songProj=null;
  renderSong(); renderJam(); autosave(); say('Section added');
 });
 $('arcbtn').addEventListener('click',()=>{
  if(!banksReady())return say('The preset banks are not loaded');
  const a=P().arc(jam.sections.length);
  jam.sections.forEach((s,i)=>{ s.energy=clamp(a[i]==null?s.energy:a[i],0,1); });
  songProj=null; buildStack(); renderSong(); renderJam(); autosave(); say('Energy arc written');
 });
 $('songplay').addEventListener('click',playSong);

 buildStack();
 renderJam(); renderSong(); setView('jam');
 setPlaying(false);
 if(!banksReady())say('The preset banks are still being written. Add ?stub to the address for the stand-in bank.',6000);
 requestAnimationFrame(loop);
}
if(document.readyState==='loading')document.addEventListener('DOMContentLoaded',boot); else boot();

// what the verification pages poke at
Studio.jam={
 get jam(){ return jam; }, get project(){ return proj; }, get engine(){ return eng; }, get lights(){ return L; },
 get section(){ return section(); }, get mode(){ return mode; }, get view(){ return view; },
 setView, renderJam, renderSong, playSong, playPause, stopAll, shareLink, exportShow, openInStudio,
 menuSheet, tempoSheet, encodeJam, decodeJam, fps, banksReady,
 buildSong:buildSongProject,
 setCur(i){ cur=clamp(i|0,0,jam.sections.length-1); buildStack(); renderJam(); renderSong(); },
 load(j){ const s=sane(j); if(!s)return false; jam=s; cur=0; songProj=null;
  buildStack(); renderJam(); renderSong(); return true; }
};
})();
