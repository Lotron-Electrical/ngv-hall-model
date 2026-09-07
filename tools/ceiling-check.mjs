// (2026-09-07) The ceiling's hardware: the eight-armed hub node on every column head and the
// permanent lighting rig along the north wall (truss, hoists, chains, fixtures). Loads the viewer,
// reads what was built, proves the geometry against the hall and the canopy, shoots it.
// Serve on :8877, headless Chrome on :9333 (CDP_PORT overrides; use your own browser when peers share the machine).
//   node tools/ceiling-check.mjs <outdir> [tag]
import fs from 'node:fs';
const out = process.argv[2] || '.', tag = process.argv[3] || 'ceiling-hw'; fs.mkdirSync(out, { recursive: true });
// CDP_PORT picks the Chrome: peers share this machine, so a proof should own its own browser
// PAGE names the file under the serve root (default index.html): a staged copy can be proved before it is committed
const port = +(process.env.CDP_PORT || 9333), url = 'http://127.0.0.1:8877/' + (process.env.PAGE || 'index.html') + '?cb=' + Date.now();
const tabs = await (await fetch(`http://127.0.0.1:${port}/json`)).json(); let t = tabs.find(x => x.type === 'page' && /index\.html|about:blank/.test(x.url)); if (!t) t = await (await fetch(`http://127.0.0.1:${port}/json/new?about:blank`, { method: 'PUT' })).json();
const ws = new WebSocket(t.webSocketDebuggerUrl); let id = 0; const pend = {}; const logs = [];
ws.onmessage = e => { const m = JSON.parse(e.data); if (m.id && pend[m.id]) { pend[m.id](m.result); delete pend[m.id]; }
  if (m.method === 'Runtime.exceptionThrown' && new RegExp((process.env.PAGE || 'index.html').replace(/[.\/]/g, '\\$&')).test((m.params.exceptionDetails.url || ''))) logs.push('EXC ' + JSON.stringify(m.params.exceptionDetails).slice(0, 400));
  if (m.method === 'Runtime.consoleAPICalled' && m.params.type === 'error') logs.push('ERR ' + m.params.args.map(a => a.value || a.description).join(' ').slice(0, 300)); };
await new Promise(r => ws.onopen = r);
const send = (method, params = {}) => new Promise(r => { const i = ++id; pend[i] = r; ws.send(JSON.stringify({ id: i, method, params })); });
const ev = async expr => { const r = await send('Runtime.evaluate', { expression: expr, returnByValue: true, awaitPromise: true }); if (!r) return undefined; if (r.exceptionDetails) return 'EVALERR ' + JSON.stringify(r.exceptionDetails.exception && r.exceptionDetails.exception.description).slice(0, 300); return r.result ? r.result.value : r; };
const sleep = ms => new Promise(r => setTimeout(r, ms));
const shot = async n => { const s = await send('Page.captureScreenshot', { format: 'jpeg', quality: 85 }); fs.writeFileSync(`${out}/${tag}-${n}.jpg`, Buffer.from(s.data, 'base64')); };
let fails = 0; const check = (ok, what) => { console.log((ok ? 'PASS ' : 'FAIL ') + what); if (!ok) fails++; };
await send('Network.enable'); await send('Network.setCacheDisabled', { cacheDisabled: true });
await send('Emulation.setDeviceMetricsOverride', { width: 1280, height: 800, deviceScaleFactor: 1, mobile: false });
await send('Page.enable'); await send('Runtime.enable'); await send('Page.navigate', { url });
for (let i = 0; i < 90; i++) { await sleep(500); if (await ev('!!(window.ngv&&window.ngv.canopy&&window.ngv.canopy.rig&&window.ngv.canopy.glass)')) break; }
const info = await ev(`(()=>{const c=ngv.canopy; if(!c||!c.rig) return null; const r=c.rig.userData.rig;
  return {bays:c.fit.bays, hubs:c.hubs?c.hubs.count:0, rig:r, rigChildren:c.rig.children.length, floorY:ngv.floorY, ceilY:ngv.ceilY}; })()`);
console.log('built', JSON.stringify(info));
check(info && info.hubs === 12 * 9, `hub nodes: ${info && info.hubs} instances (12 heads x 9 boxes)`);
check(info && info.rig && info.rig.hoists.length >= 5, `hoists: ${info && info.rig && info.rig.hoists.length} (one per ridge line the truss passes)`);
check(info && info.rig && info.rig.fixtures >= 20, `fixtures: ${info && info.rig && info.rig.fixtures}`);
// 1. every chain's top lands on the canopy surface: a ray up from the hoist meets canopy.mesh
//    within 6 cm of where the chain ends (the chain is not floating and not buried)
const chains = await ev(`(()=>{const c=ngv.canopy, r=c.rig.userData.rig, T=ngv.scene.constructor; const THREE=ngv.THREE||null;
  const out=[]; const ray=new (ngv.scene.children[0].constructor.prototype.constructor===Object?Object:Object)();
  return r.hoists.map(h=>h); })()`);
