// THE ENGINE (Lloyd, 2026-09-05): one graph, one scheduler, used both live and for the bounce. The
// live rig hangs off a persistent master so the analyser never has to be rewired; the offline
// render builds the same rig on an OfflineAudioContext and walks the same notes, so an export
// sounds like what was played.
//
// Signal path per machine:
//   machine voices -> insert fx 1 -> insert fx 2 -> channel gain (vol, mute, solo) -> panner ->
//   master, plus post-fader sends into the master delay and the master reverb.
// Master: sum -> master gain -> limiter -> destination.
(function(){
'use strict';
const Studio=window.Studio=window.Studio||{};
const A=Studio.AU;
const LOOKAHEAD=0.12, TICK=25, TAIL=2;

// ---- effects ---------------------------------------------------------------------------------
// every builder returns {input, output, dispose} and is fed the model {type, params, on}
function impulse(ac,size,damp){
 const sr=ac.sampleRate, n=Math.max(1,Math.floor(sr*Math.max(0.05,size))), b=ac.createBuffer(2,n,sr);
 const k=1-Math.pow(A.clamp(damp,0,1),0.35)*0.98;    // a one pole low pass baked into the tail
 for(let c=0;c<2;c++){ const d=b.getChannelData(c); let z=0;
  for(let i=0;i<n;i++){ const white=Math.random()*2-1; z+=k*(white-z);
   d[i]=z*Math.pow(1-i/n,2.4); } }
 return b;
}
function quantCurve(bits){ const levels=Math.max(2,Math.pow(2,Math.round(A.clamp(bits,2,16)))), n=4096, c=new Float32Array(n);
 for(let i=0;i<n;i++){ const x=i*2/(n-1)-1; c[i]=Math.round(x*levels)/levels; } return c; }

const FX={
 delay(ac,p){ const input=ac.createGain(), output=ac.createGain();
  const d=ac.createDelay(1.5); d.delayTime.value=A.clamp(p.time,0.01,1.5);
  const fb=ac.createGain(); fb.gain.value=A.clamp(p.feedback,0,0.95);
  const tone=ac.createBiquadFilter(); tone.type='lowpass'; tone.frequency.value=A.cutHz(p.tone);
  const wet=ac.createGain(), dry=ac.createGain();
  wet.gain.value=A.clamp(p.mix,0,1); dry.gain.value=1-A.clamp(p.mix,0,1);
  input.connect(dry); dry.connect(output);
  input.connect(d); d.connect(tone); tone.connect(fb); fb.connect(d); tone.connect(wet); wet.connect(output);
  return {input,output};
 },
 reverb(ac,p){ const input=ac.createGain(), output=ac.createGain();
  const cv=ac.createConvolver(); cv.normalize=true; cv.buffer=impulse(ac,p.size,p.damp);
  const wet=ac.createGain(), dry=ac.createGain();
  wet.gain.value=A.clamp(p.mix,0,1)*1.4; dry.gain.value=1-A.clamp(p.mix,0,1);
  input.connect(dry); dry.connect(output); input.connect(cv); cv.connect(wet); wet.connect(output);
  return {input,output};
 },
 chorus(ac,p){ const input=ac.createGain(), output=ac.createGain();
  const d=ac.createDelay(0.1); d.delayTime.value=0.02;
  const lfo=ac.createOscillator(), lg=ac.createGain();
  lfo.frequency.value=A.clamp(p.rate,0.01,20); lg.gain.value=A.clamp(p.depth,0,1)*0.006;
  lfo.connect(lg); lg.connect(d.delayTime); try{ lfo.start(0); }catch(e){}
  const wet=ac.createGain(), dry=ac.createGain();
  wet.gain.value=A.clamp(p.mix,0,1); dry.gain.value=1-A.clamp(p.mix,0,1);
  input.connect(dry); dry.connect(output); input.connect(d); d.connect(wet); wet.connect(output);
  return {input,output,dispose(){ try{ lfo.stop(); }catch(e){} }};
 },
 distortion(ac,p){ const input=ac.createGain(), output=ac.createGain();
  const sh=ac.createWaveShaper(); sh.curve=A.shaperCurve(p.drive); sh.oversample='2x';
  const tone=ac.createBiquadFilter(); tone.type='lowpass'; tone.frequency.value=A.cutHz(p.tone);
  const wet=ac.createGain(), dry=ac.createGain();
  wet.gain.value=A.clamp(p.mix,0,1)*(1-0.4*A.clamp(p.drive,0,1)); dry.gain.value=1-A.clamp(p.mix,0,1);
  input.connect(dry); dry.connect(output); input.connect(sh); sh.connect(tone); tone.connect(wet); wet.connect(output);
  return {input,output};
 },
 filter(ac,p){ const input=ac.createGain(), output=ac.createGain();
  const f=ac.createBiquadFilter(); f.type=(p.type>=0.5)?'highpass':'lowpass';
  f.frequency.value=A.cutHz(p.cutoff); f.Q.value=A.qOf(p.res);
  input.connect(f); f.connect(output); return {input,output};
 },
 compressor(ac,p){ const input=ac.createGain(), output=ac.createGain();
  const c=ac.createDynamicsCompressor();
  c.threshold.value=A.clamp(p.threshold,-60,0); c.ratio.value=A.clamp(p.ratio,1,20);
  c.attack.value=A.clamp(p.attack,0.001,1); c.release.value=A.clamp(p.release,0.01,1); c.knee.value=6;
  const mk=ac.createGain(); mk.gain.value=Math.pow(10,A.clamp(p.makeup,0,1)*12/20);
  input.connect(c); c.connect(mk); mk.connect(output); return {input,output};
 },
 bitcrush(ac,p){ const input=ac.createGain(), output=ac.createGain();
  // no ScriptProcessor: a waveshaper quantises the amplitude and a low pass stands in for the
  // sample rate, which gets the grit without a worklet
  const lp=ac.createBiquadFilter(); lp.type='lowpass'; lp.frequency.value=300*Math.pow(20000/300,A.clamp(p.rate,0,1));
  const sh=ac.createWaveShaper(); sh.curve=quantCurve(p.bits);
  const wet=ac.createGain(), dry=ac.createGain();
  wet.gain.value=A.clamp(p.mix,0,1); dry.gain.value=1-A.clamp(p.mix,0,1);
  input.connect(dry); dry.connect(output); input.connect(lp); lp.connect(sh); sh.connect(wet); wet.connect(output);
  return {input,output};
 },
};
function makeFx(ac,model){ if(!model||!model.on||!FX[model.type])return null;
 const T=Studio.FX_TYPES[model.type]; const p={};
 for(const k in T.params)p[k]=(model.params&&model.params[k]!=null)?model.params[k]:T.params[k].def;
 return FX[model.type](ac,p); }

// an insert slot that can be swapped without relinking the channel around it
function slot(ac){ const inp=ac.createGain(), out=ac.createGain(); let cur=null;
 const S={ input:inp, output:out,
  set(model){ try{ inp.disconnect(); }catch(e){}
   if(cur&&cur.dispose)cur.dispose();
   if(cur){ try{ cur.output.disconnect(); }catch(e){} }
   cur=makeFx(ac,model);
   if(cur){ inp.connect(cur.input); cur.output.connect(out); } else inp.connect(out); },
  dispose(){ if(cur&&cur.dispose)cur.dispose(); cur=null; } };
 S.set(null); return S; }

// ---- the rig: every machine's channel plus the two master sends, hung off a master node --------
function buildRig(ac,proj,master){
 const mfx={};
 for(const key of ['delay','reverb']){
  const inp=ac.createGain(); inp.gain.value=1;
  // a send return is fully wet whatever the model's mix knob says, otherwise turning a send up
  // would just make the channel louder. A send whose effect is off goes nowhere.
  const mm=proj.master&&proj.master[key];
  // (integration) the return is a slot, so the mixer's master knobs re-set it live; an effect
  // that is off shuts the send's input instead of passing dry
  const s=slot(ac); s.output.connect(master);
  const setMaster=(m)=>{ const on=!!(m&&m.on); inp.gain.value=on?1:0; s.set(on?{type:m.type,on:true,params:Object.assign({},m.params,{mix:1})}:null); };
  setMaster(mm); inp.connect(s.input);
  mfx[key]={input:inp,slot:s,setMaster};
 }
 const chans={}, insts={};
 const anySolo=proj.machines.some(m=>m.solo);
 for(const m of proj.machines){
  const inp=ac.createGain(); inp.gain.value=1;
  const s1=slot(ac), s2=slot(ac);
  const gain=ac.createGain(), pan=ac.createStereoPanner();
  const sd=ac.createGain(), sr=ac.createGain();
  inp.connect(s1.input); s1.output.connect(s2.input); s2.output.connect(gain);
  gain.connect(pan); pan.connect(master);
  pan.connect(sd); sd.connect(mfx.delay.input);
  pan.connect(sr); sr.connect(mfx.reverb.input);
  s1.set(m.fx&&m.fx[0]); s2.set(m.fx&&m.fx[1]);
  const live=!(m.mute||(anySolo&&!m.solo));
  gain.gain.value=live?A.clamp(m.vol,0,1):0;
  pan.pan.value=A.clamp(m.pan,-1,1);
  sd.gain.value=live?A.clamp(m.send&&m.send.delay||0,0,1):0;
  sr.gain.value=live?A.clamp(m.send&&m.send.reverb||0,0,1):0;
  const MK=Studio.MACHINES[m.type];
  const inst=MK?MK.create(ac,m,inp):{noteOn(){},noteOff(){},setParam(){},allOff(){},dispose(){}};
  chans[m.id]={input:inp,s1,s2,gain,pan,sd,sr,machine:m};
  insts[m.id]=inst;
 }
 return { chans, insts, mfx,
  dispose(){ for(const id in insts){ try{ insts[id].dispose(); }catch(e){} }
   for(const id in chans){ const c=chans[id]; c.s1.dispose(); c.s2.dispose();
    for(const n of [c.input,c.gain,c.pan,c.sd,c.sr]){ try{ n.disconnect(); }catch(e){} } }
   for(const k in mfx){ if(mfx[k].slot)mfx[k].slot.set(null);
    try{ mfx[k].input.disconnect(); }catch(e){} if(mfx[k].fx){ try{ mfx[k].fx.output.disconnect(); }catch(e){} } } } };
}

// notes of a mode, bucketed by step so the scheduler is a lookup rather than a scan
function bucket(proj,mode){ const flat=Studio.flatten(proj,mode), by=new Map();
 for(const x of flat){ let a=by.get(x.s); if(!a)by.set(x.s,a=[]); a.push(x); } return by; }

// =============================================================================================
Studio.createEngine=function(opts){
 opts=opts||{};
 const getProj=opts.project||(()=>null);
 const onNote=opts.onNote||function(){};

 const eng={ ac:null, playing:false, mode:'pattern', loop:false, master:null, analyser:null };
 let rig=null, timer=null;
 let startStep=0, startAc=0, pausedStep=0, nextStep=0, stepDur=0.12;
 let cache=null, cacheMode=null, cacheLen=0;

 function proj(){ return getProj(); }
 function bpm(){ const p=proj(); return (p&&p.bpm)||120; }
 function notes(){ const p=proj();
  if(!cache||cacheMode!==eng.mode){ cache=bucket(p,eng.mode); cacheMode=eng.mode;
   cacheLen=eng.mode==='pattern'?Studio.patternLoopSteps(p):Studio.songLengthBars(p)*Studio.STEPS_PER_BAR; }
  return cache; }
 function loopSteps(){ notes(); return Math.max(1,cacheLen); }
 function isSynth(type){ const T=Studio.MACHINE_TYPES[type]; return T&&T.kind==='synth'; }

 eng.init=function(){
  if(eng.ac)return eng.ac;
  const AC=window.AudioContext||window.webkitAudioContext;
  const ac=eng.ac=new AC();
  const master=eng.master=ac.createGain();
  const p=proj(); master.gain.value=(p&&p.master&&p.master.vol!=null)?p.master.vol:0.9;
  const lim=ac.createDynamicsCompressor();
  lim.threshold.value=-3; lim.knee.value=0; lim.ratio.value=12; lim.attack.value=0.003; lim.release.value=0.1;
  master.connect(lim); lim.connect(ac.destination);
  eng.limiter=lim;
  if(window.NGVShow&&NGVShow.createAnalyser)eng.analyser=NGVShow.createAnalyser(ac,master);
  eng.rebuild();
  return ac;
 };

 eng.rebuild=function(){
  if(!eng.ac)return;
  if(rig)rig.dispose();
  const p=proj();
  if(p&&p.master&&p.master.vol!=null)eng.master.gain.value=p.master.vol;
  rig=buildRig(eng.ac,p,eng.master);
  eng.invalidate();
 };
 eng.invalidate=function(){ cache=null; cacheMode=null; };

 // ---- transport ------------------------------------------------------------------------------
 function stepAt(t){ return startStep+(t-startAc)/stepDur; }
 function idxOf(step){ const L=loopSteps(); const i=Math.floor(step)%L; return i<0?i+L:i; }

 eng.pos=function(){
  const L=loopSteps();
  const step=eng.playing&&eng.ac?Math.max(0,stepAt(eng.ac.currentTime)):pausedStep;
  const idx=eng.mode==='song'&&!eng.loop?Math.min(step,L):(((step%L)+L)%L);
  return { step, t:step*stepDur, bar:Math.floor(idx/Studio.STEPS_PER_BAR),
   beat:Math.floor((idx%Studio.STEPS_PER_BAR)/4), stepInBar:Math.floor(idx)%Studio.STEPS_PER_BAR, loopSteps:L };
 };

 function scheduleStep(step,t){
  const by=notes(); const L=loopSteps();
  const idx=((Math.floor(step)%L)+L)%L;
  const list=by.get(idx); if(!list)return;
  const p=proj(), sw=A.clamp((p&&p.swing)||0,0,1);
  const when=(idx%2===1)?t+sw*0.5*stepDur:t;
  for(const x of list){
   const inst=rig&&rig.insts[x.mid];
   if(inst){ inst.noteOn(when,x.n,x.v);
    if(isSynth(x.type))inst.noteOff(when+Math.max(0.03,x.l*stepDur*0.98),x.n); }
   try{ onNote(x.mid,x.n,x.v,when,true); }catch(e){}
  }
 }

 function tick(){
  if(!eng.playing||!eng.ac)return;
  const p=proj(), sd=Studio.stepSeconds(bpm());
  if(Math.abs(sd-stepDur)>1e-9){ const cur=stepAt(eng.ac.currentTime); startStep=cur; startAc=eng.ac.currentTime; stepDur=sd; }
  const now=eng.ac.currentTime, until=now+LOOKAHEAD;
  const L=loopSteps(), endless=eng.mode==='pattern'||eng.loop;
  while(true){
   const t=startAc+(nextStep-startStep)*stepDur;
   if(t>until)break;
   if(!endless&&nextStep>=L)break;
   scheduleStep(nextStep,t); nextStep++;
   if(nextStep-startStep>4096)break;                 // a guard against a runaway loop
  }
  if(!endless&&stepAt(now)>=L)eng.stop();            // the song ran out, so park back at the top
 }

 eng.play=function(o){
  o=o||{};
  eng.init();
  if(eng.ac.state!=='running')eng.ac.resume().catch(()=>{});
  if(o.mode&&o.mode!==eng.mode){ eng.mode=o.mode; eng.invalidate(); }
  stepDur=Studio.stepSeconds(bpm());
  startStep=(o.fromStep!=null)?o.fromStep:pausedStep;
  startAc=eng.ac.currentTime+0.02;
  nextStep=Math.ceil(startStep-1e-6);
  eng.playing=true;
  if(timer)clearInterval(timer);
  timer=setInterval(tick,TICK);
  tick();
 };
 eng.pause=function(){
  if(!eng.playing)return;
  pausedStep=Math.max(0,stepAt(eng.ac.currentTime));
  eng.playing=false;
  if(timer){ clearInterval(timer); timer=null; }
  allOff();
 };
 eng.stop=function(){
  if(timer){ clearInterval(timer); timer=null; }
  eng.playing=false; pausedStep=0; nextStep=0;
  allOff();
 };
 eng.seek=function(step){
  pausedStep=Math.max(0,step||0);
  if(eng.playing&&eng.ac){ allOff(); startStep=pausedStep; startAc=eng.ac.currentTime+0.02; nextStep=Math.ceil(startStep-1e-6); }
 };
 function allOff(){ if(!rig||!eng.ac)return; const t=eng.ac.currentTime;
  for(const id in rig.insts){ try{ rig.insts[id].allOff(t); }catch(e){} } }

 // ---- live play and mixer --------------------------------------------------------------------
 eng.noteOn=function(mid,n,v){ eng.init(); if(eng.ac.state!=='running')eng.ac.resume().catch(()=>{});
  const inst=rig&&rig.insts[mid]; const t=eng.ac.currentTime;
  if(inst)inst.noteOn(t,n,v==null?0.9:v);
  try{ onNote(mid,n,v==null?0.9:v,t,true); }catch(e){} };
 eng.noteOff=function(mid,n){ const inst=rig&&rig.insts[mid]; if(inst&&eng.ac)inst.noteOff(eng.ac.currentTime,n); };
 eng.allOff=function(){ allOff(); };

 eng.setParam=function(mid,key,value){ const inst=rig&&rig.insts[mid]; if(inst)inst.setParam(key,value); };
 eng.setMixer=function(mid){
  if(!rig)return; const p=proj(); const anySolo=p.machines.some(m=>m.solo);
  for(const m of p.machines){ const c=rig.chans[m.id]; if(!c)continue;
   const live=!(m.mute||(anySolo&&!m.solo));
   c.gain.gain.value=live?A.clamp(m.vol,0,1):0;
   c.pan.pan.value=A.clamp(m.pan,-1,1);
   c.sd.gain.value=live?A.clamp(m.send&&m.send.delay||0,0,1):0;
   c.sr.gain.value=live?A.clamp(m.send&&m.send.reverb||0,0,1):0; }
  if(p.master&&p.master.vol!=null&&eng.master)eng.master.gain.value=p.master.vol;
 };
 eng.setFx=function(mid,slotIndex){
  if(!rig)return;
  if(mid==null){ const p=proj(); const mf=rig.mfx[slotIndex]; if(mf&&p.master)mf.setMaster(p.master[slotIndex]); return; }   // the master buses: slotIndex is 'delay' or 'reverb'
  const c=rig.chans[mid]; if(!c)return;
  const m=c.machine; (slotIndex===1?c.s2:c.s1).set(m.fx&&m.fx[slotIndex]);
 };
 eng.setMasterFx=function(){ eng.rebuild(); };   // the master sends live inside the rig

 // ---- offline render --------------------------------------------------------------------------
 eng.render=function(project){
  const p=project||proj();
  const sd=Studio.stepSeconds(p.bpm||120);
  const steps=Studio.songLengthBars(p)*Studio.STEPS_PER_BAR;
  const dur=steps*sd;
  const oac=new OfflineAudioContext(2,Math.ceil((dur+TAIL)*44100),44100);
  const master=oac.createGain(); master.gain.value=(p.master&&p.master.vol!=null)?p.master.vol:0.9;
  const lim=oac.createDynamicsCompressor();
  lim.threshold.value=-3; lim.knee.value=0; lim.ratio.value=12; lim.attack.value=0.003; lim.release.value=0.1;
  master.connect(lim); lim.connect(oac.destination);
  const r=buildRig(oac,p,master);
  const flat=Studio.flatten(p,'song'), sw=A.clamp(p.swing||0,0,1);
  for(const x of flat){
   const inst=r.insts[x.mid]; if(!inst)continue;
   const base=x.s*sd, t=(x.s%2===1)?base+sw*0.5*sd:base;
   inst.noteOn(t,x.n,x.v);
   if(isSynth(x.type))inst.noteOff(t+Math.max(0.03,x.l*sd*0.98),x.n);
  }
  return oac.startRendering().then(buf=>{ r.dispose(); return buf; });
 };

 return eng;
};
})();
