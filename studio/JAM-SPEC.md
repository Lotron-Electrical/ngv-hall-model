# Jam: frozen schemas and contracts (2026-09-05)

Repo `C:/Users/Lloyd Gibbs/Claude Projects/ngv-hall-model/`. The approved plan is at
`C:/Users/Lloyd Gibbs/.claude/plans/squishy-weaving-thunder.md`; read it first, then this file,
then `studio/SPEC.md` (the studio's contracts, still in force), then `studio/model.js` (the
timeline and sections are already in it: `Studio.barSteps`, `Studio.timeline`,
`Studio.defaultSection`, `Studio.flattenAutom`, `patternSteps` honours `p.spb`).

House rules for every owner: write ONLY your files; classic scripts adding to `window.Studio`
or `window.NGVShow`, IIFE, `'use strict'`; LF, UTF-8, ASCII only; no em dashes; comments in
plain English in the house style (short, saying why); no dependencies. Do not commit. Anything
you need from another owner's file goes in your report, not in their file. Verify with real
Chrome through Playwright (`PLAYWRIGHT_BROWSERS_PATH=E:\caches\ms-playwright`, `channel:'chrome'`,
`--autoplay-policy=no-user-gesture-required`, playwright at
`C:/Users/Lloyd Gibbs/Claude Projects/godmode-site/node_modules`, see `studio/run-tests.cjs`),
serving the repo with `node tools/serve.js --port <yours>`; kill what you start.

## Owners

| Owner | Files |
| --- | --- |
| ENGINE | `studio/engine.js`, `studio/ui.js` (bar maths only), `studio/test-timeline.html` |
| LIGHTS | `show/lightshow.js` (compositor, `c.trig`, `registerLook`), `studio/lights.js`, `studio/export.js`, `index.html` (guarded show-path edits only), `studio/test-lights.html` |
| LOOKS | `show/looks2.js` (the 12 new painters, registered through `NGVShow.registerLook`) |
| RHYTHM | `studio/presets.drums.js` (`Studio.PRESETS_DRUMS`: 20 templates + `expand`) |
| PITCH | `studio/presets.pitch.js` (`Studio.PRESETS_PITCH`: 80 degree patterns) |
| LXPRESETS | `studio/presets.lights.js` (`Studio.PRESETS_LIGHTS`: 30 light patterns) |
| CORE | `studio/presets.js` (`Studio.PRESETS`: instruments, harmony, render, applyEnergy, transitions, buildSong), `studio/test-presets.html` |
| JAM | `jam.html`, `studio/jam.js`, `studio/jam.css` |

