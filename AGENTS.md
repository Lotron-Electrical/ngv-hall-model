# AGENTS.md — operating manual for an AI agent driving the NGV Hall model

This file is written for a machine. Every number in it was read out of the running page on
2026-08-31, not remembered. If you change the design in the page, re-read the facts (see
[Reading the pixel map without a screen](#reading-the-pixel-map-without-a-screen)) rather than
trusting the defaults printed here.

- Repo: `ngv-hall-model` (single page, `index.html`, plus `model.glb` and `tools/`)
- Live copy: <https://lotron-electrical.github.io/ngv-hall-model/>
- What it is: a 3D model of the NGV's Gandel Hall with an RGBW LED design on the 12 columns, a
  pixel map (controller outputs, universes, DMX addresses), a CSV export that IS the patch for
  ELM 2026, and a live input that shows a real Art-Net / sACN stream on the model.

## The one command

```
node tools/agent-setup.js
```

Starts the bridge if it is not already up, prints what to configure in ELM, then waits — first for
Art-Net to arrive, then for the page to connect — and reports each step as one JSON line on stdout.

Useful variants:

| Command | Does |
| --- | --- |
| `node tools/agent-setup.js --status` | one JSON line describing a running bridge, changes nothing |
| `node tools/agent-setup.js --no-wait` | set up and exit, no polling |
| `node tools/agent-setup.js --stop` | stop the bridge this machine is running |
| `node tools/agent-setup.js --open` | also open the page in the default browser |
| `--ws 9930 --artnet 6454 --sacn 5568 --universes 1-1024 --fps 40 --timeout 300 --page <url>` | overrides |

Stages appear in this order and an agent should read lines until one of the three terminal stages:

`node` → `bridge` → `port` → `start` → `up` → `network` → `elm` → `page` → `wait_artnet` →
`artnet` → `wait_client` → `client`/`ready`.
Terminal: **`ready`** (success), **`timeout`** (exit 2, carries `at` and `hint`), **`error`** (exit 1).

## The design, as the page computes it

Defaults, at 8 gaps per column and 60 px/m strips (`system: strip`, `density: 60`):

| Fact | Value |
| --- | --- |
| Columns | 12 (N1..N6, S1..S6), 8 strips in the gaps of each |
| Strips | 96 |
| Pixels per strip | 762 to 770 (columns differ slightly) |
| Pixels / LEDs total | 73,536 (one LED per pixel at 60 px/m) |
| Pixels per universe | 128 RGBW (4 × 128 = 512 slots exactly; 128 is a hard ceiling, not a preference) |
| Max pixels per output | 1024, so one strip per output |
| Outputs | 96, at 16 outputs per controller = 6 controllers |
| Universes | 608 |
| Universe numbers on the page | 1 to 608 |
| Universe numbers in ELM / on the Art-Net wire | 0 to 607 |
| Colour order | RGBW, 8 bit, 4 channels per pixel, semantic R,G,B,W (the strip's GRBW wire order is the pixel controller's business) |
| Default strip order | `ns` — N1..N6 then S1..S6, gap 1..8 |
| Default data direction | all strips bottom to top |

The **page is one ahead of the wire**: `dmx_bridge.js` adds 1 to every Art-Net universe it
receives (wire 0 → page 1), and `elmCsv()` subtracts 1 when the protocol is Art-Net, so the file
carries the number ELM shows. Both ends agree; do not "fix" one of them. For sACN the offset is
zero on both sides.

## The ELM CSV contract

`window.elmCsv()` returns the whole file as a string. ELM 2026: *3D stages > Import from CSV*.
The file IS the patch — ELM never re-addresses an imported rig, so do not re-patch after import.

Header: `x,y,z,protocol,universe,address,type,bits,strip,order,name`

- `x,y,z` — millimetres, hall centred in plan, floor at y = 0. `--up z` swaps y and z for a Z-up
  target. ELM has no unit and rescales the whole rig on import.
- `protocol` — `ArtNet` or `sACN`, matching the `pm_proto` control.
- `universe` — as ELM shows it (Art-Net 0-based, sACN 1-based).
- `address` — 1-based DMX channel of the pixel's first (red) slot: 1, 5, 9 … 509.
- `type,bits` — always `RGBW,8`.
- `strip,order,name` — optional in ELM, carried so it draws the runs in wiring order:
  strip 1..96, order 1..pixels within the strip, name like `N1 gap 1`.

One row per pixel: **73,537 lines** at the defaults (header + 73,536). Verified end to end against
ELM 2026 Preview on 2026-08-31: imports with no errors, Locate LED probes at universes 0 / 300 /
600 land where the file puts them.

## Reading the pixel map without a screen

The map is not a file on disk. `index.html` computes it in JavaScript from the current controls,
so the only honest source is the page itself, running. The page keeps its state module-private and
exposes a deliberate keyhole:

- `window.elmCsv()` → the CSV string above.
- `window.ngv` → `{ state, P, lit, scene, cam, ... }`. `P.n` LEDs, `P.runs` strips,
  `P.univ[i]` page universe of LED i, `P.dmxC[i]` 0-based channel offset within the universe,
  `P.run[i]`, `P.pi[i]` pixel index within its strip.

`tools/elm-fetch.js` drives that keyhole over the DevTools protocol with no npm packages:

```
node tools/serve.js &                                  # http://127.0.0.1:8877/
chrome --headless=new --remote-debugging-port=9222     # any Chrome/Edge
node tools/elm-fetch.js --what facts                   # JSON: strips, leds, universes, summary
node tools/elm-fetch.js --what csv --out elm.csv       # the ELM import file
node tools/elm-fetch.js --what patch                   # the per-strip table as CSV
```

Flags: `--url <page>` (default `http://127.0.0.1:8877/index.html`), `--port 9222`,
`--set density=60,count=8,system=strip`, and the map controls `--ppu --u0 --maxout --opc --order
--dir --proto --up`. It creates a throwaway tab, waits for the model to load, applies the changes
through the page's own controls so it recomputes, prints, and closes the tab.

Do **not** send an `Origin` header on the DevTools WebSocket; Chrome answers 403 and the failure is
silent. `elm-fetch.js` already omits it.

Sanity check of a fetched CSV:

```
awk -F, 'NR>1{u[$5]} END{print NR-1" rows, "length(u)" universes"}' elm.csv
# expect: 73536 rows, 608 universes
```

## The live loop: ELM → bridge → page

A browser cannot open a UDP socket, so `tools/dmx_bridge.js` listens for Art-Net (udp/6454) and
sACN (udp/5568) and re-sends every universe over `ws://localhost:9930` as binary frames:
repeated records of `uint16 universe, uint16 length, length bytes of DMX` (little-endian, slot 1
first, no start code), batched at `--fps` (default 40).

Run it directly if you do not want the setup wrapper:

```
node tools/dmx_bridge.js [--ws 9930] [--artnet 6454] [--sacn 5568] [--universes 1-1024] [--fps 40]
```

The default universe window is `1-1024`; the page's patch needs 608, so anything narrower than
`1-608` silently drops strips.

Status endpoint — `GET http://127.0.0.1:9930/` (CORS open, JSON):

| Field | Meaning | Healthy value once running |
| --- | --- | --- |
| `ok` | always true when the bridge answers | `true` |
| `artnet` | Art-Net packets received | climbing |
| `sacn` | sACN packets received | climbing (or 0 if using Art-Net) |
| `universes` | distinct universes heard | `608` at the full design |
| `clients` | WebSocket clients connected | `1` per open page |
| `frames` | batched frames sent to clients | climbing while a client is connected |
| `lastSource` | e.g. `Art-Net 192.168.0.242` | the sender's IP |
| `ws` | the WebSocket port number | `9930` |

`frames` only climbs when `clients > 0`; a bridge hearing Art-Net with no page attached is normal
and correct.

### Configuring ELM 2026

1. Import the CSV as a 3D stage. Do not re-address it.
2. In ELM's Art-Net output settings, every universe row carries a destination node IP. Select all
   608 rows and bulk-fill the IP with the address `agent-setup.js` prints in its `elm` stage
   (`sendTo`), port 6454.
3. Output at 40 fps or lower. The bridge batches to `--fps` regardless, so a faster ELM is only
   more UDP.
4. Verify with `curl http://127.0.0.1:9930/` — `artnet` must climb and `universes` must reach 608.

### The same-machine port 6454 problem

Measured on 2026-08-31 against ELM 2026 Preview: same-machine **Art-Net cannot work at all**, not
just "not on your own IP". ELM sends FROM its `<adapter-ip>:6454` socket, so unicast to that
address is delivered back to ELM itself; unicast to a **second IPv4 on the same NIC dies in the
Windows stack** ("Address resolution timeout" — the host ARPs its own address on the wire); ELM
silently drops **loopback** destinations; and if another process claims 6454 first, ELM's output
goes silent entirely (its send socket is that bind). Broadcast is untested and would flood Wi-Fi.
What to do, best first:

1. **Same machine: use sACN.** Export the CSV with `pm_proto = sACN`, import that rig, leave the
   sACN page on multicast. ELM's multicast loops back to local group members and the bridge joins
   the groups across a socket pool (Windows caps ~20 IGMP memberships per socket — fixed in
   `dmx_bridge.js`). Run `node tools/dmx_bridge.js --universes 1-608`. On Wi-Fi, drop ELM's output
   rate (Settings > Project) — the multicast still transmits over the air.
2. **Two machines: use Art-Net unicast.** Bridge on the viewing machine, ELM's node IPs pointed at
   it. This is also the real-commissioning shape (ELM normally unicasts to physical controllers).

`agent-setup.js` detects the conflict at the `port` stage (`free: false`) before it starts anything.

### Firewall

Windows Defender must allow inbound UDP for `node.exe` on the private profile. If the first-run
dialog was dismissed:

```
netsh advfirewall firewall add rule name="NGV DMX bridge" dir=in action=allow protocol=UDP localport=6454
```

### Browser blocks

Corrected 2026-09-01: the 2026-08-31 "https cannot open `ws://localhost`" finding was misdiagnosed.
It is NOT mixed content (Chrome's localhost carve-out does cover ws). The blocker is **Local
Network Access** (`ERR_BLOCKED_BY_LOCAL_NETWORK_ACCESS_CHECKS`, Chrome 151): a public site reaching
a local address needs the user to Allow a permission prompt. Measured: the same hosted page
connects fine with the LNA check granted (headless auto-denies, which is what produced the
2026-08-31 "proof"). Consequences: the GitHub Pages site CAN drive from a local bridge once the
reader clicks Allow; an https IFRAME embed additionally needs `allow="local-network-access"` on
the iframe (the proposal has it); headless verification of this path must launch Chrome with
`--disable-features=LocalNetworkAccessChecks` or it will always read "not connected". The http
fallback still works everywhere: `node tools/serve.js`, then
`http://127.0.0.1:8877/index.html?connect=1` (optionally `&ws=host:port&off=N`) — auto-opens the
live input and retries until the bridge is up.

### Connecting the page

Today this is manual: open the page, expand **Live input**, set *Bridge* to `ws://localhost:9930`,
press **Connect**. *Universe offset* is added to the sender's universe to get the page's; leave it
at 0 for Art-Net through this bridge (the bridge already did the +1). An auto-connect `?ws=`
parameter is proposed in `PLAN-agentic.md` and is not implemented yet — `agent-setup.js` prints
such a URL but labels it as proposed.

The page's readout under Live input reports `N universes heard, F frames/s, L of 73,536 LEDs
addressed`. `L` reaching 73,536 means every pixel in the map found a universe in the stream.

## Files

| Path | What |
| --- | --- |
| `index.html` | the whole viewer: geometry, pixel map, ELM export, live input |
| `model.glb` | 6 MB scanned hall |
| `sound/tour.mp3` | the sound designer's 163 s mix for the ride (MP3 CBR 192k; the 24-bit master is `sound/llyod_gandelhall.wav`, ignored by git, and on Lloyd's Drive) |
| `sound/tap.mp3` | Lloyd's own synth pad for the dive (first 10 s of `legacy_synth_v9_detuned_nosuck_x2.wav`, kept as `sound/tap-synth.wav`, git-ignored): a low chord, the lift at 5.4 s, the high chord to 10 s |
| `sound/float.mp3` | the tesseract's float: 1.0 to 16.0 s of the master, ends crossfaded into a seamless 14 s loop, brought up 4.5 dB with the harmonics above 100 Hz lifted 6 dB; plays from Enter until the dive's file has joined |
| `sound/dive.mp3` | the dive to the kaleidoscope's end: 16.0 to 27.0 s of the master, cut from tour.mp3, played as a WebAudio buffer from the tap (the crash's onset at the fisheye's kick-in, its peak at full warp, then straight through the flash); the `<audio>` element only carries the tour from 25.85 s |
| `tools/dmx_bridge.js` | Art-Net / sACN → WebSocket bridge, zero dependencies |
| `tools/agent-setup.js` | the one command above, JSON-line output, zero dependencies |
| `tools/elm-fetch.js` | headless CSV / facts extraction over CDP, zero dependencies |
| `tools/serve.js` | local static server on 127.0.0.1:8877 for headless checks |
| `tools/run-bridge.cmd` | the double-click path for a human on Windows |
| `PLAN-agentic.md` | proposed `index.html` changes that would remove the remaining manual steps |

## The soundtrack (2026-09-02)

`sound/tour.mp3` is one file for the whole ride and it follows the page's clocks, never its own:
`trackStep(now)` in `index.html` runs every frame, asks `trackWant()` where the file should be for
the state the page is in, and re-seeks the element when the two drift more than 0.3 s. Two marks
place it, read off the file's envelope against the tour's cues: `TRACK.sw` = 21.9 s is the crash
that lands on the white flash (`boomStart`), `TRACK.t0` = sw + 2.5 + 1.2 + 0.25 = 25.85 s is the
tour's first frame. The dive joins the file at `sw - A.arr` (the landing time `approachStart`
precomputes by walking its own ease), the tour at `t0 + elapsed`, pauses and seeks through
`tourCtl` follow, the finale's rest lets the tail play out, and anything else silences and
rewinds it. While it plays the synthesised bed (`SND.master`) is ducked to 0. A server that
serves the file must answer HTTP byte ranges (206) or the browser cannot seek in it: `tools/serve.js`
and `tools/storyboard-notes.js` both do; GitHub Pages does. `window.dbg.track()` reports the
file's clock, the wanted time and the bed's gain for headless checks. The float (`floatWant`/`floatStep`)
is a WebAudio buffer looping on `SND.ctx` (sample-exact wrap, a gain fade that iOS honours, no media
notification): wanted from Enter while the object floats, fading out over 2 s from the moment the
dive's file is actually heard (which itself fades in over 3.5 s from that moment), off in a tour, a
roam, the rest, the tool's clips, or once the object has gone. On a free flight by hand the bed's
chord and riser stay up over the float as the build-up.

OFF since 2026-09-03 afternoon (`TAP.off`; Lloyd: take out the pad synth backing track), kept for a change of mind: under the dive and the kaleidoscope ran the tap synth (`TAP`, `tapStep`), a SUBTLE
backing at `TAP.gain` (0.16) beneath the designer's riser, crash and wash, which play as before: the
low chord starts on the tap on a seamless loop of itself (`TAP.a` to `TAP.b`), a second copy takes
over from `TAP.o2` s before the lift so that the lift (`TAP.tr` = 5.4 s in the file) lands on the
flash with the crash, to the frame (re-cued at `boomStart` if more than 120 ms out), the high chord
holds under the spin and dies through the iris. Lloyd, on hearing it alone: too loud; it is a
background backing track, the other sounds stay.
The loop's end is found by phase once decoded (`TAP.bFound`, ~4.415 s: a blend of anti-phase windows
dipped 6 dB at every wrap). Every WebAudio sound goes through `sndBus()`, a limiter, and while any
WebAudio sound is heard with the file paused a one-second silent element loops (`TRACK.keep`) so
iOS's ring/silent switch does not mute WebAudio. Levels (Lloyd, 2026-09-03 02:30: all a touch too
loud, the treble a touch too much): `LEVEL` = 0.708 (3 dB down) scales the float and the pad, the
bed's master is `SND.BED`, every WebAudio sound leaves through `SND.shelf` (3 dB down above 5 kHz),
and `tour.mp3` is encoded 3 dB down with the same shelf. The pad eases in over `TAP.ease` (2.5 s). The master's first 17 s were
lifted the same way in `tour.mp3` so the crossfade is level-matched.

## The float, the lock, Free roam, the kaleidoscope (2026-09-03)

- After Enter the sticks, keys, mouse look and the phone remote's move/look are LOCKED (`locked()`)
  until Free roam; the visitor taps the object or presses **Free roam**. The veil has no Free roam
  button any more: `#roamfab` sits on the stage above the bar while the object floats
  (`roamFabSync()` every frame, the same state the float's sound plays in), and after Stop tour
  (the object is gone then; Free roam is the way out of the lock).
- Free roam from the float (`roamStart` with the portal visible) is the SINK: over `ROAM.sink` (4 s)
  the object and its name shrink and drop into the void while the disc, the carpet hole and the spot
  close round the falling object (radius = the object's + a hand, capped at 1.7 m) and the eye glides
  to `ROAM_EYE` (`roamHome`: u 48.3, 0.6 m off the far wall; d 7.6, the centre line; 2 m up; looking
  down the axis) via `roamPathHome`/`roamGlideHome`, sideways to the axis first if the straight line
  clips a column; Free roam from the rest lands on the same spot, then the house rises to `ROAM.houseTo` (0.5) and a warm white
  comes over the columns (`roamSinkStep`). From the tour's rest, Free roam is still the fade from
  black. `portalReset()` brings the sunk object back whole on Start again; a sink cut short by Tour,
  or by an Event ticked mid-way, is closed out on the spot (`roamed`, `sunk`) for the same reason.
  The float's sound plays through the sink and goes out with the close.
- The kaleidoscope (`warpRender(1, ang, 4)`) draws the hall into the cube ONCE, without the object
  (the eye is still), and the object alone every frame into a second cube over a clear background
  (`warpObject`: cube cameras on layer 1, the object and lights enabled on it, `cube2`/`obj`
  uniforms composite it in the fisheye). The mirrors are frozen through it (`MIRROR_DEAL`). 7 cheap
  renders a frame, flat; before, faces dealt across frames left the object stepping at 15 Hz
  (Lloyd, 2026-09-03: the frame rate held but the picture was choppy). The cube size is pinned. Measured 66 -> 132 fps uncapped on the PC.
- `#roamfab` fades in (1.2 s, class `up`) only once the 5 s fly-in has landed on the orbit, and no
  sound at all starts before Enter Gandel Hall (`sndInit` refuses until `entered`).
- The dive's fisheye has a centre zoom (`WARP.pull`, 0.6; the `pull` uniform bends the radius r^pull):
  the object is magnified more as the view widens while the edge still reaches the full angle (Lloyd,
  2026-09-03: zoom into the tesseract a bit more as the field of view increases). 1 at the hand-over
  from the perspective camera and in the kaleidoscope.
- Resting sticks (2026-09-03): on a phone, once Free roam has LANDED the eye (`sticksSync`: sink glide
  done, or the fade from black done), MOVE bottom-left and LOOK bottom-right fade in at 50% (80 px
  rings). Each stays until its first touch, then shows while held and fades `STK.linger` s after
  release. They are live: a thumb within 64 px of the MOVE ring drives from its centre (`stickRing`,
  its knob follows), elsewhere on the left half it drives from the thumb's own spot with the ring's
  knob showing it (the floating `#pad` only appears when not roamed, e.g. a ?shot page); the LOOK knob
  leans with the drag and springs back. Gone with a tour or a shot.
- The soundtrack file is PARKED at its join point (TRACK.sw - 4.9 s = 17.0 s) while the object floats
  (`trackStep`, no-want branch), so the tap's seek is nil and the bytes are buffered; the join fade is
  1.5 s (was 3.5; Lloyd, 2026-09-03: the sound designer's sounds came in a little late on the tap).
- Soundtrack drift (2026-09-03, Lloyd: the sounds glitch/skip): the file is no longer seeked on small
  drift (a seek is a dropout on a phone); drift under 0.6 s is pulled in by playbackRate 0.95-1.05
  (`preservesPitch=false`), only a miss of 0.6 s+ seeks, and boomStart re-cues only past 0.6 s.
- The finale marks on the black are the PROPOSAL PAGE'S OWN LOGO IMAGES (2026-09-03) on flat planes
  (`MARK_IMG`, `markPlaneBuild` with the court, `markPlanes(dark)` swaps them for the sculptures):
  LOTRON+ELECTRICAL at W wide, ENTTEC and Shadow AV in EQUAL widths (0.45 W) centred on each other;
  the finale layout reads the partners' sizes from the planes. The court's 3D sculptures still wear
  the real colours (LOTRON samples tools/lotron-logo.png at the traced px in `logoMat`). BROUGHT TO LIGHT BY is flat. The lock holds
  through the tour and its rest (`locked`), so a thumb cannot turn the rest frame.
- The LOOK knob moves as MOVE's does: displacement from the ring's centre or the thumb's own spot.
- Event colliders (2026-09-03, Lloyd: no clipping into anything in the event scenes but confetti and
  tiny detail): `eventCollide()` after `scene.add(eventGroup)` puts every Mesh/InstancedMesh of the
  event into `solids` (people, tables, chairs, stage, lectern, booth...), skipping Points, additive
  materials (beams, pools) and anything under 0.25 m (tableware, candles); `eventSolids` are pulled
  out again on rebuild. `resolveMove` casts two rays, at the eye and 1.4 m under it, and an instanced
  hit's normal takes the instance matrix. Measured: from the roam pose a walk stops at the banquet.
- The wedding's last cut (2026-09-03, Lloyd): the aisle shot is 13 s and ends OVER THE COUPLE'S HEADS
  (from 6 s the eye lifts to 2.9 m and flies straight forward, LEVEL, no tilt, passing over them at
  about 11 s), fades to black 9.5-12.3 s, before it passes them and before it stops moving, and the finale's marks drop in on that black (`FIN.walk` 0, `bo` held at 1 until the
  drop). The walk out through the door is gone: `buildDoor` returns before building the leaf or the
  glazing opening (the wall is glass again), `finaleStart` leaves the couple to their own walk.
- The column wipe (2026-09-03, Lloyd, the speaker shot): the standing shot's line is clipped in screen
  space to the strip between the two NEAR columns' silhouettes, the row the eye sweeps past (`TITLE_WIPE`, `titleWipeHook`
  injects a discard on gl_FragCoord.x into every title material, `titleWipeStep` after the camera
  pose projects the columns each frame). The first column uncovers it, the second covers it; the
  shot arms `TITLE_WIPE.cols` each frame and tourStep clears it. The line keeps its normal size
  (Lloyd); its window is 0.6-14.2 s. NOTE the live
  text comes from storyboard/titles.json (fetched over TOUR_TEXT): change windows THERE.
- PROXIMITY (2026-09-03): every WebAudio sound leaves through `SND.prox`, set each frame by `proxStep`
  from the eye's distance to the object: a tenth at the hall end (HOME), a smooth curve to full at
  the orbit radius and full from there in, times a 2.5 s fade-in from nothing after Enter. Held at 1 through the crash, kaleidoscope, tour and rest, and once the object has sunk.
- The glass glitters like a diamond (GLASS_FRAG, 2026-09-03): 3 cm microfacets cut in each pane's own
  plane, 40% of them tilted a little; one flashes white when its mirror direction meets the spot
  above, the eye, or a fixed side light, so points come and go as the object turns.
- The object sparkles (`SPARK`): ~2.5% of its edge pixels flash white and die away over ~1.1 s,
  additive, only while it floats (not in the dive or the kaleidoscope).
- The veil's button reads "Enter Gandel Hall" on every device.

## Rules for an agent working in this repo

- Node 14+ is the only prerequisite. Nothing here uses npm packages; keep it that way.
- Never invent a number in a report. Read it from `--what facts` or the status endpoint.
- The page's own comments are the design record. Match their tone if you edit it: explain why, not
  what.
- Writes that a client would see (a live stream on a hall, a commit, a push) need the owner's word
  first.

## Zero-touch show file (measured 2026-08-31)

The saved show `ngv-gandel-hall.elm` now opens and outputs with no clicks. What makes that true,
and what does not survive a restart:

- **Live-deck playback persists.** A media playing on Live deck A (Water caustic, from the built-in
  library) is saved into the project and resumes by itself when ELM loads the file. This is the
  zero-touch mechanism.
- **Live media is PER STAGE** (corrected 2026-09-01). Launching a tile applies to the SELECTED
  stage only; the other stage keeps streaming BLACK sACN, which still counts as packets. That
  produced a false zero-touch pass on 08-31: the bridge counter climbed while every byte was 0.
  Verify content, not traffic — read a ws frame and count non-zero bytes (a page showing
  "608 universes heard" can still be a dark hall). The 00:15 save has media on BOTH stages.
- **Testing mode does NOT persist.** The Stage → Testing toggle comes back off after a reload, so
  never rely on it for a client hand-off; it is a bench tool only.
- **Run at startup is ON** (Settings → Project, mode "normal") and saved, so on a client machine ELM
  also launches itself at Windows login with the last project.
- Proof: kill ELM, relaunch with the show file, zero clicks — the sACN bridge counter climbs at a
  steady ~1,090 packets/s within 15 s of launch (all 608 universes).
- Caveat: unactivated ELM is in demo and blanks its output for a moment every few minutes. A real
  client needs a licence activated, or they will see the hall blink.
- **Import scale IS the media resolution** (measured 2026-09-01). ELM samples media per stage
  UNIT, and the import default "Fit largest side to 100 units" makes a 38 m hall sample at
  0.38 m per texel: ~21 LEDs per colour, which reads as low-density even though the patch is
  60 px/m. Import the CSV with Scale = "Multiply the file's coordinates", factor 0.06 (CSV is in
  mm, so 1 unit ≈ 16.7 mm = one LED) and the same media runs at per-LED resolution (measured:
  run length ~21 → ~2). Both stages in the 00:54 save are imported at ×0.06. Verify with a ws
  frame read: count identical consecutive RGBW pixels, target avg ≤3.
- **Never touch "Edit LED arrangement" on an imported stage** — it REGENERATES the DMX wiring
  from ELM's own scheme, silently breaking the CSV patch contract with the browser (proved
  2026-09-01: depth-slices change offset every universe). The import dialog is the only safe
  place for wiring, where "the file is the patch".

## 2026-09-03 (evening): lasers off the people, the kiss as equals, sticks off the rest screen
- Lasers (Lloyd): never point at people. The two units now hang at the ends of the stage truss
  (y0+7.35), rays leave slightly downward, every ray is cut at `LASER_FLOOR` (3 m above the floor)
  and raycast against `hallGroup` so a column or wall ends the beam. Blocking lengths refresh 4
  rays per unit per frame inside a 0.8 ms budget (`L.len`, `L.cursor`), the floor clamp is applied
  every frame. `window.dbg.party` exposes the rig for checks (`fx.lasers[].len`).
- Wedding kiss (Lloyd): no dip. Him over her with her leaning back read as the groom dominating;
  `dip` is 0, the kiss holds from 9.5 s until they straighten at 13 s, and his solved lean is
  capped at hers + 0.06 rad.
- Sticks (Lloyd): free roam, then a tour, and the finale's rest screen came up with the sticks
  (`roamed` was still true). `sticksSync` now also requires `!finale && !restFinale`.
- Kiss heads (Lloyd, later): the heads must TOUCH, not clip and not hover. Tuned by measurement
  through `window.dbg.wedding.cp.hm` instance matrices: target 23 cm ahead / 14 cm across lands
  the centres 23.0-23.2 cm apart against a 23.1 cm touch distance (the solve undershoots ~4.5 cm).
- Tap sound latency (Lloyd, 2026-09-04: the sounds on the tesseract tap still came in late). Two
  causes, both fixed: the join was a slow crossfade (file in 1.5 s, float out 2 s), now file in
  0.5 s and float out 0.8 s (`trackStep` join, `floatStep`; the void-close fade keeps its 2 s,
  scaled onto the same 0.8 s curve); and the file was parked at a FIXED 17.0 s (sw - 4.9), which
  is only right for a tap from the orbit: `trackPark` now re-reads the landing time from the eye
  twice a second (`approachArr`, the same walk `approachStart` uses) and re-parks past 1 s out, so
  a tap on the fly-in is not a 5 s seek. `window.dbg.approach` exposes the dive for checks.
- Finale marks (Lloyd, 2026-09-04: took too long to arrive, then came in too fast): `FIN.pan`
  1.5 -> 0.6 s (the aisle shot already ends on ~0.7 s of black), `FIN.drop` 5 -> 3.2 s, and the
  drop's curve is `smooth` (ease-in-out glide) instead of the cubic ease-out that entered at full
  speed. The finale is now 6.3 s, so a script placing the wedding by the tour's total uses
  total - 6.3 - 13 - 14.
- Credits (Lloyd, 2026-09-04): SPECIAL THANKS under the partners, Patrick Connell (Photogrammetry
  & 3D) left, Gabriel Fischer (Sound design & music) right. `creditsBuild(L)` draws them once to a
  canvas (IBM Plex Sans) on a W x 0.30 W plane hung in the Lotron mark's group (`logo.userData.cred`,
  `userData.img` so `markPlanes` shows it on the black), placed by `finaleLayout` (`credY`,
  `credH`); the whole stack above moved up by `credH + 0.55 H`. Checked at 412x915: clear of the
  rest buttons.

## The Install (game mode, 2026-09-04, PRIVATE: not linked from the proposal page)
`game/*.js`, spec in `GAME-PLAN.md`. It USED to be its own page sharing only `model.glb` and
`runs.json`; since 2026-09-04 it is a keyed mode of `index.html` (see "Install mode" at the end of
this section) and `game.html` is gone. Built by Codex from the spec (two rounds; round
one had the clock at an hour per second and the spawn inside a solid box). Check it headless with
`node tools/game-check.mjs` (serve on :8877, chrome via headless-chrome.sh on 9333; it prints the
HUD text and console errors and saves %TMP%/game-1.jpg, the phone view after Start Shift).
Phase 1 = world, controls, lift, pallets/boxes/wrap, fitting, clock, clean-up rule, save.
Phases owed at the time: 2 fatigue + hallucinations, 3 the crew's AI, 4 sound. All four are in
(the crew as five people you allocate, 2026-09-06, not the helper-and-team AI first sketched).
- 2026-09-04 (Claude, no Codex from here): DOUBLE DOORS at the storage doorway (`world.js`: two
  leaves hung 0.3 m on the hall side of the wall line, swinging 100 degrees into the corridor for
  anyone within 3.2 m; a parked lift does not hold them; shut = a wall in `collideWorld`). The
  scanned wall is solid there, so every hall material discards fragments inside the door volume
  (`onBeforeCompile`; the appended vertex line MUST start on a new line, the chunk ends in
  #endif). The lift is Genie-styled (`lift.js`: blue chassis + cage, grey 5-pair stack). `fx.js`:
  fatigue vignette from 01:00, from 03:00 vanishing fitted lights, leaning columns, colour drift,
  breathing FOV, a ghost lift. Clean-up counts the lift, jack and bags. Off the lift only at ground.
  Visual checks: `tools/game-look.mjs`, `tools/game-look2.mjs` (contact sheets in %TMP%).
- THE FIXTURE, and THE GUIDE (Lloyd, 2026-09-04): the light the game fits is no longer a 55 mm
  white box. `game/fixture.js` is the proposal sim's default fixture ported out of `index.html`
  `rebuild()` as an importable module: the constants (EXT_W/EXT_D/EXT_BACK/FACE_W/WALL/TILE_T,
  LEDS_PER_M 60, DIFFUSER_T 0.25, EMIT_EXPOSURE, HALO_PEAK/HALO_MEAN, gsize 0.08) and the same
  basis and offsets, so a fitted section is a 20 x 20 mm extrusion on the shaft valley, a 16 mm
  black acrylic cover on its face, 90 emitter tiles at 60/m and 90 halo discs 1 mm proud of the
  aperture. `FixtureSet` holds the WHOLE hall in four draw calls (2,304 ribbon boxes, 768 covers,
  69,120 emitter instances, 69,120 halo points) and hides an unfitted slot with a zero-scale
  matrix and a zero colour. **`index.html`'s `rebuild()` should import this module next**: while
  the sim keeps its own copy of the geometry the two WILL drift, and the game would stop showing
  the product the proposal sells. Per-LED meshes stay Phong/Lambert/Basic (the sim measured
  MeshStandardMaterial halving the frame rate at 73k instances).
  The guide: `install.guide`, default OFF (Lloyd, 2026-09-07: "have the guide turned off by default"; was ON), remembered in localStorage `ngv-install-guide`, toggled
  by `#guide` at the right end of the HUD (#hud is pointer-events:none, so the button opts back
  in; 44 px tall for a thumb). On, every EMPTY slot stands as a pulsing red bar (one
  InstancedMesh) and every FITTED one pulses green through its own fixture colour, at 1.2 Hz from
  `install.update(t)` in the main loop; off, no bars and steady strip white, and `update` returns
  on one comparison. `fx.js`'s vanishing light calls `install.showSlot(slot, bool)` now: there is
  no per-slot mesh to hide any more. Check: `node tools/game-guide.mjs <outdir>` (matrices,
  colours, the cover landing 0.4 mm off `slot.center + normal*0.009`, the toggle, and fps with
  all 768 in: 135 fps headless on this machine).
- Stamina + fatigue (Lloyd, 2026-09-04): `body.js`. Stamina drains with effort (carry 4/s, jacked
  pallet 7/s, riding the lift 1.2/s), recovers at rest (9/s standing, 4/s walking, slower as
  fatigue rises); under 15 you crawl, under 10/15 you cannot take a box / jack a pallet. Fatigue
  climbs with the clock (2/h to 01:00, 6, 12, 20/h in the last hours) plus a tenth of stamina
  spent; it lowers the stamina ceiling (to 40 at 100) and speed (to 55%), and drives the small
  hours (`fx.levelFor`: from 70 fatigue). Two bars under the HUD. Reach is measured on the floor
  plan (`items.js near`): the old straight-line reach from the eye never got a bag on the floor.
  Boarding the lift is by ACTION only; your lift parks at (63.6, 6.6), your jack at (65.0, 4.4)
  (`resetForNight` in items.js is the authority; the crew's two of each park in front of them).
- Crew (2026-09-04, REPLACED 2026-09-07): `crew.js`. It used to unlock by columns done -- a
  helper after one, then a team of two per column after that. That progression is gone: five crew
  are on the floor from 17:00 and you tell each of them what to do. See "The crew you allocate"
  below. `tools/game-crew.mjs` (the old unlock script) is deleted; `tools/game-crewtasks.mjs`
  replaces it.
- Hall rendering (2026-09-04, Lloyd: same MODEL as the viewer, not necessarily the same look):
  the game loads the identical model.glb and runs.json. `hallmat.js` is a trimmed port of the
  viewer's photoMaterial (albedo x house light, unlit by scene lights) with the viewer's renderer
  settings, and every fitted run is one of the viewer's 96 analytic line lights (12 x 8 runs), so
  fitting a run washes the column and floor the way the viewer's strips do. The viewer's
  procedural canopy lattice is NOT built; the GLB's own canopy is shown.
- Sound (2026-09-04): `sound.js`, all synthesised: lift motor hum while moving (detunes with the
  fx level in the small hours), thuds for boxes/lights/bags, wrap crinkle, fit click, jack scrape,
  door swing, 04:30 pack-up chime, 05:00 bell. Cues are read off the prompt label that was pressed.
- Pacing (estimate, not field-run): one box = one run (8 lights); the lift comes down for every
  box (12 m at 0.5 m/s each way), so a solo column is ~12-13 min = about one night. What the crew
  add to that is now yours to decide: two fitters on two crew lifts with a feeder each is roughly
  three columns a night, one fitter working alone about one and a half (2026-09-07: the helper /
  team unlocks that used to set this are gone, see "The crew you allocate"). The lift already
  rises 2-3x faster than a real GS-4046.
- Storage + collisions (Lloyd, 2026-09-04: larger storage, nothing clips; the east end and the
  stacks 2026-09-06): the corridor is 22 x 9 m (u 48.9-71, d 3-12), pallets in two rows of six
  (`palletHome`: N row d 4.5, S row d 10.5, 2.3 m apart) with a 4 m aisle, lifts and jacks at the
  aisle's end, the five ply stacks in the back bay past both rows, bags by the end wall, the skip
  at u 73.6 outside a person-sized opening (a lift stops at the wall). `refreshObstacles`
  (items.js) rebuilds a plan of circles every frame (pallets 0.95, boxes 0.4, bags 0.45, lifts two
  of 0.85, ply stacks two of 0.72, skip 1.9) and `collideWorld(pos, r, world, ignore)` pushes every
  mover out of them; a mover ignores what it carries and the lift it rides. Reaches must sit
  OUTSIDE the collision radii (pallet 1.5, skip 2.6/2.9) or the crew walk forever.
- Lift driving + deck (Lloyd, 2026-09-04: "drive more like a real scissor lift", "walk up to the
  control panel and then choose to drive or not", "get on from 1 end"): `lift.js` keeps ABOARD and
  DRIVING apart. You board from the BACK end only (`Get on lift` needs you within 1.7 m of the
  steps, `offboardWorld`, local -x); aboard, `walkDeck` moves you in chassis coordinates
  (`deckLocal`, clamped to 1.1 x 0.45) and `place` puts you on the deck, so the deck carries you.
  The control box hangs on the inside corner of the front end rail (`panel`, local +x +z, hood
  hooked over the top rail, console facing the deck). Within 0.75 m of `PANEL` ACTION =
  `Take the controls` (`driving`), ACTION again = `Let go`. Only while driving: stick/WASD is
  throttle (fwd/back) + front-wheel STEER (left/right), UP/DOWN move the deck (`body.driving`
  shows #liftBtns). Drive model: ramp ~1 s, brake 2x harder on release, 0.97 m/s stowed easing to
  0.22 m/s once the deck is 0.9 m up (Genie GS-2646 numbers), bicycle steering on a 1.7 m
  wheelbase with 0.6 rad lock: NO turning on the spot, the yaw only changes while rolling, and the
  player's yaw turns with the deck. A push-back against the travel from `collideWorld` stops the
  machine; a sideways nudge (sliding along a wall) does not. Front hubs show the steer angle,
  wheels spin. A light put down on the deck (`light.onDeck`) rides in chassis coordinates
  (`updateItems`). `tools/game-drive.mjs` proves the whole sequence: board, walk to the box, take
  controls, ramp, steer while rolling, steer without rolling (yaw unchanged), creep raised, let go,
  walk back, get off. Gotcha: `node --check` did NOT catch a duplicate `const` inside a method;
  the headless load did (SyntaxError in lift.js): the browser load is the gate, not --check.
- Drift root cause (2026-09-04, commit 7bdf556): `HALL.u` / `HALL.inRoom` in `world.js` were
  built 0.0001 short of unit length, so every world -> hall -> world round trip in `collideWorld`
  moved a mover 0.6 mm towards the d=0 wall: a 3.6 cm/s slide with no input. Basis vectors are
  normalised; `tools/game-drift.mjs` holds six no-input cases at zero movement and is the gate for
  any collider change.
- Prompt as the button (Lloyd, 2026-09-04: "I don't like the action button", "can tap on them",
  "on the side so they don't take up much viewing space"): the ACTION button is GONE. `#prompt`
  is tappable (`pointer-events:auto`, click -> `player.actionQueued`, `.can` class while
  `action.run` is non-null). On coarse pointers it sits right-aligned at right:12px bottom:246px,
  max-width 46vw, above the look stick; `#drop` took ACTION's old spot. `tools/game-tap.mjs`
  dispatches a real touch on it at 412x915 and expects the action to run.
- Look stick hold-to-turn (Lloyd, 2026-09-04: "hold a direction and keep turning"): on top of
  the drag look, a thumb held more than 26 px from where it LANDED (`active.down`, not the stick
  centre) sets `player.lookRate`, applied in `update` as yaw 2.4 rad/s, pitch 1.6 rad/s at full
  deflection (full at 66 px). Measured from the landing point so a resting thumb never turns.
  Reset on release, letGo and pointerdown.
- Lift steps, gate, climb (Lloyd, 2026-09-04: "an animation of climbing up on to the scissor
  lift"): the stowed deck is 1.25 m up (`Lift.DECK_Y`); the scissor stack is confined to
  [0.81, deck underside - 0.12] with 0.08 m arms, so folded arms no longer poke through the deck
  plate (the old 0.2 m span floor did). The steps are a VERTICAL ladder flush on the back
  face of the chassis (`Lift.LADDER`, x -1.27, rungs 0.28..1.09, Lloyd's Genie/JLG photos: nothing
  sticks out behind the machine); the climb goes straight up it. The back end is two short rail panels
  either side of a full-height DOOR, the centre third (z -0.2..0.2), `lift.gate`, hinged on the
  z -0.2 post and swinging into the deck (`rotation.y = GATE_OPEN` = a right angle; it then lies
  along the deck at z -0.2, clear of everything). A 0.12 kick plate runs all round the deck edge
  except the doorway; the door carries its own top bar, mid bar and kick plate (Lloyd, 2026-09-04). `board(player)` and
  `leave(player)` run `lift.anim` (`startAnim` / `stepAnim`): walk to the foot of the steps (local
  x -2.0), up the ladder standing as the door swings open, through the doorway onto the deck, stand at `DOOR` as the gate drops; leaving walks the same frames backwards. While
  `lift.anim` runs `nearestAction` returns 'Climbing aboard' / 'Climbing down' with run null, F is
  ignored, and yaw eases to face along the lift. `board(p, true)` / `leave(p, true)` are the
  instant forms for scripts (game-drift uses them). `tools/game-drive.mjs` waits the climb out and
  asserts the eye stayed standing (over 1.6), the door opened past 1.5 rad, and (Lloyd: "no clipping please",
  a STANDING RULE for every 3D change) that the camera point never entered any lift mesh's world
  box during the climb, both ways; `tools/game-liftlook.mjs`
  shoots the lift from the back quarter, raised, mid-climb and aboard.

### Wheels in the floor (Lloyd, 2026-09-04, phone screenshot 14:13)
- The scan floor is not level: measured by rays, it rises 0.0092 m per metre across d and 0.0005 m per metre along u (10 cm over the hall). The lift, the crew and every dropped thing stand on the flat `HALL.floorY`, so the tyres sat up to 10 cm inside the tiles.
- Fix: `world.js levelScan()` fits the floor plane at load and rotates the scan about a floor point until it is flat at `HALL.floorY`. The scan lives inside `world.hallSway` because `fx.js` writes that group's `rotation.z` for the sway (writing the scan's own rotation wiped the levelling, which is how the first attempt failed).
- Proof: `node tools/game-floorcheck.mjs` (needs the :8877 serve and headless Chrome on :9333). Samples the floor under 274 hall points and every lift part stowed, raised and parked in the hall: PASS = level within 1 mm and nothing below the floor. CDP drivers must `Network.setCacheDisabled` or they test the cached modules.


### The storage doors at the real east wall (2026-09-08)

The scan's east closure at u 48.9 was 2.85 m short of the real wall; the walls pass cut it out
and built the stone end wall at u 51.906 with the photographed gallery recess (d 3.9 to 11.5
from 1.8 m up). The storage doors keep the hall's centre line, d 7.5, where the crew's routes,
the pallet aisle and the board grid meet them (a pier door at d 2.0 was tried: the straight
corridor routes then cross the south pallet row and the machines stall): `HALL.doorU` 51.906,
`HALL.doorD` 7.5, 2.5 m wide; the walls pass cuts the doorway through its end wall with the
`door` uniform. Everything behind the wall moved +3.0 m with the door line (corridor u 51.906 to
74; pallets, skip, lights, spawns, the crew's corridor spots, the board grid, which is anchored on
the door line) and `hallmat.floorArea` is 51.5 x 15.4. The proofs
`tools/game-boards.mjs` and `tools/game-crewtasks.mjs` carry the new door line.

### Install mode: the game lives inside the sim now (Lloyd, 2026-09-04)
- Lloyd's ruling: the game is not a page of its own. The Shopify shop iframes
  `.../ngv-hall-model/?embed=1`, so the proposal sim IS the product and the night shift rides
  inside it, the way "Event" does. `game.html` was deleted.
- THE KEY. `index.html?install=gandel-2026` stores the key in `localStorage['ngv.install']` and
  reloads without the parameter, so the address bar never carries it and a shared link stays an
  ordinary link. `INSTALL_KEY` is the first thing in the module script; change it there. Without
  the stored key the settings panel's Install row is hidden and NOT ONE BYTE of `game/` is
  fetched (the modules are a dynamic `import()` inside `buildInstall`). `?embed=1` changes
  nothing: on Lloyd's own device the row shows inside the shop page too, which is intended.
- ONE SCENE, ONE LOOP, ONE HALL. `buildInstall()` / `teardownInstall()` sit next to `buildEvent`.
  The game gets the sim's `scene`, `cam`, renderer and `frame` loop; there is no second
  `model.glb`, no second hemisphere, no second animation loop. `installStep(dt, now)` is the old
  `game/main.js` loop with its render taken out, called from `frame` before the boom/warp early
  returns so everything still routes through `done()`. `loadWorld` was split into `makeWorld` (the
  datums and the plan) + `buildProps` (everything the game adds), and all of it goes into one
  group, so teardown is one `scene.remove`. `world.js setFloorY` takes the sim's measured
  `FLOOR_Y`, so the two agree instead of both carrying -1.435.
- THREE GROUPS, THREE WRITERS: `hallSway` (fx's small-hours roll) wraps `hallLevel`
  (`levelHall`'s floor levelling) wraps `hallGroup` (`applyColumnHeight`'s scale). Nothing writes
  over anything else, and both wrappers go back to identity on teardown.
- THE SEAM THAT MATTERS: the fitted lights ARE the sim's strips. `installMask()` builds a
  `Uint8Array` over `P.n`, pairing the sim's runs to the game's by (column, gap) and lighting an
  LED only if its distance up the run is inside the fitted slots; `animate()`'s last loop skips
  the rest in one place, so an unfitted light is dark in the render, the lumen and watt readout,
  the blade weighting and the light thrown on the room. Every change sets `sceneDirty=true`.
  `hallmat.js` is NOT imported into index.html. Note the geometry: 8 slots x 1.5 m = 12 m of a
  12.75 m run, so the top 0.75 m of a fully fitted run stays dark. That is the fixtures, not a bug.
- The game's `Player` binds through `player.on()` and `unbind()` takes every listener off again;
  `Sound.close()` shuts its AudioContext so a second toggle does not stack another motor hum. In
  game mode the sim's own fly keys, sticks and `resolveMove()` stand aside and the game's collider
  drives `cam`. `body.install` hides the viewer's controls and takes the stage full screen.
- CHECKS (serve on :8877, headless Chrome on :9333 via `bash ~/scripts/headless-chrome.sh start
  9333`, never `--disable-gpu`): `node tools/install-mode.mjs` is the new one and proves the gate,
  the build, the teardown (scene children, `solids`, camera children and rAF ticks all return),
  the mutual exclusion with an event, and that the plain sim renders the same picture afterwards.
  `node tools/game-guide.mjs "$TMP"`, `game-drive.mjs`, `game-check.mjs`, `game-floorcheck.mjs`
  now all drive `index.html?install=gandel-2026` and tick `#install`; they read `ngv.game`, not
  `window.game`. Measured after the merge: 133 fps in the hall, 104.8 fps with all 768 fitted and
  the guide on (game.html was 133).
- KNOWN, NOT FIXED: switching an event ON and OFF again leaves its solids in `solids` (69 -> 108
  -> 108). That is the sim's own behaviour, older than install mode; `tools/install-mode.mjs`
  therefore counts colliders around the install toggle alone.

### Doors, tags, sign, deck physics, ceiling, proximity, reticle (Lloyd, 2026-09-06)
- DOORS (Lloyd: "we shouldn't be able to clip through the doors"): each leaf is a segment collider
  on the plan (`world.doors[i].seg`, hinge to tip, recomputed in `updateDoors`), pushed against by
  `pushSeg` for every mover; the door line stays a wall until BOTH leaves are past 0.75 open
  (`world.doorsClear`, about 85 degrees), and a mover may not change sides of the line in one step
  before then (`lastSide` WeakMap keyed on the mover's own Vector3; a jump over 2 m is a teleport
  and is let through). The jambs are solid (a mover in the wall's thickness outside the opening is
  put back on its own side). Proof: the door block of `$SCRATCH/t1.mjs` (sprint at the doors, walk
  into the jamb).
- STORAGE sign over the header (`textTexture` canvas on a PlaneGeometry facing -u, `world.sign`).
- COLUMN TAGS ("we need to know which column is which"): every column wears its label twice
  (`world.tags`, 24 Sprites, room side and wall side, 3.0 m up, yellow on black).
- PICK UP / PUT DOWN ("anything we can pick up, we need to be able to put down and pick back up"):
  the prompt never says "carry it somewhere" with nothing to tap: `Put empty box down`, `Put wrap
  down`, `Put rubbish bag down` / `Put empty bag down`; `Take box off the lift` (full box, aboard or
  from the floor beside a lowered lift, `takeBoxOffLift`); `Take empty bag` (an empty bag can be
  carried to the work); a bag is only disposed when full. F / the DROP button still drops anything.
- ABOARD PICK-UP: `pickable()` (lights, boxes, wraps, full bags in reach, chosen by the smallest
  angle to the view direction, `aimed`) is offered before the lift's own prompts when aboard.
- RETICLE DECIDES (Lloyd, 2026-09-06: "the reticle should determine what option we are given"):
  `nearestAction` casts a ray from the view centre (3.4 m) against lights, boxes, bags, wraps,
  pallets, the jack, the lift group, the skip and the column colliders; the first owner hit plus
  what is in your hands decides the prompt (`player.aim` carries the hit). A miss falls back to
  the nearest small item within about 8 degrees (bars are sampled along their length). Place
  prompts stay position-based: the lift's controls and door, setting a pallet down, letting go of
  the controls. Nothing in view = "Point at something". `findFitSlot` / `nextSlotNear` take a
  column filter so a light fits on the column you point at. 26 px +, green (`#reticle.can`) when
  the action can run. Proof `tools/game-doors-deck.mjs` (also doors, tags, sign, deck physics,
  ceiling cap, readouts, ring); `game-drive` / `game-tap` now face the lift before expecting
  "Get on lift".
- DECK PHYSICS ("the lights can't clip when they are dropped onto the scissor lift"): `DECK_WIN`
  (1.2 x 0.55 inside the rail posts) and `HALF` per type; a body captured on the deck is clamped
  inside the rails by its half-extents and a bar turns to lie along the chassis; a body sliding on
  the deck is held by the rails; under a raised deck or inside the chassis footprint it lands on
  the tray (`CHASSIS.top` 0.76); a body is collided against the plan in the air too (it used to
  fall through the chassis), with the lift's circles ignored above the deck line; loose bodies
  keep out of each other on the plan. `toss` while ABOARD = a short drop onto the plate inside the
  rails (never a lob over the side), `items` passed in for the lift.
- CEILING ("scissor lift shouldn't be allowed to go through the ceiling"): index.html rays up from
  the deck against `hallLevel` + `canopy.mesh` five times a second while aboard -> `lift.ceilingY`;
  `Lift.maxHeight()` = ceiling - floor - deckY - HEADROOM (EYE + 0.15) clamps the drive;
  `lift.clearance()` feeds `#deckh` (DECK x m, CEILING y m; amber under 1.5, red under 0.3),
  shown whenever aboard, top right under the Crew/Guide buttons.
- PROXIMITY ("show a proximity to nearby objects in the scissor lift icon"): `W.proximity(world,
  lift, n, reach)` walks a probe out from the chassis edge in n directions until the collider
  pushes it (walls, columns, doors, pallets, other lifts); `#wheels` grew to a 160x200 viewBox with
  a ring and `#wprox` dots (green / amber under 0.8 / red under 0.35 m), 5 Hz while driving, plus
  the deck height text `#wht`.

### Inventory + movable bags (Lloyd, 2026-09-06)
- `player.inv` is four slots; `player.carry` is a getter/setter over the ACTIVE slot (`active`),
  so every existing `player.carry = x / null` still works: null clears the active slot and moves
  the hand to the next occupied one, an object replaces what is in hand (the unwrap). Pick-ups go
  through `player.stow(item)` (first free slot, becomes active). `Player.BULK`: a box is two of
  the four units, everything else one; `canTake(type)` gates every pick-up ("Hands full"). Only
  the active item's mesh is visible in the hands (`showHands`). Keys 1-4 and a tap on `#inv`
  (`data-slot`) select; F / DROP drops the active one. `#inv` sits under the stats block and the
  stamina bars, at a `top` hud.js measures (`stackHud`); on a phone it is a 2 x 2 block 106 px wide
  and it is HIDDEN while you drive. Redrawn only when its signature changes (`G.invSig`). Stamina
  load reads the whole inventory. Action order in `nearestAction`: hands x target combos, then the
  target as a pick-up when there is room, then hand-only fallbacks.
- Bags: any bag (empty, part full `Take rubbish bag (n/8)`, full) can be carried and put down; the
  crew skip a bag anyone is already carrying (`b.carried`, set on every stow). Proof:
  `tools/game-inventory.mjs`.

### Floor protection + the crew's tasks (Lloyd, 2026-09-06)
The two changes of 2026-09-06 arrived together and they only make sense together: read this first,
then the two sections under it for the detail.
- WHAT. A scissor lift may no longer touch the gallery carpet: it drives on ply floor-protection
  sheets, which somebody has to carry out of storage and lay. And there is somebody to do it -- the
  crew is five people from 17:00 and every one of them does the job YOU give them, instead of
  unlocking themselves by columns done and picking their own work.
- WHY TOGETHER. Boards are the job that has to happen before any other job in the hall, so the
  moment they existed the game needed a way to tell a person to go and lay them. That is the task
  sheet. It is also why a fitter can be stopped for a reason that is nobody's fault: his machine is
  out of floor and the boards worker has not reached him yet (`waiting for boards near N3`).
- WHERE IN THE CODE. `world.js` owns the sheets (the 1.2 m grid, `protectedAt`, `boardBlock`,
  `laySheet`, `restoreSheets`); `lift.js` owns the wheel rule for both the driven machine
  (`drive`) and every machine nobody is driving (`roll`); `items.js` owns the stacks, the ghost and
  the hands; `crew.js` owns the five, their `assign` / `status`, the seven tasks and the board
  plans; `index.html` owns the task sheet (`openTaskSheet` / `taskSheetPaint` / `crewWire`) and the
  panel's Tasks tab. `game/main.js` (the old standalone entry) is kept importing, not run.
- WHAT IT COST. The corridor grew 5 m east to hold five pallets of ply, the pallets moved off the
  middle of the hall, and both jobs found the same class of bug: a walker or a machine that stops
  half a metre short of the doorway and never moves again. `travelGoal`, `crossGoal` and the
  `CROSS` reaches are the answer and they are load-bearing -- change one and re-run the crew proof.
- PROOFS. `node tools/game-boards.mjs <outdir>` (21 steps) and `node tools/game-crewtasks.mjs
  <outdir>` (11 steps). Both drive real frames in headless Chrome and both assert, every frame,
  that no crew machine has a wheel on unprotected carpet. `tools/game-crew.mjs` (the old
  unlock-by-columns script) is deleted.
- WHAT THREE REVIEWS CHANGED THE DAY AFTER (Claude, 2026-09-07). Nine defects, all in how the two
  features MEET the screen rather than in either feature itself:
  - A REASON IS FOR WHILE YOU ARE PUSHING AT IT (`lift.drive`). `blocked` was written on the way
    past the collider and never reached again once the machine stood still, so the first stop at
    the end of the ply pinned "lay floor protection ahead" over the prompt for the rest of the
    night. It is cleared whenever the machine is parked. Guarded by game-boards step 13.
  - AND A STOP WITHOUT A REASON IS A BROKEN CONTROL (`Lift.BUMPED`). A crew machine on the road
    held the player dead with the stick forward and nothing on screen; a crew lift cannot be aimed
    at, either. Frame by frame a held machine looks like it is moving (it creeps in, is shoved
    back, ramps again), so the test is over a 0.6 s window: metres asked for against metres got.
    game-boards step 21.
  - A BOARD IS NOT A BOX (`crew.putDown` -> `dropSheet`). Every "put down what you are holding"
    path dropped a 2.4 m sheet on the floor like a carton: in neither `world.sheets` nor a stack,
    and 150 sheets quietly became 149. It is laid where he stands, or goes back on a stack.
  - NOBODY IS SNAPPED ONTO A DECK HE IS NOT ON (`doFit`). Two `rideDeck` paths could be reached by
    a fitter who was away fetching a box: 6 m along the hall and 1.3 m up in one frame.
  - THE COLUMN PICKER (`#tsCols[hidden]`). `hidden` loses to `#tsCols{display:grid}`, so the last
    member's twelve column buttons stayed painted and live under the next member's "Stand by".
  - THE POINTER (`player.js`, `closeTaskSheet`). A click on the open task sheet grabbed the mouse
    back; Esc out of it left a desk with a free cursor, no pause screen and the keys still live.
  - THE LEFT-HAND STACK (`hud.js stackHud`). The four clock chips wrap to three rows on a phone
    and everything under them had a fixed `top` written for one row: the stamina bars printed
    through "0 / 768 lights", the slots sat inside the UP button. The bars, the slots and the deck
    read are stacked under the measured block now. Nothing on the driving HUD touches anything at
    412 or 360 (repro harness + game-boards step 17).
  - A CARD OVER THE HALL OWNS THE SCREEN. The prompt pill was drawn over the crew panel and took
    the taps meant for a name; the toast was drawn UNDER the panel. Pill hidden while either card
    is up (`body.panelOpen` / `body.sheetOpen`), toast to z 7, panel opaque.
  - One crew line at a time: two toasts queued in the same frame used to show the first for a
    single frame.

### Floor protection: the lift drives on ply (Lloyd, 2026-09-06: "for the install sim, we also need to put down floor protection before we can drive the scissor lift on the carpet")
- THE RULE. The hall floor is the gallery's CARPET. A wheel may only roll on the concrete corridor
  (u >= 48.9) or on a laid ply sheet. `Lift.drive()` and `Lift.roll()` both take the step back
  whole (position AND yaw) when `world.boardBlock` names a wheel that WAS protected and would not
  be; a machine already standing on carpet is never wedged, so it can always drive back out.
  `lift.blocked` = `Lift.NO_BOARDS` puts the words in the prompt and turns `#wchassis` red.
- THE SHEETS. 2400 x 1200 x 18 mm, `world.sheets` = `{u, d, along, mesh}` on a 1.2 m GRID: lines
  at u = 48.9 - 1.2k (the first is the door line) and d = 0.3 + 1.2k. `along:'u'` runs the 2.4 m
  side along the hall; the default is 'd', so a spine from the doors is laid crosswise like a
  plank road. `snapSheet` / `sheetRect` / `protectedAt` / `sheetSpotWhy` / `laySheet` /
  `liftSheetUp` / `restoreSheets` are all in world.js. A sheet is NOT a collider and NOT a step.
- THE STACKS. `items.stacks`: five pallets of 30 sheets in the corridor's BACK BAY, past both
  pallet rows, long side across the corridor so the lane to the skip stays open. They could not go
  in the aisle: a 2.4 x 1.2 m stack there stands exactly where a person must stand to reach a
  light pallet (the inventory proof caught it) and on top of the crew's jacks; and a strip behind
  a pallet row is walled off, because a straight-line walker cannot pass between two pallets
  (0.4 m of gap). So the corridor grew east: `corridor.u1` 66 -> 71, the skip 68.6 -> 73.6, the
  bags to the new end wall, the install seal box 8 m longer. Two circles of r 0.72 trace a stack
  on the plan, not one of 1.3: one fat circle closes the lane the machines drive to the doors.
- IN THE HANDS. `Player.BULK.sheet = 4`: a sheet is the whole inventory. `items.ghost` shows where
  it would land every frame (green 0x35d06a valid, red 0xd94a3a not), snapped to the grid within
  3.8 m of your feet; R or the phone's TURN button flips `items.sheetAlong`. Invalid = off the
  grid, over another sheet, over a column, over anything on the plan EXCEPT a lift (the boards are
  FOR the machine: the next board always goes down inside its own plan circles), or across a door
  leaf. F / DROP lays it or does nothing; a 20 kg board is never tossed. A laid sheet comes back
  up unless a wheel stands on it.
- THE CREW. Every lift a crew moves goes through `Lift.roll()`, so the wheel rule cannot be
  forgotten in one of them. While the machine still has ground to cover the FEEDER's job is the
  boards, not the stock: it fetches one sheet a trip and lays it where `nextBoardSpot` says (see
  WHICH CELL THE CREW LAYS below: the cell that carries the most wheels, not simply the first
  uncovered one on the line). Two waypoint helpers keep them off the walls:
  `travelGoal` (a machine lines up on the 2.5 m opening before driving through it) and `crossGoal`
  / `walkVia` (a person does the same). A team ignores its OWN machine on the plan: the lift's two
  circles are a fat bound of a 2.4 x 1.15 chassis, and the feeder has to get past it in a doorway.
- SAVE. `saveGame(clock, install, world, items)` writes `sheets: [[u,d,along]...]` and
  `stackSheets`; `restoreSheets` + `restoreStacks` rebuild them on load. `resetForNight` puts the
  stacks home and LEAVES the sheets down (the protection stays for the whole job); `cleanupClear`
  counts a stack on the hall side of the door line as `board stacks` and never counts a laid
  sheet. net.js does NOT sync sheets: a crew room sees only its own boards.
- WHICH CELL THE CREW LAYS (Claude, 2026-09-07, after the first version left every team standing
  in the doorway all night). The board goes UNDER the wheel that ran out of floor, and which of the
  cells that reach that wheel matters: two wheels on an axle are 1.24 m apart, so one 2.4 m sheet
  holds the pair only when it is laid BETWEEN them. `world.sheetCells(u, d, along)` names the one
  or two grid cells that would land under a point; `nextBoardSpot` scores them by how many wheels
  each would put on ply (bare ones counting double), tries both orientations (near the doors the
  swinging leaves rule one of them out) and only walks up the travel line when none of them can be
  laid. It returns null rather than stacking ply on ply. Snapping to the wheel's own nearest grid
  line instead laid the board BESIDE the wheel it was meant to save, two boards wasted per row.
- CLEAR THE DOORWAY BEFORE TURNING OFF (`travelGoal`). A machine that starts across the room the
  moment its nose is inside drags its back corner over the door line, where the leaves sweep and
  no board may be laid: it now drives up the middle to 3.4 m in first, which is what a driver does.
  The feeder boards toward the same goal the machine is steering for (`T.goal`), not the column.
- THE WAYPOINT DEADLOCK (`CROSS` in crew.js). A walker crossing the doorway aims at a waypoint on
  the centre line first. Its arrival reach (0.55 m) MUST stay under the "lined up" test (0.85 m,
  itself under half the 2.5 m opening less the walker's 0.3 m): with reach 0.7 against a 0.5 m
  line-up, a feeder that stopped 0.6 m short of the middle was arrived AND not lined up, and never
  moved again -- with its whole team waiting behind it.
- A FULL STACK TAKES NOTHING. `returnSheet(items, stack, near)` is the one way a board goes back:
  the named stack if it has room, else the nearest that has. The prompt at a full one says `That
  stack is full`. 150 sheets came off five stacks of 30 and the count is conserved: the old
  `Math.min(30, ...)` swallowed the board in your hands, and the crew's `s.sheets++` made a 31st.
- THE SAVE WATCHES THE COUNT. Boards go down without an ACTION (DROP lays the one in your hands,
  the crew's feeder lays its own), and neither runs through `installInteract`, so index.html's
  `installStep` (and main.js's loop) compare `sheetSig` every frame and write the save when it
  moves. DROP also only thuds when something actually left the hands.
- PROOF: `node tools/game-boards.mjs <outdir>` (21 steps: the stacks on the plan, taking a sheet,
  the first board on the door line, the ghost's red and the concrete hint, TURN and the grid, a
  six-board run, the machine stopping at the end of the boards and moving on when two more go
  down, picking one up under a wheel, the save across a reload, a crew team boarding its own way
  into the hall, the night reset, two phone shots, and then one check per defect the skeptical
  tester found: DROP is saved, a full stack refuses a board, the prompt answers the reticle with
  full hands, the wheel plan clears every HUD element at 412 and 360, `sheetCells` really covers
  its point, a team boards its own way in from a BARE hall and keeps moving, and the feeder walks
  back out through the doorway from the spot it used to freeze on; and from 2026-09-07 the two
  stop messages: the boards line clears when the stick is let go, and a machine held by another
  machine says so).

### The crew you allocate (Lloyd, 2026-09-06: "Can we also add crew from the start. The player should be able to allocate tasks to the crew members")
- WHO. FIVE from the start, waiting in the corridor at 17:00, one vest colour and one name tag
  each: Dave (orange), Priya (yellow), Marco (green), Jules (blue), Tom (pink). `crew.members`,
  `crew.lifts` (two crew scissor lifts), `crew.jacks` (two crew jacks). Nobody unlocks and nobody
  picks their own job. `crew.points()`, `crew.resetForNight()`, `crew.leftInHall()` and
  `crew.toasts` are unchanged for their callers; `crew.teams` and `crew.helper` are gone, so
  `refreshObstacles` takes `crew.lifts` (index.html `installStep`, main.js's loop).
- THE SEVEN JOBS (`CREWm.TASKS`, id + label): `standby` Stand by, `fit` Fit column, `feed` Feed
  column, `boards` Lay boards to (a column or `WHOLE_HALL`), `pallets` Bring pallets in,
  `rubbish` Rubbish, `help` Help me (the old helper, on whichever column your lift is nearest).
  `crew.assignTask(nameOrWorker, task, target)` is the ONE way a job is given out: it puts down
  whatever was in hand first (`dropWork`), clears the run claim and toasts `Dave: fit N3`.
  Assignments persist across nights; `resetForNight` only moves everyone back to the corridor.
- A LIFT IS A SHARED TOOL. The first fitter who needs one takes a free one (`crew.lifts`, `L.by`);
  a third fitter gets status `waiting for a lift` and the line `No free lift for Jules`, said once.
  The PLAYER's lift is never taken. Reassigned mid-column, a fitter brings the deck down, climbs
  off and leaves the machine where it stands, free for the next one (`parkLift`). Jacks are
  claimed the same way (`reserveJack` / `unclaimJacks`): a claim must be returned to its owner on
  the next frame or a worker claims all three and then finds none free (that bug stood two of them
  still for a whole night). `reserveJack` takes the NEAREST free jack, the crew's own before the
  player's, and `fetchJack` gives a claim back after 12 s of getting nowhere with that jack off
  that member's list (a member who claimed the player's jack in the far corner of the store and
  could not thread the pallet rows to it stood there all night with two free jacks beside him).
- NOBODY TELEPORTS (Claude, 2026-09-07, the skeptic's D1 and D5). Getting on or off a machine is a
  second on the ladder (`climbOn` / `climbOff` / `stepClimb`, `CLIMB`): the man slides along the
  machine and up, and `update` runs nothing else of his while it lasts. And `parkLift` only brings
  a man off a deck he is actually STANDING on -- a fitter reassigned while he was 11 m down the
  hall on a box run used to be snapped back to the ladder foot in one 50 ms frame. He is already
  on the floor: the deck comes down, the machine goes back on the free list (`releaseLift`), and
  he stays where he stands. The same rule at pack-up. No crew member moves more than a walking
  pace in a frame, and the proof asserts it over every stepped run.
- PAIRING. A fitter and a feeder on the same column work together: the feeder loads THAT fitter's
  deck, and when that machine has run out of floor protection the feeder drops everything and lays
  ply in front of the blocked wheel (the brief-A behaviour, `layAhead`). Two fitters on one column
  claim different runs (`W.run`).
- THE BOARDS JOB (`boardPlan`): (a) the SPINE, 2.4 x 1.2 boards laid across the way you drive, up
  the middle of the hall on d 7.5 from the door line to the column; (b) the column's PATCH, every
  1.2 m grid cell whose centre is within 2.6 m of the foot that the shaft does not stand in,
  covered nearest-the-middle first so it butts on to the spine. `Whole hall` is the full spine plus
  every column's patch, nearest the doors first. Status counts down: `laying boards to N3 (14 to
  go)`. A spot nothing can be laid on for 20 s (a pallet parked on it) comes off the plan.
- STATUS TEXT, shown in the panel row and under `Talk to`. This is the WHOLE vocabulary and the
  proof fails on anything outside it (step 9): `standing by`, `waiting for a lift`, `walking to
  the lift`, `rolling to N3`, `waiting for boards near N3`, `fitting N3 (23/64)`, `fetching
  boxes`, `waiting for boxes`, `feeding N3`, `bringing the N3 pallet in`, `laying boards to N3 (14
  to go)` (the BOARDS job, counting its plan down), `laying boards to N3` (a FEEDER laying ply in
  front of his fitter's blocked wheel: there is no plan to count), `bagging wrap`, `running
  rubbish`, `helping you`, `stepping off the lift`, `putting the jack back`, `packing up`, `taking
  the N3 pallet back` / `taking the ply back` (the pack-up run).
- ASSIGNING, two ways. THE RETICLE: crew avatars are raycast targets (`items.crew`, kind `crew`);
  within 3.5 m the prompt is `Talk to Dave` with his status under it and ACTION opens his sheet
  (`items.talkTo`, hung by index.html). Gotcha: a name tag is a THREE.Sprite and `Sprite.raycast`
  throws unless `raycaster.camera` is set -- `nearestAction` sets it. THE PANEL: `#crewBtn` opens
  `#crewPanel`, which now has two tabs, `Tasks` (five rows: vest dot, name, job, status) and
  `Room` (the multiplayer contents, unchanged). THE SHEET `#taskSheet`: name + status, a grid of
  the seven jobs, then a picker of twelve columns (done ones disabled and marked `done`, ones
  another member is on marked with that member's initial) plus `Whole hall` for the boards job.
  Closes on Close, Esc, or on assigning. While it is open `body.sheetOpen` is set: `installStep`
  clears the keys and both sticks every frame BEFORE anything reads them, the pointer lock is
  released, and `Player.setPaused` refuses to pause (the shift keeps running behind the card).
- 04:30 PACK-UP is per member: deck down, machine home along the boards (`force` after 2 s stuck),
  the pallet in the air back, jack back -- and a sweep for a jack somebody left at a column,
  because a feeder sets its jack down at the foot when the pallet is in and nothing of the crew's
  may be in the hall at 05:00 (`leftInHall`). EVERY PALLET AND EVERY PLY STACK LEFT STANDING IN
  THE HALL GOES OUT TOO (`strayLoad`, Claude 2026-09-07, the skeptic's D2): the sweep used to walk
  home only a pallet that was already in the air, so twelve pallets stood at twelve column feet
  all night and the night's clean-up read `pallets` every time. Whoever is free claims the nearest
  one by name, takes a jack to it and runs it back to its storage spot (`setDown` keeps a stack's
  own turn); a member with no jack free lets the claim go instead of standing on it. Twelve
  pallets take about six minutes of shift with three jacks between five people.
- A FITTER THAT CANNOT GET THE LAST METRE PARKS AND WORKS (`PARK_R`, Claude 2026-09-07, the
  skeptic's D3). The ring round a shaft cannot be boarded at all -- a sheet has to clear the
  column by 0.6 m and every grid cell that touches the ring is refused for that reason -- so no
  machine ever reaches a run's own spot. The test used to be "within 3.6 m of the run's spot" and
  a lone fitter standing on the spine 3.64 m off it said `waiting for boards near N6` for the rest
  of the night with nobody assigned to boards. It is measured to the SHAFT now (4.6 m): a machine
  that near has arrived, whichever face the next run is on. `L.stuckCol` shortens the try on the
  next face of a column that has already beaten it, so a column is not eight separate waits.
- A CARTON IN THE HANDS GOES UP BEFORE THE STOCK IS COUNTED (`getBox`, Claude 2026-09-07). Taking
  the last carton off a pallet empties it, and the stock test then told the fitter walking back
  with that carton that there was nothing to fetch: he climbed on holding it and sat there for the
  night. A column stopped dead at 56 of 64 with the eighth box in his arms.
- THE CORRIDOR HAS ONE LANE (Claude, 2026-09-07). The two pallet rows leave 4.1 m of clear floor
  and a lift's plan circles take 2.0 m of it, so the crew's machines park down the MIDDLE of that
  band ((56.5, 7.35) and (60.0, 7.65)), which leaves about a metre of lane either side and keeps
  both pallet rows reachable. Parked against one row instead, a lift leaves a 14 cm slot and a
  straight-line walker aimed through it is stuck there for the night (the sidestep cannot back out
  of a dead end). The jacks park at (57.0, 8.9) / (60.5, 8.9) and the five wait in the SOUTH lane
  (`corridorSpot`: d 8.5 / 9.2, between the door line at d 7.5 and the S pallet row at d 10.5) at
  u 53-55.6, 4 to 7 m back from the doorway so they do not hold the doors open all shift.
- A COLUMN'S PALLET STANDS BESIDE IT ALONG THE HALL (`footSpot`, `hd.u + 2.4`), not 2.4 m out
  toward the middle as it did: the floor protection runs up the middle, and a 1.9 m pallet circle
  at d 6.2 covers most of that road and wedges every machine driving past.
- TRAVEL (`travelGoal`) in four steps: back on to the middle line at your own u if you are leaving
  a column, line up on the 2.5 m doorway, clear the door line by 3.4 m, then follow the spine up
  the middle until you are level with the column and only then turn off across the patch. A
  machine nose to nose with another parked one in the corridor eases ACROSS and goes round (a
  head-on push is exactly cancelled by the drive, so it would never move otherwise). Climbing off
  a machine leaves you inside its own plan circles, so the machine you just left is ignored by the
  collider until you are 3 m clear (`W.offLift`).
- PROOF: `node tools/game-crewtasks.mjs <outdir>`. The long working run is STEPPED, not watched:
  `crew.update(0.05)` in a tight loop with `refreshObstacles` and `updateDoors` alongside it, the
  same order index.html's frame runs them, so 420 s of shift takes seconds and every step is
  sampled. It checks the five on standby (nobody moves for 5 s), the reticle prompt and the sheet
  (W does nothing while it is open, and the game is not paused), the panel's five rows, a whole
  shift's work (no crew wheel ever on bare carpet, boards laid, Dave rolling -> waiting for boards
  -> fitting N1 (n/64), 25 lights in, pallets jacked in, the feeder feeding), reassigning a fitter
  mid-column AND reassigning one who is away on a box run (nobody moves more than a pace in a
  frame, over every stepped run), a third fitter with no machine free, a LONE fitter with nobody
  feeding him and nobody on boards (he parks and works instead of stalling), the pack-up down to
  the last pallet and ply stack (`cleanupClear` clean of both), the status vocabulary, and three
  phone shots. The 41 m spine to N1 is pre-laid by script in step 4: one worker carrying one board
  at a time cannot lay 41 m of road AND fit the column inside one night, and the protection stays
  down for the job.

### The canopy as slab glass (Lloyd, 2026-09-06: "each of the colours should be stained glass and translucent")
- WHAT IT WAS: every pane in `tools/pieces.bin` drew as one flat emissive colour, opaque, the
  same by day and night, 6 mm under a black plate. That reads as a texture. The panes are 6,378
  triangles/quads covering ~15% of the field (real: ~10,000 slabs, 35-40%).
- WHAT IT IS NOW (`buildGlassPieces` + `glassMaterial` in index.html): each polygon becomes a
  body plus a bevel ring (vertices slid inward ~14 mm along the bisectors, capped at a third of
  the slab's radius; slivers fall back to a plain fan). The `aux` attribute carries the piece's
  huv centre, a per-piece seed and the bevel coordinate (0 outer edge, 1 body). The fragment
  shader: (1) purifies the traced colour into a transmission colour (minor channels pushed down
  harder the more washed the trace, near-grey traces become clear glass, dark traces are lifted:
  a dark trace is an underexposed patch of the bake, not dark glass; dyed slabs pass less than
  clear ones), (2) computes what shines through: sky = day x dayGain x (0.5 + 0.6 x facet.sun)
  so the four faces of a bay differ under the sun, lamps = warm x house, plus a night floor,
  (3) streaks the body along a per-piece pour direction and adds fine grain (interior mottle
  about 8-9 %, as measured), (4) darkens the last 10-15 mm softly to about a third (measured on
  the 4K balcony stills; there is NO continuous bright rim on the real slabs) and throws short
  white glints on a few per cent of the edge, seeded per piece, (5) adds the LED show below with
  the plate's closed-form segment integral, stronger where the facets glint. `applyDay` pushes
  the sun vector into any material with a `sun` uniform. The plate concrete is neutral
  near-black (29,26,28 sRGB in the photographs), not brown. Numbers:
  E:/sitecapture-captures/ngv-site/agent-ref-ceiling/reference/reference-stats.json (track C,
  2026-09-06; the lf02 hue table there is bloom-biased, use the close-up 2 transmission set).
- THE PLATE draws the 224-panel steel from the lattice phase (`lat` uniform): ridge beam round
  each bay (~220 mm), the + cross through the vertex, the main X and the diamond through the
  edge midpoints (~140 mm), each with a lit flange line. Bays are 2x2 sub-squares of ~3.7 m cut
  by both diagonals (the Hyde 2004 straight-up photo; NGV: 224 triangular elements).
- The glass mesh is NOT in `solids` (the plate 6 mm behind it stops the eye; 46k triangles per
  fly-mode ray otherwise). Panes whose centre falls outside the snapped plate rect are dropped
  at load (they hung over the void band).
- PROOF: `node tools/ceiling-shots.mjs <out> <tag>` shoots day/dusk/night x up/slant/close from
  inside install mode (the only camera a script can place); compare against
  `scratchpad/ref/lf02.jpg` (Hyde) and Lloyd's b0cefe7f daylight shot. `tools/pieces_stats.py`
  prints the pane file's numbers (count, coverage per bay, sizes, colours).
- THE PANE FILE (2026-09-07, the "more accurate model" half): `tools/pieces.bin` = 6,979 slabs,
  26 % of the plate, written by `tools/merge_panes.py` (idempotent, 25 s) from three data tracks
  under E:/sitecapture-captures/ngv-site/agent-ref-ceiling/: trackB/ (the bake atlas unwrapped
  to a 5 mm/px bottom ortho by `tools/ceiling_ortho.py`, traced by `tools/trace_pieces.py`:
  2,687 real slabs with atlas colour over the third of the plate the bake resolves), reference/
  reference-stats.json (the photographs' numbers: sizes, shapes, rib alignment, the emblem and
  fan geometry, the close-up transmission table) and trackA/ (the 4K roof-void stills, NOT used:
  one shooting spot, 5 % coverage, a 0.5 m hub error). Cells the trace does not resolve are laid
  to the traced cells' own size, cover and palette (flagged `synthetic` / `bay-palette` in
  merge/pieces-merged.json) with the motifs placed by the photographed rule (the square ring
  with X, 16 round a crest node, 71 placed; the clear fans at the column heads). Old files kept
  as `tools/pieces-*.bin.bak`. Honest gaps: cover 26 % against the real 35-40 % (the blurry bake
  sets it), the synthetic cells are crisper than the traced blobs at 1:1, emblems only where no
  trace was, west-heavy. Better data means a sharper underside capture, not more code.
- THE LATTICE (2026-09-06): module 7.36 x 7.50 m (`CANOPY.PU/PV`), measured on the GLB's own
  twelve column heads (7.347 / 7.380 m along the rows, 7.50 m across; the bake's joints say
  7.35 m, NGV's 51.5 x 15 m glass says 7.36 x 7.50). The 08-31 value 7.4285 x 7.3855 was ~1 %
  large. The plate shader's diamond is the true edge-midpoint diamond; every pane keeps 89 mm
  off the painted members and 125 mm off the ridges, so the fitted phase may drift 13 mm before
  glass meets steel.

### The ceiling hardware: hub nodes and the lighting rig (2026-09-07)
Brief: "a perfect, accurate model of the Gandel Hall ceiling: geometry, structure, any
ceiling-mounted fixtures/trusses". The lattice, the relief and the glass were already measured
(above); what the photographs showed that the model did not have was the steel at the column
heads and the house lighting rig. Both live in the canopy block of index.html
(`buildHubNodes`, `buildLightingRig`, `RIG`), inside `hallGroup`, so the column-height lever
scales them with everything else.
- THE HUB NODES replace the "drum". The 08-31 cloud saw a dark body ~0.9 m across hanging
  200-300 mm under every funnel vertex and the viewer drew a cylinder there. lf_hub.jpg,
  gh03_colhead_crop.jpg and the roof-void hub stills (trackA/checks/hub_*.jpg) show what it is:
  the node where the coffer's eight members (four hips, four cross members) run down their
  facets and meet on the column's square steel head. Nothing round hangs there. Built as one
  InstancedMesh (`canopy-hub-nodes`, 12 x 9 boxes): a 0.62 m square head 300 mm deep under the
  vertex and eight 0.45 m arms (240 mm cross members, 260 mm hips) each pitched to its own facet
  (13.9 / 13.7 / 9.9 degrees), 1.1 m across, in `solids`. `canopy.hubs` holds it.
- THE LIGHTING RIG is permanent, not an event hire: it is in the 2010s balcony photograph
  (b0cefe7f, day), in gh03 and in Lloyd's 2026-08-17 balcony still (balc_b033), the same bar
  each time. A triangular truss runs the length of the hall along the NORTH wall, between the
  wall and the wall-side column row, flown on electric chain hoists whose chains rise to the
  ceiling, one per bay, carrying profile spots and PARs that face the room. Measured off those
  photographs against the tapestries (top edge 8.26 m, tools/tapestries.json) and the column
  rows: centreline 2.2 m off the wall, 9.0 m above the carpet, u 1.0 to 46.0 (about 1 m in from
  the west wall, 3 m short of the east), 300 mm side, apex up. `RIG` holds those numbers.
  Hoists sit at the six ridge lines the truss passes (chains end 20 mm under the rib), 23
  fixtures at 2 m pitch alternating profile / PAR, pitched 55 degrees into the room. Chords are
  in `solids`; the group is `canopy.rig` (`userData.rig` carries the numbers for a proof).
- THE ENVELOPE. A truss is mostly air and the sim's ceiling ray is one line up from the lift
  deck, so it would thread between the chords: `rig-envelope` is an invisible box (colour and
  depth writes off, rays only) round the chords AND the hanging fixtures, 8.16 m to 9.22 m. The
  lift's ceiling ray (`lift.ceilingY`) now tests `[hallLevel, canopy.mesh, canopy.rig]`, so a
  deck parked under the bar clamps at 8.16 m instead of driving through the fixtures.
- NOT modelled, and why: the roof-void structure above the glass (white steel, catwalks, cable
  trays, the pitched roof: trackA stills) is invisible from the hall, even through clear slabs by
  day (b0cefe7f: clear pieces read as flat sky). The two 6.3 m circular rosettes in the central
  bays (reference-stats motifs.big_circular_rosette_metric) are glass pattern, not hardware, and
  which bay they are in is not determined from any photograph; the pane file does not place them.
  Event trusses across the hall (the entrance shot, bc0db55c) are hires and vary per event.
- PROOF: `node tools/ceiling-check.mjs <outdir> [tag]` (serve :8877; `CDP_PORT=9334` to own a
  Chrome when a peer session holds :9333, which it did on 2026-09-07). 108 node instances under
  the twelve heads (within 1 mm in plan, 0.18-0.22 m under the column tops); six chains each
  ending 20 mm under the canopy surface (barycentric test against `canopy.mesh`'s own
  triangles); truss centroid 9.00 m up inside the hall; the ray line in the source; then in
  install mode the lift parked under the bar reads a ceiling of 8.16 m; six shots (along the
  bar from the west end, close from a raised deck by day and by night, up at N3, the N3 node
  from a 9.6 m deck, from under the truss).

### Phone controls (Lloyd, 2026-09-07: no big buttons; research-led)
Lloyd: "we need to improve the controls on phone", then "No big buttons that will take up screen
space. Do some research online on phone UI best practices. As well as phone joystick control best
practices." What the phone showed before this: two fixed 80 px rings, a permanent UP / DOWN / FAST
column, a DROP button and a prompt pill on the right edge, on a 412 px screen. All of it is gone
except the pill, and the pill is now the fallback, not the way you act.
- WHERE IT LIVES. `game/touch.js` (`TouchControls`, `loadCtl`, `saveCtl`, `DEFAULTS`, `RADIUS`) owns
  every gesture; `index.html` owns the markup, the CSS and the two things only the host can do (the
  world tap, the settings sheet). Only built on a coarse pointer: the desk keeps the mouse, the keys
  and the pointer lock untouched. `player.js` binds no sticks now unless a host hands it ring
  elements (`game/main.js`, the old standalone entry, still does).
- THE PLAY LAYER. `#tzone` is one transparent surface over the shift, `touch-action:none`,
  `user-select:none`, no context menu, Pointer Events with `setPointerCapture` per `pointerId`, no
  throttling of `pointermove` (Chrome already frame-aligns it). The stick, the cluster and the pill
  are siblings painted ABOVE it, so they take their own taps first.
- MOVE: A FLOATING STICK. Left 40 % of the layer, below the header row (measured off `#ghud`, not a
  fixed number: the clock chips wrap to three rows on a narrow phone). The base appears WHERE THE
  THUMB LANDS and hides on release; a faint ghost rests in the corner until the first touch. Ring
  radius 60 px (S / M / L = 50 / 60 / 72). THE LOGICAL CENTRE IS THE THUMB, always; only the drawn
  ring is pulled inside the glass, so a thumb landing near an edge starts at a zero vector instead of
  60 px of deflection. A second finger landing in the move zone while the stick is held is ignored,
  not read as a look. Scaled radial dead zone 0.10
  (`dir * ((mag - dz) / (1 - dz))`), linear, and the thumb may drag past the ring: the output clamps
  and the stick keeps the finger. RUN WITH NO BUTTON: over 0.85 for 0.4 s latches, and it stays
  latched until the thumb comes back under 0.3 (`player.touchRun`, the same sprint Shift gives) --
  and running now COSTS: `body.update(dt, clock, load, moving, sprint)` drains 1.8x, minimum 2.2/s,
  so the latch is a choice rather than the default walk.
- LOOK: FREE DRAG, NO STICK. Anywhere the stick zone is not. POSITIONAL, not a rate: 0.22 deg/px
  across and 0.18 deg/px up and down at sensitivity 1.0, with a mild curve
  `sign(d) * |d| * (|d|/10)^0.15` on the per-event delta -- the /10 reference is what keeps a normal
  drag honestly 0.22 deg/px whatever way the browser splits the events. Separate H and V sliders
  (0.5x-2x) and an invert-Y toggle. Both thumbs work at once (`pointerId`). `Look: stick` in the
  settings brings back the old rate stick (Lloyd asked for it twice on 2026-09-04), floating on the
  right; drag is the default because a drag surface driven as a rate reads as drift.
- ACT BY TAPPING THE THING. A tap (under 10 px, under 500 ms) hands its own screen point to
  `installTapWorld`, which puts it in `player.tapNdc`; `items.js nearestAction` then casts THERE
  instead of through the reticle, and whatever it hits decides the action and runs it at once
  (`installInteract`, the same path the prompt uses). A tap that hits nothing was a look gesture and
  does nothing. `navigator.vibrate(15)` on a tap that acted (Android only, after first activation).
  The pill stays as the fallback for the reticle's own target: 56 px under the +, 70 %, hidden when
  there is nothing in range. On a phone the pill takes NO POINTERS of its own: `installTapWorld`
  checks the tap point against its rect first and runs the reticle action from there, so a tap acts
  and a drag that starts on it is an ordinary look.
- THE FOUR SLOTS ARE A BOTTOM STRIP. `#inv` is a 4-in-a-row strip along the bottom centre on a
  phone, in the gap between the two thumbs, `pointer-events:none` on the strip and `auto` on the four
  44 px slots, so a drag through a gap still walks or looks. Selection is `pointerdown`, not `click`:
  Chrome never synthesises a click for a second touch point, so a slot must be tappable with the move
  stick still held. `hud.js stackHud` leaves `#inv` alone on a coarse pointer (an inline `top` would
  beat the stylesheet); the desk keeps the left-rail stack.
- THE SHIFT OWNS THE WHOLE SCREEN. On a phone the viewer's bottom bar (Menu, Tour, Full screen,
  Stats, Phone remote) is `display:none` for the whole shift: it cost 44 px of every screen, a tenth
  of the picture in landscape, and three of its buttons were live mid-shift (Tour took the camera
  with the install HUD still painted over it, Phone remote put a QR card over the running hall, Stats
  stacked a second read-out). Those three also refuse to fire while `body.playing`. Menu's job moves
  to a PAUSE GLYPH beside the gear: it sets `body.halted` (which turns `playing` off inside
  `installStep`, so the clock, the body and the crew all stop) and opens the lighting panel over the
  pinned stage; the panel carries its own `#panelClose`, and closing it calls `immersiveOn()` and
  hands the hall straight back. Tour, Stats and Phone remote are not reachable during a shift.
- ESCAPE CLOSES WHICHEVER CARD IS UP, innermost first: Controls sheet, then the menu panel, then the
  crew panel, then the task sheet, each restoring its own paused state (`closeCtlSheet`, `menuPanel`,
  `closeTaskSheet`). One handler that only knew the task sheet used to strip `sheetOpen` while the
  Controls card stayed on the screen, leaving the game live and drivable underneath it.
- CONTEXTUAL CONTROLS ONLY. Bottom-right corner (the thumb's green zone), 52 px boxes = 48 dp of hit
  area with a small glyph: DROP only with something in the hands, TURN only with a ply sheet, and
  while you drive a vertical DECK mini-stick whose magnitude is the speed, with LET GO beside it.
  That mini-stick is what deleted UP, DOWN and FAST in one go (`player.liftRate`, added into
  `Lift.drive`). The slots and DROP stand down while your hands are on the controls.
- IMMERSIVE. Start Shift asks for `#stage.requestFullscreen()` then `screen.orientation.lock`
  ('landscape') inside the same gesture; both are best-effort (the lock is not Baseline and needs
  fullscreen first), so `body.immersive` + `html.immersive` pin the stage over the page either way:
  no header, no page scroll. Menu, and stopping the shift, put it back. PORTRAIT (412x915) and
  LANDSCAPE (915x412) are both supported layouts; nothing gates portrait.
- SETTINGS. The gear beside Guide (a rare action, so the red top corner is the right place for it)
  opens `#ctlSheet` in the task sheet's card style, one label and one control per row, two columns on
  a short screen. Keys: `ngv.ctl.look` (drag|stick), `ngv.ctl.sensH`, `ngv.ctl.sensV`, `ngv.ctl.invY`,
  `ngv.ctl.stick` (S|M|L), `ngv.ctl.autorun`, `ngv.ctl.lefty`, `ngv.ctl.opacity`. Left-handed mirrors
  the stick zone AND the corner cluster. Opacity drives `--ctlop` (60-80 % is the band); everything
  persistent fades to half of it after 3 s idle (`body.ctlIdle`), the deck stick included, and the
  fade clock starts at the first frame so the resting ghost is never born faded. Left-handed mirrors
  the wheel plan (`#wheels`) as well as the stick zone and the cluster.
- WHERE THE RESEARCH BEAT THE FIRST INSTINCT: no look joystick at all (PUBG, CoD Mobile, Genshin and
  Fortnite all drag the right half); positional look, never rate, on a drag surface; a scaled radial
  dead zone instead of an axial one; and buttons that shrink their glyph, never their hit box.
  Sources: https://www.gamedeveloper.com/business/doing-thumbstick-dead-zones-right ,
  https://blog.activision.com/call-of-duty/2019-10/Getting-a-Grip-on-the-Call-of-Duty-Mobile-Controls ,
  https://genshin-impact.fandom.com/wiki/Controls ,
  https://www.fortnite.com/news/getting-started---fortnite-for-mobile?lang=en-US ,
  https://m3.material.io/foundations/accessible-design/accessibility-basics ,
  https://www.nngroup.com/articles/touch-target-size/ ,
  https://www.lukew.com/ff/entry.asp?1927= ,
  https://developer.chrome.com/blog/touch-action ,
  https://developer.mozilla.org/en-US/docs/Web/API/ScreenOrientation/lock
- PROOF: `node tools/game-phone.mjs <outdir>` drives real CDP touch (multi-touch where it matters) at
  412x915 AND 915x412: immersive and no page scroll, nothing on screen overlapping anything else,
  48 dp on every control up, the base landing under the thumb, the run latch, 100 px = 22 deg (44 at
  sensitivity 2.0, inverted, and the stick option turning at a rate), both thumbs at once, a tap on a
  pallet taking a box with the reticle pointed elsewhere, a tap on air doing nothing, DROP / TURN
  appearing and doing their job, the deck stick raising and lowering the deck, LET GO, and every
  settings row changing something measurable and surviving a reload. Section 14 is the skeptic pass
  of 2026-09-07 (15 defects): Escape, the hidden bar and the three inert buttons, the pause glyph
  holding the clock and handing the hall back, the slot strip (bottom centre, 44 dp, inside a 45 mm
  thumb arc, gaps passing drags through, a slot tapped as a second finger), the pill taking a tap and
  passing a drag, a 400 ms press, the edge clamp at four touch-down points, a palm on the left rail,
  the deck stick's idle fade, the run's stamina cost, and left-handed driving at 412x915, 360x780 and
  915x412.
- KNOWN, NOT FIXED: the reticle is drawn in the centre of `#installUi`, which is 44 px shorter than
  the canvas (the button row), so the + sits about 22 px above the true camera axis on a phone. That
  is older than this change; the TAP is cast from the canvas, so a tap is exact either way.

## The lightshow (2026-09-04)

Lloyd's own music and the light cues for it live on one clock. Three pieces:

| Piece | Does |
| --- | --- |
| `show/lightshow.js` | the look engine both pages share: `NGVShow.createShow()` paints the pixel array from a FRAME (t, bpm, beat, bass/mid/high/rms/onset) and a STATE (look, palette, level, hitAt). Looks and palettes are listed in `NGVShow.LOOKS` / `NGVShow.PALETTES` |
| `studio.html` + `studio/` | the tool, Caustic 3 style (2026-09-05): a RACK of machines (SubSynth, BassLine, PadSynth, FMSynth, BeatBox, Lights), PATTERNS A1..D8 per machine on a 16-step grid (piano roll, pad grid, or cue lanes plus a level lane for Lights), a SONG view of pattern blocks, MIXER and two FX inserts per machine, a play strip that plays the selected machine from the computer keyboard and records into the current pattern. `studio/model.js` is the schema, `engine.js` + `machines.js` the audio, `lights.js` the Lights runtime feeding the sim iframe (`index.html?embed=1&show=live`) by postMessage, `export.js` renders the WAV, bakes the frames and writes `show/<name>.cues.json` through `POST /save` on `tools/serve.js`. Test pages: `studio/test-engine.html`, `studio/test-lights.html`. Launch: `START-STUDIO.cmd` |
| `index.html?show=<name>` | playback for the proposal: the Lightshow row's Play loads `show/<name>.cues.json` and its audio and drives the columns from the cue file; the layers are ignored until Stop. `show/shows.json` lists the names |

| `jam.html` + `studio/jam.js` | the simple builder (2026-09-05), public, no server: pick one preset pattern per instrument (10 instruments x 10 styles, `studio/presets.drums.js` beat templates that expand to any meter, `studio/presets.pitch.js` degree patterns rendered against the section's key and chord cycle) and up to six light layers (`studio/presets.lights.js`, 30 patterns in six families, each syncable to Grid or an instrument's notes), stack them, add sections with energy, feel, meter, chord cycle, transition and transpose, play the song, share by link (deflate + base64url in the hash), export WAV + cues as downloads, open in the studio. `studio/presets.js` is the core: `Studio.harmony`, `Studio.PRESETS.render/applyEnergy/buildStack/buildSong/starter/arc`. Sections and the timeline live in `studio/model.js` (`Studio.timeline`: a step is always a 16th, bars have 16/12/20/14 steps by meter, tempo and feel per section). `show/looks2.js` adds 12 looks; `NGVShow.paintLayers` composites up to six layers |

`tools/show_analyse.py sound/<track>.mp3` bakes the same cue file from an external track (beats,
sections, bands, no cues), for a show cued by hand. `tools/show_pack.py <name>` turns the studio's
WAV into the mp3 that ships (the WAV is gitignored).

## The lighting render (2026-09-07)

Lloyd: "the lighting looks very one-dimensional", "nothing bounces", the glass "reflected nothing",
the strips "are hard flat lines". Six terms went into `index.html`, three of them ported line for
line into the game's `game/hallmat.js` (its `photoMaterial` carries the same closed form and the
same constants). Every one is anchored to a measured number, none is a look constant.

| Term | What it is | Where |
| --- | --- | --- |
| Lambertian line | a strip is a diffused FACE: intensity K B(azimuth) cos(elevation), K = Phi/pi^2 (4/pi of the old isotropic Phi/4pi, flux conserved). The vertical-segment integral still closes, over r^4 with one atan2 per light. rho is floored at half the shaft radius, not an epsilon | `photoMaterial`, `columnLit`, `glassMaterial`; game `photoMaterial` |
| First bounce | half a Lambertian face's flux goes below the horizon onto the carpet; one virtual cosine emitter per light at the column foot carries 0.5 x flux x the carpet's albedo, softened by the light's mean height. Albedo measured off the floor texture at load (`measureBounce`; the game hard-codes that measurement as `FLOOR_ALB`, deep red 0.228/0.059/0.070) | `bounceAlb`, `bounceY` |
| Column shadow | plan-view test: a column occludes a light when the segment fragment-to-light passes within the shaft radius of its axis, soft over half a radius. The two nearest columns are read out of the light list itself (`lightPos.w` names the column), so no new uniform vectors: the fragment stage sits at 192 of the guaranteed 224. Two columns on a desk, one on a phone (`nOcc`) | `occl`, `measureShaft` -> `COL_R` (mean run foot radius + 100 mm; game constant 0.26) |
| Glass mirror | the canopy's underside reflects the strips: a normalised Phong lobe (n = 60, about 10 degrees, the hammer-chipped slab) about the mirror direction, weighted by Schlick Fresnel (F0 0.04), inside the loop the plate already runs | `glassMaterial` |
| Emitter face | the lit face is not a flat panel: view-angle term S(theta)/cos(theta) from the cover's own blade profile, and a centre-bright section normalised to mean 1 so `EMIT_EXPOSURE` keeps its meaning | `emitterFace`, `FACE_S` |
| Glare | veiling glare at 6% of the source (CIE/Vos), computed on the HDR emitters alone (layer 2, `BLOOM_LAYER`, drawn against the hall's depth), threshold 1/exposure so a dimmed strip blooms less; half resolution, quarter on a phone. Not an UnrealBloomPass over the carpet | `bloomPass`, `GLARE_GAIN` |
| Auto-exposure | Menu > Camera > Exposure: Auto opens the lens as the house comes down, from the strips' lumens over the hall's measured surface area (`measureHallArea`, 4,813 m2), key HOUSE_LUX/4, cap x1.25 (2026-09-08: the x4 cap made the hall after Enter "way too bright"; a light show is lit things in a dark room), held at 1.0 while the house is over half up so every quote picture is unchanged. Fixed pins 1.0. Stored in `ngv.cam.exposure` | `exposureStep`, `EXPO` |

The columns' own runs do NOT light their shaft (2026-09-08). The `columnLit` diffuse term took every
run in the list, so a shaft a hand's width from its own eight strips rendered as a glowing tube
(Lloyd: "the column lights look weird"). A run whose axis is within 1.5 shaft radii of the fragment
is skipped: the LED face points away from its own shaft and the fin behind the run is in the run's
own shadow. The shaft shows its neighbours' colour and the house pools, on black steel, as the
photographs do.

The game's fitted bars (`game/fixture.js`) put their face and halo on layer 2 too, so a shift under
lit bars glares the way the proposal does.

Proofs, both against the static server on 8877 and a headless Chrome on `NGV_PORT` (default 9333;
`tools/cdp.mjs` is the shared attach/evaluate/collect-errors module every proof in here repeats):

- `tools/light-audit.mjs [outdir]`: the energy audit. Datasheet lumens per column (0.18% off),
  the shader's closed form against the analytic Lambertian line at 1, 3 and 6 m (under 1%), flux
  conservation over a 60 m sphere (0.00%), the canvas readback against the same formula in JS
  (0.3%), exposure 1.000 with the house up, x4.00 with it off, Fixed pins it, the lumen, watt and
  model lines byte-identical apart from the appended exposure readout. All ok on 2026-09-07.
- `tools/light-shots.mjs <outdir> [page]`: seven fixed night views (hall-end, column-close,
  floor-low, high-down, wall, warm-white, phone at 412x915). Shoot `.light-before.html`
  (`git show HEAD~1:index.html`) for the same frames of the page as it was. 144 fps both, on the
  desk GPU.
- The install proofs (`game-guide`, `install-mode`, `game-liftlook`) still pass on the port.

## The walls, measured (2026-09-08)

Lloyd: "get the walls 100% accurate just like how you did with the ceiling". Method as the ceiling:
real imagery on the wall's own grid, everything measured off it, nothing filled in. State and log:
`E:/sitecapture-captures/ngv-site/agent-ref-walls/PLAN-20260908-walls.md`; every number with its
pixel box, photo and +- in `agent-ref-walls/measure/{walls,courses,endwalls,glazing}.json` and
`measure/REPORT.md`.

- ORTHOPHOTOS. `tools/wall_ortho.py` renders a wall (north, south, west, east) onto a 4 mm grid in
  the hall frame from all 1,026 posed frames (walk, night, day4k): the sharpest camera per 32 px
  cell, the columns, the house truss and the wall's own proud courses as occluders, the GLB faces as
  the sampling surface. `tools/wall_depth_check.py` (two-camera NCC over a depth sweep) found the
  GLB long-wall faces 60 mm (north) / 223 mm (south) BEHIND the certified cloud; the renders and
  the page correct for it. Outputs `agent-ref-walls/ortho/<wall>/all/`. Frames are 1080p video,
  gsd median 15-16 mm on the walls: courses resolve, joints do not.
- THE FACES. `WALLF.dNorth -0.090, dSouth 15.364`; the scan mesh is moved to them in the walls
  vertex shader (`WALL_SHIFT`, each side as one, GLB material only) and the declared glazing moves
  with the south face so its photographed relation to the stone holds.
- THE COURSING. Courses 0.306 +- 0.006 m (the 0.285 read off b0cefe7f was 7 % low), continuous
  along each wall: north joints at h = 0.0798 + 0.3044 k (+- 0.03), south 0.1192 + 0.3088 k
  (+- 0.08, weak); `STONE.north/south`, an end wall takes the north's. Block joints: NONE traced
  anywhere (a 14 mm joint is one sample at 15 mm gsd; the comb peak the mosaic gives is an
  artefact, proven on the tapestries), the only block number is 0.67 +- 0.10 m typical from the
  1968 photograph BUIL004259, so the block joints are still procedural and the stats line says so.
- NORTH WALL (`WALLF`, lists not pitches). 12 windows into the gallery corridor (Lloyd: a corridor
  with art behind), sill 8.99, head 11.35, 1.256 m wide, at IRREGULAR spacing 3.09-4.37 m: eleven
  as holes in the scan relief, the twelfth at u 22.96 hidden behind the event's LED screen in every
  frame but plain in 7aad8857 (evenly spaced, no 7.4 m gap). Ten of the eleven read darker than the
  stone, so the corridor is built unlit (a Lambert back at the 0.6 m reveal, depth unmeasured); no
  art resolved. 6 grilles (about 0.9 x 0.33 m at h 2.6-3.0; u 10-30 is a stage in every frame,
  unmeasured there), a dark door at u 45.97-47.79 head 2.97, the foyer door at u 20 (b0cefe7f only,
  +- 3 m, the scan cannot see there), the inscription (7aad8857 only, not resolved by the scan),
  proud bands from the scan (plinth +150 mm to h 0.74, band +205 mm at h 7.28-8.99, already in the
  mesh). Tapestries measured at u 8.13-14.03 and 37.51-42.64 (+- 0.4): tools/tapestries.json agrees.
- SOUTH WALL. NO high openings (the scan relief has none, 7aad8857 and the 2014 photograph agree).
  Stone u 0.344-18.30 and 34.05-51.906; the pleated glazing between (5 fins at u 18.48, 22.34,
  26.20, 30.06, 33.93 +- 0.25, pitch 3.86 +- 0.12, the GLB's 3.90 agrees; fold depth, glass angle,
  transoms and the door's size do NOT resolve from any source, so the declared sawtooth stays).
  3 grilles, a lit door at u 37.96-39.66 head 2.91 (a gallery beyond: pale floor, ceiling lights;
  the 2014 photograph's lit doorway), a dark aperture at u 45.70-48.22 head 2.52 (+- 0.3).
  Tapestries measured at u 8.37-12.49 (4.1 m wide: narrower than the 5.46 m work tools/
  tapestries.json puts there by elimination) and 37.95-42.71.
- END GALLERIES (`ENDW`). Both ends share two face-plane edges: the recess head at h 9.96 / 10.04
  and an edge at 3.80 / 3.91; the west resolves elements in depth at h 3.99 (5.8 m back, the
  gallery floor), 6.33 (2.65 m), 8.34 (6.6 m), 10.97 (1.0 m). So the recess runs h 3.92-10.0, 6.2 m
  deep, tiers at 6.33 and 8.34 (three balustrades with the floor, as b0cefe7f shows). Unmeasured:
  the recess width (d 3.9-11.5 kept), the balustrade heights, the east's tiers (its frames all
  stand 13 m out on the south side): the east is the west's, said so.
- PROOF. `tools/wall-check.mjs <out> [page] [tag]` (CDP_PORT 9334): nine views by day and night
  in install mode; before/after in `agent-ref-walls/shots/`. `game/hallmat.js` paints the same
  lists flat for the sim.

## The walls (2026-09-07, superseded above where they differ)

- WHAT THE PHOTOGRAPHS SHOW. Ashlar in running bond, half-block stagger, fine pale joints. Measured
  in `E:/sitecapture-captures/ngv-site/reference-photos/b0cefe7f` (daylight, balcony): the Abstract
  sequence tapestry is 4.993 m tall and 1117 px, so 4.47 mm/px at its plane; the vertical
  autocorrelation of the stone beside it peaks at 60-63 px = 268-282 mm, taken as a 285 mm course.
  The head-on 7aad8857 gives block over course 2.25-2.75, taken as 2.5 = 710 mm. Joints about 10-15
  mm, a shade paler than the stone. A stone patch reads linear 0.207/0.171/0.146 in daylight.
- THE TONE (Lloyd's pick, four options shot with the house up: as baked / stone chroma 2x / that
  plus a mauve carpet / the photograph's brightness plus the mauve carpet; he took the photograph's
  walls and the carpet as baked). `WALL_TINT` = 3.3/4.7/4.7 multiplies the wall bake, which came
  off the night scan at 0.062/0.037/0.031. The carpet keeps its measured albedo, so the night
  bounce (bounceAlb, the game's FLOOR_ALB) is unchanged.
- THE COURSING. The bake resolves the wall at 6.8 mm and its joints are a smear about 1.5 courses
  tall, so the `walls` material draws the ashlar itself (`STONE` in index.html, the same block in
  game/hallmat.js, compiled in for that material only: no uniform spent). Hall frame from vPos:
  courses up from the carpet, blocks along the wall the face belongs to (an end wall or a recess
  reveal runs across the hall, picked by the face normal), the joint mask box-filtered over the
  pixel footprint so a far wall keeps the same joint share instead of going mortar-grey, a tone per
  block and a fine grain within it. The bake is sampled 4.5 mips soft (150 mm) for its lighting
  gradient, recesses and door shadows, which is what kills its own seams and tone blotches
  (Lloyd on the 55 mm cut: "those bricks don't line up right", the bake's blotches crossed the
  drawn blocks); joints are a mid grey darker than the stone (photo row minima 5% under the
  stone) and each stone's tone comes from the per-block hash, a fifth either way (the wall atlas gets a mip chain
  and 8x anisotropy for that; it shipped with a plain linear sampler). Origin of the block phase
  along the wall is u = 0; no photograph fixes it.
- THE STONE ITSELF (Lloyd: "give them proper texture so we don't have to see the gross smeared
  images"). The bake is no longer the wall's colour at all. `tools/stone.jpg` is a tileable
  limestone tile built in numpy to the photograph's stone (mean linear 0.207/0.171/0.146, mottle
  pink to cream over 25-100 cm, grain at 5-25 mm, pits and calcite flecks, faint bedding; 59 KB),
  1 m of stone per repeat, every block reading it at its own hashed offset; the ledges (course
  returns and soffits, no courses to draw) read it in (u, d). The bake survives only as a mask:
  its luminance sampled 2.5 mips soft, under 0.02 linear after the tint = a recess, which keeps
  the niches; its shadow ghosts and smears sit at 0.03-0.1 and are cut. Regenerate the tile with
  the numpy block in commit e2e8b29's successor (seeded, deterministic).
- THE FEATURES (Lloyd: "the walls have details that are missing"; `WALLF` in index.html, the same
  numbers painted flat in game/hallmat.js). Measured off the head-on 7aad8857 (tapestry inner edges
  14.08 and 37.92 m as the ruler) and the balcony b0cefe7f (courses as the vertical ruler):
  deep recessed openings high in both long walls, one per half bay on the N-row column line and
  midway (u = 7.71 + 3.685 k), 1.3 m wide, 9.0 to 11.0 m up, 0.6 m reveals (cut out of the bake
  mesh by discard, four Lambert reveals and a black back built behind); vent grilles 1.0 x 0.16 m
  at 4.2 m pitch (u = 12.5 + 4.2 k), 2.8 m up, black quads 5 mm proud; the foyer door in the north
  wall at u = 20.0 (+-3 m, no ruler crosses it), 2.3 x 2.5 m, a lit white vestibule 1 m deep;
  the Felton inscription centred between the tapestries (u 26.0, 4.2 m up, a canvas, mirrored in
  u on the north wall because u runs right to left seen from inside); a 100 mm shadow gap at the
  carpet. Not done: the openings' exact u phase (+-0.5 m) and the grille phase (+-1 m).
- THE END WALLS (2026-09-08, from the ceiling session's panorama trace: the plate ends on the
  vertex phase one bay past the outer columns, 7 pitches = 51.5 m). The scan's closures stand
  at u = -4.65 and 49.06; the real end walls are at u = 0.34 and 51.91 (7.71 - 7.366 and 44.54 +
  7.366 on the N-row column line). `ENDW` + buildEndWalls: the walls shader cuts both scan
  closures out, the long walls and the carpet (the carpet's own albedo, no photo) run on to
  51.91, and two stone end walls carry the gallery the balcony stills show (756d0ba6, 9277befa,
  d1b1f2a4: stone piers each side of a tall central recess between the column rows, three dark
  tiers inside, stone above and below): recess d 3.9 to 11.5, y 1.8 to 10.0, 6 m deep, tiers at
  3.6, 6.4, 9.2 m. The east end is built like the west (the balcony photographs are taken from
  it; its tier heights are unmeasured). OPEN: the install sim's corridor door (buildDoor, the
  `door` uniform) still sits in the old closure plane at 49.06, told to the install session.
- PROOF. `tools/light-audit.mjs` (the shader still conserves flux), `tools/game-guide.mjs`, and
  the before/after pairs: `git show HEAD~1:index.html > .wall-before.html`, shoot both pages at
  (-20, 1.6, 6.3) facing the north wall with the house up. Not done: the bake's own courses are
  not registered to the drawn grid (its phase is a smear), so the drawn grid is the only one shown.

## The house light (2026-09-08)

- WHY (Lloyd, 2026-09-07: "the lighting needs to be fixed"). The house term was one flat number on
  every surface, E = house + ambient: the carpet, the wall at 11 m and the truss's underside all
  the same, nothing with a direction, nothing falling off.
- WHAT. The house light is the permanent rig (RIG, "The ceiling's hardware"): the 23 profiles and
  PARs along the north wall, pitched 55 degrees into the room, plus the room's first bounce.
  `RIG_PHOT` in index.html (mirrored number for number in tools/rigphot.mjs, asserted by the
  audit): each fixture a Gaussian cone in candela, the profile an ETC Source Four 26 degree at
  750 W (105 kcd on axis, sigma 11.5 degrees), the PAR a PAR64 CP62 medium flood at 1 kW (60 kcd,
  44 x 24 degrees, wide axis along the hall); E = I(theta) cos / r2 summed over the 23 in
  `rigGLSL`, seats and aims from the builder's own formula so no uniform is spent (the fragment
  stage was at 192 of 224). Cone flux integrated numerically (the PAR's sigma is past small
  angle): the rig at full makes 372,000 lm; the photographs' 150 lux on the carpet is the rig at
  `dim` = 24%, direct 0.75 of HOUSE_LUX with 95% of the flux on the carpet (measured by the audit)
  plus the bounce 0.25 falling to half at the wall top, direct + bounce = 1 so every quote picture
  keeps its mean. Tungsten 3200 K, `col`. Columns take the same loop in columnLit (indirectDiffuse,
  world normal) and the hemisphere keeps only the bounce share. The daylight term on the stone
  walls grows with height (skyF = 0.4 + 0.6 h2): the upper wall sees the canopy.
- PROOF. `node tools/house-audit.mjs <outdir>`: the two cones on a 720 grid against the page's 180
  grid (0.0%), lumens in = lux out over carpet + long walls + end walls (100.1%), the carpet's
  share (95%), the carpet's mean at house 1 (149 lux), the page's RIG_PHOT = the mirror's to
  1e-6, a canvas readback of a pool centre against the carpet between pools (1.2% off), no
  console errors. tools/light-audit.mjs stays all ok; its canvas probe now multiplies the
  (led - dark) / (house - dark) ratio by the mirror's house E at the probe, since the house pixel
  is no longer albedo x 1.0. Before/after: `git show <parent>:index.html > .light-before2.html`
  and the four views in tools/house-audit.mjs.
- THE CANOPY'S COLOUR ON THE WALLS (2026-09-08). tools/canopy_map.py rasterises every traced pane
  of tools/pieces.bin (the ceiling session's panorama trace, the photograph's own colours) into a
  2 m grid over the hall, area-weighted mean per cell, divided by the plate mean, blurred over
  4 m (a wall point takes light from a wide patch of canopy) and clamped 0.7..1.3: the RELATIVE
  tint of the daylight bay by bay, tools/canopy-colour.png (26 x 8, sRGB 0..1 = 0..2). The
  absolute cast of daylight through the glass is already in the stone albedo (matched to a
  daylight photograph), so the map is mean white. photoMaterial samples it at the fragment's
  (u, d) one mip soft and multiplies the day term (`dayCol`). Re-run the script after every
  pieces.bin refresh. Plate mean transmission chroma 0.391/0.361/0.248.
- NOT DONE. The sun's beam through the glass (no per-pane pattern, only the bay-by-bay tint);
  the fixtures' real focus and gel state on any given night; the rig's own fixtures do not glare
  (they are dark Lambert bodies, not emitters).

## The ceiling, tile by tile (Lloyd, 2026-09-07: "make the ceiling look exactly like the real Gandel hall ceiling ... Every stained glass tile must be shaped and recorded and registered. Do not fabricate anything")

**What shipped (2026-09-08).** `tools/pieces.bin` is now 6,926 pieces, every one traced from a
photograph and coloured from the same pixels; the synthetic infill of the 09-07 file (pieces laid
to statistics and motif rules) is gone. `tools/pieces-provenance.json` is index-aligned with the
pane file: source, source resolution, area, equivalent diameter, shape class and signal per piece.

**The source.** The NGV's own Zoomify panorama of the whole ceiling (BUIL000804, restitched from
the public tiles into `E:/sitecapture-captures/ngv-site/agent-ref-ceiling/online/ngv_zoomify_BUIL000804_full.jpg`,
29575 x 8272, about 1.8 mm per pixel on the plate, the steel clipped to black). It is already
rectified: the fifteen member lines across and five along are straight, and their pitch drifts
2181 to 2037 px, so the registration is piecewise-linear through the lines
(`tools/pano_register.py`), each line placed on its lattice hu / hv; the result is a 4 mm tile on
the shared huv grid in `sources/pano/` with a mask, a per-pixel source resolution and the
registration recorded in `meta.json`. A second stage (`tools/pano_refine.py --thin`) then measures
the steel on that tile itself, the 15 x 5 member nodes with a + template and the 56 sub-square
centres (where the hip crosses the diamond member) with an X template on the black steel, and
warps the tile piecewise-affinely (four triangles per sub-square) so the measured steel lands on
the lattice: 54 of 131 points measured with confidence, their radial offset p50 97 / p90 185 mm
before and 26 / 83 mm after; on the hips, which neither stage used, the median offset is 32 mm
and the p90 fell from 127 to 87 mm. Wide-member templates (the ridges' true widths) were tried
and rejected: they slide along the ridge and made the hips worse. Member offsets at the sub-square
edge midpoints (`--edges`) were tried too: 62 of 130 measurable, hips unchanged (34 vs 32 mm), so
the ~30 mm that remains is the floor of this evidence, not of the method.

**Which line is which, and which way round.** Settled by data, not by reading the picture: the
blurred-Lab NCC of the panorama against the bake ortho (`trackB/bottom-ortho-v29.png`, the real
GLB texture unwrapped) under four symmetries and five half-bay offsets. flipLR with a +PU/2
offset scores 0.63; the next best 0.51 (rot180, same offset), everything else 0.38 or under and
the unshifted phase 0.09 at most. The posed underside render (`underside/all/`, hall frame)
confirms north/south independently (0.41 vs 0.32 flipped). So the panorama's x runs east to
west, its thin verticals are the six column lines, its thick ones the ridges.

**The plate ends on the vertex phase.** This is the geometric correction of the pass. The
09-01 canopy ended on ridge lines at both walls (seven whole coffers). Three independent
sources say otherwise: the panorama (half a pitch from the outer ridges to the walls, the hips
meeting on the wall line: a half coffer), the roof-void walk (glass seen from hu -52.7 to -1.2
and nothing beyond either end, `topside2/`), and the bake itself (dark for the half bay west of
-52.7, and the 08-31 cloud's "8th bay crossing the east closure" is the east half coffer). Six
whole coffers and a half at each wall, one bay past the outer columns, seven pitches, 51.52 m:
NGV's own 51.5. `buildCanopy` now takes the u extent from the column heads (outer head minus /
plus one module), builds the half coffers by clipping each facet and rib polygon on the wall line
(they stay planar, so the cut is exact), and reports 8 x 2. The GLB's walls are wrong here: its
east wall (hu -4.0) is 2.84 m short of the real one and its west wall about 5 m past the real
one; the canopy passes through the GLB east wall rather than being cut short (flagged to the
walls pass; the real walls are at hu -52.68 and -1.16).

**The trace.** `tools/ceiling_trace2.py --side under --lattice new --absolute 12 --min-eqd 30 --min-inscribed 18`: because the
panorama's steel is exactly black, a slab is any pixel whose brightest channel clears 12 (the
relative envelope the topside needs missed the dark purples and blues). Watershed at the necks,
union-find merge, 9 mm polygon simplification, 30 mm minimum equivalent diameter, 18 mm minimum
inscribed diameter (what a 1.8 mm source resolves), pieces more than half on a steel band dropped and the rest clipped clear
(`tools/ceiling_assemble.py`, same band metric as `merge_panes.py`: ridge 0.125 m, cross / hip /
both diamonds 0.09 m). 6,987 distinct slabs traced on a 2 mm grid (four overlapping windows; a slab touching a
window's interior cut is left to the window that holds it whole, and the assembler drops the
406 duplicates), 6,926 kept (20 too small after clipping, 41 on the steel). The tile is rendered
and refined at 2 mm (`--mm 2`) so the tracer works at the panorama's own resolution; the
whole plate at 2 mm does not fit in memory, hence the windows.
Per bay 436 to 598 pieces in the whole coffers, 202 to 231 in the halves; glass covers 17 to 21 %
of each bay's plan, the same everywhere, which is what a plate of one design should show.

**Proof.** `node tools/ceiling-tiles.mjs <outdir>` (serve on :8877, Chrome on CDP_PORT): the pane
file's count is what the page read and every piece is inside the plate and lifted; every
provenance entry names a traced source under 10 mm/px; the plate ends on the vertex phase along
the hall and the ridge phase across it, 8 x 2, seven pitches; no piece centroid inside a steel
band; no page exceptions; shots of the west wall, the east wall, straight up and along.
`tools/ceiling-check.mjs` still passes (hubs, hoists on the ridge lines, the lift clamp).

**Colour, checked against our own videos.** Every piece's panorama colour was compared with the
same polygon in the posed hall renders (`underside/`: the day-walk, the night scans, the 4K
balcony frames, 12 to 20 mm/px). Those renders are too blurred at slab scale to calibrate
anything (per-channel fit gain 0.4, residual ~50 of 255: the blur mixes each slab with its
neighbours and the steel), but for the saturated slabs the hue agrees to 16 to 18 degrees
median against the walk and the combined sheet, so the panorama's colours are not corrected:
a correction fitted to blur would be fabrication. Scratch: `colour_check.json`.

**Every other source, weighed.** The harvest (124 files, `online/catalogue.json`) holds one other
straight-up photograph, Rennie Ellis's c.1980s slide (SLV IE7153100, 4790 x 7000): its member
lines run 670 to 1000 px apart for a 3.7 m sub-square, so it is about 4 mm/px with strong
perspective across the frame, film-soft, and cannot check or improve a 1.8 mm source; the rest
are oblique hall views, 1968 record shots, plans and a construction photo. Our own imagery: the
roof-void walk resolves 5 to 8 mm in patches (`topside2/`, self-registered to 48 mm median), the
posed hall renders 12 to 20 mm. The NGV panorama is the sharpest view of the glass that exists
in any source found, so the pane file rests on it alone, with the others as checks.

**Still open, honestly.** The panorama is one photograph: exposure and white balance are its
own, and pieces under 30 mm or narrower than 18 mm are not traced (in the test window 9 % of the
glass area is untraced: edge halos, slivers and the band clips, not whole slabs). The roof-void topside
(`topside2/`, 2 to 4 mm, self-registered per bay to 48 mm median) and the posed underside
renders (`underside/`) exist as independent checks and could refine shapes bay by bay; the
assembler takes several traces in priority order with per-piece provenance for exactly that.
The GLB wall error above is the other half of "looks exactly like the hall".
