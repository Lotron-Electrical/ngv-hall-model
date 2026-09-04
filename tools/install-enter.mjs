// the way in (Lloyd, 2026-09-04): with the key stored, a "The Install" button stands beside Enter
// Gandel Hall on the loader and one tap starts the shift; without the key the button does not exist.
import fs from 'node:fs';
const port = 9333, base = 'http://127.0.0.1:8877/index.html';
const out = process.argv[2] || process.env.TMP;
const tabs = await (await fetch(`http://127.0.0.1:${port}/json`)).json();
let t = tabs.find((x) => x.type === 'page'); if (!t) t = await (await fetch(`http://127.0.0.1:${port}/json/new?about:blank`, { method: 'PUT' })).json();
const ws = new WebSocket(t.webSocketDebuggerUrl); let id = 0; const pend = {}; const logs = [];
ws.onmessage = (e) => { const m = JSON.parse(e.data); if (m.id && pend[m.id]) { pend[m.id](m.result); delete pend[m.id]; }
  if (m.method === 'Runtime.exceptionThrown') logs.push('EXC ' + JSON.stringify(m.params.exceptionDetails).slice(0, 300)); };
await new Promise((r) => ws.onopen = r);
const send = (method, params = {}) => new Promise((r) => { const i = ++id; pend[i] = r; ws.send(JSON.stringify({ id: i, method, params })); });
const ev = async (expr) => { const r = await send('Runtime.evaluate', { expression: expr, returnByValue: true, awaitPromise: true }); return r.result ? r.result.value : r; };
const sleep = (ms) => new Promise((r) => setTimeout(r, ms));
const bad = []; const say = (ok, msg) => { console.log((ok ? 'ok   ' : 'FAIL ') + msg); if (!ok) bad.push(msg); };
await send('Emulation.setDeviceMetricsOverride', { width: 412, height: 915, deviceScaleFactor: 1, mobile: true });
await send('Page.enable'); await send('Runtime.enable'); await send('Network.setCacheDisabled', { cacheDisabled: true });
const load = async (url) => { await send('Page.navigate', { url }); for (let i = 0; i < 40; i++) { await sleep(1000); if (await ev(`!!document.querySelector('#loader.ready')`)) break; } };
await load(base + '?cb=' + Date.now()); await ev(`localStorage.removeItem('ngv.install')`); await load(base + '?cb=' + Date.now());
let r = await ev(`(()=>{const b=document.querySelector('#enterInstall');return JSON.stringify({hidden:b.hidden,shown:getComputedStyle(b).display!=='none'});})()`);
say(JSON.parse(r).hidden && !JSON.parse(r).shown, `without the key the button is not there (${r})`);
await load(base + '?install=gandel-2026'); await sleep(1500);
r = await ev(`(()=>{const b=document.querySelector('#enterInstall');const rc=b.getBoundingClientRect();return JSON.stringify({hidden:b.hidden,shown:getComputedStyle(b).display!=='none',h:Math.round(rc.height),inView:rc.bottom<=innerHeight&&rc.top>=0,search:location.search});})()`);
const j = JSON.parse(r); say(!j.hidden && j.shown && j.inView && j.h >= 40, `with the key the button stands on the loader (${r})`);
const s1 = await send('Page.captureScreenshot', { format: 'jpeg', quality: 80 }); fs.writeFileSync(`${out}/enter-install.jpg`, Buffer.from(s1.data, 'base64'));
await ev(`document.querySelector('#enterInstall').click()`); for (let i = 0; i < 30; i++) { await sleep(500); if (await ev(`!!(window.ngv&&ngv.game)`)) break; } await sleep(800);
r = await ev(`(()=>JSON.stringify({game:!!ngv.game,ui:document.querySelector('#installUi').classList.contains('on'),prompt:document.querySelector('#prompt')?.textContent,loaderGone:document.querySelector('#loader').classList.contains('gone')}))()`);
const k = JSON.parse(r); say(k.game && k.ui && k.loaderGone, `one tap enters the hall and starts the shift (${r})`);
const s2 = await send('Page.captureScreenshot', { format: 'jpeg', quality: 80 }); fs.writeFileSync(`${out}/enter-install-in.jpg`, Buffer.from(s2.data, 'base64'));
say(logs.length === 0, 'no exceptions ' + logs.join(' | '));
console.log(bad.length ? 'FAIL' : 'PASS'); ws.close(); process.exit(bad.length ? 1 : 0);
