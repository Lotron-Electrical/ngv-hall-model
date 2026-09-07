// (2026-09-08) The ceiling's glass, tile by tile. Loads the viewer, reads the canopy it built and the
// pane file it loaded, and proves: the plate ends on the vertex phase along the hall (eight coffers
// across, the two at the walls halves) and on the ridge phase across it; every piece in
// tools/pieces.bin is inside the plate and lifted; the piece count matches
// tools/pieces-provenance.json, whose every entry names a traced source (no synthetic pieces);
// no piece centroid sits on the steel. Then shoots the west wall, the east wall and straight up.
// Serve on :8877, headless Chrome on :9333 (CDP_PORT overrides; PAGE names a staged copy).
//   node tools/ceiling-tiles.mjs <outdir> [tag]
import fs from 'node:fs';
const out = process.argv[2] || '.', tag = process.argv[3] || 'ceiling-tiles'; fs.mkdirSync(out, { recursive: true });
const port = +(process.env.CDP_PORT || 9333), page = process.env.PAGE || 'index.html', url = 'http://127.0.0.1:8877/' + page + '?cb=' + Date.now();
const tabs = await (await fetch(`http://127.0.0.1:${port}/json`)).json(); let t = tabs.find(x => x.type === 'page' && /index\.html|about:blank/.test(x.url)); if (!t) t = await (await fetch(`http://127.0.0.1:${port}/json/new?about:blank`, { method: 'PUT' })).json();
const ws = new WebSocket(t.webSocketDebuggerUrl); let id = 0; const pend = {}; const logs = []; const infos = [];
ws.onmessage = e => { const m = JSON.parse(e.data); if (m.id && pend[m.id]) { pend[m.id](m.result); delete pend[m.id]; }
  if (m.method === 'Runtime.exceptionThrown' && new RegExp(page.replace(/[.\/]/g, '\\$&')).test((m.params.exceptionDetails.url || ''))) logs.push('EXC ' + JSON.stringify(m.params.exceptionDetails).slice(0, 400));
  if (m.method === 'Runtime.consoleAPICalled' && m.params.type === 'error') logs.push('ERR ' + m.params.args.map(a => a.value || a.description).join(' ').slice(0, 300));
  if (m.method === 'Runtime.consoleAPICalled' && m.params.type === 'info') infos.push(m.params.args.map(a => a.value || a.description).join(' ')); };
await new Promise(r => ws.onopen = r);
const send = (method, params = {}) => new Promise(r => { const i = ++id; pend[i] = r; ws.send(JSON.stringify({ id: i, method, params })); });
const ev = async expr => { const r = await send('Runtime.evaluate', { expression: expr, returnByValue: true, awaitPromise: true }); if (!r) return undefined; if (r.exceptionDetails) return 'EVALERR ' + JSON.stringify(r.exceptionDetails).slice(0, 300); return r.result.value; };
const sleep = ms => new Promise(r => setTimeout(r, ms));
const shot = async n => { const s = await send('Page.captureScreenshot', { format: 'jpeg', quality: 85 }); fs.writeFileSync(`${out}/${tag}-${n}.jpg`, Buffer.from(s.data, 'base64')); };
let fails = 0; const check = (ok, what) => { console.log((ok ? 'PASS ' : 'FAIL ') + what); if (!ok) fails++; };
await send('Network.enable'); await send('Network.setCacheDisabled', { cacheDisabled: true });
await send('Emulation.setDeviceMetricsOverride', { width: 1280, height: 800, deviceScaleFactor: 1, mobile: false });
await send('Page.enable'); await send('Runtime.enable'); await send('Page.navigate', { url });
for (let i = 0; i < 90; i++) { await sleep(500); if (await ev('!!(window.ngv&&window.ngv.canopy&&window.ngv.canopy.rig&&window.ngv.canopy.glass)')) break; }
await sleep(1000);
const fit = await ev(`(()=>{const c=ngv.canopy; return {bays:c.fit.bays, rect:c.fit.rect, ou:c.fit.ou, ov:c.fit.ov, PU:c.fit.PU, PV:c.fit.PV, anchors:c.fit.anchors,
  glassTris:c.glass.geometry.attributes.position.count/3}; })()`);
