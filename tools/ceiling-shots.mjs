// (2026-09-06) the canopy as it renders, shot from inside install mode (the only camera a script
// can place): from the floor looking up, from a raised lift deck at a slant, and close under the
// glass, by day (12:00), dusk (18:30) and night (21:00). Serve on :8877, headless Chrome on :9333.
//   node tools/ceiling-shots.mjs <outdir> [tag]
import fs from 'node:fs';
const out = process.argv[2] || '.', tag = process.argv[3] || 'ceiling'; fs.mkdirSync(out, { recursive: true });
const port = 9333, url = 'http://127.0.0.1:8877/index.html?install=gandel-2026&cb=' + Date.now();
const tabs = await (await fetch(`http://127.0.0.1:${port}/json`)).json(); let t = tabs.find(x => x.type === 'page'); if (!t) t = await (await fetch(`http://127.0.0.1:${port}/json/new?about:blank`, { method: 'PUT' })).json();
const ws = new WebSocket(t.webSocketDebuggerUrl); let id = 0; const pend = {}; const logs = [];
ws.onmessage = e => { const m = JSON.parse(e.data); if (m.id && pend[m.id]) { pend[m.id](m.result); delete pend[m.id]; } if (m.method === 'Runtime.exceptionThrown') logs.push('EXC ' + JSON.stringify(m.params.exceptionDetails).slice(0, 400)); };
await new Promise(r => ws.onopen = r);
const send = (method, params = {}) => new Promise(r => { const i = ++id; pend[i] = r; ws.send(JSON.stringify({ id: i, method, params })); });
const ev = async expr => { const r = await send('Runtime.evaluate', { expression: expr, returnByValue: true, awaitPromise: true }); if (!r) return undefined; if (r.exceptionDetails) return 'EVALERR ' + JSON.stringify(r.exceptionDetails.exception && r.exceptionDetails.exception.description).slice(0, 300); return r.result ? r.result.value : r; };
const sleep = ms => new Promise(r => setTimeout(r, ms));
const shot = async n => { const s = await send('Page.captureScreenshot', { format: 'jpeg', quality: 85 }); fs.writeFileSync(`${out}/${tag}-${n}.jpg`, Buffer.from(s.data, 'base64')); };
await send('Network.enable'); await send('Network.setCacheDisabled', { cacheDisabled: true });
await send('Emulation.setDeviceMetricsOverride', { width: 1280, height: 800, deviceScaleFactor: 1, mobile: false });
await send('Page.enable'); await send('Runtime.enable'); await send('Page.navigate', { url });
for (let i = 0; i < 60; i++) { await sleep(500); if (await ev('!!(window.ngv&&window.ngv.hall&&document.getElementById("install"))')) break; }
await ev(`localStorage.setItem('ngv.install','gandel-2026'); document.getElementById('install').click()`);
for (let i = 0; i < 60; i++) { await sleep(500); if (await ev('!!(window.ngv&&window.ngv.game)')) break; }
await ev(`document.querySelector('#start').click()`); await sleep(800);
// the HUD off for a clean picture
await ev(`for(const id of ['ghud','prompt','inv','reticle','deckh','wheels','touch']){const e=document.getElementById(id); if(e) e.style.visibility='hidden';}`);
const info = await ev(`(()=>{const c=ngv.canopy;const g=c&&c.glass;return g?{bays:c.fit.bays,glassTris:g.geometry.attributes.position.count/3,floorY:ngv.floorY,ceilY:ngv.ceilY,mat:g.material.name}:'no canopy glass'})()`);
console.log('canopy', JSON.stringify(info));
// place the player: on the floor, or on the lift deck at height h (the deck carries the eye)
const place = async (u, d, h, yawU, yawD, pitch) => ev(`(()=>{const g=ngv.game,P=g.player,L=g.lift;const p=g.hallToWorld(${u},${d},g.world.floorY);
  const q=g.hallToWorld(${u}+${yawU},${d}+${yawD},g.world.floorY); P.yaw=Math.atan2(-(q.x-p.x),-(q.z-p.z)); P.pitch=${pitch};
  if(${h}>0.2){ L.pos.copy(p); L.yaw=0; L.height=Math.max(0,${h}-L.deckY); L.ceilingY=Infinity; L.refresh(); if(!L.aboard)L.board(P,true); L.deckLocal.set(0,0); }
  else { if(L.aboard)L.leave(P,true); P.pos.copy(p); }
  return [P.yaw.toFixed(2),P.pitch]; })()`);
const setDay = async (h, house) => { await ev(`(()=>{const t=document.getElementById('tod');t.value=${h};t.dispatchEvent(new Event('input'));const hs=document.getElementById('house');if(hs){hs.value=${house};hs.dispatchEvent(new Event('input'));} ngv.dirty();})()`); await sleep(900); };
for (const [name, h, house] of [['day', 12, 0], ['dusk', 18.5, 30], ['night', 21, 60]]) {
  await setDay(h, house);
  await place(24, 7.5, 0, 6, 0, 1.35); await sleep(900); await shot(`${name}-up`);
  await place(8, 2.0, 8.0, 12, 5, 0.45); await sleep(1200); await shot(`${name}-slant`);
  await place(24, 7.5, 10.2, 3, 1.5, 0.95); await sleep(1200); await shot(`${name}-close`);
}
console.log(logs.join('\n') || 'no errors');
ws.close(); process.exit(0);
