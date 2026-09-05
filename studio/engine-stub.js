// THE STUB ENGINE (Lloyd, 2026-09-05): no audio at all, just a clock. It exists so the UI can be
// built and screenshotted while machines.js and engine.js are still being written, and so a broken
// audio graph never takes the whole studio down. Loaded only by studio.html when the URL carries
// ?stub, and it never overwrites a real engine.
//
// It advances pos() from performance.now() at the project's bpm, honours pattern and song lengths,
// and fires onNote as the playhead crosses each flattened note, so the playhead, the key flashes
// and the lights runtime all behave as they will with the real engine.
(function(){
'use strict';
const Studio=window.Studio=window.Studio||{};

Studio.createEngineStub=function(opts){
 const getProj=opts.project, onNote=opts.onNote||function(){};
 let playing=false, mode='pattern', startWall=0, startStep=0, curStep=0, flat=null, flatMode=null, lastStep=-1;
 const fakeBands={bass:0,mid:0,high:0,rms:0,onset:0};

 const proj=()=>getProj();
 const stepSec=()=>Studio.stepSeconds(proj().bpm||120);
 const loopSteps=()=>mode==='pattern'?Studio.patternLoopSteps(proj()):Studio.songLengthBars(proj())*Studio.STEPS_PER_BAR;
 function notes(){ if(!flat||flatMode!==mode){ flat=Studio.flatten(proj(),mode); flatMode=mode; } return flat; }

 // the clock: wall time since Play, in steps, wrapped by the loop length
 function advance(){
  if(!playing)return curStep;
  const n=loopSteps();
  let s=startStep+(performance.now()/1000-startWall)/stepSec();
  if(s>=n){ if(eng.loop||mode==='pattern')s=s%n; else { s=n; playing=false; } }
  // notes crossed since the last read fire once each, the same contract the real engine has
  const list=notes();
  if(s<lastStep)lastStep=-1;
  for(const q of list)if(q.s>lastStep&&q.s<=s)onNote(q.mid,q.n,q.v,performance.now()/1000,true);
  lastStep=s; curStep=s; return s;
 }

 const eng={
  ac:null, playing:false, mode:'pattern', loop:true, master:null, analyser:{read(out){ for(const k in fakeBands)out[k]=fakeBands[k]; return out; }},
  stub:true,
  init(){ return true; },
  rebuild(){},
  invalidate(){ flat=null; },
  play(o){ o=o||{}; mode=eng.mode=o.mode||mode; if(o.fromStep!=null)curStep=o.fromStep;
   startStep=curStep; startWall=performance.now()/1000; lastStep=curStep-0.0001; playing=eng.playing=true; },
  pause(){ advance(); playing=eng.playing=false; },
  stop(){ playing=eng.playing=false; curStep=0; lastStep=-1; },
  seek(s){ curStep=Math.max(0,s); lastStep=curStep-0.0001; startStep=curStep; startWall=performance.now()/1000; },
  pos(){ const s=advance(); eng.playing=playing; const n=loopSteps();
   return {step:s, t:s*stepSec(), bar:Math.floor(s/16), beat:Math.floor(s/4)%4, stepInBar:Math.floor(s)%16, loopSteps:n}; },
  noteOn(mid,n,v){ onNote(mid,n,v,performance.now()/1000,true); },
  noteOff(){}, setParam(){}, setMixer(){}, setFx(){},
  render(){ return Promise.reject(new Error('the stub engine renders no audio')); },
 };
 return eng;
};

// a lights runtime that only remembers state, for the same reason
Studio.createLightsStub=function(){
 const L={ show:null, state:{look:'pulse',palette:'helix',level:1,hitAt:-9}, stub:true,
  resolve(){}, invalidate(){}, tick(){}, setRecord(){},
  press(kind,val){ if(kind==='hit')L.state.hitAt=performance.now()/1000; else L.state[kind]=val; return null; } };
 return L;
};
})();
