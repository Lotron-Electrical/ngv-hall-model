# PLAN-agentic.md — proposed `index.html` changes

Proposals only. Nothing in this file has been applied; `index.html` was not touched. Each item
says what it costs and what it buys. Ranked by value per line of change.

## 1. `?ws=<url>` auto-connect for Live input (≈ 6 lines)

Today an agent can start the bridge, configure ELM and verify Art-Net is arriving, then has to ask
a human to click **Connect**. That is the only remaining hand-off in the loop.

Read `ws` from the query string on load: if present, put it in `#lv_url` and click `#lv_btn`.
Add `&liveoff=<n>` for the universe offset while there.

```js
// near the live-input wiring
{const q=new URLSearchParams(location.search);
 if(q.has('liveoff'))document.getElementById('lv_off').value=+q.get('liveoff')||0;
 if(q.has('ws')){document.getElementById('lv_url').value=q.get('ws');
  document.getElementById('livein').open=true; document.getElementById('lv_btn').click();}}
```

Risk: a link someone else supplies could point the page at an arbitrary WebSocket. Restrict to
`ws://localhost` / `ws://127.0.0.1` unless the page itself is being served from that host.
`tools/agent-setup.js` already prints the URL this would enable (labelled as proposed).

## 2. `?status=json` machine-readable dump (≈ 12 lines)

`tools/elm-fetch.js` currently reaches into `window.ngv` to derive the facts. That works but it
makes every agent re-implement the same derivation, and it breaks the moment the internals move.

Have the page publish the facts itself: with `?status=json`, once the map is computed, write the
object into `<pre id="ngvstatus">` and `console.log` it, and expose it as `window.ngv.facts()`
regardless of the parameter. The object is exactly what `elm-fetch --what facts` prints now:
system, density, gapsPerColumn, strips, leds, pixels, pixelsPerUniverse, firstUniverse,
maxPixelsPerOutput, outputsPerController, stripOrder, dataDirection, elmProtocol, elmUpAxis,
pageUniverseMin, pageUniverseMax, summary.

A DOM node beats a console line: `chrome --headless --dump-dom` can read it with no CDP client at
all, which is the cheapest possible path for a weak agent.

## 3. `?export=elm` — CSV without a click (≈ 4 lines)

With `?export=elm`, call `elmCsv()` after the map is ready and put the string into
`<pre id="ngvcsv">` instead of (or as well as) triggering the download. Same argument as above:
`--dump-dom` then becomes a complete extraction path, and the Chrome download directory stops
being part of the contract. Combine with `?density=`/`?count=`/`?ppu=`/`?proto=` so one URL fully
determines the file.

## 4. Link AGENTS.md from the Live input panel (1 line)

The Live input `<p class="note">` already tells a human what to download. Add:
"Driving this with an AI? Point it at [AGENTS.md](AGENTS.md) and run `node tools/agent-setup.js`."
This is how a client's agent discovers the manual exists.

## 5. Show the bridge status inline (≈ 10 lines)

While Live input is open, poll `http://<bridge-host>:<port>/` every 2 s and show
`universes / clients / lastSource` under the Connect button. The endpoint already sends
`Access-Control-Allow-Origin: *`. It turns "nothing is happening" into a diagnosis: no bridge, or
a bridge with no Art-Net, or Art-Net on universes the map does not use.

## 6. Report unmatched universes (≈ 8 lines)

The page knows every universe its map wants (1..608) and every universe the stream carries. When a
frame arrives carrying universes outside the map — the classic off-by-one from an Art-Net/sACN
numbering mix-up — say so: "heard universes 0-607, map wants 1-608: set the universe offset to 1".
This one line of feedback removes the most common live-input support call.

## Not proposed

- A REST endpoint on the page. It is a static GitHub Pages file; there is nowhere to run one.
- Bundling a headless browser. `tools/elm-fetch.js` uses whatever Chrome the machine already has,
  which is the right dependency for a client's laptop.
- Committing a generated `elm.csv` to the repo. It would go stale the moment a control changes,
  and a stale patch is worse than no patch.
