// THE STUDIO'S MODEL (Lloyd, 2026-09-05): the one shape every studio file agrees on. A project is a
// rack of MACHINES (Caustic style: each machine is an instrument with its own bank of PATTERNS),
// a SONG that lays pattern blocks on a bar grid per machine, and a master. The Lights machine is a
// machine like any other: its notes are light cues for the hall sim rather than sounds.
//
// Steps: 16 per bar. A pattern is 1 to 8 bars. A note is {s, l, n, v}: s = step index from the
// pattern's start (integer), l = length in steps (>= 1), n = what (midi note for synths, pad index
// for the BeatBox, cue index for Lights, see LIGHT_KEYS), v = velocity 0..1 (level for a Lights
// level cue). A Lights pattern also carries `level`, one value per step or null for no change.
(function(){
'use strict';
const Studio=window.Studio=window.Studio||{};

Studio.STEPS_PER_BAR=16;
Studio.MAX_BARS=8;
Studio.PATTERN_NAMES=(()=>{ const out=[]; for(const b of 'ABCD')for(let i=1;i<=8;i++)out.push(b+i); return out; })();   // A1..D8, 32 per machine

// machine catalogue: type -> display name, kind (synth: piano keys; drum: 8 pads; lights: cue
// pads), the parameter table (key -> {name, min, max, def, unit?}) the rack panel draws as knobs
const P=(name,min,max,def,unit)=>({name,min,max,def,unit:unit||''});
Studio.MACHINE_TYPES={
 subsynth:{ name:'SubSynth', kind:'synth', color:'#4fa3ff', params:{
   osc1:P('Osc 1',0,3,1), osc2:P('Osc 2',0,3,0), mix:P('Osc mix',0,1,0.5), detune:P('Detune',0,50,8,'ct'), oct2:P('Osc 2 oct',-2,2,-1),
   cutoff:P('Cutoff',0,1,0.5), res:P('Resonance',0,1,0.2), fenv:P('Filter env',0,1,0.4), fdecay:P('Filter decay',0.02,2,0.3,'s'),
   attack:P('Attack',0.001,2,0.01,'s'), decay:P('Decay',0.01,2,0.2,'s'), sustain:P('Sustain',0,1,0.7), release:P('Release',0.01,4,0.3,'s'),
   lfoRate:P('LFO rate',0.1,20,4,'Hz'), lfoAmt:P('LFO to filter',0,1,0), glide:P('Glide',0,0.5,0,'s'), vol:P('Volume',0,1,0.7) } },
 bassline:{ name:'BassLine', kind:'synth', color:'#ff8a3d', params:{
   wave:P('Wave',0,1,0), cutoff:P('Cutoff',0,1,0.35), res:P('Resonance',0,1,0.6), envmod:P('Env mod',0,1,0.6), decay:P('Decay',0.05,1,0.25,'s'),
   accent:P('Accent',0,1,0.5), slide:P('Slide',0.02,0.3,0.08,'s'), dist:P('Distortion',0,1,0.1), vol:P('Volume',0,1,0.7) } },
 padsynth:{ name:'PadSynth', kind:'synth', color:'#b78cff', params:{
   voices:P('Voices',1,7,5), spread:P('Spread',0,60,18,'ct'), width:P('Stereo width',0,1,0.6), cutoff:P('Cutoff',0,1,0.45), res:P('Resonance',0,1,0.1),
   attack:P('Attack',0.01,4,0.4,'s'), release:P('Release',0.05,6,1.2,'s'), lfoRate:P('LFO rate',0.05,5,0.3,'Hz'), lfoAmt:P('LFO to filter',0,1,0.2), vol:P('Volume',0,1,0.5) } },
 fmsynth:{ name:'FMSynth', kind:'synth', color:'#5fd4a8', params:{
   ratio:P('Mod ratio',0.5,8,2), index:P('Mod index',0,20,4), idecay:P('Index decay',0.01,3,0.4,'s'), attack:P('Attack',0.001,1,0.005,'s'), decay:P('Decay',0.01,3,0.5,'s'),
   sustain:P('Sustain',0,1,0.2), release:P('Release',0.01,4,0.4,'s'), feedback:P('Feedback',0,1,0), vol:P('Volume',0,1,0.6) } },
 beatbox:{ name:'BeatBox', kind:'drum', color:'#ffd166', pads:['Kick','Snare','Clap','Closed hat','Open hat','Tom','Rim','Crash'], params:{
   kickTune:P('Kick tune',0,1,0.5), kickDecay:P('Kick decay',0.05,1,0.35,'s'), snareTone:P('Snare tone',0,1,0.5), snareDecay:P('Snare decay',0.05,0.6,0.18,'s'),
   hatDecay:P('Hat decay',0.01,0.3,0.05,'s'), ohatDecay:P('Open hat decay',0.05,1,0.3,'s'), tomTune:P('Tom tune',0,1,0.5), crashDecay:P('Crash decay',0.2,3,1.2,'s'),
   drive:P('Drive',0,1,0.1), vol:P('Volume',0,1,0.8) } },
 lights:{ name:'Lights', kind:'lights', color:'#ff5db1', params:{ level:P('Level',0,1,1) } },   // a master for the light level, over the pattern's level lane
};
Studio.MACHINE_ORDER=['subsynth','bassline','padsynth','fmsynth','beatbox','lights'];

// what a Lights note's n means: 0..11 a look, 12..21 a palette, 22 a hit. Read from the engine so
// the two lists never drift apart. Level cues live in pattern.level, not in notes.
Studio.LIGHT_KEYS=(()=>{ const S=window.NGVShow; const looks=S?S.LOOK_NAMES:[], pals=S?S.PALETTE_NAMES:[];
 return looks.map(n=>({kind:'look',val:n})).concat(pals.map(n=>({kind:'palette',val:n})),[{kind:'hit',val:true}]); })();
Studio.lightKeyIndex=(kind,val)=>Studio.LIGHT_KEYS.findIndex(k=>k.kind===kind&&(kind==='hit'||k.val===val));

// effects: type -> params. A machine has up to two insert slots; the master has none but a limiter
Studio.FX_TYPES={
 delay:{ name:'Delay', params:{ time:P('Time',0.05,1,0.375,'s'), feedback:P('Feedback',0,0.95,0.4), mix:P('Mix',0,1,0.25), tone:P('Tone',0,1,0.5) } },
 reverb:{ name:'Reverb', params:{ size:P('Size',0.2,6,2.2,'s'), mix:P('Mix',0,1,0.25), damp:P('Damp',0,1,0.5) } },
 chorus:{ name:'Chorus', params:{ rate:P('Rate',0.05,5,0.6,'Hz'), depth:P('Depth',0,1,0.4), mix:P('Mix',0,1,0.5) } },
 distortion:{ name:'Distortion', params:{ drive:P('Drive',0,1,0.4), tone:P('Tone',0,1,0.5), mix:P('Mix',0,1,1) } },
 filter:{ name:'Filter', params:{ type:P('Type',0,1,0), cutoff:P('Cutoff',0,1,0.5), res:P('Resonance',0,1,0.3) } },
 compressor:{ name:'Compressor', params:{ threshold:P('Threshold',-40,0,-18,'dB'), ratio:P('Ratio',1,20,4), attack:P('Attack',0.001,0.1,0.01,'s'), release:P('Release',0.02,1,0.15,'s'), makeup:P('Makeup',0,1,0.3) } },
 bitcrush:{ name:'Bitcrush', params:{ bits:P('Bits',2,16,8), rate:P('Rate',0,1,0.5), mix:P('Mix',0,1,0.5) } },
};

let uid=0;
Studio.uid=(p)=>(p||'m')+(++uid).toString(36)+Date.now().toString(36).slice(-4);
Studio.defaultParams=(table)=>{ const o={}; for(const k in table)o[k]=table[k].def; return o; };

Studio.newPattern=(type,bars)=>{ const p={bars:bars||1, notes:[]}; if(type==='lights')p.level=new Array((bars||1)*Studio.STEPS_PER_BAR).fill(null); return p; };
Studio.newMachine=(type,name)=>{ const T=Studio.MACHINE_TYPES[type]; if(!T)throw new Error('no machine type '+type);
 const m={ id:Studio.uid('m'), type, name:name||T.name, params:Studio.defaultParams(T.params), patterns:{A1:Studio.newPattern(type,1)}, curPat:'A1',
  vol:0.8, pan:0, mute:false, solo:false, fx:[null,null], send:{delay:0,reverb:0} };
 return m; };
Studio.newFx=(type)=>({ type, params:Studio.defaultParams(Studio.FX_TYPES[type].params), on:true });
Studio.newProject=(name)=>({ name:name||'untitled', bpm:124, swing:0, machines:[], song:{bars:16, tracks:{}}, master:{vol:0.9, delay:Studio.newFx('delay'), reverb:Studio.newFx('reverb')}, version:1 });

// pattern helpers
Studio.patternSteps=(p)=>p.bars*Studio.STEPS_PER_BAR;
Studio.resizePattern=(p,bars)=>{ bars=Math.max(1,Math.min(Studio.MAX_BARS,bars|0)); const n=bars*Studio.STEPS_PER_BAR; p.bars=bars; p.notes=p.notes.filter(x=>x.s<n);
 if(p.level){ const L=new Array(n).fill(null); for(let i=0;i<Math.min(n,p.level.length);i++)L[i]=p.level[i]; p.level=L; } return p; };
Studio.addNote=(p,note)=>{ const n=Studio.patternSteps(p); if(note.s<0||note.s>=n)return null; note.l=Math.max(1,Math.min(note.l||1,n-note.s));
 // a synth may hold a chord, but one note per pitch per step; drums and cues are one per (step, n)
 p.notes=p.notes.filter(x=>!(x.s===note.s&&x.n===note.n)); p.notes.push(note); p.notes.sort((a,b)=>a.s-b.s||a.n-b.n); return note; };
Studio.removeNote=(p,s,n)=>{ p.notes=p.notes.filter(x=>!(x.s===s&&x.n===n)); };
Studio.toggleNote=(p,s,n,v,l)=>{ const had=p.notes.some(x=>x.s===s&&x.n===n); if(had)Studio.removeNote(p,s,n); else Studio.addNote(p,{s,n,v:v==null?0.8:v,l:l||1}); return !had; };

// song helpers: blocks per machine track, [{bar, pat, len}] sorted by bar, never overlapping
Studio.track=(proj,mid)=>(proj.song.tracks[mid]=proj.song.tracks[mid]||[]);
Studio.placeBlock=(proj,mid,bar,pat,len)=>{ const tr=Studio.track(proj,mid); const m=proj.machines.find(x=>x.id===mid); const p=m&&m.patterns[pat]; if(!p)return null;
 len=len||p.bars; const b={bar,pat,len}; proj.song.tracks[mid]=tr.filter(x=>x.bar+x.len<=bar||x.bar>=bar+len); proj.song.tracks[mid].push(b); proj.song.tracks[mid].sort((a,c)=>a.bar-c.bar);
 proj.song.bars=Math.max(proj.song.bars,bar+len); return b; };
Studio.removeBlock=(proj,mid,bar)=>{ const tr=Studio.track(proj,mid); proj.song.tracks[mid]=tr.filter(x=>!(bar>=x.bar&&bar<x.bar+x.len)); };
Studio.songLengthBars=(proj)=>{ let n=0; for(const mid in proj.song.tracks)for(const b of proj.song.tracks[mid])n=Math.max(n,b.bar+b.len); return Math.max(n,1); };
Studio.stepSeconds=(bpm)=>60/bpm/4;
Studio.barSeconds=(bpm)=>60/bpm*4;

// every note of the song, flattened to absolute steps: [{mid, s, l, n, v, pat}], for the engine's
// scheduler and the export. In pattern mode the same function runs on one bar-loop of the current
// patterns (mode 'pattern'): every machine's current pattern from step 0, looped by the caller.
Studio.flatten=(proj,mode)=>{ const out=[];
 if(mode==='pattern'){ for(const m of proj.machines){ const p=m.patterns[m.curPat]; if(!p)continue; for(const x of p.notes)out.push({mid:m.id,s:x.s,l:x.l,n:x.n,v:x.v,pat:m.curPat,type:m.type}); } }
 else { for(const m of proj.machines){ for(const b of Studio.track(proj,m.id)){ const p=m.patterns[b.pat]; if(!p)continue; const ps=Studio.patternSteps(p), blockSteps=b.len*Studio.STEPS_PER_BAR;
   // a block longer than its pattern repeats the pattern (Caustic does the same)
   for(let off=0;off<blockSteps;off+=ps)for(const x of p.notes){ if(off+x.s>=blockSteps)continue; out.push({mid:m.id,s:b.bar*Studio.STEPS_PER_BAR+off+x.s,l:Math.min(x.l,blockSteps-off-x.s),n:x.n,v:x.v,pat:b.pat,type:m.type}); } } } }
 out.sort((a,b)=>a.s-b.s||a.n-b.n); return out; };
// the Lights level lane, flattened the same way: [{s, v}]
Studio.flattenLevel=(proj,mode)=>{ const out=[]; for(const m of proj.machines){ if(m.type!=='lights')continue;
 if(mode==='pattern'){ const p=m.patterns[m.curPat]; if(p&&p.level)p.level.forEach((v,i)=>{ if(v!=null)out.push({s:i,v}); }); }
 else for(const b of Studio.track(proj,m.id)){ const p=m.patterns[b.pat]; if(!p||!p.level)continue; const ps=Studio.patternSteps(p), bs=b.len*Studio.STEPS_PER_BAR;
   for(let off=0;off<bs;off+=ps)p.level.forEach((v,i)=>{ if(v!=null&&off+i<bs)out.push({s:b.bar*Studio.STEPS_PER_BAR+off+i,v}); }); } }
 out.sort((a,b)=>a.s-b.s); return out; };
// pattern-mode loop length in steps: the longest current pattern across the rack
Studio.patternLoopSteps=(proj)=>{ let n=Studio.STEPS_PER_BAR; for(const m of proj.machines){ const p=m.patterns[m.curPat]; if(p)n=Math.max(n,Studio.patternSteps(p)); } return n; };

// THE DEMO PROJECT: the studio opens on something that plays, so the first Play makes sound and
// light. Four bars of a 124 bpm groove in A minor, looks changing on the bar.
Studio.demoProject=()=>{ const pr=Studio.newProject('demo'); const S=Studio.STEPS_PER_BAR;
 const drums=Studio.newMachine('beatbox','Drums'); const dp=Studio.resizePattern(drums.patterns.A1,1);
 for(let i=0;i<16;i+=4)Studio.addNote(dp,{s:i,n:0,v:1,l:1}); Studio.addNote(dp,{s:4,n:1,v:0.9,l:1}); Studio.addNote(dp,{s:12,n:1,v:0.9,l:1}); Studio.addNote(dp,{s:4,n:2,v:0.6,l:1}); Studio.addNote(dp,{s:12,n:2,v:0.6,l:1});
 for(let i=2;i<16;i+=4)Studio.addNote(dp,{s:i,n:3,v:0.7,l:1}); Studio.addNote(dp,{s:14,n:4,v:0.5,l:1});
 const bass=Studio.newMachine('bassline','Bass'); const bp=Studio.resizePattern(bass.patterns.A1,1);
 const A1=45; [[0,A1],[3,A1],[6,A1+12],[8,A1],[10,A1+3],[12,A1],[14,A1+7]].forEach(([s,n],i)=>Studio.addNote(bp,{s,n,v:i%3===0?1:0.7,l:1}));
 const pad=Studio.newMachine('padsynth','Pad'); const pp=Studio.resizePattern(pad.patterns.A1,4);
 [[0,[57,60,64]],[16,[53,57,60]],[32,[60,64,67]],[48,[55,59,62]]].forEach(([s,ns])=>ns.forEach(n=>Studio.addNote(pp,{s,n,v:0.8,l:16})));
 const arp=Studio.newMachine('subsynth','Pluck'); arp.params.decay=0.12; arp.params.sustain=0; arp.params.cutoff=0.6; arp.params.fenv=0.5; const ap=Studio.resizePattern(arp.patterns.A1,1);
 [69,72,76,81,76,72,69,64,69,72,76,81,76,72,69,64].forEach((n,i)=>{ if(i%2===0)Studio.addNote(ap,{s:i,n,v:0.6,l:1}); });
 const lights=Studio.newMachine('lights','Lights'); const lp=Studio.resizePattern(lights.patterns.A1,4);
 const LK=Studio.lightKeyIndex; Studio.addNote(lp,{s:0,n:LK('look','pulse'),v:1,l:1}); Studio.addNote(lp,{s:0,n:LK('palette','helix'),v:1,l:1});
 Studio.addNote(lp,{s:16,n:LK('look','beatwave'),v:1,l:1}); Studio.addNote(lp,{s:32,n:LK('look','helix'),v:1,l:1}); Studio.addNote(lp,{s:32,n:LK('palette','ice'),v:1,l:1});
 Studio.addNote(lp,{s:48,n:LK('look','sweep'),v:1,l:1}); Studio.addNote(lp,{s:48,n:LK('hit',true),v:1,l:1});
 pr.machines.push(drums,bass,pad,arp,lights);
 for(const m of pr.machines)Studio.placeBlock(pr,m.id,0,'A1',8);
 pr.song.bars=8; return pr; };

// deep copy that survives JSON (typed arrays are never stored, so this is enough)
Studio.clone=(o)=>JSON.parse(JSON.stringify(o));
})();
