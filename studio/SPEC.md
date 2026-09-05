# The Studio v2: a Caustic 3 style DAW with a Lights machine

Repo: `C:/Users/Lloyd Gibbs/Claude Projects/ngv-hall-model/`. Everything for the studio lives in
`studio/` plus the shell `studio.html` at the repo root. The old single-file `studio.html` is the
previous version: mine it for working code (the drum and synth voices, `analyseBuffer`, the WAV
encoder, the save/load/export POSTs, the iframe bridge) but the new layout replaces it.

Lloyd's ask, verbatim: "There was an app/DAW called Caustic 3. I want it to work like that. But
also have an instrument which is the visual/lighting controls."

Caustic 3 in one paragraph: a RACK of machines (each an instrument: SubSynth, BassLine, PadSynth,
BeatBox, ...). Each machine has a bank of PATTERNS (A1..D8), each 1 to 8 bars on a 16-step grid,
edited in a piano roll (synths) or a pad grid (drums). A SONG view lays pattern blocks per machine
on a bar timeline. A MIXER has volume, pan, mute, solo and sends per machine, and an EFFECTS rack
gives each machine two insert slots. Along the bottom, a piano keyboard (or pads) plays the
selected machine live; with Record on, what you play lands in the current pattern. Play runs in
PATTERN mode (every machine loops its current pattern) or SONG mode (the arrangement).

Our twist: the Lights machine is one more machine in the rack. Its "notes" are light cues (look,
palette, hit) and it has a level lane; its pads are the looks and palettes; the hall sim sits in
a panel and follows it live. Export renders the song to WAV and writes the cue file the sim plays.

## Files and owners

| File | Owner | Holds |
| --- | --- | --- |
| `studio/model.js` | written, read it first | schema, machine and fx catalogues, helpers, `Studio.demoProject()`, `Studio.flatten()` |
| `studio/machines.js` | AUDIO | every machine's voice: `Studio.MACHINES[type] = { create(ac, machine, dest) -> inst }` |
| `studio/engine.js` | AUDIO | `Studio.createEngine()`: context, graph, mixer, fx, scheduler (pattern / song), live play, offline render |
| `studio/lights.js` | LIGHTS | the Lights machine's runtime: cue resolver, live presses with record, the iframe bridge |
| `studio/export.js` | LIGHTS | render to WAV, frame analysis, cue file, POST /save, shows.json |
| `studio/ui.css` | UI | the whole stylesheet |
| `studio/ui.js` | UI | views: rack, pattern editor, song, mixer, fx, transport, keyboard/pads, sim panel, save/load, key routing |
| `studio.html` | UI | the shell: loads `show/lightshow.js`, then `studio/model.js`, `machines.js`, `engine.js`, `lights.js`, `export.js`, `ui.js` in that order |

Load order matters: every file is a classic script that adds to `window.Studio` (an IIFE, `'use
strict'`). No modules, no bundler, no dependencies. LF line endings, UTF-8, ASCII only. No em dashes
anywhere. Comments in plain English in the house style (see `show/lightshow.js`): short, saying
why. Buttons: high-contrast text on their fill, always.

Every owner writes ONLY their files. If you need a change in another file, put it in your report
(the integrator applies it). If `model.js` is missing something you need, add a helper in your
own file under your own namespace rather than editing model.js.

## Contracts

### machines.js (AUDIO)

```js
Studio.MACHINES[type] = {
  create(ac, machine, dest) -> inst   // ac: AudioContext or OfflineAudioContext; machine: the model object; dest: AudioNode to connect the machine's output to
}
inst.noteOn(time, n, v)       // n: midi note (synth) or pad index 0..7 (beatbox); v: 0..1
inst.noteOff(time, n)         // synths; a no-op for drums
inst.setParam(key, value)     // live knob; reads machine.params[key] otherwise at note time
inst.allOff(time)             // release every voice (Stop)
inst.dispose()
```
The machine's own `vol` param is its output gain before the mixer channel. Polyphony: SubSynth,
PadSynth, FMSynth at least 8 voices; BassLine is mono with slide when notes overlap (a note that
starts before the previous ends glides, 303 style) and accent when v >= 0.9. Beatbox pads are the
eight in `Studio.MACHINE_TYPES.beatbox.pads`, all synthesised (no samples): kick with pitch drop,
snare noise + tone, clap triple burst, closed and open hat (high-passed noise), tom, rim, crash.
Parameter tables are in `model.js`; honour every key there, with the ranges given.
The Lights machine has NO audio: `Studio.MACHINES.lights.create` returns an inst whose methods are
no-ops (the engine still schedules its notes and hands them to the lights runtime, see below).

