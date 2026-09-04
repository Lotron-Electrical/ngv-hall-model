// install mode (Lloyd, 2026-09-04): the game is a keyed mode of the proposal sim, so the thing
// that has to be proved is not the game (game-drive/guide/floorcheck do that) but the SEAM: that
// a visitor without the key sees and downloads nothing, that the toggle builds and tears down
// without leaving a lift, a collider, a listener or a second animation loop behind, that an event
// and a night shift are never both on, and that the ordinary sim looks the same afterwards.
// Needs the :8877 serve and headless Chrome on :9333 (bash ~/scripts/headless-chrome.sh start 9333).
import fs from 'node:fs';
const port = 9333, out = process.argv[2] || process.env.TMP;
const base = 'http://127.0.0.1:8877/index.html';
const tabs = await (await fetch(`http://127.0.0.1:${port}/json`)).json();
let t = tabs.find((x) => x.type === 'page'); if (!t) t = await (await fetch(`http://127.0.0.1:${port}/json/new?about:blank`, { method: 'PUT' })).json();
const ws = new WebSocket(t.webSocketDebuggerUrl); let id = 0; const pend = {}; let logs = [];
ws.onmessage = (e) => { const m = JSON.parse(e.data); if (m.id && pend[m.id]) { pend[m.id](m.result); delete pend[m.id]; }
  if (m.method === 'Runtime.exceptionThrown') logs.push('EXC ' + JSON.stringify(m.params.exceptionDetails).slice(0, 300));
  if (m.method === 'Runtime.consoleAPICalled' && m.params.type === 'error') logs.push('ERR ' + m.params.args.map((a) => a.value || a.description).join(' ').slice(0, 300)); };
await new Promise((r) => (ws.onopen = r));
const send = (method, params = {}) => new Promise((r) => { const i = ++id; pend[i] = r; ws.send(JSON.stringify({ id: i, method, params })); });
const ev = async (expr) => { const r = await send('Runtime.evaluate', { expression: expr, returnByValue: true, awaitPromise: true }); return r.result ? r.result.value : r; };
const sleep = (ms) => new Promise((r) => setTimeout(r, ms));
const shot = async (n) => { const s = await send('Page.captureScreenshot', { format: 'jpeg', quality: 70 }); const p = `${out}/install-${n}.jpg`; fs.writeFileSync(p, Buffer.from(s.data, 'base64')); return p; };
const shots = [];
let bad = [];
const say = (ok, msg) => { console.log((ok ? 'ok   ' : 'FAIL ') + msg); if (!ok) bad.push(msg); };

await send('Page.enable'); await send('Runtime.enable'); await send('Network.enable'); await send('Network.setCacheDisabled', { cacheDisabled: true });
await send('Emulation.setDeviceMetricsOverride', { width: 900, height: 600, deviceScaleFactor: 1, mobile: false });

// every network request the page makes, so "no game code runs" can be checked as bytes, not belief
let reqs = [];
ws.addEventListener('message', (e) => { const m = JSON.parse(e.data); if (m.method === 'Network.requestWillBeSent') reqs.push(m.params.request.url); });

const load = async (url) => { logs = []; reqs = []; await send('Page.navigate', { url }); await sleep(1200);
  for (let i = 0; i < 40; i++) { await sleep(500); if (await ev('!!(window.ngv&&window.ngv.hall)')) break; } await sleep(1500); };
const rowShown = () => ev(`(()=>{const b=document.getElementById('install'); if(!b)return 'missing'; return b.closest('.row').style.display!=='none';})()`);
// a second animation loop shows up as twice the rAF ticks, so the loop is counted, not assumed
const tickStart = () => ev(`(()=>{window.__t=0; if(!window.__raf){window.__raf=requestAnimationFrame; requestAnimationFrame=(f)=>window.__raf((x)=>{window.__t++; return f(x);});} window.__t=0; return true;})()`);
const ticks = async (ms) => { await ev('window.__t=0'); await sleep(ms); return ev('window.__t'); };
const snap = () => ev(`(()=>({kids:ngv.scene.children.length, solids:dbg.solids, cam:ngv.cam.children.length, game:!!ngv.game}))()`);

