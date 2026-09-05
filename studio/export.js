// THE EXPORT (Lloyd, 2026-09-05): a project becomes two files the hall can play on its own. The
// music is rendered offline and written as a 16 bit WAV; the cue file carries the light cues on the
// same clock plus the bands MEASURED off that rendered audio, so the hall reacts to the mix that
// actually exists rather than to a guess made from the notes.
//
// Both go into show/ through the dev server's POST /save, and the show's name is added to
// show/shows.json so index.html lists it. index.html?show=<name> then plays it.
(function(){
'use strict';
const Studio=window.Studio=window.Studio||{};

const clamp=(x,a,b)=>x<a?a:x>b?b:x;
const r4=x=>Math.round(x*10000)/10000;
const arr4=a=>Array.from(a,r4);
const safeName=n=>String(n||'untitled').replace(/[^\w.-]+/g,'-').replace(/^-+|-+$/g,'')||'untitled';
Studio.safeName=safeName;

// ---- the radix-2 FFT the frame analysis runs on. In place, re/im both length a power of two.
function fft(re,im){
 const n=re.length;
 for(let i=1,j=0;i<n;i++){ let bit=n>>1; for(;j&bit;bit>>=1)j^=bit; j^=bit;
  if(i<j){ let t=re[i];re[i]=re[j];re[j]=t; t=im[i];im[i]=im[j];im[j]=t; } }
 for(let len=2;len<=n;len<<=1){ const ang=-2*Math.PI/len, wr=Math.cos(ang), wi=Math.sin(ang);
  for(let i=0;i<n;i+=len){ let cr=1,ci=0; const h=len>>1;
   for(let k=0;k<h;k++){
    const ur=re[i+k], ui=im[i+k];
    const vr=re[i+k+h]*cr-im[i+k+h]*ci, vi=re[i+k+h]*ci+im[i+k+h]*cr;
    re[i+k]=ur+vr; im[i+k]=ui+vi; re[i+k+h]=ur-vr; im[i+k+h]=ui-vi;
    const ncr=cr*wr-ci*wi; ci=cr*wi+ci*wr; cr=ncr;
   } } }
}
function pct99(a){ const c=Float32Array.from(a); c.sort(); return c[Math.max(0,Math.floor(0.99*(c.length-1)))]||1e-9; }
function normalise(a){ const p=pct99(a), out=new Float32Array(a.length);
 for(let i=0;i<a.length;i++)out[i]=clamp(a[i]/p,0,1); return out; }
function smooth3(a){ const out=new Float32Array(a.length);
 for(let i=0;i<a.length;i++){ let s=0,c=0; for(let d=-1;d<=1;d++){ const j=i+d; if(j>=0&&j<a.length){s+=a[j];c++;} } out[i]=s/c; }
 return out; }

// frames off the rendered buffer: 2048 window, 1024 hop, Hann, bands as the sqrt of mean power so
// they read as amplitudes and not as energies (energy makes a quiet passage look dead).
// The 3 frame smoothing comes BEFORE the normalise on purpose: averaging an already normalised
// array pulls its peaks back under 1 and the band never reaches full. The onset stays sharp,
// because a blunted transient is not an onset.
function analyseBuffer(buf){
 const N=2048, HOP=1024, sr=buf.sampleRate;
 const L=buf.getChannelData(0), R=buf.numberOfChannels>1?buf.getChannelData(1):L;
 const n=L.length, mono=new Float32Array(n);
 for(let i=0;i<n;i++)mono[i]=(L[i]+R[i])*0.5;
 const win=new Float32Array(N); for(let i=0;i<N;i++)win[i]=0.5-0.5*Math.cos(2*Math.PI*i/N);
 const nf=Math.max(1,Math.floor((n-N)/HOP)+1);
 const rms=new Float32Array(nf), bass=new Float32Array(nf), mid=new Float32Array(nf),
       high=new Float32Array(nf), onset=new Float32Array(nf);
 const re=new Float32Array(N), im=new Float32Array(N), mag=new Float32Array(N/2), prev=new Float32Array(N/2);
 const hz=sr/N, bin=f=>clamp(Math.round(f/hz),1,N/2-1);
 const b0=bin(20), b1=bin(150), m1=bin(2000), h1=bin(11000);
 const rmsPow=(lo,hi)=>{ let s=0,c=0; for(let i=lo;i<hi;i++){ s+=mag[i]*mag[i]; c++; } return c?Math.sqrt(s/c):0; };
 for(let f=0;f<nf;f++){
  const off=f*HOP; let e=0;
  for(let i=0;i<N;i++){ const v=(off+i<n?mono[off+i]:0)*win[i]; re[i]=v; im[i]=0; e+=v*v; }
  rms[f]=Math.sqrt(e/N);
  fft(re,im);
  let flux=0;
  for(let i=0;i<N/2;i++){ const m=Math.sqrt(re[i]*re[i]+im[i]*im[i]); mag[i]=m;
   const d=m-prev[i]; if(d>0)flux+=d; prev[i]=m; }
  bass[f]=rmsPow(b0,b1); mid[f]=rmsPow(b1,m1); high[f]=rmsPow(m1,h1); onset[f]=flux;
 }
 return { rms:normalise(smooth3(rms)), bass:normalise(smooth3(bass)), mid:normalise(smooth3(mid)),
  high:normalise(smooth3(high)), onset:normalise(onset), nf, hop_s:HOP/sr };
}

// 16 bit PCM stereo, the format every browser and every media player opens without help
function wav16(buf){
 const ch=Math.min(2,buf.numberOfChannels), n=buf.length, sr=buf.sampleRate;
 const L=buf.getChannelData(0), R=ch>1?buf.getChannelData(1):L;
 const bytes=44+n*ch*2, ab=new ArrayBuffer(bytes), v=new DataView(ab);
 const str=(o,s)=>{ for(let i=0;i<s.length;i++)v.setUint8(o+i,s.charCodeAt(i)); };
 str(0,'RIFF'); v.setUint32(4,bytes-8,true); str(8,'WAVE'); str(12,'fmt ');
 v.setUint32(16,16,true); v.setUint16(20,1,true); v.setUint16(22,ch,true);
 v.setUint32(24,sr,true); v.setUint32(28,sr*ch*2,true); v.setUint16(32,ch*2,true); v.setUint16(34,16,true);
 str(36,'data'); v.setUint32(40,n*ch*2,true);
 let o=44;
 for(let i=0;i<n;i++)for(let c=0;c<ch;c++){ const s=clamp(c?R[i]:L[i],-1,1);
  v.setInt16(o,s<0?s*32768:s*32767,true); o+=2; }
 return ab;
}

// ---- files in and out of the repo, through the dev server. Reads are root absolute so a page
// served from a subfolder (the test page under studio/) still finds show/ where it really is.
const SHOW='/show/';
async function post(path,body,type){
 const r=await fetch('/save?path='+encodeURIComponent(path),{method:'POST',
  headers:{'Content-Type':type||'application/octet-stream'},body});
 if(!r.ok)throw new Error('save failed: '+r.status+' '+await r.text());
 return r.json();
}
Studio.post=post;

Studio.saveProject=async function(proj){
 const p='show/'+safeName(proj&&proj.name)+'.project.json';
 const r=await post(p,JSON.stringify(proj,null,1),'application/json');
 return {path:p,bytes:r.bytes};
};
Studio.loadProject=async function(name){
 const p=SHOW+safeName(name)+'.project.json';
 try{ const r=await fetch(p+'?x='+Date.now(),{cache:'no-store'}); if(!r.ok)return null;
  const j=await r.json(); return (j&&j.machines&&j.song)?j:null; }
 catch(e){ return null; }
};
Studio.listShows=async function(){
 try{ const r=await fetch(SHOW+'shows.json?x='+Date.now(),{cache:'no-store'});
  if(!r.ok)return []; const j=await r.json(); return Array.isArray(j)?j:[]; }
 catch(e){ return []; }
};

// the Lights machines in layer order, capped at six, exactly as studio/lights.js orders them
function lightLayers(proj){ const out=proj.machines.filter(m=>m.type==='lights');
 out.sort((a,b)=>(a.layer|0)-(b.layer|0)); return out.slice(0,6); }

// THE CUE TIMELINE (v2, 2026-09-05): every Lights machine's notes and the shared level lane, on
// the timeline's clock so a 7/8 or 130 bpm section lands where it sounds. One entry per (layer,
// moment), so the hall applies a look, its palette and a hit from a single stamp.
//
// Layer 0 keeps the v1 fields (look, palette, level, hit) untouched, so a player that has never
// heard of layers still gets the main look and the master level. Layers 1..5 add `layer`, plus the
// `gain`, `sync` and `family` the compositor needs, stamped at t = 0 where the layer starts.
function cueList(proj){
 const T=Studio.timeline?Studio.timeline(proj):null;
 const sec=Studio.stepSeconds(proj.bpm||124);
 const tAt=s=>r4(T?T.time(s):s*sec);
 const by=new Map();
 const at=(layer,s)=>{ const t=tAt(s), k=layer+'@'+t; let e=by.get(k); if(!e){ e={t,layer}; by.set(k,e); } return e; };
 const machs=lightLayers(proj), idx=new Map(); machs.forEach((m,i)=>idx.set(m.id,i));
 // the layer's own settings, on the first stamp: the compositor reads them straight off the cue
 machs.forEach((m,i)=>{ const e=at(i,0);
  e.gain=r4(clamp((m.params&&m.params.level!=null?m.params.level:1)*(m.gain!=null?m.gain:1),0,1));
  e.sync=m.sync||'grid';
  if(m.family)e.family=m.family; });
 for(const x of Studio.flatten(proj,'song')){
  const li=idx.get(x.mid); if(li==null)continue;
  const k=Studio.LIGHT_KEYS[x.n]; if(!k)continue;
  const e=at(li,x.s);
  if(k.kind==='look')e.look=k.val; else if(k.kind==='palette')e.palette=k.val; else if(k.kind==='hit')e.hit=true;
 }
 // the level lane is the hall master and belongs to layer 0, whichever machine wrote it
 for(const l of Studio.flattenLevel(proj,'song'))at(0,l.s).level=r4(clamp(l.v,0,1));
 return Array.from(by.values()).sort((a,b)=>a.t-b.t||a.layer-b.layer);
}

// the beat grid, off the timeline so odd meters and per-section tempo are honoured: a downbeat is
// the first beat of a bar, whatever that bar's meter says.
function beatGrid(proj,bpm,dur){
 const beats=[], downbeats=[], T=Studio.timeline?Studio.timeline(proj):null;
 if(T&&T.bars&&T.bars.length){
  for(const B of T.bars){ const div=(B.meter&&B.meter.div)||4, n=(B.meter&&B.meter.beats)||4, spBeat=16/div;
   for(let k=0;k<n;k++){ const t=r4(T.time(B.step+k*spBeat)); if(t>dur)break; beats.push(t); if(k===0)downbeats.push(t); } }
  const last=beats.length?beats[beats.length-1]:0, step=60/bpm;
  for(let t=last+step;t<dur;t+=step)beats.push(r4(t));   // the tail past the last bar, so the hall keeps a beat
 } else { const beatSec=60/bpm;
  for(let b=0;b*beatSec<dur;b++){ beats.push(r4(b*beatSec)); if(b%4===0)downbeats.push(r4(b*beatSec)); } }
 return {beats,downbeats};
}

// sections, one per four bars, named after what is playing: no drums reads as a break, drums with
// bass and pad under them read as a drop, anything else is on its way up
function sections(proj,bpm){
 const T=Studio.timeline?Studio.timeline(proj):null, S=Studio.STEPS_PER_BAR, barSec=Studio.barSeconds(bpm);
 const stepOf=b=>T?T.barStep(b):b*S, timeOf=b=>r4(T?T.time(stepOf(b)):b*barSec);
 const notes=Studio.flatten(proj,'song'), bars=Studio.songLengthBars(proj), out=[];
 for(let b=0;b<bars;b+=4){
  const e=Math.min(bars,b+4), s0=stepOf(b), s1=stepOf(e);
  const types={};
  for(const x of notes){ if(x.s<s0)continue; if(x.s>=s1)break; types[x.type]=true; }
  const drums=!!types.beatbox, bass=!!types.bassline, pad=!!types.padsynth;
  const label=!drums?'break':(drums&&bass&&pad?'drop':'build');
  const kinds=['beatbox','bassline','padsynth','subsynth','fmsynth'].filter(k=>types[k]).length;
  out.push({t0:timeOf(b), t1:timeOf(e), label, energy:r4(kinds/5)});
 }
 return out;
}

// ---- the two files, made in memory and handed back. The jam page runs on the public site where
// there is no dev server to POST to, so the render, the analysis and the cue file are separated
// from the writing: this makes them, exportShow below writes them into the repo.
Studio.exportFiles=async function(proj,eng,name,progress){
 const say=(text,p)=>{ if(progress)try{ progress(text,p); }catch(e){} };
 name=safeName(name||(proj&&proj.name));
 if(!eng||!eng.render)throw new Error('export needs an engine with render()');

 say('Rendering the music',0.05);
 await new Promise(r=>setTimeout(r,20));
 const buf=await eng.render(proj);

 say('Encoding the WAV',0.45);
 await new Promise(r=>setTimeout(r,20));
 const wav=wav16(buf);

 say('Measuring the frames',0.6);
 await new Promise(r=>setTimeout(r,20));
 const fr=analyseBuffer(buf);

 const bpm=proj.bpm||124, dur=buf.duration;
 const grid=beatGrid(proj,bpm,dur);
 const cues={
  file:name+'.wav', duration:r4(dur), sr:44100, hop_s:r4(fr.hop_s), bpm, cueVersion:2,
  beats:grid.beats, downbeats:grid.downbeats, sections:sections(proj,bpm),
  frames:{rms:arr4(fr.rms),bass:arr4(fr.bass),mid:arr4(fr.mid),high:arr4(fr.high),onset:arr4(fr.onset)},
  cues:cueList(proj),
  project:Studio.clone(proj),
 };
 const cuesJson=JSON.stringify(cues);
 say('Files ready',0.95);
 return { wavBlob:new Blob([wav],{type:'audio/wav'}), cuesJson, wav, cues, name, frames:fr.nf };
};

// ---- the whole job: render, encode, measure, write into show/ through the dev server
Studio.exportShow=async function(proj,eng,name,progress){
 const say=(text,p)=>{ if(progress)try{ progress(text,p); }catch(e){} };
 const made=await Studio.exportFiles(proj,eng,name,progress);
 const wav=made.wav, cues=made.cues; name=made.name;

 say('Writing the files',0.8);
 await post('show/'+name+'.wav',made.wavBlob,'audio/wav');
 await post('show/'+name+'.cues.json',made.cuesJson,'application/json');
 const list=await Studio.listShows();
 if(list.indexOf(name)<0){ list.push(name); await post('show/shows.json',JSON.stringify(list),'application/json'); }
 await post('show/'+name+'.project.json',JSON.stringify(proj,null,1),'application/json');

 say('Done',1);
 return {wav, cues, url:'index.html?show='+encodeURIComponent(name), name, frames:made.frames};
};

// exposed so the test page can measure the pieces on their own
Studio.wav16=wav16; Studio.analyseBuffer=analyseBuffer; Studio.fft=fft; Studio.cueList=cueList;
Studio.lightLayers=lightLayers; Studio.beatGrid=beatGrid;
})();