### engine.js (AUDIO)

```js
const eng = Studio.createEngine({ project: () => proj, onNote: (mid, n, v, time, on) => {} });
eng.init()                       // makes the AudioContext (call inside a gesture); idempotent
eng.ac                           // the live AudioContext (null before init)
eng.rebuild()                    // rebuild the graph from the project (after add/remove machine, fx changes)
eng.play({mode:'pattern'|'song', fromStep:0}) ; eng.pause() ; eng.stop() ; eng.playing ; eng.mode
eng.pos()  -> {step: float steps since song/loop start, t: seconds, bar, beat, stepInBar, loopSteps}
             // pattern mode loops over Studio.patternLoopSteps(project); song mode runs Studio.songLengthBars()*16 then stops (or loops when eng.loop = true)
eng.seek(step)
eng.noteOn(mid, n, v) / eng.noteOff(mid, n)      // live play, immediate
eng.setParam(mid, key, value) ; eng.setMixer(mid) // re-read vol/pan/mute/solo/send for one machine
eng.setFx(mid, slot)                              // rebuild that machine's insert slot from the model
eng.master                                        // the master GainNode (for the analyser)
eng.analyser                                      // NGVShow.createAnalyser(ac, eng.master) made at init; .read(out) gives {bass,mid,high,rms,onset}
eng.render(project) -> Promise<AudioBuffer>       // whole song at 44100 stereo through an OfflineAudioContext, same scheduling code, plus 2 s tail
```
Scheduler: lookahead 120 ms, tick 25 ms, notes from `Studio.flatten(project, mode)` (recompute
when the project changes: expose `eng.invalidate()` and call it from the UI on every edit; cheap
enough to call often). Swing: `project.swing` 0..1 delays odd 16ths by up to half a step. For the
Lights machine the engine does not play audio; it calls `onNote(mid, n, v, time, true)` at note
time for every machine (the lights runtime needs it, the UI uses it to flash keys). Mixer per
machine: machine out -> insert fx slot 1 -> slot 2 -> channel gain (vol, mute, solo) -> panner ->
master bus, plus a send gain to the master delay and the master reverb (`project.master.delay`,
`project.master.reverb` are fx models). Master: sum -> master gain -> limiter (compressor -3 dB,
ratio 12, attack 3 ms, release 100 ms) -> destination. Effects: build every `Studio.FX_TYPES` entry
(delay with tone, reverb from a generated noise impulse, chorus, distortion waveshaper, filter
with type 0 = low-pass 1 = high-pass, compressor, bitcrush via a ScriptProcessor-free approach:
a WaveShaper quantiser plus a low-pass for the rate is acceptable).

Test page (AUDIO writes it): `studio/test-engine.html` loads lightshow.js, model.js, machines.js,
engine.js, renders `Studio.demoProject()` offline and prints a JSON line to the document body and
the console: `{ok, seconds, peak, rms, perMachinePeak:{...}}` where perMachinePeak is measured by
rendering each machine solo. Every machine with notes must have peak > 0.05; the mix peak must be
below 1.0 (the limiter) and above 0.3.

### lights.js (LIGHTS)