const chainProbe = await ev(`(()=>{const c=ngv.canopy, r=c.rig.userData.rig; const res=[];
  // reuse a chain mesh's own world position as the ray origin: children named by geometry
  const chainMeshes=c.rig.children.filter(o=>o.isMesh&&o.geometry.parameters&&o.geometry.parameters.radiusTop===0.007);
  const Ray=chainMeshes[0].position.constructor; // Vector3
  for(const m of chainMeshes){ const p=m.position.clone(); p.y=r.hoists[0].chainBottom;
    // walk the ray by sampling: the page keeps no Raycaster handle, so sample the canopy mesh with its own bbox test
    res.push({x:p.x,z:p.z,top:m.position.y+m.scale.y/2,bottom:m.position.y-m.scale.y/2}); }
  return res; })()`);
const rayHits = await ev(`(()=>{const c=ngv.canopy; const m=c.mesh; const pos=m.geometry.attributes.position; const res=[];
  const chains=${JSON.stringify(chainProbe)};
  // ray up from (x,z): test each canopy triangle in plan (Moller-free: barycentric in xz), interpolate y
  for(const ch of chains){ let best=null;
    for(let i=0;i<pos.count;i+=3){ const ax=pos.getX(i),az=pos.getZ(i),bx=pos.getX(i+1),bz=pos.getZ(i+1),cx=pos.getX(i+2),cz=pos.getZ(i+2);
      const d=(bz-cz)*(ax-cx)+(cx-bx)*(az-cz); if(Math.abs(d)<1e-9)continue;
      const l1=((bz-cz)*(ch.x-cx)+(cx-bx)*(ch.z-cz))/d, l2=((cz-az)*(ch.x-cx)+(ax-cx)*(ch.z-cz))/d, l3=1-l1-l2;
      if(l1<-1e-6||l2<-1e-6||l3<-1e-6)continue;
      const y=l1*pos.getY(i)+l2*pos.getY(i+1)+l3*pos.getY(i+2); if(best===null||y<best)best=y; }
    res.push({top:ch.top, canopy:best, gap:best===null?null:best-ch.top}); }
  return res; })()`);
console.log('chains', JSON.stringify(rayHits));
check(rayHits.length >= 5 && rayHits.every(h => h.gap !== null && h.gap > -0.01 && h.gap < 0.06), 'every chain ends on the canopy underside (0 to 60 mm gap)');
// 2. the truss sits where measured: 2.2 m off the north wall, 9.0 m above the carpet, inside the hall
const where = await ev(`(()=>{const c=ngv.canopy; const r=c.rig.userData.rig; const ch=c.rig.children.filter(o=>o.name==='rig-chord');
  const O=ngv.hall; const bb=new (ch[0].geometry.boundingBox.constructor)(); const res=[];
  for(const m of ch){ m.updateWorldMatrix(true,false); res.push({y:m.position.y}); }
  return {chordY:res.map(a=>a.y), floorY:${JSON.stringify(info.floorY)}, rig:r}; })()`);
const midY = where.chordY.reduce((a, b) => a + b, 0) / 3 - (-1.43545);
check(Math.abs(midY - 9.0) < 0.05, `truss centroid ${midY.toFixed(2)} m above the carpet (9.0 measured)`);
check(where.rig.u0 >= 0.5 && where.rig.u1 <= 47.5 && where.rig.d > 0.6 && where.rig.d < 3.3, `truss inside the hall: u ${where.rig.u0}..${where.rig.u1}, d ${where.rig.d} (wall at 0, columns at 3.8)`);
// 3. the hub nodes hang under the twelve funnel vertices, not below the column tops by more than the node depth
const hubs = await ev(`(()=>{const c=ngv.canopy; const im=c.hubs; const M=new (im.matrix.constructor)(); const res=[];
  for(let k=0;k<im.count;k+=9){ im.getMatrixAt(k,M); const e=M.elements; res.push({x:e[12],y:e[13],z:e[14]}); }
  const heads=[]; ngv.hall.traverse(o=>{ if(o.isMesh&&/column/i.test((o.material.name||''))&&o.geometry.boundingBox){ const b=o.geometry.boundingBox; heads.push({x:(b.min.x+b.max.x)/2,z:(b.min.z+b.max.z)/2,top:b.max.y}); } });
  return res.map(h=>{ let best=1e9,top=null; for(const c of heads){ const d=Math.hypot(c.x-h.x,c.z-h.z); if(d<best){best=d;top=c.top;} } return {d:best,under:top-h.y}; }); })()`);