console.log('built', JSON.stringify(fit));
const glassLine = infos.find(s => /^canopy glass:/.test(s)) || '';
console.log(glassLine);
const m = glassLine.match(/(\d+) panes in the file, (\d+) inside the plate/);
const inFile = m ? +m[1] : -1, kept = m ? +m[2] : -1;
// the pane file and its provenance, read here as the page reads them
const bin = fs.readFileSync('tools/pieces.bin'); const n = bin.readUInt32LE(4);
const prov = JSON.parse(fs.readFileSync('tools/pieces-provenance.json', 'utf8'));
check(n === inFile, `pane file: ${n} pieces, the page read ${inFile}`);
check(kept === n, `every piece is inside the plate and lifted (${kept} of ${n})`);
check(prov.pieces.length === n && prov.pieces.every(p => p.src && p.gsd > 0 && p.gsd < 10), `provenance: ${prov.pieces.length} entries, all naming a traced source under 10 mm/px, none synthetic`);
const PU = fit.PU, PV = fit.PV, ou = fit.ou, ov = fit.ov, [su0, sv0, su1, sv1] = fit.rect;
const fu0 = (su0 - ou) / PU, fu1 = (su1 - ou) / PU, fv0 = (sv0 - ov) / PV, fv1 = (sv1 - ov) / PV;
check(Math.abs(fu0 - Math.round(fu0)) < 0.01 && Math.abs(fu1 - Math.round(fu1)) < 0.01, `plate ends on the vertex phase along the hall (su0 ${su0.toFixed(3)}, su1 ${su1.toFixed(3)}: ${(fu1 - fu0).toFixed(2)} pitches)`);
check(Math.abs(Math.abs(fv0 - Math.round(fv0)) - 0.5) < 0.01 && Math.abs(Math.abs(fv1 - Math.round(fv1)) - 0.5) < 0.01, `plate ends on the ridge phase across the hall`);
check(fit.bays[0] === 8 && fit.bays[1] === 2, `8 x 2 coffers across (two halves at the walls): ${fit.bays}`);
check(Math.abs((su1 - su0) - 7 * PU) < 0.01, `seven pitches wall to wall: ${(su1 - su0).toFixed(2)} m (NGV: 51.5 m)`);
// no piece centroid on the steel: same bands the shader paints (ridge 0.125, the rest 0.09)
const u0 = bin.readFloatLE(8), v0 = bin.readFloatLE(12), mm = bin.readUInt16LE(16); let o = 18, onSteel = 0, outside = 0;
const du = -58.3053, dv = -0.4556;
for (let i = 0; i < n; i++) { const k = bin[o + 3]; o += 4; let cu = 0, cv = 0;
  for (let j = 0; j < k; j++) { cu += u0 + bin.readUInt16LE(o) / mm; cv += v0 + bin.readUInt16LE(o + 2) / mm; o += 4; }
  cu = cu / k + du; cv = cv / k + dv;
  if (cu < su0 || cu > su1 || cv < sv0 || cv > sv1) outside++;
  const qu = (cu - ou) / PU, qv = (cv - ov) / PV, fu = qu - Math.round(qu), fv = qv - Math.round(qv);
  const dRidge = Math.min(Math.abs(Math.abs(fu) - 0.5) * PU, Math.abs(Math.abs(fv) - 0.5) * PV);
  const dCross = Math.min(Math.abs(fu) * PU, Math.abs(fv) * PV);
  const x = fu * PU, y = fv * PV, dHip = Math.abs(Math.abs(x) - Math.abs(y)) * 0.7071, dDia = Math.abs(Math.abs(x) + Math.abs(y) - PU / 2) * 0.7071;
  if (dRidge < 0.125 || dCross < 0.09 || dHip < 0.09 || dDia < 0.09) onSteel++; }
check(outside === 0, `piece centroids inside the plate: ${n - outside} of ${n}`);
check(onSteel === 0, `piece centroids clear of the steel bands: ${n - onSteel} of ${n}`);
// shots: the west wall, the east wall (through the GLB's short east wall, see AGENTS.md), straight up
const place = async (u, d, yawU, yawD, pitch) => ev(`(()=>{const g=ngv.game,P=g.player,L=g.lift;const p=g.hallToWorld(${u},${d},g.world.floorY);
  const q=g.hallToWorld(${u}+${yawU},${d}+${yawD},g.world.floorY); P.yaw=Math.atan2(-(q.x-p.x),-(q.z-p.z)); P.pitch=${pitch}; if(L.aboard)L.leave(P,true); P.pos.copy(p); return [P.yaw.toFixed(2),P.pitch]; })()`);
const setDay = async (h, house) => { await ev(`(()=>{const t=document.getElementById('tod');t.value=${h};t.dispatchEvent(new Event('input'));const hs=document.getElementById('house');if(hs){hs.value=${house};hs.dispatchEvent(new Event('input'));} ngv.dirty();})()`); await sleep(900); };
// the same page in install mode: the only camera a script can place is the player's
await send('Page.navigate', { url: url + '&install=gandel-2026' });
for (let i = 0; i < 90; i++) { await sleep(500); if (await ev('!!(window.ngv&&window.ngv.hall&&document.getElementById("install")&&window.ngv.canopy&&window.ngv.canopy.glass)')) break; }
await ev(`localStorage.setItem('ngv.install','gandel-2026'); document.getElementById('install').click()`);
for (let i = 0; i < 60; i++) { await sleep(500); if (await ev('!!(window.ngv&&window.ngv.game)')) break; }
await ev(`document.querySelector('#start').click()`); await sleep(800);
await setDay(12, 40);
await place(12, 7.5, -4, 0, 0.9); await sleep(1200); await shot('west-wall');
await place(40, 7.5, 6, 0, 1.1); await sleep(1200); await shot('east-wall');
await place(30, 7.5, 0, -1.2, 1.45); await sleep(1200); await shot('straight-up');
await place(30, 2.0, 5, 1.5, 0.75); await sleep(1200); await shot('along');
console.log(logs.length ? logs.join('\n') : 'no page errors');
check(logs.length === 0, 'no exceptions on the page');
console.log(fails ? `FAIL ${fails}` : 'ALL PASS'); ws.close(); process.exit(fails ? 1 : 0);