```js
const L = Studio.createLights({ project: () => proj, engine: () => eng, iframe: () => iframeEl });
L.show                 // NGVShow.createShow() used locally to keep state
L.state                // {look, palette, level, hitAt} the current resolved state (song/pattern cues up to now, overridden by live presses)
L.resolve(pos)         // recompute L.state from Studio.flatten(project, eng.mode) and Studio.flattenLevel(...) up to pos.step (cache the flattened arrays; L.invalidate() clears)
L.press(kind, val)     // 'look'|'palette'|'hit'|'level': sets state now; if the UI's record flag is on and the engine is playing, writes into the Lights machine's current pattern at the quantised step (kind level writes pattern.level[step]); returns the note it wrote or null
L.setRecord(on, quantiseSteps)   // quantiseSteps: 1 (a 16th), 4 (a beat), 0 (off = nearest 16th anyway, the grid is the finest resolution)
L.tick()               // once per rAF from the UI: pos from the engine, bands from eng.analyser, frame {t,bpm,beatN,beatPhase,barPhase,bass,mid,high,rms,onset}, then iframe.contentWindow.postMessage({t:'show', frame, state:L.state, on:true}, '*')
L.invalidate()
```
Beat maths for the frame: from `eng.pos()` (step, bpm): beatN = floor(step/4), beatPhase = (step
mod 4)/4, barPhase = (step mod 16)/16. When the engine is stopped, keep posting frames (t frozen)
so the hall holds the last state, at a lower rate (every 4th rAF).
Hits: a hit cue at step s sets `state.hitAt` to that song time once when the playhead crosses it
(track the last crossed step, do not re-fire on every tick).

### export.js (LIGHTS)

```js
Studio.exportShow(proj, eng, name, progress) -> Promise<{wav, cues, url}>
```
1. `eng.render(proj)` -> AudioBuffer. 2. WAV 16-bit PCM stereo. 3. Frames from the buffer: mono
mix, frame 2048, hop 1024, Hann, your own radix-2 FFT; rms, bass (20-150 Hz), mid (150-2000),
high (2000-11000) as sqrt of mean linear power, onset = positive spectral flux; smooth bands with
a 3-frame moving average FIRST, then normalise each array so its 99th percentile is 1.0, clip 0..1.
4. Cue file `{file:"<name>.wav", duration, sr:44100, hop_s:1024/44100, bpm, beats, downbeats,
sections:[one per 4 bars, label from the machines active: 'break' if no drums, 'drop' if drums and
bass and pad, else 'build'], frames:{...}, cues:[{t, look?, palette?, level?, hit?}], project}`
where cues come from `Studio.flatten(proj,'song')` for the Lights machine and
`Studio.flattenLevel(proj,'song')`, t = step * Studio.stepSeconds(bpm), 4 dp. 5. POST
`show/<name>.wav`, `show/<name>.cues.json`, then read `show/shows.json` (404 -> []), add the name,
POST it back. Also `Studio.saveProject(proj)` -> POST `show/<name>.project.json` and
`Studio.loadProject(name)` -> fetch it (null when 404). `progress(text, 0..1)` is called along the way.
URL for the result: `index.html?show=<name>`.

### ui.js + ui.css + studio.html (UI)

Views, switched by tabs in the top bar, Caustic order: RACK, PATTERN, SONG, MIXER, FX. Always
visible: the top bar (project name, transport Play/Pause, Stop, Record, mode Pattern/Song, Loop,
BPM stepper 60-200, swing, position bar:beat:step and time, master meter, Save, Load, Export,
Sim toggle) and the bottom PLAY STRIP (piano keyboard for synth machines, 8 pads for BeatBox, look
and palette pads plus level slider and HIT for Lights; machine selector tabs above it, one tab
per machine in rack order, coloured by `MACHINE_TYPES[type].color`). The SIM PANEL: the hall in an
iframe `index.html?embed=1&show=live` docked on the right, default 38 % of the width, a drag
handle to resize, the Sim button hides and shows it. It stays mounted across view switches.

