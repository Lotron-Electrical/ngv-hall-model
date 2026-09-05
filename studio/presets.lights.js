// LIGHT PATTERN PRESETS (LXPRESETS, 2026-09-05): 30 light patterns, six families of five, one
// role per family so stacking stays legible. A pattern is DATA only: cues on a 64-step grid
// (4 bars x 16), an optional 64-entry level lane, and the tags the builder picks by (style,
// energy range, default sync, gain).
//
// A cue is [step, kind, value] with kind 'look' | 'palette' | 'hit'. Cue steps sit on musically
// sensible places: bar lines 0/16/32/48, half bars 8/24/40/56, and the beat before a bar line
// when the pattern wants to land on the downbeat.
//
// Looks: some patterns name a look that lives in show/looks2.js (tide, columnglow, ripple,
// meteor, kickpunch, tips, bloom, columnstrobe, lightning, twinkle, grain, fire, palettewalk,
// huechase). looks2.js is written in parallel with this file, so EVERY pattern also carries
// `fallbackLook`, one of the 12 originals in show/lightshow.js, and the builder must use it when
// the named look is not registered. That way a missing look costs the pattern its flavour, not
// its existence.
//
// Sync: 'grid' follows the bar clock; an instrument id ('drums', 'bass', ...) makes the layer's
// triggers that machine's notes. Accent patterns default to the instrument they are named after,
// movement patterns lean on drums or bass, base patterns stay on the grid.
(function(){
'use strict';
const Studio=window.Studio=window.Studio||{};

const clamp=(x,a,b)=>x<a?a:x>b?b:x;
const r3=x=>Math.round(x*1000)/1000;

// A level lane is 64 entries; null leaves the level alone at that step. These four shapes cover
// everything the patterns need, so the lanes stay readable as intent rather than as numbers.
function lane(fn){ const a=new Array(64); for(let i=0;i<64;i++){ const v=fn(i); a[i]=(v==null)?null:r3(clamp(v,0,1)); } return a; }
// one full swell every `period` steps, so the hall breathes with the bars
function breathe(period,lo,hi){ return lane(i=>lo+(hi-lo)*(0.5-0.5*Math.cos(2*Math.PI*(i/period)))); }
// a rise across every bar: each bar lands brighter than it started
function barSwell(lo,hi){ return lane(i=>lo+(hi-lo)*((i%16)/15)); }
// fall away over the `w` steps before each mark, so the hit that follows has somewhere to go
function dipBefore(marks,w,lo,hi){ return lane(i=>{ let best=-1;
 for(let k=0;k<marks.length;k++){ const d=((marks[k]-i)%64+64)%64; if(d>0&&d<=w&&(best<0||d<best))best=d; }
 return best<0?hi:lo+(hi-lo)*((best-1)/Math.max(w-1,1)); }); }
// sit dark and jump on each mark, decaying over `w` steps: for lightning and other rare stabs
function spikes(marks,w,lo,hi){ return lane(i=>{ let best=-1;
 for(let k=0;k<marks.length;k++){ const d=((i-marks[k])%64+64)%64; if(d<w&&(best<0||d<best))best=d; }
 return best<0?lo:hi-(hi-lo)*(best/w); }); }

Studio.PRESETS_LIGHTS={ list:[

// BASE: the bed the rest of the show sits on. Slow, wide, always on the grid, never busy.
{ id:'lx.breathe', name:'Breathe', family:'base',
  style:['ambient','house','hiphop','halftime'], energy:[0,0.7],
  bars:4, gain:1, sync:'grid', fallbackLook:'pulse',
  cues:[ [0,'palette','helix'], [0,'look','pulse'], [32,'palette','ocean'] ],
  level:breathe(32,0.35,1) },

{ id:'lx.tide', name:'Slow tide', family:'base',
  style:['ambient','halftime','dubstep','abstract'], energy:[0,0.6],
  bars:4, gain:0.9, sync:'grid', fallbackLook:'pulse',
  cues:[ [0,'palette','ocean'], [0,'look','tide'], [32,'palette','ice'] ],
  level:breathe(64,0.3,0.95) },

{ id:'lx.columnglow', name:'Column glow', family:'base',
  style:['house','techno','ambient','trap'], energy:[0.1,0.8],
  bars:4, gain:0.95, sync:'grid', fallbackLook:'rise',
  cues:[ [0,'palette','mint'], [0,'look','columnglow'], [32,'palette','ice'] ],
  level:barSwell(0.45,0.9) },

{ id:'lx.spectrumfloor', name:'Spectrum floor', family:'base',
  style:['techno','house','dnb','dubstep'], energy:[0.15,0.9],
  bars:4, gain:1, sync:'grid', fallbackLook:'spectrum',
  cues:[ [0,'palette','ice'], [0,'look','spectrum'], [32,'palette','neon'] ] },

{ id:'lx.emberbed', name:'Ember bed', family:'base',
  style:['hiphop','halftime','ambient','trap'], energy:[0,0.65],
  bars:4, gain:0.9, sync:'grid', fallbackLook:'pulse',
  cues:[ [0,'palette','ember'], [0,'look','pulse'], [32,'palette','sunset'] ],
  level:breathe(64,0.4,0.85) },

// MOVEMENT: something travelling. Synced to drums or bass so the travel is the music's, not a
// free-running animation over the top of it.
{ id:'lx.beatwaves', name:'Beat waves', family:'movement',
  style:['dnb','house','techno','breakbeat'], energy:[0.25,1],
  bars:4, gain:1, sync:'drums', fallbackLook:'beatwave',
  cues:[ [0,'palette','helix'], [0,'look','beatwave'], [32,'palette','neon'] ],
  level:dipBefore([0],4,0.45,1) },

{ id:'lx.sweep', name:'Sweep', family:'movement',
  style:['house','techno','dnb','ambient'], energy:[0.2,0.9],
  bars:4, gain:0.9, sync:'bass', fallbackLook:'sweep',
  cues:[ [0,'palette','ocean'], [0,'look','sweep'], [16,'palette','mint'], [32,'palette','ocean'], [48,'palette','ice'] ] },

{ id:'lx.hallchase', name:'Hall chase', family:'movement',
  style:['techno','house','breakbeat','dnb'], energy:[0.3,1],
  bars:4, gain:1, sync:'drums', fallbackLook:'hallchase',
  cues:[ [0,'palette','neon'], [0,'look','hallchase'], [32,'palette','sunset'] ] },

{ id:'lx.ripple', name:'Ripple from centre', family:'movement',
  style:['dubstep','halftime','ambient','abstract'], energy:[0.2,0.9],
  bars:4, gain:0.95, sync:'bass', fallbackLook:'beatwave',
  cues:[ [0,'palette','helix'], [0,'look','ripple'], [24,'palette','ocean'], [56,'palette','helix'] ],
  level:barSwell(0.5,1) },

{ id:'lx.meteor', name:'Meteor fall', family:'movement',
  style:['dnb','dubstep','trap','breakbeat'], energy:[0.35,1],
  bars:4, gain:1, sync:'drums', fallbackLook:'beatwave',
  cues:[ [0,'palette','ice'], [0,'look','meteor'], [32,'palette','white'], [62,'hit',true] ],
  level:dipBefore([62],6,0.35,1) },

// ACCENT: short and punchy, each one riding the instrument it is named for.
{ id:'lx.kickpunch', name:'Kick punch', family:'accent',
  style:['techno','house','trap','dubstep'], energy:[0.3,1],
  bars:4, gain:1, sync:'drums', fallbackLook:'pulse',
  cues:[ [0,'palette','blood'], [0,'look','kickpunch'], [32,'palette','ember'] ] },

{ id:'lx.snaresplit', name:'Snare split', family:'accent',
  style:['hiphop','breakbeat','dnb','trap'], energy:[0.3,1],
  bars:4, gain:0.9, sync:'drums', fallbackLook:'split',
  cues:[ [0,'palette','neon'], [0,'look','split'], [32,'palette','helix'] ] },

{ id:'lx.basstips', name:'Bass pulse tips', family:'accent',
  style:['dubstep','dnb','trap','halftime'], energy:[0.3,1],
  bars:4, gain:0.95, sync:'bass', fallbackLook:'rise',
  cues:[ [0,'palette','gold'], [0,'look','tips'], [32,'palette','sunset'] ],
  level:barSwell(0.55,1) },

{ id:'lx.hatglitter', name:'Hat glitter', family:'accent',
  style:['trap','house','dnb','hiphop'], energy:[0.25,1],
  bars:4, gain:0.8, sync:'drums', fallbackLook:'sparkle',
  cues:[ [0,'palette','white'], [0,'look','sparkle'], [32,'palette','ice'] ] },

{ id:'lx.downbeatbloom', name:'Downbeat bloom', family:'accent',
  style:['house','halftime','hiphop','ambient'], energy:[0.2,0.95],
  bars:4, gain:1, sync:'drums', fallbackLook:'beatwave',
  cues:[ [0,'palette','sunset'], [0,'look','bloom'], [0,'hit',true], [16,'hit',true],
         [32,'palette','gold'], [32,'hit',true], [48,'hit',true] ],
  level:dipBefore([0,16,32,48],3,0.4,1) },

// STROBE: max-blended and expensive, so these are written for the top of the arc only.
{ id:'lx.strobehits', name:'Strobe hits', family:'strobe',
  style:['techno','dnb','dubstep','house'], energy:[0.85,1],
  bars:4, gain:1, sync:'drums', fallbackLook:'strobe',
  cues:[ [0,'palette','white'], [0,'look','strobe'], [32,'palette','ice'] ] },

{ id:'lx.columnstrobe', name:'Column strobe', family:'strobe',
  style:['techno','dnb','breakbeat','dubstep'], energy:[0.85,1],
  bars:4, gain:1, sync:'drums', fallbackLook:'strobe',
  cues:[ [0,'palette','white'], [0,'look','columnstrobe'], [32,'palette','neon'] ] },

// dark for most of the bar, one stab on the last beat: the gap is what makes the stab read
{ id:'lx.blackouthits', name:'Blackout hits', family:'strobe',
  style:['dubstep','trap','techno','halftime'], energy:[0.8,1],
  bars:4, gain:1, sync:'grid', fallbackLook:'blackout',
  cues:[ [0,'palette','white'], [0,'look','blackout'], [12,'look','strobe'], [12,'hit',true],
         [16,'look','blackout'], [28,'look','strobe'], [28,'hit',true],
         [32,'look','blackout'], [44,'look','strobe'], [44,'hit',true],
         [48,'look','blackout'], [60,'look','strobe'], [60,'hit',true] ] },

{ id:'lx.lightning', name:'Lightning', family:'strobe',
  style:['dubstep','dnb','abstract','techno'], energy:[0.8,1],
  bars:4, gain:1, sync:'grid', fallbackLook:'strobe',
  cues:[ [0,'palette','ice'], [0,'look','lightning'], [14,'hit',true], [30,'hit',true],
         [46,'hit',true], [62,'hit',true] ],
  level:spikes([14,30,46,62],6,0.2,1) },

{ id:'lx.flashimpact', name:'Flash on impact', family:'strobe',
  style:['trap','dubstep','halftime','hiphop'], energy:[0.75,1],
  bars:4, gain:1, sync:'drums', fallbackLook:'strobe',
  cues:[ [0,'palette','white'], [0,'look','strobe'], [0,'hit',true], [32,'hit',true],
         [48,'palette','blood'], [56,'hit',true] ],
  level:dipBefore([0,32,56],4,0.3,1) },

// TEXTURE: detail over the top. Low gain by design so they never fight the base layer.
{ id:'lx.glitter', name:'Glitter', family:'texture',
  style:['house','trap','dnb','hiphop'], energy:[0.2,1],
  bars:4, gain:0.8, sync:'grid', fallbackLook:'sparkle',
  cues:[ [0,'palette','white'], [0,'look','sparkle'], [32,'palette','gold'] ] },

{ id:'lx.twinkle', name:'Twinkle', family:'texture',
  style:['ambient','house','halftime','abstract'], energy:[0.1,0.8],
  bars:4, gain:0.75, sync:'grid', fallbackLook:'sparkle',
  cues:[ [0,'palette','ice'], [0,'look','twinkle'], [32,'palette','helix'] ],
  level:breathe(32,0.5,1) },

{ id:'lx.grain', name:'Noise grain', family:'texture',
  style:['abstract','ambient','dubstep','techno'], energy:[0.1,0.8],
  bars:4, gain:0.7, sync:'grid', fallbackLook:'sparkle',
  cues:[ [0,'palette','white'], [0,'look','grain'], [32,'palette','mint'] ] },

{ id:'lx.helixspiral', name:'Helix spiral', family:'texture',
  style:['techno','abstract','dnb','ambient'], energy:[0.15,0.9],
  bars:4, gain:0.85, sync:'grid', fallbackLook:'helix',
  cues:[ [0,'palette','helix'], [0,'look','helix'], [32,'palette','neon'] ] },

{ id:'lx.fire', name:'Fire', family:'texture',
  style:['dubstep','trap','hiphop','halftime'], energy:[0.2,1],
  bars:4, gain:0.9, sync:'grid', fallbackLook:'pulse',
  cues:[ [0,'palette','ember'], [0,'look','fire'], [32,'palette','sunset'] ],
  level:breathe(16,0.55,1) },

// COLOUR: the layer that moves hue. Palette cues land on bar lines so colour follows the chords.
{ id:'lx.rainbowroll', name:'Rainbow roll', family:'colour',
  style:['house','breakbeat','dnb','abstract'], energy:[0.2,1],
  bars:4, gain:0.9, sync:'grid', fallbackLook:'rainbow',
  cues:[ [0,'palette','neon'], [0,'look','rainbow'], [32,'palette','helix'] ] },

{ id:'lx.palettewalk', name:'Palette walk', family:'colour',
  style:['ambient','house','halftime','abstract'], energy:[0.1,0.9],
  bars:4, gain:0.9, sync:'grid', fallbackLook:'rainbow',
  cues:[ [0,'palette','ice'], [0,'look','palettewalk'], [16,'palette','mint'],
         [32,'palette','sunset'], [48,'palette','helix'] ] },

{ id:'lx.warmcool', name:'Warm/cool swing', family:'colour',
  style:['hiphop','halftime','house','ambient'], energy:[0.1,0.85],
  bars:4, gain:0.9, sync:'grid', fallbackLook:'split',
  cues:[ [0,'palette','ember'], [0,'look','split'], [16,'palette','ice'],
         [32,'palette','sunset'], [48,'palette','ocean'] ],
  level:breathe(32,0.6,1) },

// one palette per bar, which is one per chord in the default 4-bar cycle
{ id:'lx.chordcolour', name:'Chord colour', family:'colour',
  style:['ambient','house','halftime','abstract'], energy:[0.15,0.9],
  bars:4, gain:0.95, sync:'grid', fallbackLook:'rise',
  cues:[ [0,'palette','helix'], [0,'look','columnglow'], [16,'palette','gold'],
         [32,'palette','ice'], [48,'palette','sunset'] ],
  level:barSwell(0.5,0.95) },

{ id:'lx.huechase', name:'Hue chase', family:'colour',
  style:['dnb','breakbeat','techno','abstract'], energy:[0.3,1],
  bars:4, gain:0.9, sync:'bass', fallbackLook:'rainbow',
  cues:[ [0,'palette','neon'], [0,'look','huechase'], [32,'palette','blood'] ] },

] };

// convenience for the builder and the jam page: by id, and by family in list order
Studio.PRESETS_LIGHTS.byId=(id)=>Studio.PRESETS_LIGHTS.list.find(p=>p.id===id)||null;
Studio.PRESETS_LIGHTS.byFamily=(fam)=>Studio.PRESETS_LIGHTS.list.filter(p=>p.family===fam);

})();
