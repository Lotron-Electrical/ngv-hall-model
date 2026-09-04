// THE LIGHTSHOW ENGINE (Lloyd, 2026-09-04): one file, two pages. The studio drives it live while
// the music is being made, and the proposal page plays a baked show back with its audio. Nothing
// in here listens to sound: the caller hands it a FRAME (where the music is: beat, bar, bass, mid,
// high, onset, level) and a STATE (what the operator asked for: look, palette, level, hit) and it
// paints the pixel array. Colours are written LINEAR, straight into the instance colour buffer
// that index.html turns into RGBW duties and light on the room.
//
// Pixel facts the looks lean on (index.html's P): s = 0..1 up the strip, col = column index
// 0..11 (N1..N6 then S1..S6), colx = 0..1 along the hall, gap = 0..7 around the column, pid = a
// stable pixel id for hashes.
(function(){
'use strict';

// PALETTES: A is the body colour, B the accent (tips, sparks, the other side). Hue, sat, val.
const PALETTES={
 ice:     {A:{h:205,s:0.85,v:1},   B:{h:190,s:0.1,v:1}},
 helix:   {A:{h:262,s:0.9,v:1},    B:{h:315,s:0.9,v:1}},
 ember:   {A:{h:12,s:1,v:1},       B:{h:38,s:0.9,v:1}},
 gold:    {A:{h:42,s:0.75,v:1},    B:{h:48,s:0.15,v:1}},
 mint:    {A:{h:150,s:0.9,v:1},    B:{h:180,s:0.5,v:1}},
 blood:   {A:{h:350,s:1,v:1},      B:{h:0,s:0,v:1}},
 white:   {A:{h:40,s:0.12,v:1},    B:{h:210,s:0.2,v:1}},
 neon:    {A:{h:120,s:1,v:1},      B:{h:290,s:1,v:1}},
 ocean:   {A:{h:222,s:1,v:0.9},    B:{h:165,s:0.9,v:1}},
 sunset:  {A:{h:330,s:0.85,v:1},   B:{h:25,s:0.9,v:1}},
};
const PALETTE_NAMES=Object.keys(PALETTES);

// LOOKS: name, a line for the pad, and the painter. Every painter gets (i, c) and returns nothing;
// it writes c.r, c.g, c.b (0..1, display gamma) for pixel i. c carries the frame and the pixel.
const LOOKS=[
 ['pulse',   'The whole hall breathes with the bass'],
 ['rise',    'A level meter up every column, bright tip'],
 ['beatwave','A wave launched up the columns on every beat'],
 ['hallchase','The lit column steps down the hall on the beat'],
 ['spectrum','Bass at the foot, mids in the middle, highs at the top'],
 ['strobe',  'A white hit on every onset, odd and even columns in turn'],
 ['sparkle', 'Glitter, denser as the highs come up'],
 ['rainbow', 'Hue rolling up the columns with the bar'],
 ['sweep',   'A bar-long sweep along the hall'],
 ['helix',   'A spiral climbing every column'],
 ['split',   'North one colour, south the other, swapped each beat'],
 ['blackout','Everything off'],
];
const LOOK_NAMES=LOOKS.map(l=>l[0]);

function hsv(h,s,v,out){ const c=v*s, x=c*(1-Math.abs((h/60)%2-1)), m=v-c; let r,g,b;
 h=((h%360)+360)%360;
 if(h<60){r=c;g=x;b=0;}else if(h<120){r=x;g=c;b=0;}else if(h<180){r=0;g=c;b=x;}else if(h<240){r=0;g=x;b=c;}else if(h<300){r=x;g=0;b=c;}else{r=c;g=0;b=x;}
 out[0]=r+m; out[1]=g+m; out[2]=b+m; return out; }
// display gamma to linear, the same curve index.html uses for its layers
const LIN=new Float32Array(1025); for(let i=0;i<=1024;i++){ const x=i/1024; LIN[i]=x<=0.04045?x/12.92:Math.pow((x+0.055)/1.055,2.4); }
function lin(x){ return x<=0?0:x>=1?1:LIN[(x*1024)|0]; }
function hash(n){ n=(n^61)^(n>>>16); n=Math.imul(n,9); n^=n>>>4; n=Math.imul(n,0x27d4eb2d); n^=n>>>15; return (n>>>0)/4294967296; }
const clamp=(x,a,b)=>x<a?a:x>b?b:x;
const smooth=x=>x<=0?0:x>=1?1:x*x*(3-2*x);

// the painters. k is a brightness, mixed A on a dim floor of B unless the look says otherwise
const PAINT={
 pulse(i,c){ const k=0.12+0.88*c.bassS, m=c.midS*0.6; c.r=c.A[0]*(1-m)+c.B[0]*m; c.g=c.A[1]*(1-m)+c.B[1]*m; c.b=c.A[2]*(1-m)+c.B[2]*m; c.r*=k; c.g*=k; c.b*=k; },
 rise(i,c){ const h=Math.pow(c.rmsS,0.7)*1.05, s=c.s; let k=s<h?0.55+0.45*(s/Math.max(h,1e-3)):0; const tip=Math.exp(-Math.abs(s-h)*40); c.r=c.A[0]*k+c.B[0]*tip; c.g=c.A[1]*k+c.B[1]*tip; c.b=c.A[2]*k+c.B[2]*tip; },
 beatwave(i,c){ // two waves in flight: this beat's and the last one's, each rising over 1.2 beats
  let k=0; for(let w=0;w<2;w++){ const ph=(c.beatPhase+w)/1.25, d=c.s-ph; if(d<0&&d>-0.14)k=Math.max(k,1+d/0.14); }
  k=k*(0.5+0.5*c.bassS); const fl=0.06; c.r=c.B[0]*fl+c.A[0]*k; c.g=c.B[1]*fl+c.A[1]*k; c.b=c.B[2]*fl+c.A[2]*k; },
 hallchase(i,c){ const on=(c.col%6)===(c.beatN%6), k=on?1-0.5*c.beatPhase:0.08; const C=on?c.A:c.B; c.r=C[0]*k; c.g=C[1]*k; c.b=C[2]*k; },
 spectrum(i,c){ const s=c.s; let k,C; if(s<0.34){k=c.bassS;C=c.A;} else if(s<0.67){k=c.midS;C=c.M;} else {k=c.highS;C=c.B;} const e=Math.exp(-Math.pow((s-(s<0.34?0.17:s<0.67?0.5:0.84))*6,2)); k=0.05+0.95*k*(0.4+0.6*e); c.r=C[0]*k; c.g=C[1]*k; c.b=C[2]*k; },
 strobe(i,c){ const odd=(c.col&1)===(c.strobeN&1), k=odd?c.strobeK:0, fl=0.1*(0.5+0.5*c.bassS); c.r=c.A[0]*fl+k; c.g=c.A[1]*fl+k; c.b=c.A[2]*fl+k; },
 sparkle(i,c){ const fr=Math.floor(c.t*14), dn=0.01+0.18*c.highS, q=c.pid; const k=hash(q*7919+fr)<dn?1:(hash(q*7919+fr-1)<dn?0.45:0); const fl=0.08; c.r=c.A[0]*fl+c.B[0]*k; c.g=c.A[1]*fl+c.B[1]*k; c.b=c.A[2]*fl+c.B[2]*k; },
 rainbow(i,c){ hsv(c.s*300+c.col*30-c.barPhase*360-c.beatN*20,1,0.25+0.75*c.rmsS,c.tmp); c.r=c.tmp[0]; c.g=c.tmp[1]; c.b=c.tmp[2]; },
 sweep(i,c){ const ph=((c.colx*1.3-c.barPhase*1.3)%1.3+1.3)%1.3, k=ph<0.3?1-ph/0.3:0, fl=0.07; c.r=c.B[0]*fl+c.A[0]*k; c.g=c.B[1]*fl+c.A[1]*k; c.b=c.B[2]*fl+c.A[2]*k; },
 helix(i,c){ const k=Math.pow(0.5+0.5*Math.sin(c.s*Math.PI*6+c.gap*Math.PI/4-c.t*5-c.beatN),3)*(0.4+0.6*c.rmsS); const m=c.s; c.r=(c.A[0]*(1-m)+c.B[0]*m)*k; c.g=(c.A[1]*(1-m)+c.B[1]*m)*k; c.b=(c.A[2]*(1-m)+c.B[2]*m)*k; },
 split(i,c){ const north=c.col<6, sw=(c.beatN&1)===1, C=(north!==sw)?c.A:c.B, k=0.3+0.7*c.bassS; c.r=C[0]*k; c.g=C[1]*k; c.b=C[2]*k; },
 blackout(i,c){ c.r=c.g=c.b=0; },
};

function createShow(){
 const S={
  on:false,
  // what the operator asked for
  state:{look:'pulse', palette:'helix', level:1, hitAt:-9, strobe:true},
  // where the music is. bpm/beat/bar come from the transport or the cue file; bands from the
  // analyser or the cue file. The engine smooths the bands itself so a caller may feed raw values.
  frame:{t:0, bpm:120, beatN:0, beatPhase:0, barPhase:0, bass:0, mid:0, high:0, rms:0, onset:0},
  sm:{bass:0, mid:0, high:0, rms:0, strobeN:0, strobeK:0, lastOnset:-9, lastT:0},
  ctx:{r:0,g:0,b:0,s:0,col:0,colx:0,gap:0,pid:0,t:0,beatN:0,beatPhase:0,barPhase:0,bassS:0,midS:0,highS:0,rmsS:0,strobeN:0,strobeK:0,A:[0,0,0],B:[0,0,0],M:[0,0,0],tmp:[0,0,0]},
  looks:LOOK_NAMES, palettes:PALETTE_NAMES, LOOKS, PALETTES,
  // one call per rendered frame: a = linear rgb per pixel (3 floats), P = the page's pixel map
  paint(a,P){
   const f=S.frame, st=S.state, m=S.sm, c=S.ctx, n=P.n;
   const dt=clamp(f.t-m.lastT,0,0.1); m.lastT=f.t;
   // bands: fast up, slow down, so a kick reads as a hit and not a flicker
   const rise=1-Math.exp(-dt*40), fall=1-Math.exp(-dt*7);
   for(const k of ['bass','mid','high','rms']){ const v=clamp(f[k],0,1); m[k]+= (v>m[k]?rise:fall)*(v-m[k]); }
   // onsets: a fresh transient (or a hit pad press) starts a strobe that dies in 120 ms
   if(f.onset>0.6&&f.t-m.lastOnset>0.11){ m.lastOnset=f.t; m.strobeN++; }
   if(st.hitAt>m.lastOnset){ m.lastOnset=st.hitAt; m.strobeN++; }
   m.strobeK=Math.exp(-(f.t-m.lastOnset)/0.09);
   const pal=PALETTES[st.palette]||PALETTES.helix;
   hsv(pal.A.h,pal.A.s,pal.A.v,c.A); hsv(pal.B.h,pal.B.s,pal.B.v,c.B);
   for(let q=0;q<3;q++)c.M[q]=(c.A[q]+c.B[q])*0.5;
   c.t=f.t; c.beatN=f.beatN|0; c.beatPhase=clamp(f.beatPhase,0,1); c.barPhase=clamp(f.barPhase,0,1);
   c.bassS=m.bass; c.midS=m.mid; c.highS=m.high; c.rmsS=m.rms; c.strobeN=m.strobeN; c.strobeK=m.strobeK;
   const painter=PAINT[st.look]||PAINT.pulse, lv=clamp(st.level,0,1);
   // a hit pad press flashes the whole hall white over whatever look is up
   const hit=Math.exp(-(f.t-st.hitAt)/0.12);
   for(let i=0;i<n;i++){
    c.s=P.s[i]; c.col=P.col[i]; c.colx=P.colx[i]; c.gap=P.gap[i]; c.pid=P.pid[i];
    painter(i,c);
    const o=i*3;
    a[o]=lin(clamp(c.r*lv+hit,0,1)); a[o+1]=lin(clamp(c.g*lv+hit,0,1)); a[o+2]=lin(clamp(c.b*lv+hit,0,1));
   }
  },
  // the cue file's timeline: the last stamped state at time t wins. cues = [{t,look,palette,level,hit}]
  applyCues(cues,t){ const st=S.state; let last=null;
   for(let i=0;i<cues.length;i++){ const q=cues[i]; if(q.t>t)break; last=q; if(q.hit)st.hitAt=q.t; }
   if(last){ if(last.look)st.look=last.look; if(last.palette)st.palette=last.palette; if(last.level!=null)st.level=last.level; }
  },
  // a baked cue file's frames (from studio export or tools/show_analyse.py) read at time t
  frameFromCues(cf,t){ const f=S.frame, k=cf.frames, hop=cf.hop_s||0.0232, j=clamp((t/hop)|0,0,k.rms.length-1);
   f.t=t; f.bass=k.bass[j]; f.mid=k.mid[j]; f.high=k.high[j]; f.rms=k.rms[j]; f.onset=k.onset[j]; f.bpm=cf.bpm||120;
   const b=cf.beats||[]; let lo=0,hi=b.length; while(lo<hi){ const md=(lo+hi)>>1; if(b[md]<=t)lo=md+1; else hi=md; }
   const bi=lo-1; if(bi>=0&&bi<b.length-1){ f.beatN=bi; f.beatPhase=(t-b[bi])/(b[bi+1]-b[bi]); } else if(bi>=0){ f.beatN=bi; f.beatPhase=clamp((t-b[bi])*f.bpm/60,0,1); } else { f.beatN=0; f.beatPhase=0; }
   f.barPhase=((f.beatN%4)+f.beatPhase)/4; },
 };
 return S;
}

// the live analyser: bands from a WebAudio AnalyserNode, for the studio while the music plays
function createAnalyser(ac,node){
 const an=ac.createAnalyser(); an.fftSize=2048; an.smoothingTimeConstant=0.4; node.connect(an);
 const bins=new Float32Array(an.frequencyBinCount), prev=new Float32Array(an.frequencyBinCount), hz=ac.sampleRate/an.fftSize;
 const band=(lo,hi)=>{ let s=0,c=0; for(let i=Math.max(1,Math.floor(lo/hz));i<Math.min(bins.length,Math.ceil(hi/hz));i++){ s+=Math.pow(10,bins[i]/20); c++; } return c?s/c:0; };
 const norm={bass:1e-3,mid:1e-3,high:1e-3,rms:1e-3,flux:1e-3};   // running peaks, so the bands sit at 0..1 whatever the level
 return { node:an, read(out){ an.getFloatFrequencyData(bins);
   let flux=0; for(let i=1;i<bins.length;i++){ const d=Math.pow(10,bins[i]/20)-Math.pow(10,prev[i]/20); if(d>0)flux+=d; prev[i]=bins[i]; }
   const v={bass:band(20,150), mid:band(150,2000), high:band(2000,11000), flux};
   v.rms=(v.bass*2+v.mid+v.high*0.5)/3.5;
   for(const k in v){ norm[k]=Math.max(v[k],norm[k]*0.9995); out[k==='flux'?'onset':k]=clamp(v[k]/norm[k],0,1); }
   return out; } };
}

window.NGVShow={createShow, createAnalyser, LOOKS, LOOK_NAMES, PALETTES, PALETTE_NAMES};
})();
