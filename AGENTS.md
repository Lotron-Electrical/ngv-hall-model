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
`game.html` + `game/*.js`, spec in `GAME-PLAN.md`. Shares only `model.glb` and `runs.json` with the
viewer; `index.html` is never touched by game work. Built by Codex from the spec (two rounds; round
one had the clock at an hour per second and the spawn inside a solid box). Check it headless with
`node tools/game-check.mjs` (serve on :8877, chrome via headless-chrome.sh on 9333; it prints the
HUD text and console errors and saves %TMP%/game-1.jpg, the phone view after Start Shift).
Phase 1 = world, controls, lift, pallets/boxes/wrap, fitting, clock, clean-up rule, save.
Phases owed: 2 fatigue + hallucinations, 3 helper and team AI, 4 sound.
- 2026-09-04 (Claude, no Codex from here): DOUBLE DOORS at the storage doorway (`world.js`: two
  leaves hung 0.3 m on the hall side of the wall line, swinging 100 degrees into the corridor for
  anyone within 3.2 m; a parked lift does not hold them; shut = a wall in `collideWorld`). The
  scanned wall is solid there, so every hall material discards fragments inside the door volume
  (`onBeforeCompile`; the appended vertex line MUST start on a new line, the chunk ends in
  #endif). The lift is Genie-styled (`lift.js`: blue chassis + cage, grey 5-pair stack). `fx.js`:
  fatigue vignette from 01:00, from 03:00 vanishing fitted lights, leaning columns, colour drift,
  breathing FOV, a ghost lift. Clean-up counts the lift, jack and bags. Off the lift only at ground.
  Visual checks: `tools/game-look.mjs`, `tools/game-look2.mjs` (contact sheets in %TMP%).
- Stamina + fatigue (Lloyd, 2026-09-04): `body.js`. Stamina drains with effort (carry 4/s, jacked
  pallet 7/s, riding the lift 1.2/s), recovers at rest (9/s standing, 4/s walking, slower as
  fatigue rises); under 15 you crawl, under 10/15 you cannot take a box / jack a pallet. Fatigue
  climbs with the clock (2/h to 01:00, 6, 12, 20/h in the last hours) plus a tenth of stamina
  spent; it lowers the stamina ceiling (to 40 at 100) and speed (to 55%), and drives the small
  hours (`fx.levelFor`: from 70 fatigue). Two bars under the HUD. Reach is measured on the floor
  plan (`items.js near`): the old straight-line reach from the eye never got a bag on the floor.
  Boarding the lift is by ACTION only; the lift parks at (53.6, 9.6), the jack at (55.8, 9.6).
- Crew (2026-09-04): `crew.js`. After column 1 a HELPER (orange) works the column nearest your
  lift: jacks its pallet to the column foot, keeps two open boxes there, loads your deck when it
  is down and empty, bags wrap, runs full bags to the skip. After column 2 a TEAM (yellow, two
  figures, their own Genie lift and jack) claims the nearest unclaimed column and does it run by
  run (~7 s a light, slower as the clock tires them); one more team per further column, max 3.
  At 04:30 everyone packs up (lifts home, pallets back). Toasts announce joins and finished
  columns. `tools/game-crew.mjs` scripts the unlocks and watches them work.
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
  box (12 m at 0.5 m/s each way), so a solo column is ~12-13 min = about one night, the helper
  night ~1.5 columns, then a column per team per night. The lift already rises 2-3x faster than
  a real GS-4046.
- Storage + collisions (Lloyd, 2026-09-04: larger storage, nothing clips): the corridor is 17 x 9 m
  (u 48.9-66, d 3-12), pallets in two rows of six (`palletHome`: N row d 4.5, S row d 10.5, 2.3 m
  apart) with a 4 m aisle, lifts and jacks at the aisle's end, bags by the end wall, the skip
  outside a person-sized opening (a lift stops at the wall). `refreshObstacles` (items.js) rebuilds
  a plan of circles every frame (pallets 0.95, boxes 0.4, bags 0.45, lifts two of 0.85, skip 1.9)
  and `collideWorld(pos, r, world, ignore)` pushes every mover out of them; a mover ignores what
  it carries and the lift it rides. Reaches must sit OUTSIDE the collision radii (pallet 1.5,
  skip 2.6/2.9) or the crew walk forever.
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
  plate (the old 0.2 m span floor did). Two treads (`Lift.TREADS`, local x -1.72/-1.42, y
  0.44/0.88) and stringers hang off the back of the chassis. The back mid rail is `lift.gate`, a
  group hinged at (-1.23, 0.55, -0.6); `rotation.x = -1.2` is fully up. `board(player)` and
  `leave(player)` run `lift.anim` (`startAnim` / `stepAnim`): walk to the foot of the steps (local
  x -2.0), up the treads with the gate rising, duck under the top rail (`player.eye` 1.68 -> 0.95)
  onto the deck, stand at `DOOR` as the gate drops; leaving walks the same frames backwards. While
  `lift.anim` runs `nearestAction` returns 'Climbing aboard' / 'Climbing down' with run null, F is
  ignored, and yaw eases to face along the lift. `board(p, true)` / `leave(p, true)` are the
  instant forms for scripts (game-drift uses them). `tools/game-drive.mjs` waits the climb out and
  asserts eye dipped under 1.0 and the gate rose past 0.8 rad both ways; `tools/game-liftlook.mjs`
  shoots the lift from the back quarter, raised, mid-climb and aboard.