// ---- 1. locked: no row, no game, no game module fetched
await ev(`try{localStorage.clear()}catch(e){}`);
await load(base + '?cb=' + Date.now());
say((await rowShown()) === false, 'without the key the Install row is hidden');
say((await ev('typeof ngv.game')) === 'undefined', 'without the key ngv.game is undefined');
say(!reqs.some((u) => /\/game\//.test(u)), 'without the key no game module is fetched (' + reqs.filter((u) => /\/game\//.test(u)).join(',') + ')');
await tickStart();
const t0 = await ticks(2000);
const clean0 = await snap();
shots.push(await shot('sim-before'));
const pngBefore = (await send('Page.captureScreenshot', { format: 'png' })).data;

// ---- 2. embed, still locked
await load(base + '?embed=1&cb=' + Date.now());
say((await rowShown()) === false, '?embed=1 without the key shows nothing new');
say((await ev('typeof ngv.game')) === 'undefined', '?embed=1 without the key has no game');

// ---- 3. the key: the row appears and the toggle builds
await load(base + '?install=gandel-2026&cb=' + Date.now());
say(!/install=/.test(await ev('location.search')), 'the key is stripped from the address and the page reloads clean');
say((await ev(`localStorage.getItem('ngv.install')`)) === 'gandel-2026', 'the key is stored');
say((await rowShown()) === true, 'with the key the Install row shows');
await tickStart();
const before = await snap();
const tIdle = await ticks(2000);

await ev(`document.getElementById('install').click()`);
for (let i = 0; i < 30; i++) { await sleep(500); if (await ev('!!ngv.game')) break; }
say(!!(await ev('!!ngv.game')), 'toggling on builds the game');
say(!!(await ev('!!(ngv.game&&ngv.game.lift&&ngv.game.crew&&ngv.game.install.slots.length===768)')), 'lift, crew and 768 slots are there');
say((await ev(`document.body.classList.contains('install')`)) === true, 'the page is in install mode');
await ev(`document.querySelector('#start').click()`); await sleep(1500);
const tGame = await ticks(2000);
say(tGame < t0 * 2.2, `one loop only while playing (${tGame} ticks/2 s vs ${t0} idle)`);
// the seam that matters: the fitted lights ARE the sim's strips, so an unfitted hall must have
// every LED at zero and fitting one run must light that run and nothing else
const litCount = `(()=>{let m=null; ngv.scene.traverse(o=>{if(!m&&o.isInstancedMesh&&o.instanceColor&&o.count===ngv.P.n)m=o;}); if(!m)return -1; const a=m.instanceColor.array; let n=0; for(let i=0;i<a.length;i+=3)if(a[i]+a[i+1]+a[i+2]>0.002)n++; return n;})()`;
const dark = await ev(litCount);
say(dark === 0, `nothing is lit before a light goes in (${dark} LEDs)`);
await ev(`(()=>{const g=ngv.game,r=g.install.runs[0]; for(const s of r.slots)g.install.fit(s);})()`); await sleep(600);
// which runs any lit LED belongs to (the strips are running a pattern, so not every LED in a
// fitted run is on at a given instant; what must hold is that no OTHER run has a lit LED)
const litRuns = await ev(`(()=>{let m=null; ngv.scene.traverse(o=>{if(!m&&o.isInstancedMesh&&o.instanceColor&&o.count===ngv.P.n)m=o;}); const a=m.instanceColor.array,P=ngv.P,seen={},g=ngv.game.install.runs[0];
 for(let i=0;i<P.n;i++)if(a[i*3]+a[i*3+1]+a[i*3+2]>0.002){const r=P.runs[P.run[i]]; seen[r.column+' gap '+r.gap]=(seen[r.column+' gap '+r.gap]||0)+1;}
 return {seen, want:g.column+' gap '+g.gap};})()`);
const keys = Object.keys(litRuns.seen);
say(keys.length === 1 && keys[0] === litRuns.want, `only the fitted run is lit (${JSON.stringify(litRuns.seen)}, wanted ${litRuns.want})`);
shots.push(await shot('on'));
const fps = await ev(`(async()=>{const a=ngv.game.dbg.frames; await new Promise(r=>setTimeout(r,2000)); return Math.round((ngv.game.dbg.frames-a)/2);})()`);
console.log('     fps in install mode:', fps);

// ---- 5. teardown gives the sim back
await ev(`document.getElementById('install').click()`); await sleep(1500);
const after = await snap();
say(after.game === false, 'toggling off tears the game down');
say(after.kids === before.kids, `scene children back to ${before.kids} (got ${after.kids})`);
say(after.solids === before.solids, `solids back to ${before.solids} (got ${after.solids})`);
say(after.cam === before.cam, `nothing left hanging off the camera (${before.cam} -> ${after.cam})`);
const tOff = await ticks(2000);
say(Math.abs(tOff - tIdle) < tIdle * 0.4 + 8, `no leaked loop after teardown (${tOff} ticks/2 s vs ${tIdle} before)`);
say((await ev(`document.body.classList.contains('install')`)) === false, 'install classes are off the body');
say((await ev(`getComputedStyle(document.getElementById('installUi')).display`)) === 'none', 'the install overlay is hidden again');
shots.push(await shot('off'));

// ---- 6. event and install are mutually exclusive. This runs AFTER the teardown counts because
// the sim's own event build has always left its solids in the list when it is switched off again
// (69 -> 108 -> 108 on an untouched page), and that is not install mode's to fix here.
await ev(`document.getElementById('install').click()`);
for (let i = 0; i < 30; i++) { await sleep(500); if (await ev('!!ngv.game')) break; }
await ev(`document.getElementById('event').click()`); await sleep(1500);
const both = await ev(`({event:document.getElementById('event').checked, install:document.getElementById('install').checked, game:!!ngv.game})`);
say(!(both.event && both.game), 'event and install are never both on: ' + JSON.stringify(both));
if (both.event) { await ev(`document.getElementById('event').click()`); await sleep(1200); }

// ---- 7. and it builds a second time
await ev(`document.getElementById('install').click()`);
for (let i = 0; i < 30; i++) { await sleep(500); if (await ev('!!ngv.game')) break; }
say(!!(await ev('!!ngv.game')), 'toggling on again works');
await ev(`document.getElementById('install').click()`); await sleep(1200);
say((await ev('typeof ngv.game')) === 'undefined', 'and off again');

// ---- 8. the ordinary sim, never having had install on, looks the same
await ev(`try{localStorage.clear()}catch(e){}`);
await load(base + '?cb=' + Date.now());
const clean1 = await snap();
say(clean1.kids === clean0.kids && clean1.solids === clean0.solids, `the plain sim is unchanged (${JSON.stringify(clean0)} vs ${JSON.stringify(clean1)})`);
shots.push(await shot('sim-after'));
const pngAfter = (await send('Page.captureScreenshot', { format: 'png' })).data;
const d = Math.abs(pngBefore.length - pngAfter.length) / pngBefore.length;
say(d < 0.05, `the plain sim renders the same picture (png size differs ${(d * 100).toFixed(1)}%)`);

say(logs.length === 0, 'no console errors on the plain sim' + (logs.length ? ': ' + logs.join(' | ') : ''));
console.log('screenshots:\n' + shots.join('\n'));
console.log(bad.length ? 'FAIL\n' + bad.join('\n') : 'PASS: install mode gates, builds, tears down and leaves the sim alone');
ws.close(); process.exit(bad.length ? 1 : 0);
