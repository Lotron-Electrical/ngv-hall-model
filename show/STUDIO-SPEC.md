# The Studio: brief for the build

Build `studio.html` at the repo root of `C:/Users/Lloyd Gibbs/Claude Projects/ngv-hall-model/`.
One file, no build step, classic `<script>` tags. It loads `show/lightshow.js` (already written,
read it first: `window.NGVShow` gives `createShow()`, `createAnalyser(ac,node)`, `LOOKS`,
`LOOK_NAMES`, `PALETTES`, `PALETTE_NAMES`). Do not edit `index.html` or `show/lightshow.js`;
if you find they need a change, write it down in your report instead.

## What it is for

Lloyd makes his own music for the NGV Gandel Hall proposal AND cues the lights on the 12 columns at
the same time, on one clock. The hall sim (`index.html`) runs in an iframe beside the instruments and
shows the lights as the music plays. Record stamps every light pad press against the transport time.
Export renders the music to a WAV and writes a cue file the sim plays back on its own.

## Layout (desktop, 1440 x 900 and up; must also work at 1280 x 720)

- Top bar: project name field, transport (Play/Pause, Stop, Record toggle, Loop toggle), BPM
  stepper (60 to 180, default 124), key select (C..B) and mode (minor/major), bar:beat readout,
  time readout, master level meter, Save, Load, Export.
- Left column (about 420 px): the SONG. A list of sections in order, each a card with: name
  (intro/build/drop/break/outro or free text), bars (4/8/16/32), chord progression preset, drum
  pattern preset, per-instrument on/off (kick, snare, hat, clap, sub, chords, arp, lead), filter
  (a single 0..1 slider for the pad/arp low-pass; a checkbox "sweep up over the section" that ramps
  it from 0.2 to the slider value across the section, the build's riser), energy (0..1, drives the
  sidechain depth and hat density). Buttons: add section, duplicate, delete, move up/down.
  Below the list: the drum grid for the selected section, 4 rows x 16 steps, click to toggle,
  seeded from the preset. Chord presets in scale degrees, e.g. `i VI III VII`, `i iv VI v`,
  `i VII VI VII`, `vi IV I V` (major), `I V vi IV` (major): one chord per bar, cycling.
- Centre: the sim iframe, `index.html?embed=1&show=live`, filling the remaining width and the full
  height between the top bar and the timeline.
- Right column (about 300 px): the LIGHTS. Pads for every look in `NGVShow.LOOKS` (label plus the
  one-line description as a tooltip), pads for every palette in `NGVShow.PALETTES` (pad painted
  with its A and B colours), a LEVEL slider, a HIT button, a Quantise select (off, 1/4 beat, 1 beat).
  The current look and palette pads are highlighted. Keys: `1`..`9`,`0`,`-`,`=` for looks in order,
  `q w e r t y u i o p` for palettes in order, `[` and `]` step level by 0.1, Space is HIT.
  Keys must not fire while an input, select or textarea has focus. Enter toggles Play/Pause,
  Escape is Stop, `R` toggles Record.
- Bottom (about 160 px): the TIMELINE. Section blocks in order, scaled to their length, a lane of
  light cues drawn as ticks coloured by palette with the look name on hover, the playhead. Click
  in the timeline seeks. Click a cue tick to delete it (with a small x on hover).
- Live keys for the lead: computer keyboard `a s d f g h j k l ;` are white keys from the key's
  root, `w e t y u o p` the black keys between, `z`/`x` octave down/up. Show a small on-screen
  keyboard that lights the held keys. These are notes, not light keys, so the light keys above
  must not overlap: light pads use the number row and `q..p` only when a "Lights" focus toggle is
  on (a button in the right column and the Tab key), otherwise the letter row plays the lead and
  the number row still fires looks. Default focus: lights. Make the current focus obvious.

Style: match the sim. Tokens from index.html: `--bg:#0e0f11; --rule:#2a2d33; --ink:#e9e6df;
--dim:#9a978f; --accent:#b9a887; --ok:#6fbf8a; --panel:#16181c`, body font "IBM Plex Sans",
system-ui; headings "Barlow Condensed". Buttons: high contrast text on their fill, always. The
active Record button is red. Everything reachable at 1280 x 720 (scroll the side columns, never
clip). No em dashes anywhere, in code comments or UI text. Comments in plain English, short, saying
why, in the house style you see in `index.html` and `show/lightshow.js`.

## The audio engine

WebAudio. One `Engine` that takes an AudioContext (live or Offline) and renders the song from a
start time, so the live transport and the export use the same code path and sound identical.

- Scheduler: lookahead 120 ms, tick 25 ms (setInterval) for live; for offline, schedule
  everything up front then `startRendering`.
- Grid: 4 beats per bar, 16 steps per bar. Total length = sum of section bars.
- Master chain: instruments -> sidechain gain (ducked by the kick: on each kick, gain drops to
  1 - 0.6 * energy and recovers over 60 % of a beat) for chords, arp and sub; drums bypass it ->
  master gain -> a soft limiter (DynamicsCompressor threshold -3 dB, ratio 12, attack 3 ms,
  release 100 ms) -> destination. A `NGVShow.createAnalyser(ac, masterGain)` sits on the master.
- Kick: sine with a pitch drop 150 Hz -> 45 Hz over 40 ms, decay 300 ms, plus a 5 ms click.
- Snare: noise burst through a band-pass at 1.8 kHz, decay 160 ms, plus a 180 Hz tone, 90 ms.
- Hat: noise through a high-pass at 7 kHz, closed 40 ms, open 180 ms (every 4th hat step open
  when energy > 0.6).