RACK: one panel per machine, stacked, scrolling: name (editable), type badge, knobs for every
param in its table (a knob = a vertical drag control drawn on a small canvas or a styled range
input, with the value and unit under it), mute/solo, remove, move up/down; an Add machine button
with the six types. PATTERN: pattern bank selector (A1..D8 as a grid of small buttons, the ones
with notes marked), bars 1..8, clear, copy/paste pattern; the editor: for synths a piano roll
(rows = midi 24..96 scrolling, columns = steps, click to add a note of the current length, drag
right edge to lengthen, right-click or click again to remove, velocity by shift-drag or a
velocity lane below); for BeatBox an 8 x steps grid; for Lights a lane grid with one row per
`Studio.LIGHT_KEYS` entry (looks first, then palettes, then hit), coloured by palette for palette
rows, and a level lane below drawn as bars you draw across with the mouse. The playhead runs across
the editor while playing. SONG: a bar ruler along the top, one row per machine, blocks drawn from
`proj.song.tracks`; click an empty bar to place the machine's current pattern, drag a block's right
edge to stretch, click a block to select it, Delete removes, double-click opens that pattern in
the PATTERN view; the playhead; song length grows to fit. MIXER: a channel strip per machine with
a vertical volume fader, pan, mute, solo, delay send, reverb send, and a master strip with the
master delay and reverb knobs. FX: for the selected machine, two slots, each a select of
`Studio.FX_TYPES` and knobs for its params, on/off.

Live play: computer keyboard on the PLAY STRIP. Synths: `z x c v b n m , . /` white keys from C3,
`s d g h j l ;` the blacks, `q w e r t y u i o p` a second white row an octave up, `2 3 5 6 7 9 0`
its blacks, `[` `]` octave. BeatBox: `z x c v b n m ,` fire the eight pads (same keys). Lights:
`1..9 0 - =` looks, `q w e r t y u i o p` palettes, `[` `]` level down/up, Space HIT. So the key map
changes with the selected machine; the on-screen strip shows the letters. Keys never fire while
an input, select or textarea has focus. Enter = play/pause, Escape = stop, Shift+R = record.
Record: with Record armed and the engine playing, every key press writes into the selected
machine's current pattern at the quantised step (Quantise select: 1/16, 1/8, 1/4 beat; default
1/16). For synths write length from press to release (min 1 step). For Lights call `L.press`.
Mouse on the on-screen keys and pads does the same as the keyboard.

Every edit calls `eng.invalidate()` and `L.invalidate()`, then the view re-renders what changed.
Autosave the project JSON to localStorage on every edit (debounced 500 ms) and restore it on load;
if nothing is stored, open `Studio.demoProject()`. Save and Load go through export.js.

## Verification, before any owner reports

Run `node tools/serve.js --port 8878` from the repo (or use one that is already up on that port).
Use Playwright with real Chrome: `PLAYWRIGHT_BROWSERS_PATH=E:\caches\ms-playwright`,
`channel:'chrome'`, args `--autoplay-policy=no-user-gesture-required`. Playwright is installed
at `C:/Users/Lloyd Gibbs/Claude Projects/godmode-site/node_modules` (set `NODE_PATH` to that for
a `.cjs` script). Screenshots go to `studio/verify/`. Kill only servers you started.

- AUDIO: `studio/test-engine.html` passes (numbers in the report). Also a live check: a page
  that inits the engine, plays pattern mode 2 s, reads `eng.pos().step` > 8 and analyser rms > 0.
- LIGHTS: a test page `studio/test-lights.html` that loads everything but ui.js, builds the demo
  project, starts the engine in song mode, runs `L.tick()` for 3 s with a real iframe of
  `index.html?embed=1&show=live`, and asserts `iframe.contentWindow.ngvShow.frame.t > 2` and the
  iframe's look changed from `pulse` to `beatwave` after bar 1. Then `Studio.exportShow` on the demo
  as `verify` and check the three files land in `show/` with equal frame lengths; remove the
  verify files afterwards (and take `verify` out of `show/shows.json`).
- UI: screenshots of every view at 1440 x 900 and 1280 x 720, LOOK at each one (Read the PNG):
  no clipped text, no overlap, every control reachable (scroll where needed). Since machines.js
  and engine.js may not exist while you build, ui.js must guard: if `Studio.createEngine` is
  missing, use a stub engine (`studio/engine-stub.js`, yours, only loaded by a `?stub` query)
  that advances `pos()` from performance.now() so views and the playhead can be exercised.
