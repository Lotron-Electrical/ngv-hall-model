// THE JAM'S STAND-IN PRESET BANK (Lloyd, 2026-09-05): loaded only by jam.html?stub, and only used
// where the real bank is missing. CORE, RHYTHM, PITCH and LXPRESETS are writing presets.js and the
// three preset files in parallel with this page; until they land the jam has nothing to draw, so
// this file provides the same shapes with a handful of hand-written patterns. It is deliberately
// dumb music: the point is that every row, tile, card and screenshot exists and that the engine
// has something real to play, not that it sounds good.
//
// Nothing here overwrites a real bank. Each global is filled in only when it is absent, so once
// the real files are in the load order ?stub becomes a no-op.
(function(){
'use strict';
const Studio=window.Studio=window.Studio||{};
const SPB=16;
const clamp=(x,a,b)=>x<a?a:x>b?b:x;

// the ten instruments, same ids and slots as the frozen table so the jam's rows are the real rows
const INSTS=[
 {id:'drums', type:'beatbox',  name:'Drums',      slot:'drums',   vol:0.85, send:{delay:0,   reverb:0.05}, params:{drive:0.15}},
 {id:'perc',  type:'beatbox',  name:'Percussion', slot:'perc',    vol:0.6,  send:{delay:0.15,reverb:0},    params:{kickTune:0.8,snareTone:0.8,hatDecay:0.03,drive:0.05}},
 {id:'bass',  type:'bassline', name:'Bass',       slot:'low',     vol:0.75, send:{delay:0,   reverb:0},    params:{cutoff:0.35,res:0.55,decay:0.25,dist:0.15}},
 {id:'sub',   type:'subsynth', name:'Sub',        slot:'sub',     vol:0.8,  send:{delay:0,   reverb:0},    params:{osc1:3,osc2:3,mix:0,cutoff:0.25,res:0,fenv:0,decay:0.2,sustain:1}},
 {id:'pad',   type:'padsynth', name:'Pad',        slot:'mid-low', vol:0.5,  send:{delay:0,   reverb:0.35}, params:{voices:5,spread:18,cutoff:0.4,attack:0.5,release:1.5}},
 {id:'chords',type:'padsynth', name:'Chords',     slot:'mid-low', vol:0.55, send:{delay:0.2, reverb:0.15}, params:{voices:3,spread:10,cutoff:0.55,attack:0.01,release:0.25}},
 {id:'keys',  type:'fmsynth',  name:'Keys',       slot:'mid',     vol:0.55, send:{delay:0,   reverb:0.2},  params:{ratio:2,index:3,decay:0.6,sustain:0.3}},
 {id:'lead',  type:'subsynth', name:'Lead',       slot:'high',    vol:0.5,  send:{delay:0.3, reverb:0.2},  params:{osc1:1,osc2:1,mix:0.5,cutoff:0.55,res:0.25,decay:0.3}},
 {id:'arp',   type:'subsynth', name:'Arp',        slot:'high',    vol:0.45, send:{delay:0.35,reverb:0},    params:{osc1:1,osc2:2,mix:0.4,cutoff:0.6,res:0.3,decay:0.12,sustain:0}},
 {id:'fx',    type:'fmsynth',  name:'FX',         slot:'top',     vol:0.4,  send:{delay:0,   reverb:0.5},  params:{ratio:1.5,index:8,decay:2,sustain:0.6}}
];

// A minor, the frozen house key. Chord cycles as pitch classes plus a quality, enough to place a
// triad; the real harmony module parses chord names properly.
const CHORDS={ Am:[9,0,4], F:[5,9,0], C:[0,4,7], G:[7,11,2], Dm:[2,5,9], Em:[4,7,11], D:[2,6,9], E7:[4,8,11] };
const CYCLES={ neutral:['Am','F','C','G'], dark:['Am','Dm','Em','Am'], lift:['Am','F','G','Em'],
 pull:['Am','F','E7','E7'], bright:['Am','D','F','G'] };
const ROOT=57;   // A3

// fold a pitch class into a register window, so a bass line stays a bass line
function fold(pc,lo,hi){ let n=lo+(((pc-lo)%12)+12)%12; while(n<lo)n+=12; while(n>hi)n-=12; return n; }

// ---- pattern generators. Each takes (ctx) and returns notes on a spb-step bar grid.
function drumGen(kick,snare,hat){
 return function(ctx){
  const out=[], n=ctx.spb, bars=ctx.bars, v=0.55+0.45*ctx.energy;
  for(let b=0;b<bars;b++){ const off=b*n;
   for(const s of kick) if(s<n) out.push({s:off+s,l:1,n:0,v:clamp(v,0,1)});
   for(const s of snare)if(s<n) out.push({s:off+s,l:1,n:1,v:clamp(v*0.9,0,1)});
   for(let s=0;s<n;s+=hat)   out.push({s:off+s,l:1,n:3,v:clamp(v*0.55,0,1)});
  }
  return out;
 };
}
// a pitched line: each entry is [step, length, chord tone index, octave offset, velocity]
function pitchGen(shape,lo,hi){
 return function(ctx){
  const out=[], n=ctx.spb, v=0.55+0.45*ctx.energy;
  for(let b=0;b<ctx.bars;b++){
   const name=ctx.chords[Math.floor(b/ctx.cycleBars)%ctx.chords.length], tones=CHORDS[name]||CHORDS.Am, off=b*n;
   for(const e of shape){ if(e[0]>=n)continue;
    const pc=tones[e[2]%tones.length];
    out.push({s:off+e[0], l:Math.min(e[1],n-e[0]), n:fold(pc,lo,hi)+12*e[3]+ctx.transpose, v:clamp(v*e[4],0,1)}); }
  }
  return out;
 };
}

const PATS=[
 {id:'drums.four',  inst:'drums', name:'Four to the floor', style:'house',  minEnergy:0.1, gen:drumGen([0,4,8,12],[4,12],2)},
 {id:'drums.break', inst:'drums', name:'Broken',            style:'breakbeat', minEnergy:0.2, gen:drumGen([0,10],[4,12],2)},
 {id:'perc.tick',   inst:'perc',  name:'Ticker',            style:'techno', minEnergy:0.2, gen:drumGen([],[],4)},
 {id:'perc.roll',   inst:'perc',  name:'Roller',            style:'dnb',    minEnergy:0.4, gen:drumGen([6],[14],2)},
 {id:'bass.roll',   inst:'bass',  name:'Rolling',           style:'house',  minEnergy:0.1, gen:pitchGen([[0,3,0,0,1],[6,2,0,0,0.7],[10,3,2,0,0.8]],33,45)},
 {id:'bass.stab',   inst:'bass',  name:'Stabs',             style:'techno', minEnergy:0.3, gen:pitchGen([[0,2,0,0,1],[8,2,0,0,0.8]],33,45)},
 {id:'sub.hold',    inst:'sub',   name:'Held',              style:'ambient',minEnergy:0,   gen:pitchGen([[0,16,0,0,0.9]],28,39)},
 {id:'sub.pump',    inst:'sub',   name:'Pumping',           style:'dubstep',minEnergy:0.3, gen:pitchGen([[0,6,0,0,1],[8,6,0,0,0.8]],28,39)},
 {id:'pad.warm',    inst:'pad',   name:'Warm bed',          style:'house',  minEnergy:0,   gen:pitchGen([[0,16,0,0,0.8],[0,16,1,0,0.7],[0,16,2,0,0.6]],48,72)},
 {id:'pad.air',     inst:'pad',   name:'Air',               style:'ambient',minEnergy:0,   gen:pitchGen([[0,16,1,1,0.6],[0,16,2,1,0.5]],55,79)},
 {id:'chords.push', inst:'chords',name:'Pushed',            style:'house',  minEnergy:0.2, gen:pitchGen([[2,2,0,0,0.8],[2,2,1,0,0.7],[10,2,2,0,0.7]],52,72)},
 {id:'chords.hold', inst:'chords',name:'Held',              style:'ambient',minEnergy:0,   gen:pitchGen([[0,8,0,0,0.7],[0,8,2,0,0.6]],52,72)},
 {id:'keys.pluck',  inst:'keys',  name:'Pluck',             style:'hiphop', minEnergy:0.2, gen:pitchGen([[0,2,0,0,0.8],[4,2,2,0,0.6],[12,2,1,0,0.7]],55,76)},
 {id:'keys.riff',   inst:'keys',  name:'Riff',              style:'trap',   minEnergy:0.3, gen:pitchGen([[0,1,0,0,0.9],[3,1,1,0,0.6],[6,1,2,0,0.7],[11,1,0,1,0.6]],55,76)},
 {id:'lead.call',   inst:'lead',  name:'Call',              style:'house',  minEnergy:0.4, gen:pitchGen([[0,4,2,0,0.8],[8,4,1,0,0.7]],60,79)},
 {id:'lead.hook',   inst:'lead',  name:'Hook',              style:'trap',   minEnergy:0.5, gen:pitchGen([[0,2,0,1,0.9],[4,2,2,0,0.7],[10,4,1,0,0.7]],60,79)},
 {id:'arp.up',      inst:'arp',   name:'Climbing',          style:'techno', minEnergy:0.3, gen:pitchGen([[0,1,0,0,0.8],[2,1,1,0,0.6],[4,1,2,0,0.7],[6,1,0,1,0.6],[8,1,1,0,0.6],[10,1,2,0,0.7],[12,1,0,1,0.6],[14,1,1,1,0.6]],60,79)},
 {id:'arp.down',    inst:'arp',   name:'Falling',           style:'dnb',    minEnergy:0.4, gen:pitchGen([[0,1,2,1,0.8],[3,1,1,0,0.6],[6,1,0,0,0.7],[9,1,2,0,0.6],[12,1,1,0,0.6]],60,79)},
 {id:'fx.swell',    inst:'fx',    name:'Swell',             style:'ambient',minEnergy:0,   gen:pitchGen([[0,16,0,1,0.6]],64,84)},
 {id:'fx.sting',    inst:'fx',    name:'Sting',             style:'abstract',minEnergy:0.4,gen:pitchGen([[12,4,1,1,0.7]],64,84)}
];

// ---- the light bank. Two per family; the looks and palettes are read off lightshow.js at build
// time so a name that does not exist can never reach a cue.
const FAMILIES=['base','movement','accent','strobe','texture','colour'];
function lookNames(){ return (window.NGVShow&&window.NGVShow.LOOK_NAMES)||[]; }
function palNames(){ return (window.NGVShow&&window.NGVShow.PALETTE_NAMES)||[]; }
function pickLook(i){ const L=lookNames(); return L.length?L[i%L.length]:null; }
function pickPal(i){ const P=palNames(); return P.length?P[i%P.length]:null; }

const LX=[];
FAMILIES.forEach((fam,fi)=>{
 for(let k=0;k<2;k++){
  LX.push({ id:'lx.'+fam+(k+1), name:(k?'Second ':'First ')+fam, family:fam, style:['house','techno','ambient'],
   energy:[0,1], bars:4, gain:1, sync:'grid', lookIdx:fi*2+k, palIdx:fi+k });
 }
});

// ---- building a project out of picks ---------------------------------------------------------
function instById(id){ return INSTS.find(x=>x.id===id)||null; }
function patById(id){ return PATS.find(x=>x.id===id)||null; }
function lxById(id){ return LX.find(x=>x.id===id)||null; }

function ctxFor(section,jam){
 const meter=section.meter||{beats:4,div:4};
 return { spb:Studio.barSteps?Studio.barSteps(meter):SPB, bars:1,
  chords:CYCLES[section.cycle||'neutral']||CYCLES.neutral, cycleBars:1,
  transpose:section.transpose||0, energy:section.energy==null?0.6:section.energy,
  key:ROOT, seed:(jam&&jam.seed)||1 };
}

// one machine per picked instrument, its pattern rendered for this section
function addInstruments(proj,section,jam,barsPerPattern){
 const ctx=ctxFor(section,jam); ctx.bars=barsPerPattern;
 const made=[];
 for(const inst of INSTS){
  const pid=section.picks&&section.picks[inst.id]; if(!pid)continue;
  const preset=patById(pid); if(!preset)continue;
  if(ctx.energy<(preset.minEnergy||0))continue;
  const m=Studio.newMachine(inst.type,inst.name);
  Object.assign(m.params,inst.params||{});
  m.vol=inst.vol; m.send={delay:(inst.send&&inst.send.delay)||0, reverb:(inst.send&&inst.send.reverb)||0};
  m.inst=inst.id; m.slot=inst.slot;
  const pat={bars:barsPerPattern, spb:ctx.spb, notes:preset.gen(ctx), src:preset.id};
  m.patterns={A1:pat}; m.curPat='A1';
  proj.machines.push(m);
  made.push({inst:inst.id, mid:m.id});
 }
 return made;
}

// one Lights machine per layer, its cues written as notes on the pattern
function addLights(proj,section,jam,barsPerPattern,instMap){
 const list=(section.lights||[]).slice(0,6);
 list.forEach((entry,i)=>{
  const preset=lxById(entry.id); if(!preset)return;
  const m=Studio.newMachine('lights','LX '+(i+1)+' '+preset.family);
  m.layer=i; m.family=preset.family;
  const syncId=entry.sync&&entry.sync!=='grid'?(instMap[entry.sync]||'grid'):'grid';
  m.sync=syncId;
  const e=section.energy==null?0.6:section.energy;
  m.params.level=clamp((entry.gain==null?preset.gain:entry.gain)*(0.15+0.85*e),0,1);
  const spb=Studio.barSteps?Studio.barSteps(section.meter||{beats:4,div:4}):SPB;
  const pat=Studio.newPattern('lights',barsPerPattern);
  pat.spb=spb; pat.level=new Array(barsPerPattern*spb).fill(null);
  const look=pickLook(preset.lookIdx), pal=pickPal(preset.palIdx);
  if(look!=null){ const n=Studio.lightKeyIndex('look',look); if(n>=0)pat.notes.push({s:0,l:1,n,v:1}); }
  if(pal!=null){ const n=Studio.lightKeyIndex('palette',pal); if(n>=0)pat.notes.push({s:0,l:1,n,v:1}); }
  if(preset.family==='accent'){ const n=Studio.lightKeyIndex('hit',true);
   if(n>=0)for(let b=0;b<barsPerPattern;b++)pat.notes.push({s:b*spb,l:1,n,v:1}); }
  m.patterns={A1:pat}; m.curPat='A1';
  proj.machines.push(m);
 });
}

const STUB={
 stub:true,
 instruments:INSTS,
 CYCLES,
 // the live stack: one section, pattern mode, everything one bar long so it loops tight
 buildStack:function(section,jam){
  const proj=Studio.newProject((jam&&jam.name)||'jam');
  proj.bpm=(jam&&jam.bpm)||124; proj.swing=(jam&&jam.swing)||0;
  const map={}; for(const x of addInstruments(proj,section,jam,1))map[x.inst]=x.mid;
  addLights(proj,section,jam,1,map);
  return proj;
 },
 // the song: every section rendered in turn and its blocks placed on the timeline
 buildSong:function(jam){
  const proj=Studio.newProject((jam&&jam.name)||'jam');
  proj.bpm=(jam&&jam.bpm)||124; proj.swing=(jam&&jam.swing)||0;
  proj.song.sections=[]; proj.song.autom=[];
  const sections=(jam&&jam.sections)||[];
  const byInst={}, byLayer={};
  let bar=0;
  sections.forEach((section,si)=>{
   const len=section.bars||8, ctx=ctxFor(section,jam); ctx.bars=1;
   const name='S'+(si+1);
   for(const inst of INSTS){
    const pid=section.picks&&section.picks[inst.id]; if(!pid)continue;
    const preset=patById(pid); if(!preset)continue;
    if(ctx.energy<(preset.minEnergy||0))continue;
    let m=byInst[inst.id];
    if(!m){ m=Studio.newMachine(inst.type,inst.name); Object.assign(m.params,inst.params||{});
     m.vol=inst.vol; m.send={delay:(inst.send&&inst.send.delay)||0, reverb:(inst.send&&inst.send.reverb)||0};
     m.inst=inst.id; m.slot=inst.slot; m.patterns={}; byInst[inst.id]=m; proj.machines.push(m); }
    m.patterns[name]={bars:1, spb:ctx.spb, notes:preset.gen(ctx), src:preset.id};
    if(!m.curPat)m.curPat=name;
    const tr=Studio.track(proj,m.id);
    for(let b=0;b<len;b++)tr.push({bar:bar+b, pat:name, len:1});
   }
   (section.lights||[]).slice(0,6).forEach((entry,i)=>{
    const preset=lxById(entry.id); if(!preset)return;
    let m=byLayer[i];
    if(!m){ m=Studio.newMachine('lights','LX '+(i+1)); m.layer=i; m.family=preset.family; m.sync='grid';
     m.patterns={}; byLayer[i]=m; proj.machines.push(m); }
    m.family=preset.family;
    const spb=ctx.spb, pat=Studio.newPattern('lights',1); pat.spb=spb; pat.level=new Array(spb).fill(null);
    const look=pickLook(preset.lookIdx), pal=pickPal(preset.palIdx);
    if(look!=null){ const n=Studio.lightKeyIndex('look',look); if(n>=0)pat.notes.push({s:0,l:1,n,v:1}); }
    if(pal!=null){ const n=Studio.lightKeyIndex('palette',pal); if(n>=0)pat.notes.push({s:0,l:1,n,v:1}); }
    m.patterns[name]=pat; if(!m.curPat)m.curPat=name;
    const tr=Studio.track(proj,m.id);
    for(let b=0;b<len;b++)tr.push({bar:bar+b, pat:name, len:1});
   });
   proj.song.sections.push({ bar, len, meter:section.meter||{beats:4,div:4}, bpm:proj.bpm,
    feel:section.feel||'straight', key:{root:ROOT,scale:'minor'},
    chords:CYCLES[section.cycle||'neutral']||CYCLES.neutral, cycleBars:1,
    transpose:section.transpose||0, energy:section.energy==null?0.6:section.energy,
    transition:section.transition||'none', seed:(jam&&jam.seed)||1 });
   bar+=len;
  });
  proj.song.bars=Math.max(1,bar);
  return proj;
 },
 // a whole stack for a style at middling energy, the tap-a-chip starter
 starter:function(style){
  const picks={};
  for(const inst of INSTS){
   const forStyle=PATS.filter(p=>p.inst===inst.id&&p.style===style);
   const any=PATS.filter(p=>p.inst===inst.id);
   const pick=(forStyle[0]||any[0]);
   picks[inst.id]=pick?pick.id:null;
  }
  const lights=[ {id:'lx.base1',sync:'grid',gain:1},
   {id:'lx.movement1',sync:'drums',gain:0.8},
   {id:'lx.colour1',sync:'grid',gain:0.7} ];
  return { bars:8, energy:0.6, feel:'straight', meter:{beats:4,div:4}, cycle:'neutral',
   transpose:0, transition:'none', picks, lights };
 },
 // the house energy curve resampled to however many sections there are
 arc:function(n){
  const base=[0.15,0.45,0.9,0.3,0.6,1.0,0.2], out=[];
  n=Math.max(1,n|0);
  for(let i=0;i<n;i++){ const x=n===1?0:i/(n-1)*(base.length-1);
   const a=Math.floor(x), b=Math.min(base.length-1,a+1), f=x-a;
   out.push(Math.round((base[a]*(1-f)+base[b]*f)*100)/100); }
  return out;
 },
 render:function(preset,ctx){ const g=preset&&preset.gen;
  return {bars:ctx.bars||1, spb:ctx.spb||SPB, notes:g?g(ctx):[], src:preset&&preset.id}; }
};

// fill in only what is missing, so ?stub is harmless once the real files are in the load order
if(!Studio.PRESETS)Studio.PRESETS=STUB;
if(!Studio.PRESETS_DRUMS)Studio.PRESETS_DRUMS={stub:true, list:PATS.filter(p=>p.inst==='drums'||p.inst==='perc')};
if(!Studio.PRESETS_PITCH)Studio.PRESETS_PITCH={stub:true, list:PATS.filter(p=>p.inst!=='drums'&&p.inst!=='perc')};
if(!Studio.PRESETS_LIGHTS)Studio.PRESETS_LIGHTS={stub:true, list:LX};
})();