console.log('hubs', JSON.stringify(hubs));
check(hubs.length === 12 && hubs.every(h => h.d < 0.6), 'twelve hub nodes, each within 0.6 m of a column head in plan');
check(hubs.every(h => h.under > -0.05 && h.under < 0.40), 'each node centre 0 to 0.4 m under its column top (300 mm node)');
// 4. the lift clamp sees the rig: the install sim's ceiling ray includes canopy.rig
const src = fs.readFileSync(new URL('../' + (process.env.PAGE || 'index.html'), import.meta.url), 'utf8');
check(/intersectObjects\(\[hallLevel,canopy&&canopy\.mesh,canopy&&canopy\.rig\]/.test(src), 'lift ceiling ray tests the rig as well as the glass');
// 5. the sim: the same page in install mode (the only camera a script can place is the
//    player's), the lift parked under the truss must clamp to the truss, not the glass
await send('Page.navigate', { url: url + '&install=gandel-2026' });
for (let i = 0; i < 90; i++) { await sleep(500); if (await ev('!!(window.ngv&&window.ngv.hall&&document.getElementById("install")&&window.ngv.canopy&&window.ngv.canopy.rig)')) break; }
await ev(`localStorage.setItem('ngv.install','gandel-2026'); document.getElementById('install').click()`);
for (let i = 0; i < 60; i++) { await sleep(500); if (await ev('!!(window.ngv&&window.ngv.game)')) break; }
await ev(`document.querySelector('#start').click()`); await sleep(800);
await ev(`for(const id of ['ghud','prompt','inv','reticle','deckh','wheels','touch','tzone','crewbtn','guidebtn']){const e=document.getElementById(id); if(e) e.style.visibility='hidden';}`);
const place = async (u, d, h, yawU, yawD, pitch) => ev(`(()=>{const g=ngv.game,P=g.player,L=g.lift;const p=g.hallToWorld(${u},${d},g.world.floorY);
  const q=g.hallToWorld(${u}+${yawU},${d}+${yawD},g.world.floorY); P.yaw=Math.atan2(-(q.x-p.x),-(q.z-p.z)); P.pitch=${pitch};
  if(${h}>0.2){ L.pos.copy(p); L.yaw=0; L.height=Math.max(0,${h}-L.deckY); L.ceilingY=Infinity; L.refresh(); if(!L.aboard)L.board(P,true); L.deckLocal.set(0,0); }
  else { if(L.aboard)L.leave(P,true); P.pos.copy(p); }
  return [P.yaw.toFixed(2),P.pitch]; })()`);
const setDay = async (h, house) => { await ev(`(()=>{const t=document.getElementById('tod');t.value=${h};t.dispatchEvent(new Event('input'));const hs=document.getElementById('house');if(hs){hs.value=${house};hs.dispatchEvent(new Event('input'));} ngv.dirty();})()`); await sleep(900); };
await setDay(12, 40);
// the clamp: the lift under the truss at u 10, d 2.2, deck at 5 m; the ceiling ray refreshes
// five times a second while aboard and must report the rig envelope's underside, about 8.2 m up
await place(10, 2.2, 5.0, 8, 0, 0.6); await sleep(1200);
const clamp = await ev(`(()=>{const g=ngv.game; return {ceil:g.lift.ceilingY-g.world.floorY, max:g.lift.maxHeight()}; })()`);
console.log('clamp under the truss', JSON.stringify(clamp));
check(clamp && clamp.ceil > 8.0 && clamp.ceil < 8.4, `lift ceiling under the truss reads ${clamp && clamp.ceil.toFixed(2)} m (the rig envelope's underside, fixtures included, is 8.16; the glass would be 11+)`);
await shot('under-truss');
await place(-1.0, 7.5, 0, 12, -3.0, 0.42); await sleep(900); await shot('rig-along');
await place(9.0, 6.0, 7.5, -3.5, -3.8, 0.18); await sleep(1200); await shot('rig-near');
await place(22.3, 5.4, 0, 0.0, -1.2, 1.35); await sleep(900); await shot('hub-up');
await place(20.5, 6.5, 9.6, 1.8, -2.6, 0.55); await sleep(1200); await shot('hub-close');
await setDay(21, 60);
await place(9.0, 6.0, 7.5, -3.5, -3.8, 0.18); await sleep(1200); await shot('rig-night');
console.log(logs.join('\n') || 'no page errors');
check(!logs.some(l => l.startsWith('EXC')), 'no exceptions on the page');
console.log(fails ? `FAIL ${fails}` : 'ALL PASS'); process.exit(fails ? 1 : 0);