Load order in jam.html: `show/lightshow.js`, `show/looks2.js`, `studio/model.js`, `machines.js`,
`engine.js`, `lights.js`, `export.js`, `presets.drums.js`, `presets.pitch.js`,
`presets.lights.js`, `presets.js`, `jam.js`. studio.html adds `looks2.js` after lightshow.js and
the four preset files before ui.js (JAM owner edits studio.html's script list; nothing else).

## Style guide (pinned, every preset author obeys it)

A minor, root midi 57 (A3). Default chord cycle Am F C G, one chord per bar, 4-bar cycle.
Project tempo 124; dnb and dubstep are written half-time at 124 (snare on 3), never at 174.
Velocities: accent 1.0, normal 0.7, ghost 0.4. Pattern lengths 1, 2 or 4 bars, never 3.
Frequency slots (one instrument per slot in any stack): sub (Sub), low (Bass), mid-low (Pad,
Chords), mid (Keys), high (Lead, Arp), top (FX), drums (Drums), perc (Percussion).
Every pattern must sound on its own at step 0 of bar 1 (the solo audit listens there).
Styles, exactly these ids: `dnb hiphop house techno trap breakbeat halftime dubstep ambient abstract`.

## Instruments (CORE copies this table into `Studio.PRESETS.instruments`)

| id | machine type | name | params (else defaults) | vol | send | slot |
| --- | --- | --- | --- | --- | --- | --- |
| drums | beatbox | Drums | drive 0.15 | 0.85 | reverb 0.05 | drums |
| perc | beatbox | Percussion | kickTune 0.8, kickDecay 0.12, snareTone 0.8, snareDecay 0.09, hatDecay 0.03, tomTune 0.7, drive 0.05 | 0.6 | delay 0.15 | perc |
| bass | bassline | Bass | cutoff 0.35, res 0.55, envmod 0.6, decay 0.25, dist 0.15 | 0.75 | none | low |
| sub | subsynth | Sub | osc1 3 (sine), osc2 3, mix 0, cutoff 0.25, res 0, fenv 0, attack 0.01, decay 0.2, sustain 1, release 0.15, vol 0.8 | 0.8 | none | sub |
| pad | padsynth | Pad | voices 5, spread 18, width 0.7, cutoff 0.4, attack 0.5, release 1.5, lfoAmt 0.25 | 0.5 | reverb 0.35 | mid-low |
| chords | padsynth | Chords | voices 3, spread 10, width 0.4, cutoff 0.55, attack 0.01, release 0.25 | 0.55 | delay 0.2, reverb 0.15 | mid-low |
| keys | fmsynth | Keys | ratio 2, index 3, idecay 0.3, attack 0.005, decay 0.6, sustain 0.3, release 0.5 | 0.55 | reverb 0.2 | mid |
| lead | subsynth | Lead | osc1 1 (saw), osc2 1, mix 0.5, detune 10, oct2 0, cutoff 0.55, res 0.25, fenv 0.4, fdecay 0.25, attack 0.01, decay 0.3, sustain 0.5, release 0.3, glide 0.05 | 0.5 | delay 0.3, reverb 0.2 | high |
| arp | subsynth | Arp | osc1 1, osc2 2, mix 0.4, cutoff 0.6, res 0.3, fenv 0.5, fdecay 0.12, attack 0.002, decay 0.12, sustain 0, release 0.1 | 0.45 | delay 0.35 | high |
| fx | fmsynth | FX | ratio 1.5, index 8, idecay 1.5, attack 0.2, decay 2, sustain 0.6, release 1.5, feedback 0.3 | 0.4 | reverb 0.5 | top |

Sub-synth osc codes: 0 sine? No: `osc1`/`osc2` are 0..3 in `machines.js` (read it: the order there
is authoritative; PITCH and CORE must read `machines.js` and use the code that means sine or saw).

## Pitched preset (PITCH writes 10 per instrument for bass, sub, pad, chords, keys, lead, arp, fx)

```js
Studio.PRESETS_PITCH = { list: [ {
  id:'pad.warm', inst:'pad', name:'Warm bed', style:'house', minEnergy:0.2, bars:4, cycleBars:1,
  register:[48,72],          // midi window the rendered notes are folded into
  notes:[ {s:0, l:16, ct:0, oct:0, v:0.8},     // ct: chord tone 0 root, 1 third, 2 fifth, 3 seventh (or octave if the chord has none)
          {s:0, l:16, ct:1, oct:0, v:0.7},
          {s:12, l:4, deg:5, oct:1, v:0.5} ]   // deg: scale degree 1..7 of the section key; one of ct or deg per note
} ] };
```
`s` and `l` are steps on a 16-step 4/4 bar; the renderer clips notes past the bar end of an odd
meter and repeats the pattern by bars. `cycleBars` = bars per chord (1 or 2). Every instrument
gets one pattern per style, named for its feel (not the style), e.g. "Rolling", "Skank",
"Stabs". Bass and sub are `ct` only. Arp and lead may use `deg`. 80 patterns in total.

## Drum template (RHYTHM writes 10 for drums, 10 for perc, and `expand`)

Meters are groups of steps: `Studio.PRESETS_DRUMS.GROUPS = {'4/4':[4,4,4,4], '3/4':[4,4,4],
'5/4':[4,4,4,4,4], '6/8':[6,6], '7/8':[4,4,6], '12/8':[6,6,6,6]}` and roles per group:
4/4 down up back up-back (i.e. `['down','back','up','back']`), 3/4 `['down','up','back']`,
5/4 `['down','up','back','up','back']`, 6/8 `['down','back']`, 7/8 `['down','up','back']`,
12/8 `['down','back','up','back']`.
```js
{ id:'drums.house', inst:'drums', name:'Four to the floor', style:'house', minEnergy:0.1,
  roles:{ down:[{at:0,n:0,v:1.0}], up:[{at:0,n:0,v:1.0}], back:[{at:0,n:0,v:1.0},{at:0,n:1,v:0.9},{at:0,n:2,v:0.6}] },
  every:{ n:3, div:2, v:0.55, offV:0.35 },      // hats: one every `div` steps in every group at energy 0.5; density moves with energy
  open:{ at:2, n:4, v:0.5, minEnergy:0.6 },     // open hat at step `at` of each group when energy allows
  ghost:[{role:'up',at:2,n:1,v:0.4}],           // extras that appear at energy >= 0.4
  fill:[{fromEnd:4,n:1,v:0.8},{fromEnd:2,n:1,v:0.9},{fromEnd:1,n:5,v:0.9}] }   // last bar only, steps counted back from the bar end
Studio.PRESETS_DRUMS.expand(preset, meter, energy, seed, opts) -> {bars:1, spb, notes:[{s,l:1,n,v}]}
// opts: {fill:true|false, feel:'straight'|'half'|'double'} ; half = drop the 'up' role hits and move 'back' to the last group; double = hats at div/2
```
`n` is the pad index in `Studio.MACHINE_TYPES.beatbox.pads` (0 kick, 1 snare, 2 clap, 3 closed
hat, 4 open hat, 5 tom, 6 rim, 7 crash). Energy rules inside `expand`: hats div 4 below 0.2,
2 below 0.6, 1 above (16ths), rolls in the last group above 0.85; ghosts from 0.4; velocities
scaled `0.55 + 0.45*energy`; the seed (a 32-bit int) drives any choice among equals.

## Light pattern (LXPRESETS writes 30)

```js
Studio.PRESETS_LIGHTS = { list: [ {
  id:'lx.breathe', name:'Breathe', family:'base',       // base | movement | accent | strobe | texture | colour
  style:['ambient','house','hiphop'], energy:[0,0.7],    // where it belongs; the builder picks by style then energy
  bars:4, gain:1, sync:'grid',                            // default sync: 'grid' or an instrument id (drums, bass, ...)
  cues:[ [0,'look','pulse'], [0,'palette','helix'], [32,'palette','ocean'] ],   // [step, kind, value]; kind: look | palette | hit
  level:[ /* 64 entries: null or 0..1, may be omitted */ ]
} ] };
```
Looks available: the 12 in `show/lightshow.js` plus the 12 new ones in `show/looks2.js` (LOOKS
owner): `tide columnglow ripple meteor kickpunch tips bloom columnstrobe lightning twinkle grain
fire palettewalk huechase` (14 names, LOOKS picks the best 12 and reports the final list; LXPRESETS
uses only names that exist: read looks2.js before finishing, and fall back to the 12 originals).
Families and blend: base, movement, texture, colour add; accent adds; strobe uses max.

## Looks (LOOKS)

`NGVShow.registerLook(name, family, description, painter)` is provided by LIGHTS in lightshow.js;
`painter(i,c)` writes `c.r,c.g,c.b` (display gamma 0..1) from `c.s, c.col, c.colx, c.gap, c.pid,
c.t, c.beatN, c.beatPhase, c.barPhase, c.bassS, c.midS, c.highS, c.rmsS, c.strobeN, c.strobeK,
c.trig (0..1, decays after the layer's last trigger), c.A, c.B, c.M, c.tmp`. Until LIGHTS lands,
LOOKS tests against a private shim of `registerLook` that pushes into `NGVShow.LOOKS` and
`NGVShow.PAINT` (LIGHTS exposes both on `window.NGVShow`).

## Section and jam schemas (CORE implements, JAM consumes)

```js
section = { bars:8, energy:0.6, feel:'straight'|'half'|'double', meter:{beats:4,div:4},
  cycle:'neutral'|'dark'|'lift'|'pull'|'bright', transpose:0, transition:'none'|'fill'|'riser'|'drop'|'gap',
  picks:{ drums:'drums.house', perc:null, bass:'bass.rolling', sub:null, pad:'pad.warm', chords:null, keys:null, lead:null, arp:null, fx:null },
  lights:[ {id:'lx.breathe', sync:'grid', gain:1}, {id:'lx.beatwaves', sync:'bass', gain:0.8} ] }
jam = { name, bpm:124, swing:0, humanise:0.3, seed:1, sections:[section, ...] }

Studio.harmony.CYCLES = { neutral:['Am','F','C','G'], dark:['Am','Dm','Em','Am'], lift:['Am','F','G','Em'], pull:['Am','F','E7','E7'], bright:['Am','D','F','G'] }
Studio.harmony.chord(name, key) -> {root, tones:[pc...], quality}    // Am F C G E7 D Dm Em (+ any letter with m / 7 / m7)
Studio.harmony.scale(key) -> [pc...]                                    // minor (natural) by default
Studio.PRESETS.render(preset, ctx) -> pattern {bars, spb, notes, src}   // ctx = {key, chords:[names], cycleBars, transpose, spb, energy, seed}
Studio.PRESETS.buildSong(jam) -> project                                 // one machine per used instrument, one Lights machine per light layer with .layer/.sync/.family, patterns rendered per section, blocks placed, song.sections + song.autom filled, master + swing set
Studio.PRESETS.buildStack(section, jam) -> project                       // the live stack: same as one section, pattern mode, no transitions
Studio.PRESETS.starter(style) -> section                                 // picks per instrument + 3 light layers for the style at energy 0.6
Studio.PRESETS.arc(n) -> [energy...]                                     // 0.15 0.45 0.9 0.3 0.6 1.0 0.2 resampled to n sections
```
Energy application (CORE): density ladder `n = round(2 + 8*e)` over the priority
`sub, drums, pad, perc, bass, chords, keys, lead, arp, fx` after the user's picks (a pick is
kept if `e >= minEnergy`); velocity `0.55 + 0.45*e`; cutoff automation `0.25 + 0.65*e` on pad,
chords, lead, arp, bass; sends scaled `0.35 - 0.25*e` on top of the instrument defaults;
transitions in the last bars as the plan says (fill: drum `expand(...,{fill:true})` on the last
bar plus crash on the next downbeat; riser: a 2-bar FX note with cutoff 0.2 -> 1 and a lights
level ramp 0.4 -> 1; drop: drums and bass blocks end 4 bars early (8 if the section is 16), pad
held; gap: every block ends one beat early and a lights level 0 on that beat). Humanise: seeded
velocity jitter up to `15% * humanise` (timing jitter is the engine's swing only). Light layer
gain `0.15 + 0.85*e` unless the pattern says otherwise; strobe family only when `e > 0.85` or
the section transition is riser/fill.

## Lights runtime contracts (LIGHTS)

`machine.layer` 0..5, `machine.sync` `'grid'` or a machine id, `machine.family`,
`machine.params.level` as today. `L.state = {level, hitAt, layers:[{look, palette, gain, family,
trigN, trigPhase, cyclePhase, sync}]}` with `state.look/palette` mirrored from layer 0.
`lightsMachines()` sorted by layer, cap 6. Synced layer: triggers = that machine's flattened
note steps (deduped), `trigN` = index of the last trigger at or before the playhead, `trigPhase`
= progress to the next, `cyclePhase` = position in that machine's current pattern length; the
layer's cue lookup wraps on that length. postMessage carries `state` as above; `index.html`
paints with `NGVShow.paintLayers` when `state.layers` exists, else `paint`. Export cue entries
carry `layer` and `sync`; cue file `cueVersion:2`; layer-0 entries keep the v1 fields so a v1
player still shows layer 0. Cue times use `Studio.timeline(proj).time(step)`.

## Engine contracts (ENGINE)

Scheduler, `pos()`, `render()`, swing and `seek` read `Studio.timeline(proj)` (cache it, clear on
`eng.invalidate()`). `pos()` keeps `{step, t, bar, beat, stepInBar, loopSteps}` and adds the
timeline's `at(step)` fields (beatN, beatPhase, barPhase, beatsPerBar, meter, bpm, section).
`Studio.flattenAutom(proj, mode)` events fire in `scheduleStep` and in `render()` through
`inst.setParam(param, v)`. `eng.rebuild()` while playing must hot-swap the rig without losing
the transport position (the jam rebuilds the stack on every tile tap). Pattern mode is unchanged
(one loop at proj.bpm, 16-step bars). `test-timeline.html` asserts: no-section project flattens
identically to `b.bar*16` maths; 3/4, 6/8, 5/4, 7/8 sections give 12/12/20/14 steps per bar;
`time` and `stepAt` invert; a 130 bpm section changes step duration only inside itself; a live
play across a 4/4 to 7/8 boundary keeps `pos().step` monotonic and `pos().bar` correct.

## Jam page (JAM)

Phone-first, same tokens as `studio/ui.css`. Top: Play/Stop, tempo, a Style row (10 chips; tap =
`PRESETS.starter(style)` applied to the current section), Arc button. Body: one row per
instrument (10 tiles, one active or none), then six light rows by family (5 tiles, one active or
none, each with a Sync chip cycling Grid / Drums / Bass / ... and a gain slider on long-press or
in its card). Tapping rebuilds the stack (`buildStack`) and hot-swaps the engine without
stopping. Sections strip at the bottom: Add section (copies the current stack), cards with
energy slider, feel, meter, cycle, transition, transpose, bars; reorder, duplicate, remove; Song
play (`buildSong`, song mode). Hall tab: iframe `index.html?embed=1&show=live&bare=1`. Share:
the jam JSON compressed with `CompressionStream('deflate-raw')` to base64url in the hash;
restore on load. Export: WAV + cues JSON as browser downloads (`Studio.exportShow` cannot POST
on the public site; reuse its render and cue-file functions, LIGHTS exposes
`Studio.exportFiles(proj, eng, name, progress) -> {wavBlob, cuesJson}`). Open in studio: write
`localStorage['ngv.studio.project']` and open `studio.html`. Autosave the jam to localStorage;
first load = house starter, 4 sections with the arc. Verification as the plan says (screenshots
390x844 touch and 1280x720, no overflow, rAF >= 30 fps for 30 s with 6 layers, end to end).
