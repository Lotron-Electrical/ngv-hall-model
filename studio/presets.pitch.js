// PITCHED PATTERNS (Lloyd, 2026-09-05): 80 hand written patterns, ten per pitched instrument, one
// per style. They are written in DEGREES, not midi, so the same pattern follows whatever chord
// cycle and key the section carries. CORE's render() turns them into notes.
//
//   ct  = chord tone of the bar's chord: 0 root, 1 third, 2 fifth, 3 seventh (octave if none)
//   deg = scale degree 1..7 of the section key (A minor: 1 A, 2 B, 3 C, 4 D, 5 E, 6 F, 7 G)
//   oct = octave offset applied after the tone is chosen
//   s,l = step and length on a 16 step 4/4 bar; the renderer clips at the bar end of an odd meter
//   register = the midi window the rendered note is folded into, so the slots never collide
//
// House rules kept everywhere below: velocities are only 1.0 accent, 0.7 normal, 0.4 ghost;
// pattern lengths are 1, 2 or 4 bars, never 3; every pattern has a note at step 0 so it passes the
// solo audit; bass and sub are chord tones only, because a scale degree under a chord change is
// how a bass line goes sour. Names describe the feel, not the style.
(function(){
'use strict';
const Studio=window.Studio=window.Studio||{};

// registers: one window per frequency slot, so a full stack does not pile up in one octave
const R_SUB=[28,45], R_BASS=[33,52], R_PAD=[48,72], R_CHORDS=[52,76], R_KEYS=[57,81],
      R_LEAD=[69,93], R_ARP=[69,96], R_FX=[72,96];

Studio.PRESETS_PITCH={ list:[

// =============================================================================================
// BASS (bassline, low slot). Root on the downbeat with the kick, movement on the "and"s. Chord
// tones only. One bar patterns so every bar re-voices onto its own chord.
// =============================================================================================
{ id:'bass.rolling', inst:'bass', name:'Rolling', style:'dnb', minEnergy:0.15, bars:1, cycleBars:1, register:R_BASS,
  notes:[ {s:0,l:2,ct:0,oct:0,v:1.0}, {s:3,l:1,ct:0,oct:0,v:0.4}, {s:6,l:2,ct:2,oct:0,v:0.7},
          {s:8,l:1,ct:0,oct:0,v:0.7}, {s:10,l:1,ct:1,oct:0,v:0.4}, {s:12,l:2,ct:0,oct:0,v:0.7},
          {s:14,l:2,ct:2,oct:0,v:0.7} ] },

{ id:'bass.dusty', inst:'bass', name:'Dusty walk', style:'hiphop', minEnergy:0.15, bars:1, cycleBars:1, register:R_BASS,
  notes:[ {s:0,l:4,ct:0,oct:0,v:1.0}, {s:6,l:2,ct:2,oct:0,v:0.7}, {s:10,l:3,ct:0,oct:0,v:0.7},
          {s:14,l:2,ct:1,oct:0,v:0.4} ] },

{ id:'bass.pump', inst:'bass', name:'Octave pump', style:'house', minEnergy:0.2, bars:1, cycleBars:1, register:R_BASS,
  notes:[ {s:0,l:1,ct:0,oct:0,v:1.0}, {s:2,l:1,ct:0,oct:1,v:0.7}, {s:4,l:1,ct:0,oct:0,v:0.7},
          {s:6,l:1,ct:0,oct:1,v:0.7}, {s:8,l:1,ct:0,oct:0,v:0.7}, {s:10,l:1,ct:0,oct:1,v:0.4},
          {s:12,l:1,ct:2,oct:0,v:0.7}, {s:14,l:1,ct:0,oct:1,v:0.7} ] },

{ id:'bass.driver', inst:'bass', name:'Driver', style:'techno', minEnergy:0.2, bars:1, cycleBars:1, register:R_BASS,
  notes:[ {s:0,l:2,ct:0,oct:0,v:1.0}, {s:3,l:1,ct:0,oct:0,v:0.7}, {s:4,l:1,ct:0,oct:0,v:0.4},
          {s:7,l:1,ct:0,oct:0,v:0.7}, {s:8,l:2,ct:0,oct:0,v:0.7}, {s:11,l:1,ct:0,oct:0,v:0.7},
          {s:12,l:2,ct:2,oct:0,v:0.7}, {s:15,l:1,ct:0,oct:0,v:0.4} ] },

{ id:'bass.slider', inst:'bass', name:'Slider', style:'trap', minEnergy:0.1, bars:1, cycleBars:1, register:R_BASS,
  notes:[ {s:0,l:8,ct:0,oct:0,v:1.0}, {s:8,l:4,ct:2,oct:0,v:0.7}, {s:12,l:4,ct:1,oct:0,v:0.7} ] },

{ id:'bass.funk', inst:'bass', name:'Funk stab', style:'breakbeat', minEnergy:0.2, bars:1, cycleBars:1, register:R_BASS,
  notes:[ {s:0,l:1,ct:0,oct:0,v:1.0}, {s:2,l:1,ct:2,oct:0,v:0.4}, {s:3,l:1,ct:0,oct:0,v:0.7},
          {s:6,l:2,ct:1,oct:0,v:0.7}, {s:8,l:1,ct:0,oct:0,v:0.7}, {s:11,l:1,ct:2,oct:0,v:0.4},
          {s:14,l:2,ct:0,oct:1,v:0.7} ] },

{ id:'bass.anchor', inst:'bass', name:'Anchor', style:'halftime', minEnergy:0.1, bars:1, cycleBars:1, register:R_BASS,
  notes:[ {s:0,l:6,ct:0,oct:0,v:1.0}, {s:8,l:2,ct:0,oct:0,v:0.7}, {s:12,l:4,ct:2,oct:0,v:0.7} ] },

{ id:'bass.wobble', inst:'bass', name:'Wobble', style:'dubstep', minEnergy:0.2, bars:1, cycleBars:1, register:R_BASS,
  notes:[ {s:0,l:3,ct:0,oct:0,v:1.0}, {s:6,l:2,ct:0,oct:0,v:0.7}, {s:10,l:2,ct:2,oct:0,v:0.7},
          {s:12,l:1,ct:0,oct:0,v:0.4}, {s:14,l:2,ct:0,oct:0,v:0.7} ] },

{ id:'bass.drift', inst:'bass', name:'Drift', style:'ambient', minEnergy:0.1, bars:2, cycleBars:1, register:R_BASS,
  notes:[ {s:0,l:16,ct:0,oct:0,v:0.7}, {s:16,l:16,ct:2,oct:0,v:0.4} ] },

{ id:'bass.fragment', inst:'bass', name:'Fragment', style:'abstract', minEnergy:0.15, bars:1, cycleBars:1, register:R_BASS,
  notes:[ {s:0,l:2,ct:0,oct:0,v:1.0}, {s:5,l:1,ct:3,oct:0,v:0.7}, {s:7,l:2,ct:2,oct:0,v:0.4},
          {s:13,l:3,ct:0,oct:0,v:0.7} ] },

// =============================================================================================
// SUB (subsynth, sine, sub slot). Roots and fifths held long. The sub never plays a third: it is
// the one voice below the crossover and a third down there is mud.
// =============================================================================================
{ id:'sub.pillar', inst:'sub', name:'Pillar', style:'dnb', minEnergy:0.1, bars:1, cycleBars:1, register:R_SUB,
  notes:[ {s:0,l:12,ct:0,oct:0,v:1.0}, {s:12,l:4,ct:2,oct:0,v:0.7} ] },

{ id:'sub.weight', inst:'sub', name:'Weight', style:'hiphop', minEnergy:0.1, bars:1, cycleBars:1, register:R_SUB,
  notes:[ {s:0,l:8,ct:0,oct:0,v:1.0}, {s:10,l:4,ct:0,oct:0,v:0.7} ] },

{ id:'sub.floor', inst:'sub', name:'Floor', style:'house', minEnergy:0.1, bars:1, cycleBars:1, register:R_SUB,
  notes:[ {s:0,l:4,ct:0,oct:0,v:1.0}, {s:4,l:4,ct:0,oct:0,v:0.7}, {s:8,l:4,ct:0,oct:0,v:0.7},
          {s:12,l:4,ct:2,oct:0,v:0.7} ] },

{ id:'sub.hum', inst:'sub', name:'Hum', style:'techno', minEnergy:0.1, bars:1, cycleBars:1, register:R_SUB,
  notes:[ {s:0,l:16,ct:0,oct:0,v:0.7} ] },

{ id:'sub.drop', inst:'sub', name:'Drop', style:'trap', minEnergy:0.1, bars:1, cycleBars:1, register:R_SUB,
  notes:[ {s:0,l:10,ct:0,oct:0,v:1.0}, {s:10,l:6,ct:2,oct:0,v:0.7} ] },

{ id:'sub.step', inst:'sub', name:'Step', style:'breakbeat', minEnergy:0.15, bars:1, cycleBars:1, register:R_SUB,
  notes:[ {s:0,l:3,ct:0,oct:0,v:1.0}, {s:6,l:2,ct:0,oct:0,v:0.7}, {s:8,l:4,ct:2,oct:0,v:0.7},
          {s:14,l:2,ct:0,oct:0,v:0.4} ] },

{ id:'sub.slab', inst:'sub', name:'Slab', style:'halftime', minEnergy:0.1, bars:1, cycleBars:1, register:R_SUB,
  notes:[ {s:0,l:8,ct:0,oct:0,v:1.0}, {s:8,l:8,ct:2,oct:0,v:0.7} ] },

{ id:'sub.swell', inst:'sub', name:'Swell', style:'dubstep', minEnergy:0.1, bars:1, cycleBars:1, register:R_SUB,
  notes:[ {s:0,l:6,ct:0,oct:0,v:1.0}, {s:8,l:8,ct:0,oct:0,v:0.7} ] },

{ id:'sub.deep', inst:'sub', name:'Deep', style:'ambient', minEnergy:0.1, bars:2, cycleBars:1, register:R_SUB,
  notes:[ {s:0,l:32,ct:0,oct:0,v:0.7} ] },

{ id:'sub.pulse', inst:'sub', name:'Pulse', style:'abstract', minEnergy:0.1, bars:1, cycleBars:1, register:R_SUB,
  notes:[ {s:0,l:4,ct:0,oct:0,v:1.0}, {s:7,l:2,ct:2,oct:0,v:0.4}, {s:11,l:5,ct:0,oct:0,v:0.7} ] },

// =============================================================================================
// PAD (padsynth, mid-low slot). Sustained voicings, one bar so each chord gets its own voicing.
// Root is often left out: the bass already owns it and the pad sits better above it.
// =============================================================================================
{ id:'pad.warm', inst:'pad', name:'Warm bed', style:'house', minEnergy:0.15, bars:1, cycleBars:1, register:R_PAD,
  notes:[ {s:0,l:16,ct:0,oct:0,v:0.7}, {s:0,l:16,ct:1,oct:0,v:0.7}, {s:0,l:16,ct:2,oct:0,v:0.4} ] },

{ id:'pad.haze', inst:'pad', name:'Haze', style:'ambient', minEnergy:0.1, bars:2, cycleBars:1, register:R_PAD,
  notes:[ {s:0,l:32,ct:0,oct:0,v:0.7}, {s:0,l:32,ct:2,oct:0,v:0.4}, {s:16,l:16,ct:1,oct:1,v:0.4} ] },

{ id:'pad.breath', inst:'pad', name:'Breath', style:'dnb', minEnergy:0.15, bars:1, cycleBars:1, register:R_PAD,
  notes:[ {s:0,l:14,ct:0,oct:0,v:0.7}, {s:0,l:14,ct:2,oct:0,v:0.4}, {s:8,l:8,ct:1,oct:1,v:0.4} ] },

{ id:'pad.dust', inst:'pad', name:'Dust', style:'hiphop', minEnergy:0.15, bars:1, cycleBars:1, register:R_PAD,
  notes:[ {s:0,l:16,ct:1,oct:0,v:0.7}, {s:0,l:16,ct:2,oct:0,v:0.4}, {s:0,l:16,ct:3,oct:0,v:0.4} ] },

{ id:'pad.drone', inst:'pad', name:'Drone', style:'techno', minEnergy:0.15, bars:1, cycleBars:1, register:R_PAD,
  notes:[ {s:0,l:16,ct:0,oct:0,v:0.7}, {s:0,l:16,ct:2,oct:0,v:0.4} ] },

{ id:'pad.fog', inst:'pad', name:'Fog', style:'trap', minEnergy:0.15, bars:1, cycleBars:1, register:R_PAD,
  notes:[ {s:0,l:12,ct:0,oct:0,v:0.7}, {s:0,l:12,ct:1,oct:0,v:0.4}, {s:12,l:4,ct:2,oct:1,v:0.4} ] },

{ id:'pad.lift', inst:'pad', name:'Lift', style:'breakbeat', minEnergy:0.2, bars:1, cycleBars:1, register:R_PAD,
  notes:[ {s:0,l:8,ct:0,oct:0,v:0.7}, {s:0,l:8,ct:2,oct:0,v:0.4}, {s:8,l:8,ct:1,oct:0,v:0.7},
          {s:8,l:8,ct:3,oct:0,v:0.4} ] },

{ id:'pad.slab', inst:'pad', name:'Slab', style:'halftime', minEnergy:0.15, bars:1, cycleBars:1, register:R_PAD,
  notes:[ {s:0,l:16,ct:0,oct:0,v:0.7}, {s:0,l:16,ct:1,oct:0,v:0.7}, {s:0,l:16,ct:2,oct:1,v:0.4} ] },

{ id:'pad.wash', inst:'pad', name:'Wash', style:'dubstep', minEnergy:0.15, bars:1, cycleBars:1, register:R_PAD,
  notes:[ {s:0,l:16,ct:2,oct:0,v:0.7}, {s:0,l:16,ct:3,oct:0,v:0.4}, {s:0,l:16,ct:0,oct:1,v:0.4} ] },

{ id:'pad.smear', inst:'pad', name:'Smear', style:'abstract', minEnergy:0.1, bars:2, cycleBars:1, register:R_PAD,
  notes:[ {s:0,l:20,ct:0,oct:0,v:0.7}, {s:4,l:16,ct:3,oct:0,v:0.4}, {s:20,l:12,ct:1,oct:1,v:0.4} ] },

// =============================================================================================
// CHORDS (padsynth, short attack and release, mid-low slot). Rhythmic stabs. Every stab is the
// full triad so the harmony reads even when the pad is off.
// =============================================================================================
{ id:'chords.skank', inst:'chords', name:'Skank', style:'house', minEnergy:0.3, bars:1, cycleBars:1, register:R_CHORDS,
  notes:[ {s:0,l:2,ct:0,oct:0,v:0.7}, {s:0,l:2,ct:1,oct:0,v:0.7}, {s:0,l:2,ct:2,oct:0,v:0.7},
          {s:6,l:2,ct:0,oct:0,v:0.7}, {s:6,l:2,ct:1,oct:0,v:0.7}, {s:6,l:2,ct:2,oct:0,v:0.7},
          {s:10,l:2,ct:0,oct:0,v:0.4}, {s:10,l:2,ct:1,oct:0,v:0.4}, {s:10,l:2,ct:2,oct:0,v:0.4},
          {s:14,l:2,ct:0,oct:0,v:0.7}, {s:14,l:2,ct:1,oct:0,v:0.7}, {s:14,l:2,ct:2,oct:0,v:0.7} ] },

{ id:'chords.chop', inst:'chords', name:'Chop', style:'dnb', minEnergy:0.35, bars:1, cycleBars:1, register:R_CHORDS,
  notes:[ {s:0,l:2,ct:0,oct:0,v:1.0}, {s:0,l:2,ct:1,oct:0,v:1.0}, {s:0,l:2,ct:2,oct:0,v:0.7},
          {s:7,l:1,ct:0,oct:0,v:0.4}, {s:7,l:1,ct:1,oct:0,v:0.4}, {s:7,l:1,ct:2,oct:0,v:0.4},
          {s:10,l:3,ct:0,oct:0,v:0.7}, {s:10,l:3,ct:1,oct:0,v:0.7}, {s:10,l:3,ct:2,oct:0,v:0.7} ] },

{ id:'chords.dust', inst:'chords', name:'Dusty stab', style:'hiphop', minEnergy:0.3, bars:1, cycleBars:1, register:R_CHORDS,
  notes:[ {s:0,l:3,ct:0,oct:0,v:0.7}, {s:0,l:3,ct:1,oct:0,v:0.7}, {s:0,l:3,ct:3,oct:0,v:0.4},
          {s:6,l:2,ct:1,oct:0,v:0.4}, {s:6,l:2,ct:2,oct:0,v:0.4},
          {s:11,l:4,ct:0,oct:0,v:0.7}, {s:11,l:4,ct:2,oct:0,v:0.7}, {s:11,l:4,ct:3,oct:0,v:0.4} ] },

{ id:'chords.tick', inst:'chords', name:'Tick', style:'techno', minEnergy:0.35, bars:1, cycleBars:1, register:R_CHORDS,
  notes:[ {s:0,l:1,ct:0,oct:0,v:0.7}, {s:0,l:1,ct:1,oct:0,v:0.7}, {s:0,l:1,ct:2,oct:0,v:0.7},
          {s:4,l:1,ct:0,oct:0,v:0.4}, {s:4,l:1,ct:1,oct:0,v:0.4}, {s:4,l:1,ct:2,oct:0,v:0.4},
          {s:8,l:1,ct:0,oct:0,v:0.7}, {s:8,l:1,ct:1,oct:0,v:0.7}, {s:8,l:1,ct:2,oct:0,v:0.7},
          {s:12,l:1,ct:0,oct:0,v:0.4}, {s:12,l:1,ct:1,oct:0,v:0.4}, {s:12,l:1,ct:2,oct:0,v:0.4} ] },

{ id:'chords.bell', inst:'chords', name:'Bell stab', style:'trap', minEnergy:0.3, bars:1, cycleBars:1, register:R_CHORDS,
  notes:[ {s:0,l:4,ct:0,oct:0,v:0.7}, {s:0,l:4,ct:1,oct:0,v:0.7}, {s:0,l:4,ct:2,oct:0,v:0.4},
          {s:8,l:2,ct:1,oct:0,v:0.4}, {s:8,l:2,ct:2,oct:0,v:0.4},
          {s:12,l:4,ct:0,oct:0,v:0.7}, {s:12,l:4,ct:2,oct:0,v:0.7} ] },

{ id:'chords.push', inst:'chords', name:'Push', style:'breakbeat', minEnergy:0.35, bars:1, cycleBars:1, register:R_CHORDS,
  notes:[ {s:0,l:2,ct:0,oct:0,v:1.0}, {s:0,l:2,ct:1,oct:0,v:1.0}, {s:0,l:2,ct:2,oct:0,v:0.7},
          {s:3,l:1,ct:0,oct:0,v:0.4}, {s:3,l:1,ct:2,oct:0,v:0.4},
          {s:8,l:2,ct:0,oct:0,v:0.7}, {s:8,l:2,ct:1,oct:0,v:0.7}, {s:8,l:2,ct:2,oct:0,v:0.7},
          {s:13,l:3,ct:1,oct:0,v:0.7}, {s:13,l:3,ct:2,oct:0,v:0.7} ] },

{ id:'chords.hold', inst:'chords', name:'Hold', style:'halftime', minEnergy:0.25, bars:1, cycleBars:1, register:R_CHORDS,
  notes:[ {s:0,l:8,ct:0,oct:0,v:0.7}, {s:0,l:8,ct:1,oct:0,v:0.7}, {s:0,l:8,ct:2,oct:0,v:0.4},
          {s:10,l:6,ct:1,oct:0,v:0.7}, {s:10,l:6,ct:2,oct:0,v:0.7}, {s:10,l:6,ct:3,oct:0,v:0.4} ] },

{ id:'chords.grind', inst:'chords', name:'Grind', style:'dubstep', minEnergy:0.35, bars:1, cycleBars:1, register:R_CHORDS,
  notes:[ {s:0,l:2,ct:0,oct:0,v:1.0}, {s:0,l:2,ct:2,oct:0,v:1.0}, {s:0,l:2,ct:3,oct:0,v:0.7},
          {s:6,l:2,ct:0,oct:0,v:0.7}, {s:6,l:2,ct:2,oct:0,v:0.7},
          {s:8,l:2,ct:1,oct:0,v:0.4}, {s:8,l:2,ct:2,oct:0,v:0.4},
          {s:14,l:2,ct:0,oct:0,v:0.7}, {s:14,l:2,ct:2,oct:0,v:0.7} ] },

{ id:'chords.glass', inst:'chords', name:'Glass', style:'ambient', minEnergy:0.15, bars:1, cycleBars:1, register:R_CHORDS,
  notes:[ {s:0,l:16,ct:1,oct:0,v:0.4}, {s:0,l:16,ct:2,oct:0,v:0.4}, {s:0,l:16,ct:3,oct:0,v:0.4} ] },

{ id:'chords.shard', inst:'chords', name:'Shard', style:'abstract', minEnergy:0.3, bars:1, cycleBars:1, register:R_CHORDS,
  notes:[ {s:0,l:1,ct:0,oct:0,v:0.7}, {s:0,l:1,ct:3,oct:0,v:0.7},
          {s:5,l:2,ct:1,oct:0,v:0.4}, {s:5,l:2,ct:2,oct:0,v:0.4},
          {s:9,l:1,ct:0,oct:1,v:0.7}, {s:9,l:1,ct:2,oct:0,v:0.7},
          {s:14,l:1,ct:3,oct:0,v:0.4}, {s:14,l:1,ct:1,oct:0,v:0.4} ] },

// =============================================================================================
// KEYS (fmsynth, mid slot). Riffs: a line you could hum, chord tones only so it never argues with
// the bass through a chord change. Octave jumps do the work a scale run would do.
// =============================================================================================
{ id:'keys.riff', inst:'keys', name:'Riff', style:'hiphop', minEnergy:0.35, bars:1, cycleBars:1, register:R_KEYS,
  notes:[ {s:0,l:2,ct:0,oct:0,v:1.0}, {s:3,l:1,ct:2,oct:0,v:0.4}, {s:6,l:2,ct:1,oct:0,v:0.7},
          {s:8,l:2,ct:0,oct:1,v:0.7}, {s:11,l:2,ct:2,oct:0,v:0.4}, {s:14,l:2,ct:1,oct:0,v:0.7} ] },

{ id:'keys.roll', inst:'keys', name:'Roll', style:'dnb', minEnergy:0.4, bars:1, cycleBars:1, register:R_KEYS,
  notes:[ {s:0,l:1,ct:0,oct:0,v:1.0}, {s:2,l:1,ct:2,oct:0,v:0.4}, {s:4,l:1,ct:1,oct:1,v:0.7},
          {s:6,l:2,ct:0,oct:1,v:0.7}, {s:10,l:2,ct:2,oct:0,v:0.4}, {s:12,l:3,ct:1,oct:0,v:0.7} ] },

{ id:'keys.chime', inst:'keys', name:'Chime', style:'house', minEnergy:0.35, bars:1, cycleBars:1, register:R_KEYS,
  notes:[ {s:0,l:2,ct:2,oct:0,v:0.7}, {s:4,l:2,ct:0,oct:1,v:0.7}, {s:8,l:2,ct:1,oct:1,v:0.4},
          {s:12,l:4,ct:2,oct:0,v:0.7} ] },

{ id:'keys.pip', inst:'keys', name:'Pip', style:'techno', minEnergy:0.4, bars:1, cycleBars:1, register:R_KEYS,
  notes:[ {s:0,l:1,ct:0,oct:0,v:0.7}, {s:6,l:1,ct:2,oct:0,v:0.4}, {s:8,l:1,ct:0,oct:1,v:0.7},
          {s:14,l:2,ct:1,oct:0,v:0.4} ] },

{ id:'keys.trill', inst:'keys', name:'Trill', style:'trap', minEnergy:0.4, bars:1, cycleBars:1, register:R_KEYS,
  notes:[ {s:0,l:1,ct:0,oct:1,v:1.0}, {s:1,l:1,ct:1,oct:1,v:0.4}, {s:2,l:1,ct:2,oct:1,v:0.7},
          {s:8,l:2,ct:0,oct:1,v:0.7}, {s:12,l:1,ct:2,oct:0,v:0.4}, {s:13,l:3,ct:1,oct:0,v:0.7} ] },

{ id:'keys.bounce', inst:'keys', name:'Bounce', style:'breakbeat', minEnergy:0.4, bars:1, cycleBars:1, register:R_KEYS,
  notes:[ {s:0,l:2,ct:0,oct:0,v:1.0}, {s:5,l:1,ct:1,oct:0,v:0.4}, {s:7,l:2,ct:2,oct:0,v:0.7},
          {s:10,l:2,ct:0,oct:1,v:0.7}, {s:14,l:2,ct:1,oct:0,v:0.4} ] },

{ id:'keys.toll', inst:'keys', name:'Toll', style:'halftime', minEnergy:0.3, bars:1, cycleBars:1, register:R_KEYS,
  notes:[ {s:0,l:6,ct:0,oct:0,v:1.0}, {s:8,l:4,ct:2,oct:0,v:0.7}, {s:13,l:3,ct:1,oct:1,v:0.7} ] },

{ id:'keys.grit', inst:'keys', name:'Grit', style:'dubstep', minEnergy:0.4, bars:1, cycleBars:1, register:R_KEYS,
  notes:[ {s:0,l:2,ct:0,oct:0,v:1.0}, {s:4,l:2,ct:3,oct:0,v:0.7}, {s:8,l:1,ct:2,oct:0,v:0.4},
          {s:11,l:2,ct:0,oct:1,v:0.7}, {s:14,l:2,ct:1,oct:0,v:0.4} ] },

{ id:'keys.drops', inst:'keys', name:'Drops', style:'ambient', minEnergy:0.2, bars:2, cycleBars:1, register:R_KEYS,
  notes:[ {s:0,l:6,ct:2,oct:0,v:0.4}, {s:10,l:6,ct:1,oct:1,v:0.4}, {s:20,l:8,ct:0,oct:1,v:0.7},
          {s:28,l:4,ct:3,oct:0,v:0.4} ] },

{ id:'keys.scatter', inst:'keys', name:'Scatter', style:'abstract', minEnergy:0.35, bars:1, cycleBars:1, register:R_KEYS,
  notes:[ {s:0,l:1,ct:0,oct:0,v:0.7}, {s:3,l:2,ct:3,oct:0,v:0.4}, {s:9,l:1,ct:1,oct:1,v:0.7},
          {s:13,l:2,ct:2,oct:0,v:0.4} ] },

// =============================================================================================
// LEAD (subsynth saw, high slot). Short hooks with holes in them: two bars so the hook has a
// question and an answer, and long gaps so the drums and bass stay audible. Scale degrees are
// allowed here, which is what lets a lead pull against the chord instead of sitting inside it.
// =============================================================================================
{ id:'lead.hook', inst:'lead', name:'Hook', style:'house', minEnergy:0.5, bars:2, cycleBars:1, register:R_LEAD,
  notes:[ {s:0,l:3,ct:0,oct:0,v:1.0}, {s:4,l:2,deg:7,oct:0,v:0.4}, {s:8,l:4,ct:2,oct:0,v:0.7},
          {s:20,l:2,ct:1,oct:0,v:0.7}, {s:24,l:6,ct:0,oct:0,v:0.7} ] },

{ id:'lead.call', inst:'lead', name:'Call', style:'dnb', minEnergy:0.5, bars:2, cycleBars:1, register:R_LEAD,
  notes:[ {s:0,l:2,ct:0,oct:0,v:1.0}, {s:6,l:2,deg:5,oct:0,v:0.4}, {s:8,l:4,ct:2,oct:0,v:0.7},
          {s:18,l:2,deg:4,oct:0,v:0.7}, {s:22,l:6,ct:0,oct:0,v:0.7} ] },

{ id:'lead.tale', inst:'lead', name:'Tale', style:'hiphop', minEnergy:0.45, bars:2, cycleBars:1, register:R_LEAD,
  notes:[ {s:0,l:4,ct:2,oct:0,v:0.7}, {s:6,l:2,deg:5,oct:0,v:0.4}, {s:10,l:4,ct:1,oct:0,v:0.7},
          {s:16,l:2,ct:0,oct:0,v:1.0}, {s:22,l:8,deg:7,oct:0,v:0.7} ] },

{ id:'lead.blade', inst:'lead', name:'Blade', style:'techno', minEnergy:0.55, bars:2, cycleBars:1, register:R_LEAD,
  notes:[ {s:0,l:2,ct:0,oct:0,v:1.0}, {s:8,l:2,ct:0,oct:0,v:0.4}, {s:16,l:2,ct:2,oct:0,v:0.7},
          {s:24,l:4,deg:7,oct:0,v:0.7} ] },

{ id:'lead.cry', inst:'lead', name:'Cry', style:'trap', minEnergy:0.5, bars:2, cycleBars:1, register:R_LEAD,
  notes:[ {s:0,l:3,deg:1,oct:0,v:1.0}, {s:6,l:3,deg:3,oct:0,v:0.7}, {s:12,l:4,deg:2,oct:0,v:0.4},
          {s:20,l:8,deg:1,oct:0,v:0.7} ] },

{ id:'lead.skip', inst:'lead', name:'Skip', style:'breakbeat', minEnergy:0.5, bars:2, cycleBars:1, register:R_LEAD,
  notes:[ {s:0,l:2,ct:0,oct:0,v:1.0}, {s:3,l:1,deg:7,oct:0,v:0.4}, {s:6,l:2,ct:2,oct:0,v:0.7},
          {s:12,l:2,ct:1,oct:0,v:0.7}, {s:19,l:3,deg:5,oct:0,v:0.4}, {s:26,l:4,ct:0,oct:0,v:0.7} ] },

{ id:'lead.horn', inst:'lead', name:'Horn', style:'halftime', minEnergy:0.45, bars:2, cycleBars:1, register:R_LEAD,
  notes:[ {s:0,l:6,ct:0,oct:0,v:1.0}, {s:10,l:4,ct:2,oct:0,v:0.7}, {s:20,l:10,deg:7,oct:0,v:0.7} ] },

{ id:'lead.snarl', inst:'lead', name:'Snarl', style:'dubstep', minEnergy:0.55, bars:2, cycleBars:1, register:R_LEAD,
  notes:[ {s:0,l:4,ct:0,oct:0,v:1.0}, {s:6,l:2,ct:3,oct:0,v:0.4}, {s:12,l:3,ct:2,oct:0,v:0.7},
          {s:22,l:6,deg:5,oct:0,v:0.7} ] },

{ id:'lead.thread', inst:'lead', name:'Thread', style:'ambient', minEnergy:0.25, bars:4, cycleBars:1, register:R_LEAD,
  notes:[ {s:0,l:8,deg:1,oct:0,v:0.4}, {s:16,l:10,deg:5,oct:0,v:0.4}, {s:36,l:12,deg:3,oct:0,v:0.7},
          {s:56,l:8,deg:2,oct:0,v:0.4} ] },

{ id:'lead.stutter', inst:'lead', name:'Stutter', style:'abstract', minEnergy:0.45, bars:2, cycleBars:1, register:R_LEAD,
  notes:[ {s:0,l:1,ct:0,oct:0,v:1.0}, {s:2,l:1,ct:0,oct:0,v:0.4}, {s:7,l:2,deg:6,oct:0,v:0.7},
          {s:15,l:1,ct:2,oct:0,v:0.4}, {s:21,l:3,deg:4,oct:0,v:0.7}, {s:29,l:2,ct:1,oct:0,v:0.4} ] },

// =============================================================================================
// ARP (subsynth pluck, high slot). Cycles through the chord tones on a fixed grid, so the arp is
// the voice that spells out the chord change. Short notes, no overlap, accent on each downbeat.
// =============================================================================================
{ id:'arp.up', inst:'arp', name:'Up', style:'house', minEnergy:0.35, bars:1, cycleBars:1, register:R_ARP,
  notes:[ {s:0,l:1,ct:0,oct:0,v:1.0}, {s:2,l:1,ct:1,oct:0,v:0.7}, {s:4,l:1,ct:2,oct:0,v:0.7},
          {s:6,l:1,ct:0,oct:1,v:0.7}, {s:8,l:1,ct:1,oct:1,v:0.7}, {s:10,l:1,ct:2,oct:1,v:0.4},
          {s:12,l:1,ct:0,oct:1,v:0.7}, {s:14,l:1,ct:2,oct:0,v:0.4} ] },

{ id:'arp.roll', inst:'arp', name:'Roll', style:'dnb', minEnergy:0.45, bars:1, cycleBars:1, register:R_ARP,
  notes:[ {s:0,l:1,ct:0,oct:0,v:1.0}, {s:1,l:1,ct:1,oct:0,v:0.4}, {s:2,l:1,ct:2,oct:0,v:0.7},
          {s:3,l:1,ct:0,oct:1,v:0.4}, {s:4,l:1,ct:1,oct:1,v:0.7}, {s:5,l:1,ct:2,oct:1,v:0.4},
          {s:6,l:1,ct:0,oct:1,v:0.7}, {s:7,l:1,ct:2,oct:0,v:0.4}, {s:8,l:1,ct:0,oct:0,v:0.7},
          {s:9,l:1,ct:1,oct:0,v:0.4}, {s:10,l:1,ct:2,oct:0,v:0.7}, {s:11,l:1,ct:0,oct:1,v:0.4},
          {s:12,l:1,ct:1,oct:1,v:0.7}, {s:13,l:1,ct:2,oct:1,v:0.4}, {s:14,l:1,ct:2,oct:0,v:0.7},
          {s:15,l:1,ct:1,oct:0,v:0.4} ] },

{ id:'arp.tick', inst:'arp', name:'Tick', style:'techno', minEnergy:0.4, bars:1, cycleBars:1, register:R_ARP,
  notes:[ {s:0,l:1,ct:0,oct:0,v:1.0}, {s:1,l:1,ct:2,oct:0,v:0.4}, {s:2,l:1,ct:1,oct:0,v:0.7},
          {s:3,l:1,ct:2,oct:0,v:0.4}, {s:4,l:1,ct:0,oct:0,v:0.7}, {s:5,l:1,ct:2,oct:0,v:0.4},
          {s:6,l:1,ct:1,oct:1,v:0.7}, {s:7,l:1,ct:2,oct:0,v:0.4}, {s:8,l:1,ct:0,oct:0,v:0.7},
          {s:9,l:1,ct:2,oct:0,v:0.4}, {s:10,l:1,ct:1,oct:0,v:0.7}, {s:11,l:1,ct:2,oct:0,v:0.4},
          {s:12,l:1,ct:0,oct:0,v:0.7}, {s:13,l:1,ct:2,oct:0,v:0.4}, {s:14,l:1,ct:1,oct:1,v:0.7},
          {s:15,l:1,ct:2,oct:0,v:0.4} ] },

{ id:'arp.skitter', inst:'arp', name:'Skitter', style:'trap', minEnergy:0.4, bars:1, cycleBars:1, register:R_ARP,
  notes:[ {s:0,l:1,ct:0,oct:0,v:1.0}, {s:3,l:1,ct:1,oct:0,v:0.7}, {s:6,l:1,ct:2,oct:0,v:0.7},
          {s:9,l:1,ct:0,oct:1,v:0.7}, {s:12,l:1,ct:2,oct:0,v:0.4}, {s:14,l:1,ct:1,oct:0,v:0.4} ] },

{ id:'arp.bounce', inst:'arp', name:'Bounce', style:'breakbeat', minEnergy:0.4, bars:1, cycleBars:1, register:R_ARP,
  notes:[ {s:0,l:1,ct:0,oct:0,v:1.0}, {s:2,l:1,ct:2,oct:0,v:0.7}, {s:3,l:1,ct:1,oct:0,v:0.4},
          {s:6,l:1,ct:0,oct:1,v:0.7}, {s:8,l:1,ct:2,oct:0,v:0.7}, {s:10,l:1,ct:1,oct:0,v:0.4},
          {s:11,l:1,ct:0,oct:1,v:0.7}, {s:14,l:1,ct:2,oct:0,v:0.4} ] },

{ id:'arp.dust', inst:'arp', name:'Dust', style:'hiphop', minEnergy:0.35, bars:1, cycleBars:1, register:R_ARP,
  notes:[ {s:0,l:1,ct:0,oct:0,v:1.0}, {s:2,l:1,ct:2,oct:0,v:0.4}, {s:5,l:1,ct:1,oct:0,v:0.7},
          {s:7,l:1,ct:2,oct:0,v:0.4}, {s:10,l:1,ct:0,oct:1,v:0.7}, {s:12,l:1,ct:2,oct:0,v:0.7},
          {s:15,l:1,ct:1,oct:0,v:0.4} ] },

{ id:'arp.stride', inst:'arp', name:'Stride', style:'halftime', minEnergy:0.35, bars:2, cycleBars:1, register:R_ARP,
  notes:[ {s:0,l:2,ct:0,oct:0,v:1.0}, {s:4,l:2,ct:2,oct:0,v:0.7}, {s:8,l:2,ct:1,oct:0,v:0.7},
          {s:12,l:2,ct:2,oct:0,v:0.4}, {s:16,l:2,ct:0,oct:1,v:1.0}, {s:20,l:2,ct:2,oct:0,v:0.7},
          {s:24,l:2,ct:1,oct:0,v:0.7}, {s:28,l:2,ct:0,oct:0,v:0.4} ] },

{ id:'arp.chop', inst:'arp', name:'Chop', style:'dubstep', minEnergy:0.45, bars:1, cycleBars:1, register:R_ARP,
  notes:[ {s:0,l:1,ct:0,oct:0,v:1.0}, {s:2,l:1,ct:0,oct:0,v:0.4}, {s:4,l:1,ct:2,oct:0,v:0.7},
          {s:6,l:1,ct:1,oct:0,v:0.7}, {s:10,l:1,ct:2,oct:0,v:0.4}, {s:12,l:1,ct:0,oct:1,v:0.7},
          {s:14,l:1,ct:1,oct:0,v:0.4} ] },

{ id:'arp.glass', inst:'arp', name:'Glass', style:'ambient', minEnergy:0.2, bars:2, cycleBars:1, register:R_ARP,
  notes:[ {s:0,l:4,ct:0,oct:0,v:0.7}, {s:6,l:4,ct:2,oct:0,v:0.4}, {s:12,l:4,ct:1,oct:0,v:0.4},
          {s:18,l:4,ct:2,oct:1,v:0.4}, {s:24,l:4,ct:0,oct:1,v:0.7}, {s:30,l:2,ct:1,oct:0,v:0.4} ] },

{ id:'arp.jitter', inst:'arp', name:'Jitter', style:'abstract', minEnergy:0.4, bars:1, cycleBars:1, register:R_ARP,
  notes:[ {s:0,l:1,ct:0,oct:0,v:1.0}, {s:1,l:1,ct:2,oct:0,v:0.4}, {s:4,l:1,ct:3,oct:0,v:0.7},
          {s:7,l:1,ct:1,oct:0,v:0.4}, {s:8,l:1,ct:0,oct:1,v:0.7}, {s:11,l:1,ct:2,oct:0,v:0.4},
          {s:13,l:1,ct:3,oct:0,v:0.7}, {s:15,l:1,ct:1,oct:0,v:0.4} ] },

// =============================================================================================
// FX (fmsynth, high index, top slot). Long swells or one big hit. Never a melody: this slot is
// the one that gets automated (cutoff and level ramps) by the transitions, so it stays simple.
// =============================================================================================
{ id:'fx.riser', inst:'fx', name:'Riser', style:'dnb', minEnergy:0.5, bars:2, cycleBars:1, register:R_FX,
  notes:[ {s:0,l:32,ct:0,oct:0,v:0.7} ] },

{ id:'fx.impact', inst:'fx', name:'Impact', style:'hiphop', minEnergy:0.45, bars:1, cycleBars:1, register:R_FX,
  notes:[ {s:0,l:16,ct:0,oct:0,v:0.7} ] },

{ id:'fx.swell', inst:'fx', name:'Swell', style:'house', minEnergy:0.4, bars:4, cycleBars:1, register:R_FX,
  notes:[ {s:0,l:64,ct:2,oct:0,v:0.4} ] },

{ id:'fx.drone', inst:'fx', name:'Drone', style:'techno', minEnergy:0.4, bars:2, cycleBars:1, register:R_FX,
  notes:[ {s:0,l:32,ct:0,oct:0,v:0.4}, {s:0,l:32,ct:2,oct:0,v:0.4} ] },

{ id:'fx.hit', inst:'fx', name:'Hit', style:'trap', minEnergy:0.5, bars:1, cycleBars:1, register:R_FX,
  notes:[ {s:0,l:8,ct:0,oct:0,v:1.0} ] },

{ id:'fx.sweep', inst:'fx', name:'Sweep', style:'breakbeat', minEnergy:0.45, bars:2, cycleBars:1, register:R_FX,
  notes:[ {s:0,l:24,ct:1,oct:0,v:0.4} ] },

{ id:'fx.boom', inst:'fx', name:'Boom', style:'halftime', minEnergy:0.45, bars:1, cycleBars:1, register:R_FX,
  notes:[ {s:0,l:12,ct:0,oct:0,v:1.0} ] },

{ id:'fx.siren', inst:'fx', name:'Siren', style:'dubstep', minEnergy:0.55, bars:2, cycleBars:1, register:R_FX,
  notes:[ {s:0,l:16,ct:2,oct:0,v:0.7}, {s:16,l:16,ct:3,oct:0,v:0.7} ] },

{ id:'fx.air', inst:'fx', name:'Air', style:'ambient', minEnergy:0.15, bars:4, cycleBars:1, register:R_FX,
  notes:[ {s:0,l:64,ct:1,oct:0,v:0.4}, {s:32,l:32,ct:2,oct:1,v:0.4} ] },

{ id:'fx.blip', inst:'fx', name:'Blip', style:'abstract', minEnergy:0.4, bars:1, cycleBars:1, register:R_FX,
  notes:[ {s:0,l:2,ct:0,oct:0,v:0.7}, {s:9,l:4,ct:3,oct:0,v:0.4} ] }

] };
})();
