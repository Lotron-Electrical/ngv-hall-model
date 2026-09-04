// THE SEAL (Lloyd, 2026-09-04: "do a sweep to ensure the model is sealed"). From a grid of standing
// points across the hall and the storage corridor, at eye height and at the knee, a cube map is
// rendered with the sky painted a sentinel green; any green pixel is the outside showing
// through a hole. The sweep prints every point with a leak, the face it is on and how big, and
// screenshots the worst three from the player's eye, looking straight at the hole.
// Needs the :8877 serve and headless Chrome on :9333.
import fs from 'node:fs';
const port = 9333, base = 'http://127.0.0.1:8877/index.html', out = process.argv[2] || process.env.TMP;
const tabs = await (await fetch(`http://127.0.0.1:${port}/json`)).json();
let t = tabs.find((x) => x.type === 'page'); if (!t) t = await (await fetch(`http://127.0.0.1:${port}/json/new?about:blank`, { method: 'PUT' })).json();
const ws = new WebSocket(t.webSocketDebuggerUrl); let id = 0; const pend = {}; const logs = [];
ws.onmessage = (e) => { const m = JSON.parse(e.data); if (m.id && pend[m.id]) { pend[m.id](m.result); delete pend[m.id]; }
  if (m.method === 'Runtime.exceptionThrown') logs.push('EXC ' + JSON.stringify(m.params.exceptionDetails).slice(0, 400)); };
await new Promise((r) => (ws.onopen = r));
const send = (method, params = {}) => new Promise((r) => { const i = ++id; pend[i] = r; ws.send(JSON.stringify({ id: i, method, params })); });
const ev = async (expr) => { const r = await send('Runtime.evaluate', { expression: expr, returnByValue: true, awaitPromise: true }); if (r.exceptionDetails) throw new Error(JSON.stringify(r.exceptionDetails).slice(0, 500)); return r.result ? r.result.value : r; };
const sleep = (ms) => new Promise((r) => setTimeout(r, ms));
await send('Page.enable'); await send('Runtime.enable'); await send('Network.setCacheDisabled', { cacheDisabled: true });
await send('Emulation.setDeviceMetricsOverride', { width: 1280, height: 800, deviceScaleFactor: 1, mobile: false });
// --sim sweeps the proposal viewer as the client sees it (no shift, hall only); default is the shift
const SIM = process.argv.includes('--sim');
await send('Page.navigate', { url: base + (SIM ? '?still' : '?install=gandel-2026') });
for (let i = 0; i < 60; i++) { await sleep(1000); if (await ev(`!!document.querySelector('#loader.ready')`)) break; }
await sleep(1500);
if (SIM) { await ev(`document.getElementById('enter').click(); document.getElementById('roamfab').click(); 1`); await sleep(4000); }
else { await ev(`document.getElementById('enterInstall').click()`); for (let i = 0; i < 30; i++) { await sleep(1000); if (await ev(`document.body.classList.contains('playing')`)) break; } await sleep(1500); }