- Clap: three noise bursts 10 ms apart through a band-pass at 1.2 kHz, decay 120 ms.
- Sub: sine one octave below the chord root plus a quiet saw through a low-pass at 120 Hz, gated
  on the off-beats (steps 2, 6, 10, 14) when energy > 0.5, else held for the bar.
- Chords: 3 detuned saws per note (detune -12, 0, +12 cents), 3 or 4 note voicings, through a
  low-pass whose cutoff is the section filter (0..1 mapped to 300 Hz .. 8 kHz), attack 80 ms,
  release 400 ms, one chord per bar, stereo width from a slight left/right pan per voice.
- Arp: a pluck (triangle, decay 180 ms) on every 16th step, walking chord tones up then down
  two octaves, same filter as chords.
- Lead: a monosynth (saw + square an octave up, low-pass 2.5 kHz with a little envelope, glide
  30 ms). Live: notes from the keyboard. Recorded lead notes `{t, dur, midi}` play back in the
  render and in playback.
- Levels: kick -6 dB, snare -8, hat -16, clap -10, sub -8, chords -12, arp -14, lead -10. Trim
  so the limiter is only touched on the drops.

## Transport and time

`t` is seconds from the start of the song. Live: `t = ac.currentTime - t0` (with pause and seek
kept consistent). Every rAF the studio computes the FRAME: `{t, bpm, beatN, beatPhase, barPhase,
bass, mid, high, rms, onset}` (beatN from t and bpm, bands from the analyser) and posts to the
iframe: `iframe.contentWindow.postMessage({t:'show', frame, state, on:true}, '*')` where `state` is
`{look, palette, level, hitAt}` (hitAt = the song time of the last HIT press). Also run the same
`NGVShow.createShow()` locally and call `applyCues(cues, t)` so the local state follows the recorded
lane when playing, but a live pad press during Record wins and is stamped. The iframe reads the
message on its side already (see the `message` listener in `index.html`, near
`function animate`).

Cues: `{t, look?, palette?, level?, hit?: true}`. A pad press while playing and Record is on
appends one, `t` quantised when Quantise is on. A press while stopped or not recording just sets
the live state. Cues are sorted by t.

## Project file

JSON `{name, bpm, key, mode, sections:[...], drums:{sectionIndex:[16-step rows]}, lead:[notes],
cues:[...], look, palette, level}`. Autosave to localStorage on every change. Save posts to
`POST /save?path=show/<name>.project.json` with the JSON body (the dev server at
`tools/serve.js` accepts it; run `node tools/serve.js --port 8878` to test). Load fetches the same
path. A "Load" that finds no file shows a short message, not an error.

## Export

1. Render the song with an OfflineAudioContext (44100 Hz, stereo) through the same Engine.
2. Encode 16-bit PCM WAV.
3. Compute the frames from the rendered buffer in JS: mix to mono, frame size 2048, hop 1024,
   Hann window, a radix-2 FFT you write (about 30 lines). Per frame: rms, bass (mean power 20-150
   Hz), mid (150-2000), high (2000-11000), onset (spectral flux, positive differences summed).
   Each array normalised so its 99th percentile is 1.0 then clipped to 0..1, bands smoothed with a
   3-frame moving average, onset unsmoothed.
4. Cue file `{file:"<name>.wav", duration, sr:44100, hop_s:1024/44100, bpm, beats:[every beat
   time], downbeats:[every bar start], sections:[{t0,t1,label,energy}], frames:{rms,bass,mid,high,
   onset}, cues:[...], lead:[...] }`, floats to 4 dp.
5. POST `show/<name>.wav` and `show/<name>.cues.json`, then fetch `show/shows.json` (may be
   404, treat as `[]`), add the name if missing, POST it back.
6. Show progress and finish with a link: `index.html?show=<name>`.

## Verify before you report

- `node tools/serve.js --port 8878` from the repo, then Playwright with real Chrome
  (`PLAYWRIGHT_BROWSERS_PATH=E:\caches\ms-playwright`, `channel:'chrome'`, launch args
  `--autoplay-policy=no-user-gesture-required`). Load `http://127.0.0.1:8878/studio.html` at
  1440 x 900 and at 1280 x 720, screenshot both to `show/verify-studio-*.png` and LOOK at them
  (Read the PNGs): no clipped text, no overlapping panels, every control reachable, the iframe
  visible with the hall.
- Add two sections (build 8 bars, drop 8 bars), press Play, wait 3 s, and assert in the page that
  the iframe received frames: `iframe.contentWindow.ngvShow.frame.t > 1` and
  `iframe.contentWindow.ngvShow.on === true`.
- Press Record, fire two look pads and a HIT, stop, assert the cues array has 3 entries with
  increasing t.
- Run Export on that 16-bar song. Assert `show/<name>.wav` exists with a plausible size (16 bars
  at 124 bpm is about 31 s, about 5.4 MB) and `show/<name>.cues.json` parses with all frame arrays
  the same length, and `show/shows.json` lists the name. Use the name `verify`.
- Open `http://127.0.0.1:8878/index.html?show=verify`, click the Play button in the Lightshow row
  (`#showplay`), wait 4 s, screenshot to `show/verify-playback.png`, and LOOK at it: the columns
  must be lit in colour, not warm white, not dark.
- Kill the server you started. Report what you built, what you verified with the numbers, and any
  problem you could not fix.
