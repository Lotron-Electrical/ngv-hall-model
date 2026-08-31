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

Measured 2026-08-31: **an https page cannot open `ws://localhost` — Chrome blocks it** (the
localhost carve-out covers http fetches, not insecure WebSockets). The published GitHub Pages site
and any https embed of it will always show "not connected". Serve the page over http instead:
`node tools/serve.js`, then `http://127.0.0.1:8877/index.html?connect=1` — the `?connect=1`
parameter (optionally `&ws=host:port&off=N`) auto-opens the live input and retries until the
bridge is up, so no one has to find the panel and press Connect.

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
| `tools/dmx_bridge.js` | Art-Net / sACN → WebSocket bridge, zero dependencies |
| `tools/agent-setup.js` | the one command above, JSON-line output, zero dependencies |
| `tools/elm-fetch.js` | headless CSV / facts extraction over CDP, zero dependencies |
| `tools/serve.js` | local static server on 127.0.0.1:8877 for headless checks |
| `tools/run-bridge.cmd` | the double-click path for a human on Windows |
| `PLAN-agentic.md` | proposed `index.html` changes that would remove the remaining manual steps |

## Rules for an agent working in this repo

- Node 14+ is the only prerequisite. Nothing here uses npm packages; keep it that way.
- Never invent a number in a report. Read it from `--what facts` or the status endpoint.
- The page's own comments are the design record. Match their tone if you edit it: explain why, not
  what.
- Writes that a client would see (a live stream on a hall, a commit, a push) need the owner's word
  first.