// the grid: hall u 2..47 x d 1.5..14 and (on the shift) corridor u 50..65 x d 4..11, at 1.6 m and 0.3 m
const pts = [];
for (let u = 2; u <= 47; u += 5) for (const d of [1.5, 4.5, 7.6, 10.5, 14]) pts.push([u, d]);
if (!SIM) for (let u = 50; u <= 65; u += 3.75) for (const d of [4, 7.5, 11]) pts.push([u, d]);
const res = await ev(`(async()=>{
  const THREE=await import('three'); const R=ngv.R, scene=ngv.scene, g=ngv.game;
  const HU=new THREE.Vector3(0.975681,0,0.219196), HD=new THREE.Vector3(0.219196,0,-0.975681), HO=new THREE.Vector3(-54.907447,-1.43545,3.040286);
  const fy=g?g.world.floorY:ngv.floorY; const W=(u,d,y)=>HO.clone().addScaledVector(HU,u).addScaledVector(HD,d).setY(y);
  const N=160, rt=new THREE.WebGLCubeRenderTarget(N), cc=new THREE.CubeCamera(0.05,400,rt); const buf=new Uint8Array(N*N*4);
  const bg=scene.background; scene.background=new THREE.Color(0x00ff00);
  // a point inside a pallet, a wall or a column is not a standing point: a short ray that meets a
  // back face first is inside something, and that point is skipped, not reported
  const meshes=[]; scene.traverse(o=>{ if(o.isMesh&&o.visible&&o.geometry&&o.material&&!o.material.transparent&&o.name!=='seal')meshes.push(o); });
  const ray=new THREE.Raycaster(); ray.far=0.9; const probes=[[1,0,0],[-1,0,0],[0,0,1],[0,0,-1],[0,1,0],[0,-1,0]].map(a=>new THREE.Vector3(...a));
  // the raycaster culls back faces on a one-sided material, so every material is two-sided for the probe and put back after
  const sides=meshes.map(m=>[].concat(m.material).map(x=>x.side)); const setSides=(all)=>meshes.forEach((m,i)=>[].concat(m.material).forEach((x,j)=>{ x.side=all?THREE.DoubleSide:sides[i][j]; x.needsUpdate=true; }));
  const inside=(p)=>{ setSides(true); let r=false; ray.far=0.9; for(const dir of probes){ ray.set(p,dir); const h=ray.intersectObjects(meshes,true)[0]; if(h&&h.face){ const n=h.face.normal.clone().transformDirection(h.object.matrixWorld); if(n.dot(dir)>0){ r=true; break; } } } setSides(false); return r; };
  // a spot with a prop standing on it (a pallet, the jack, a lift) is not a standing point either
  const props=scene.getObjectByName('install'); const propMeshes=[]; if(props)props.traverse(o=>{ if(o.isMesh&&o.visible&&o.name!=='seal')propMeshes.push(o); });
  const occupied=(u,d)=>{ if(!propMeshes.length)return false; ray.set(W(u,d,fy+2.5),new THREE.Vector3(0,-1,0)); ray.far=2.6; const h=ray.intersectObjects(propMeshes,true)[0]; return !!(h&&h.point.y>fy+0.05); };
  const faces=['+x','-x','+y','-y','+z','-z']; const outp=[]; let skipped=[];
  for(const [u,d] of ${JSON.stringify(pts)}) for(const h of [1.6,0.3]){
    const p=W(u,d,fy+h); if(inside(p)||occupied(u,d)){ skipped.push(u+','+d+','+h); continue; }
    cc.position.copy(p); cc.update(R,scene);
    const per=[]; let tot=0;
    for(let f=0;f<6;f++){ R.readRenderTargetPixels(rt,0,0,N,N,buf,f); let n=0,cx=0,cy=0; for(let i=0;i<N*N;i++){ const r=buf[i*4],gg=buf[i*4+1],b=buf[i*4+2]; if(gg>200&&r<70&&b<70){ n++; cx+=i%N; cy+=(i/N)|0; } }
      per.push(n); tot+=n; }
    if(tot>0) outp.push({u,d,h,tot,pct:+(100*tot/(6*N*N)).toFixed(2),per:Object.fromEntries(faces.map((k,i)=>[k,per[i]]).filter(([,v])=>v>0))});
  }
  scene.background=bg; rt.dispose(); return {n:${pts.length}*2-skipped.length, skipped, leaks:outp};
})()`);
console.log(`${SIM ? 'PROPOSAL VIEWER' : 'THE SHIFT'}: points swept ${res.n}; skipped as inside geometry: ${res.skipped.length ? res.skipped.join(' ') : 'none'}`);
if (!res.leaks.length) console.log('SEALED: no sky pixel from any point');
else { res.leaks.sort((a, b) => b.tot - a.tot); for (const l of res.leaks) console.log(`leak u=${l.u} d=${l.d} h=${l.h}  ${l.pct}% of the cube  faces ${JSON.stringify(l.per)}`); }
// the worst three, from the eye, looking at the face with the most sky
const dirs = { '+x': [1, 0, 0], '-x': [-1, 0, 0], '+y': [0, 1, 0], '-y': [0, -1, 0], '+z': [0, 0, 1], '-z': [0, 0, -1] };
const shots = [];
for (const [i, l] of res.leaks.slice(0, 3).entries()) {
  const face = Object.entries(l.per).sort((a, b) => b[1] - a[1])[0][0], v = dirs[face];
  if (SIM) await ev(`(()=>{const THREE_U=[0.975681,0,0.219196],D=[0.219196,0,-0.975681],O=[-54.907447,-1.43545,3.040286]; const p=[O[0]+THREE_U[0]*${l.u}+D[0]*${l.d}, ngv.floorY+${l.h}, O[2]+THREE_U[2]*${l.u}+D[2]*${l.d}]; ngv.cam.position.set(p[0],p[1],p[2]); ngv.cam.lookAt(p[0]+${v[0]},p[1]+${v[1]},p[2]+${v[2]}); ngv.R.render(ngv.scene,ngv.cam); return 1;})()`);
  else await ev(`(()=>{const g=ngv.game; g.player.pos.copy(g.hallToWorld(${l.u},${l.d},g.world.floorY)); g.player.yaw=Math.atan2(-(${v[0]}),-(${v[2]})); g.player.pitch=${v[1] > 0 ? 1.2 : v[1] < 0 ? -1.2 : 0}; return 1;})()`);
  await sleep(700);
  const s = await send('Page.captureScreenshot', { format: 'jpeg', quality: 75, clip: { x: 0, y: 90, width: 1280, height: 560, scale: 1 } });
  const p = `${out}/leak-${i + 1}-u${l.u}-d${l.d}-${face.replace('+', 'p').replace('-', 'm')}.jpg`; fs.writeFileSync(p, Buffer.from(s.data, 'base64')); shots.push(p);
}
if (shots.length) console.log('shots:\n' + shots.join('\n'));
if (logs.length) console.log('logs', logs);
ws.close();
