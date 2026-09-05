// TWELVE MORE LOOKS (LOOKS owner, 2026-09-05). The first twelve live in show/lightshow.js; these
// fill the families the compositor stacks: two more base beds, two movement looks, three accents
// that fire on c.trig, two strobes, two textures and one colour walk. Same painter contract as
// lightshow.js: painter(i,c) writes c.r, c.g, c.b in display gamma 0..1 and returns nothing.
//
// Pixel facts (index.html's P, unchanged): s = 0..1 up the strip, col = 0..11 (N1..N6 then
// S1..S6), colx = 0..1 along the hall, gap = 0..7 around the column, pid = a stable pixel id.
// Music facts: t, beatN, beatPhase, barPhase, bassS, midS, highS, rmsS, strobeN, strobeK and
// trig (0..1, decaying since the layer's last trigger). Colours: c.A body, c.B accent, c.M mid.
//
// REGISTRATION. LIGHTS provides NGVShow.registerLook(name, family, description, painter). Until
// that lands this file falls back, in order: push into NGVShow.LOOKS / LOOK_NAMES / PAINT if the
// painter table is exposed, else queue on NGVShow._pendingLooks. LIGHTS must drain that queue at
// the end of registerLook's definition:
//   (NGVShow._pendingLooks||[]).forEach(q=>registerLook(q.name,q.family,q.description,q.painter));
// Either way NGVShow.LOOKS2 always carries this file's twelve, so the test page and any tool can
// read them without waiting for the compositor.
(function(){
'use strict';

const NS = window.NGVShow = window.NGVShow || {};

// local copies of lightshow's helpers: this file must not depend on that file's internals
function hsv(h,s,v,out){ const c=v*s, x=c*(1-Math.abs((h/60)%2-1)), m=v-c; let r,g,b;
 h=((h%360)+360)%360;
 if(h<60){r=c;g=x;b=0;}else if(h<120){r=x;g=c;b=0;}else if(h<180){r=0;g=c;b=x;}else if(h<240){r=0;g=x;b=c;}else if(h<300){r=x;g=0;b=c;}else{r=c;g=0;b=x;}
 out[0]=r+m; out[1]=g+m; out[2]=b+m; return out; }
function hash(n){ n=(n^61)^(n>>>16); n=Math.imul(n,9); n^=n>>>4; n=Math.imul(n,0x27d4eb2d); n^=n>>>15; return (n>>>0)/4294967296; }
const clamp=(x,a,b)=>x<a?a:x>b?b:x;
// accents and strobes want a trigger envelope. c.trig is the real one; before LIGHTS lands, or on
// a grid layer that never triggered, fall back to the beat so a look is never dead on the pad.
function trig(c){ return c.trig!=null?c.trig:Math.exp(-c.beatPhase*3.2); }

const NEW=[

// ---- base: quiet beds that hold the room lit ----------------------------------------------
['tide','base','Slow swells crossing the hall, no beat in them',
 function tide(i,c){
  // two waves at different rates so the pattern never repeats on the eye
  const w1=0.5+0.5*Math.sin(c.s*2.1-c.t*0.55+c.colx*2.4);
  const w2=0.5+0.5*Math.sin(c.s*3.7+c.t*0.31-c.colx*1.6);
  const m=w2*0.6;                                   // the troughs drift towards the accent colour
  const k=(0.16+0.64*w1)*(0.45+0.55*c.rmsS);
  c.r=(c.A[0]*(1-m)+c.B[0]*m)*k; c.g=(c.A[1]*(1-m)+c.B[1]*m)*k; c.b=(c.A[2]*(1-m)+c.B[2]*m)*k;
 }],

['columnglow','base','Twelve lamps, each column its own level',
 function columnglow(i,c){
  // per-column phase from a hash: the hall reads as separate lamps, not one field
  const q=hash(c.col*131+7);
  const lv=0.22+0.78*Math.abs(Math.sin(c.t*(0.32+0.5*q)+q*6.283));
  const body=1-Math.pow(Math.abs(c.s*2-1),3);       // soft off at both ends of the strip
  const k=body*lv*(0.3+0.7*c.midS);
  const C=(c.col&1)?c.B:c.A;                        // alternating so the hall has depth
  c.r=C[0]*k; c.g=C[1]*k; c.b=C[2]*k;
 }],

// ---- movement: things that travel ----------------------------------------------------------
['ripple','movement','Rings leaving the middle of the hall every bar',
 function ripple(i,c){
  // distance is along the hall plus a little up the strip, so the rings lean as they pass
  const d=Math.abs(c.colx-0.5)*1.6+c.s*0.5;
  const ph=((d-c.barPhase*1.6)%0.8+0.8)%0.8;
  let k=ph<0.22?Math.pow(1-ph/0.22,1.5):0;
  k*=0.45+0.55*c.rmsS;
  const fl=0.05;                                    // a dim bed so the dark hall still reads
  c.r=c.B[0]*fl+c.A[0]*k; c.g=c.B[1]*fl+c.A[1]*k; c.b=c.B[2]*fl+c.A[2]*k;
 }],

['meteor','movement','Heads falling down the columns with tails, staggered',
 function meteor(i,c){
  const off=(c.col*0.37+c.gap*0.045)%1;             // stagger so it cascades down the hall
  const ph=((c.beatN%2)+c.beatPhase)/2;             // one fall every two beats
  const head=1-((ph+off)%1);
  const d=c.s-head;
  let k=(d>0&&d<0.32)?Math.pow(1-d/0.32,2):0;       // the tail is above the head, it falls
  k*=0.5+0.5*c.rmsS;
  const tip=Math.exp(-Math.abs(d)*50);              // the head itself, in the accent colour
  c.r=c.A[0]*k+c.B[0]*tip; c.g=c.A[1]*k+c.B[1]*tip; c.b=c.A[2]*k+c.B[2]*tip;
 }],

// ---- accent: fired by c.trig, added on top of a base ---------------------------------------
['kickpunch','accent','The hit lands at the foot and rushes up the columns',
 function kickpunch(i,c){
  const g=trig(c);
  const front=(1-g)*1.4;                            // the front climbs as the trigger decays
  const d=c.s-front;
  let k=(d<0&&d>-0.45)?(1+d/0.45):0;
  k*=g*(0.35+0.65*c.bassS);
  c.r=c.A[0]*k; c.g=c.A[1]*k; c.b=c.A[2]*k;
 }],

['tips','accent','Only the top of every strip, punched by the bass',
 function tips(i,c){
  const g=trig(c);
  const t=Math.pow(Math.max(0,(c.s-0.76)/0.24),0.7);
  const k=t*(0.2+0.8*g)*(0.3+0.7*c.bassS);
  c.r=(c.B[0]*0.85+c.A[0]*0.15)*k; c.g=(c.B[1]*0.85+c.A[1]*0.15)*k; c.b=(c.B[2]*0.85+c.A[2]*0.15)*k;
 }],

['bloom','accent','Opens from the middle of each strip and swells out',
 function bloom(i,c){
  const g=trig(c);
  const w=0.10+0.46*(1-g);                          // the flower opens as the trigger dies
  const d=Math.abs(c.s-0.5);
  let k=d<w?Math.pow(1-d/w,0.8):0;                  // a full band, not a thin line: it must punch
  k*=g*(0.5+0.5*c.midS);
  // the rim of the ring is the accent colour and the middle the blend: the edge is what you read
  const m=clamp(d/Math.max(w,1e-3),0,1);
  c.r=(c.M[0]*(1-m)+c.B[0]*m)*k; c.g=(c.M[1]*(1-m)+c.B[1]*m)*k; c.b=(c.M[2]*(1-m)+c.B[2]*m)*k;
 }],

// ---- strobe: short and hot, the compositor blends these with max ----------------------------
['columnstrobe','strobe','A hard hit on a third of the columns, a new third each time',
 function columnstrobe(i,c){
  const pick=hash(c.col*977+c.strobeN*31)<0.34;
  const k=pick?c.strobeK:0;
  const fl=0.05*(0.4+0.6*c.rmsS);                   // dim bed between hits so the hall is not dead
  c.r=c.A[0]*fl+k*(0.5+0.5*c.A[0]); c.g=c.A[1]*fl+k*(0.5+0.5*c.A[1]); c.b=c.A[2]*fl+k*(0.5+0.5*c.A[2]);
 }],

['lightning','strobe','A fork on one or two columns, double blink, bright at the top',
 function lightning(i,c){
  const n=c.strobeN|0;
  const a=(hash(n*613+11)*12)|0, b=(hash(n*1811+3)*12)|0;
  const on=(c.col===a)||(hash(n*7+5)<0.45&&c.col===b);
  // two blinks out of one onset: the second, weaker one is what makes it read as lightning
  const K=c.strobeK;
  const blink=K>0.72?1:(K>0.3&&K<0.5?0.65:0);
  const branch=on?Math.pow(1-c.s*0.55,1.6):0;       // brightest at the ceiling, fading to the floor
  const k=branch*blink;
  const fl=0.035;
  c.r=c.B[0]*fl+k*(0.85+0.15*c.B[0]); c.g=c.B[1]*fl+k*(0.85+0.15*c.B[1]); c.b=c.B[2]*fl+k*(0.85+0.15*c.B[2]);
 }],

// ---- texture: fine detail over a base ------------------------------------------------------
['grain','texture','A noise field over every pixel, sliding, not sparkling',
 function grain(i,c){
  // interpolated between two frames of noise: shimmer instead of the hard flicker of sparkle
  const fr=Math.floor(c.t*20), f=c.t*20-fr, q=c.pid;
  const n1=hash(q*131+fr*7919), n2=hash(q*131+(fr+1)*7919);
  const n=n1+(n2-n1)*f;
  const k=(0.08+0.92*Math.pow(n,2.2))*(0.25+0.75*c.midS);
  c.r=(c.A[0]*(1-n)+c.B[0]*n)*k; c.g=(c.A[1]*(1-n)+c.B[1]*n)*k; c.b=(c.A[2]*(1-n)+c.B[2]*n)*k;
 }],

['fire','texture','Hot at the foot, cooling upward, cells rising through it',
 function fire(i,c){
  const cell=Math.floor(c.s*14-c.t*6);              // cells climb because time is subtracted
  const n=hash(c.col*911+c.gap*37+cell*7919);
  const h=Math.max(0.06,(0.3+0.7*n)*(0.35+0.65*c.rmsS));   // this pixel's flame height
  const k=Math.pow(Math.max(0,1-c.s/h),1.4);
  const m=clamp(c.s/h,0,1);                         // the pale tip of a flame, in the accent colour
  c.r=(c.A[0]*(1-m)+c.B[0]*m)*k; c.g=(c.A[1]*(1-m)+c.B[1]*m)*k; c.b=(c.A[2]*(1-m)+c.B[2]*m)*k;
 }],

// ---- colour: hue is the subject ------------------------------------------------------------
['huechase','colour','One hue running the length of the hall and up the strips',
 function huechase(i,c){
  const h=c.colx*220+c.s*120-c.t*45+c.beatN*18;     // beatN steps it, so the chase is on the music
  const band=0.55+0.45*Math.sin(c.s*6.283-c.barPhase*6.283);
  const v=(0.28+0.72*c.rmsS)*band;
  hsv(h,0.95,Math.max(0,v),c.tmp);
  c.r=c.tmp[0]; c.g=c.tmp[1]; c.b=c.tmp[2];
 }],
];

// the registry this file always owns, whatever LIGHTS has landed
NS.LOOKS2=NEW.map(e=>({name:e[0], family:e[1], description:e[2], painter:e[3]}));

function register(name,family,description,painter){
 if(typeof NS.registerLook==='function'){ NS.registerLook(name,family,description,painter); return 'registerLook'; }
 if(NS.PAINT&&Array.isArray(NS.LOOKS)){                      // compositor half-landed: fill it by hand
  NS.PAINT[name]=painter; NS.LOOKS.push([name,description,family]);
  if(Array.isArray(NS.LOOK_NAMES))NS.LOOK_NAMES.push(name);
  return 'direct';
 }
 (NS._pendingLooks=NS._pendingLooks||[]).push({name,family,description,painter});
 return 'pending';
}
NS.LOOKS2.forEach(l=>{ l.how=register(l.name,l.family,l.description,l.painter); });

})();
