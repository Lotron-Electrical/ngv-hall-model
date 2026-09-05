// THE MACHINES (Lloyd, 2026-09-05): one voice bank per machine type, all synthesised, no samples,
// because the whole song has to render offline as well as play live. Every machine is built on
// whatever AudioContext it is handed, so a bounce sounds like what was played.
//
// Studio.MACHINES[type].create(ac, machine, dest) -> inst
//   inst.noteOn(time, n, v)   n = midi note (synths) or pad index 0..7 (BeatBox)
//   inst.noteOff(time, n)     a no-op for drums
//   inst.setParam(key, value) live knob; params are read from machine.params at note time anyway
//   inst.allOff(time)         release every voice (Stop)
//   inst.dispose()
(function(){
'use strict';
const Studio=window.Studio=window.Studio||{};

// ---- shared audio helpers, also used by engine.js -------------------------------------------
const A=Studio.AU=Studio.AU||{};
A.clamp=(x,a,b)=>x<a?a:x>b?b:x;
A.mtof=(m)=>440*Math.pow(2,(m-69)/12);
A.cutHz=(x)=>80*Math.pow(12000/80,A.clamp(x,0,1));      // a 0..1 knob across the useful range
A.qOf=(r)=>0.7+A.clamp(r,0,1)*18;
A.WAVES=['sine','triangle','sawtooth','square'];
A.wave=(i)=>A.WAVES[A.clamp(Math.round(i||0),0,3)];

// one two second noise buffer per context, shared by every noise source
const noiseCache=new WeakMap();
A.noiseBuffer=(ac)=>{ let b=noiseCache.get(ac); if(b)return b;
 const n=Math.floor(ac.sampleRate*2); b=ac.createBuffer(1,n,ac.sampleRate); const d=b.getChannelData(0);
 for(let i=0;i<n;i++)d[i]=Math.random()*2-1; noiseCache.set(ac,b); return b; };
A.noise=(ac,when,dur)=>{ const s=ac.createBufferSource(); s.buffer=A.noiseBuffer(ac); s.loop=true;
 s.start(Math.max(0,when),Math.random()*1.5); s.stop(Math.max(0,when)+dur); return s; };

// a soft clipper curve; k = 0..1 drive
A.shaperCurve=(k,len)=>{ const n=len||1024, c=new Float32Array(n), d=1+A.clamp(k,0,1)*40;
 for(let i=0;i<n;i++){ const x=i*2/(n-1)-1; c[i]=Math.tanh(x*d)/Math.tanh(d); } return c; };

// a gain node carrying an ADSR. release(t) starts the tail and returns when the tail ends, so the
// caller knows when it is safe to stop the oscillators.
A.adsr=(ac,when,p,peak)=>{
 const g=ac.createGain(), t=Math.max(0,when), a=Math.max(0.001,p.attack), d=Math.max(0.005,p.decay);
 const s=A.clamp(p.sustain,0,1)*peak, r=Math.max(0.01,p.release);
 g.gain.setValueAtTime(0.0001,t);
 g.gain.linearRampToValueAtTime(Math.max(0.0002,peak),t+a);
 g.gain.exponentialRampToValueAtTime(Math.max(0.0002,s||0.0002),t+a+d);
 if(!s)g.gain.setValueAtTime(0.0001,t+a+d);
 return { node:g, release(rt){ const x=Math.max(t+0.002,rt);
   // hold whatever the envelope had reached; .value is useless in an OfflineAudioContext, so fall
   // back to the sustain level rather than reading it
   A.hold(g.gain,x,Math.max(0.0002,s||peak*0.5||0.0002));
   g.gain.exponentialRampToValueAtTime(0.0001,x+r); g.gain.setValueAtTime(0,x+r+0.005); return x+r+0.02; } };
};
// stop an automation dead at time t, keeping the value it had reached where the browser can
A.hold=(param,t,fallback)=>{ if(param.cancelAndHoldAtTime){ try{ param.cancelAndHoldAtTime(t); return; }catch(e){} }
 param.cancelScheduledValues(t); param.setValueAtTime(fallback,t); };
// a percussive envelope: up in atk, down to nothing by when+dec
A.hit=(ac,when,peak,dec,atk)=>{ const g=ac.createGain(), t=Math.max(0,when), a=atk===undefined?0.002:atk;
 g.gain.setValueAtTime(0.0001,t); g.gain.linearRampToValueAtTime(Math.max(0.0002,peak),t+a);
 g.gain.exponentialRampToValueAtTime(0.0001,t+Math.max(a+0.01,dec)); return g; };

// read a parameter, falling back to the type's default so a half built machine still plays
function pget(machine,key){ const v=machine.params?machine.params[key]:undefined;
 if(v!=null&&isFinite(v))return v;
 const T=Studio.MACHINE_TYPES[machine.type], d=T&&T.params[key]; return d?d.def:0; }

Studio.MACHINES={};

// =============================================================================================
// SubSynth: two oscillators, a resonant low pass with its own decay envelope, an ADSR, an LFO on
// the filter and optional glide. Polyphonic.
// =============================================================================================
Studio.MACHINES.subsynth={ create(ac,machine,dest){
 const out=ac.createGain(); out.gain.value=pget(machine,'vol'); out.connect(dest);
 const lfo=ac.createOscillator(), lfoG=ac.createGain();
 lfo.type='sine'; lfo.frequency.value=pget(machine,'lfoRate'); lfoG.gain.value=pget(machine,'lfoAmt')*4000;
 lfo.connect(lfoG); try{ lfo.start(0); }catch(e){}
 let voices=[], lastHz=0;
 function kill(v,stopAt){ v.dead=true; for(const o of v.oscs){ try{ o.stop(Math.max(0,stopAt)); }catch(e){} }
  setTimeout(()=>{ try{ lfoG.disconnect(v.filter.frequency); }catch(e){} },0); }
 return {
  noteOn(time,n,v){
   if(voices.length>15){ const old=voices.shift(); kill(old,(old.env.release(time)));  }
   const hz=A.mtof(n), vel=A.clamp(v==null?0.8:v,0,1);
   const f=ac.createBiquadFilter(); f.type='lowpass';
   const base=A.cutHz(pget(machine,'cutoff')), fenv=pget(machine,'fenv'), fd=pget(machine,'fdecay');
   f.Q.value=A.qOf(pget(machine,'res'));
   const top=Math.min(16000,base+(16000-base)*fenv);
   f.frequency.setValueAtTime(Math.max(60,top),Math.max(0,time));
   f.frequency.exponentialRampToValueAtTime(Math.max(60,base),Math.max(0,time)+Math.max(0.02,fd));
   lfoG.connect(f.frequency);
   const env=A.adsr(ac,time,{attack:pget(machine,'attack'),decay:pget(machine,'decay'),sustain:pget(machine,'sustain'),release:pget(machine,'release')},vel*0.35);
   f.connect(env.node); env.node.connect(out);
   const mix=A.clamp(pget(machine,'mix'),0,1), glide=pget(machine,'glide');
   const oscs=[];
   [[A.wave(pget(machine,'osc1')),1-mix,0,0],[A.wave(pget(machine,'osc2')),mix,pget(machine,'detune'),pget(machine,'oct2')]].forEach(([type,amt,det,oct])=>{
    if(amt<=0.001)return;
    const o=ac.createOscillator(); o.type=type; o.detune.value=det;
    const target=hz*Math.pow(2,Math.round(oct));
    if(glide>0.001&&lastHz>0){ o.frequency.setValueAtTime(lastHz*Math.pow(2,Math.round(oct)),Math.max(0,time));
     o.frequency.exponentialRampToValueAtTime(target,Math.max(0,time)+glide); }
    else o.frequency.setValueAtTime(target,Math.max(0,time));
    const g=ac.createGain(); g.gain.value=amt; o.connect(g); g.connect(f);
    try{ o.start(Math.max(0,time)); }catch(e){}
    oscs.push(o);
   });
   lastHz=hz;
   voices.push({n,oscs,filter:f,env,dead:false});
  },
  noteOff(time,n){
   for(let i=voices.length-1;i>=0;i--){ const v=voices[i]; if(v.n!==n||v.dead)continue;
    kill(v,v.env.release(time)); voices.splice(i,1); return; }
  },
  setParam(key,value){ machine.params[key]=value;
   if(key==='vol')out.gain.value=value;
   if(key==='lfoRate')lfo.frequency.value=value;
   if(key==='lfoAmt')lfoG.gain.value=value*4000;
  },
  allOff(time){ for(const v of voices)kill(v,v.env.release(time)); voices=[]; },
  dispose(){ try{ lfo.stop(); }catch(e){} try{ out.disconnect(); }catch(e){} voices=[]; }
 };
}};

// =============================================================================================
// BassLine: one 303 style mono voice kept alive for the machine's life, so overlapping notes
// glide instead of retriggering. Accent on velocity >= 0.9 opens the filter and lifts the level.
// =============================================================================================
Studio.MACHINES.bassline={ create(ac,machine,dest){
 const out=ac.createGain(); out.gain.value=pget(machine,'vol');
 const shaper=ac.createWaveShaper(); shaper.curve=A.shaperCurve(pget(machine,'dist'));
 const post=ac.createGain(); post.gain.value=1;
 shaper.connect(post); post.connect(out); out.connect(dest);
 const f=ac.createBiquadFilter(); f.type='lowpass'; f.Q.value=A.qOf(pget(machine,'res'));
 f.frequency.value=A.cutHz(pget(machine,'cutoff'));
 const amp=ac.createGain(); amp.gain.value=0;
 f.connect(amp); amp.connect(shaper);
 const osc=ac.createOscillator(); osc.type=pget(machine,'wave')<0.5?'sawtooth':'square';
 osc.frequency.value=55; osc.connect(f); try{ osc.start(0); }catch(e){}
 let lastEnd=-9, lastHz=0;
 return {
  noteOn(time,n,v){
   const t=Math.max(0,time), hz=A.mtof(n), vel=A.clamp(v==null?0.8:v,0,1);
   const acc=vel>=0.9, dec=Math.max(0.05,pget(machine,'decay'));
   const slide=(time<lastEnd-1e-4&&lastHz>0)?Math.max(0.02,pget(machine,'slide')):0;
   osc.frequency.cancelScheduledValues(t);
   if(slide){ osc.frequency.setValueAtTime(lastHz,t); osc.frequency.exponentialRampToValueAtTime(hz,t+slide); }
   else osc.frequency.setValueAtTime(hz,t);
   const base=A.cutHz(pget(machine,'cutoff'));
   const mod=A.clamp(pget(machine,'envmod'),0,1)*(acc?1+pget(machine,'accent'):1);
   const top=Math.min(15000,base+(15000-base)*A.clamp(mod,0,1));
   f.frequency.cancelScheduledValues(t);
   f.frequency.setValueAtTime(Math.max(60,top),t);
   f.frequency.exponentialRampToValueAtTime(Math.max(60,base),t+dec);
   const peak=0.3*vel*(acc?1+0.6*pget(machine,'accent'):1);
   amp.gain.cancelScheduledValues(t);
   if(!slide)amp.gain.setValueAtTime(0.0001,t);
   amp.gain.linearRampToValueAtTime(peak,t+0.006);
   amp.gain.setValueAtTime(peak,t+Math.max(0.01,dec*0.6));
   amp.gain.exponentialRampToValueAtTime(0.0001,t+dec+0.05);
   lastHz=hz; lastEnd=time;
  },
  noteOff(time,n){ lastEnd=Math.max(lastEnd,time); },
  setParam(key,value){ machine.params[key]=value;
   if(key==='vol')out.gain.value=value;
   if(key==='wave')osc.type=value<0.5?'sawtooth':'square';
   if(key==='res')f.Q.value=A.qOf(value);
   if(key==='dist')shaper.curve=A.shaperCurve(value);
  },
  allOff(time){ const t=Math.max(0,time); A.hold(amp.gain,t,0.0002);
   amp.gain.exponentialRampToValueAtTime(0.0001,t+0.03); lastEnd=-9; },
  dispose(){ try{ osc.stop(); }catch(e){} try{ out.disconnect(); }catch(e){} }
 };
}};

// =============================================================================================
// PadSynth: a unison of detuned saws spread across the stereo field, a gentle filter, a long
// attack and release. Polyphonic.
// =============================================================================================
Studio.MACHINES.padsynth={ create(ac,machine,dest){
 const out=ac.createGain(); out.gain.value=pget(machine,'vol'); out.connect(dest);
 const lfo=ac.createOscillator(), lfoG=ac.createGain();
 lfo.type='sine'; lfo.frequency.value=pget(machine,'lfoRate'); lfoG.gain.value=pget(machine,'lfoAmt')*2500;
 lfo.connect(lfoG); try{ lfo.start(0); }catch(e){}
 let voices=[];
 function kill(v,stopAt){ v.dead=true; for(const o of v.oscs){ try{ o.stop(Math.max(0,stopAt)); }catch(e){} }
  setTimeout(()=>{ try{ lfoG.disconnect(v.filter.frequency); }catch(e){} },0); }
 return {
  noteOn(time,n,v){
   if(voices.length>13){ const old=voices.shift(); kill(old,old.env.release(time)); }
   const hz=A.mtof(n), vel=A.clamp(v==null?0.8:v,0,1);
   const nv=Math.max(1,Math.min(7,Math.round(pget(machine,'voices'))));
   const spread=pget(machine,'spread'), width=A.clamp(pget(machine,'width'),0,1);
   const f=ac.createBiquadFilter(); f.type='lowpass';
   f.frequency.value=A.cutHz(pget(machine,'cutoff')); f.Q.value=A.qOf(pget(machine,'res'));
   lfoG.connect(f.frequency);
   const env=A.adsr(ac,time,{attack:pget(machine,'attack'),decay:0.2,sustain:1,release:pget(machine,'release')},vel*0.3);
   f.connect(env.node); env.node.connect(out);
   const oscs=[];
   for(let i=0;i<nv;i++){
    const off=nv===1?0:(i/(nv-1))*2-1;                       // -1..1 across the unison
    const p=ac.createStereoPanner(); p.pan.value=off*width; p.connect(f);
    const o=ac.createOscillator(); o.type='sawtooth'; o.frequency.value=hz; o.detune.value=off*spread;
    const g=ac.createGain(); g.gain.value=1/nv;
    o.connect(g); g.connect(p); try{ o.start(Math.max(0,time)); }catch(e){}
    oscs.push(o);
   }
   voices.push({n,oscs,filter:f,env,dead:false});
  },
  noteOff(time,n){ for(let i=voices.length-1;i>=0;i--){ const v=voices[i]; if(v.n!==n||v.dead)continue;
   kill(v,v.env.release(time)); voices.splice(i,1); return; } },
  setParam(key,value){ machine.params[key]=value;
   if(key==='vol')out.gain.value=value;
   if(key==='lfoRate')lfo.frequency.value=value;
   if(key==='lfoAmt')lfoG.gain.value=value*2500;
  },
  allOff(time){ for(const v of voices)kill(v,v.env.release(time)); voices=[]; },
  dispose(){ try{ lfo.stop(); }catch(e){} try{ out.disconnect(); }catch(e){} voices=[]; }
 };
}};

// =============================================================================================
// FMSynth: one carrier, one modulator with its own index envelope. Feedback is approximated by a
// second modulator folded into the first (a true single operator loop is not expressible in the
// Web Audio graph without a ScriptProcessor). Polyphonic.
// =============================================================================================
Studio.MACHINES.fmsynth={ create(ac,machine,dest){
 const out=ac.createGain(); out.gain.value=pget(machine,'vol'); out.connect(dest);
 let voices=[];
 function kill(v,stopAt){ v.dead=true; for(const o of v.oscs){ try{ o.stop(Math.max(0,stopAt)); }catch(e){} } }
 return {
  noteOn(time,n,v){
   if(voices.length>15){ const old=voices.shift(); kill(old,old.env.release(time)); }
   const t=Math.max(0,time), hz=A.mtof(n), vel=A.clamp(v==null?0.8:v,0,1);
   const ratio=pget(machine,'ratio'), index=pget(machine,'index'), idec=Math.max(0.01,pget(machine,'idecay'));
   const fb=A.clamp(pget(machine,'feedback'),0,1);
   const env=A.adsr(ac,time,{attack:pget(machine,'attack'),decay:pget(machine,'decay'),sustain:pget(machine,'sustain'),release:pget(machine,'release')},vel*0.35);
   env.node.connect(out);
   const car=ac.createOscillator(); car.type='sine'; car.frequency.value=hz; car.connect(env.node);
   const mod=ac.createOscillator(); mod.type='sine'; mod.frequency.value=hz*ratio;
   const mg=ac.createGain();
   const peak=index*hz;
   mg.gain.setValueAtTime(Math.max(0.0001,peak),t);
   mg.gain.exponentialRampToValueAtTime(Math.max(0.0001,peak*0.02+0.0001),t+idec);
   mod.connect(mg); mg.connect(car.frequency);
   const oscs=[car,mod];
   if(fb>0.001){ const fbo=ac.createOscillator(); fbo.type='sine'; fbo.frequency.value=hz*ratio;
    const fg=ac.createGain(); fg.gain.value=fb*hz*ratio*2; fbo.connect(fg); fg.connect(mod.frequency);
    try{ fbo.start(t); }catch(e){} oscs.push(fbo); }
   try{ car.start(t); mod.start(t); }catch(e){}
   voices.push({n,oscs,env,dead:false});
  },
  noteOff(time,n){ for(let i=voices.length-1;i>=0;i--){ const v=voices[i]; if(v.n!==n||v.dead)continue;
   kill(v,v.env.release(time)); voices.splice(i,1); return; } },
  setParam(key,value){ machine.params[key]=value; if(key==='vol')out.gain.value=value; },
  allOff(time){ for(const v of voices)kill(v,v.env.release(time)); voices=[]; },
  dispose(){ try{ out.disconnect(); }catch(e){} voices=[]; }
 };
}};

// =============================================================================================
// BeatBox: eight synthesised pads in the order of MACHINE_TYPES.beatbox.pads. Everything goes
// through one drive stage so the kit glues.
// =============================================================================================
Studio.MACHINES.beatbox={ create(ac,machine,dest){
 const out=ac.createGain(); out.gain.value=pget(machine,'vol');
 const shaper=ac.createWaveShaper(); shaper.curve=A.shaperCurve(pget(machine,'drive'));
 const bus=ac.createGain(); bus.gain.value=0.9;
 bus.connect(shaper); shaper.connect(out); out.connect(dest);

 function kick(t,g){
  const tune=pget(machine,'kickTune'), dec=pget(machine,'kickDecay');
  const o=ac.createOscillator(); o.type='sine';
  const top=90+tune*160, bot=35+tune*25;
  o.frequency.setValueAtTime(top,t); o.frequency.exponentialRampToValueAtTime(bot,t+0.05);
  const e=A.hit(ac,t,g,dec,0.004); o.connect(e); e.connect(bus); o.start(t); o.stop(t+dec+0.05);
  const c=ac.createOscillator(); c.type='square'; c.frequency.value=900;
  const ce=A.hit(ac,t,g*0.4,0.008,0.001); c.connect(ce); ce.connect(bus); c.start(t); c.stop(t+0.02);
 }
 function snare(t,g){
  const tone=pget(machine,'snareTone'), dec=pget(machine,'snareDecay');
  const n=A.noise(ac,t,dec+0.03), bp=ac.createBiquadFilter(); bp.type='bandpass';
  bp.frequency.value=900+tone*3000; bp.Q.value=0.8;
  const e=A.hit(ac,t,g,dec); n.connect(bp); bp.connect(e); e.connect(bus);
  const o=ac.createOscillator(); o.type='triangle'; o.frequency.value=150+tone*140;
  const oe=A.hit(ac,t,g*0.5,dec*0.5); o.connect(oe); oe.connect(bus); o.start(t); o.stop(t+dec*0.6+0.02);
 }
 function clap(t,g){
  for(let k=0;k<3;k++){ const w=t+k*0.011, n=A.noise(ac,w,0.16);
   const bp=ac.createBiquadFilter(); bp.type='bandpass'; bp.frequency.value=1200; bp.Q.value=1.2;
   const e=A.hit(ac,w,g*(k===2?1:0.6),0.13,0.001); n.connect(bp); bp.connect(e); e.connect(bus); }
 }
 function hat(t,g,open){
  const dec=open?pget(machine,'ohatDecay'):pget(machine,'hatDecay');
  const n=A.noise(ac,t,dec+0.03), hp=ac.createBiquadFilter(); hp.type='highpass'; hp.frequency.value=7000;
  const e=A.hit(ac,t,g,dec,0.001); n.connect(hp); hp.connect(e); e.connect(bus);
 }
 function tom(t,g){
  const tune=pget(machine,'tomTune');
  const o=ac.createOscillator(); o.type='sine';
  const top=140+tune*260; o.frequency.setValueAtTime(top,t); o.frequency.exponentialRampToValueAtTime(top*0.55,t+0.12);
  const e=A.hit(ac,t,g,0.32,0.003); o.connect(e); e.connect(bus); o.start(t); o.stop(t+0.36);
  const n=A.noise(ac,t,0.05), hp=ac.createBiquadFilter(); hp.type='highpass'; hp.frequency.value=2000;
  const ne=A.hit(ac,t,g*0.15,0.04,0.001); n.connect(hp); hp.connect(ne); ne.connect(bus);
 }
 function rim(t,g){
  const o=ac.createOscillator(); o.type='square'; o.frequency.value=1700;
  const bp=ac.createBiquadFilter(); bp.type='bandpass'; bp.frequency.value=1700; bp.Q.value=6;
  const e=A.hit(ac,t,g*0.8,0.035,0.001); o.connect(bp); bp.connect(e); e.connect(bus); o.start(t); o.stop(t+0.05);
  const n=A.noise(ac,t,0.03), hp=ac.createBiquadFilter(); hp.type='highpass'; hp.frequency.value=3000;
  const ne=A.hit(ac,t,g*0.3,0.025,0.001); n.connect(hp); hp.connect(ne); ne.connect(bus);
 }
 function crash(t,g){
  const dec=pget(machine,'crashDecay');
  const n=A.noise(ac,t,dec+0.05), hp=ac.createBiquadFilter(); hp.type='highpass'; hp.frequency.value=4500;
  const bp=ac.createBiquadFilter(); bp.type='bandpass'; bp.frequency.value=8000; bp.Q.value=0.4;
  const e=A.hit(ac,t,g*0.8,dec,0.004); n.connect(hp); hp.connect(bp); bp.connect(e); e.connect(bus);
 }
 // levels per pad so the kit sits in balance without the mixer doing the work
 const LVL=[1.0,0.7,0.6,0.28,0.3,0.6,0.45,0.35];
 const PADS=[kick,snare,clap,(t,g)=>hat(t,g,false),(t,g)=>hat(t,g,true),tom,rim,crash];
 return {
  noteOn(time,n,v){ const i=A.clamp(Math.round(n),0,7), t=Math.max(0,time);
   PADS[i](t,A.clamp(v==null?1:v,0,1)*LVL[i]); },
  noteOff(){},
  setParam(key,value){ machine.params[key]=value;
   if(key==='vol')out.gain.value=value;
   if(key==='drive')shaper.curve=A.shaperCurve(value); },
  allOff(){},
  dispose(){ try{ out.disconnect(); }catch(e){} }
 };
}};

// =============================================================================================
// Lights: a machine in the rack like any other, but it makes no sound. The engine still schedules
// its notes and hands them to the lights runtime through onNote.
// =============================================================================================
Studio.MACHINES.lights={ create(ac,machine,dest){
 return { noteOn(){}, noteOff(){}, setParam(key,value){ machine.params[key]=value; }, allOff(){}, dispose(){}, silent:true };
}};

})();
