// the fitted fixture and the guide (2026-09-04): the game's light is now a port of the proposal
// sim's fixture (game/fixture.js) and every empty slot can stand as a red bar. This checks the
// fixture really lands on the run line, that fitting and hiding move the right instances, that
// the guide toggle does what it says, and what the frame rate is with all 768 lights in.
// Needs the :8877 serve and headless Chrome on :9333 (bash ~/scripts/headless-chrome.sh start 9333).
import fs from 'node:fs';
const port = 9333, url = 'http://127.0.0.1:8877/game.html?cb=' + Date.now();
const out = process.argv[2] || process.env.TMP;
const tabs = await (await fetch(`http://127.0.0.1:${port}/json`)).json();
let t = tabs.find((x) => x.type === 'page'); if (!t) t = await (await fetch(`http://127.0.0.1:${port}/json/new?about:blank`, { method: 'PUT' })).json();
const ws = new WebSocket(t.webSocketDebuggerUrl); let id = 0; const pend = {}; const logs = [];
ws.onmessage = (e) => { const m = JSON.parse(e.data); if (m.id && pend[m.id]) { pend[m.id](m.result); delete pend[m.id]; }
  if (m.method === 'Runtime.exceptionThrown') logs.push('EXC ' + JSON.stringify(m.params.exceptionDetails).slice(0, 400));
  if (m.method === 'Runtime.consoleAPICalled' && m.params.type === 'error') logs.push('ERR ' + JSON.stringify(m.params.args.map((a) => a.value || a.description)).slice(0, 300)); };
await new Promise((r) => ws.onopen = r);
const send = (method, params = {}) => new Promise((r) => { const i = ++id; pend[i] = r; ws.send(JSON.stringify({ id: i, method, params })); });
const ev = async (expr) => { const r = await send('Runtime.evaluate', { expression: expr, returnByValue: true, awaitPromise: true }); return r.result ? r.result.value : r; };
const sleep = (ms) => new Promise((r) => setTimeout(r, ms));
const shot = async (n) => { const s = await send('Page.captureScreenshot', { format: 'jpeg', quality: 80 }); fs.writeFileSync(`${out}/guide-${n}.jpg`, Buffer.from(s.data, 'base64')); return `${out}/guide-${n}.jpg`; };
await send('Emulation.setDeviceMetricsOverride', { width: 900, height: 600, deviceScaleFactor: 1, mobile: false });
await send('Page.enable'); await send('Runtime.enable'); await send('Network.enable');
await send('Network.setCacheDisabled', { cacheDisabled: true });   // or the modules come from cache
await send('Page.navigate', { url });
for (let i = 0; i < 30; i++) { await sleep(1000); if (await ev('!!window.game')) break; }
await ev(`localStorage.clear(); window.game.install.setGuide(true); document.querySelector('#start').click()`); await sleep(500);

const bad = [];
const say = (ok, msg) => { console.log((ok ? 'ok   ' : 'FAIL ') + msg); if (!ok) bad.push(msg); };

// helpers that live in the page: instance scale and the world box of one cover instance
await ev(`import('three').then(m=>{window.T=m;window.qs= (i,m)=>{const M=new T.Matrix4();m.getMatrixAt(i,M);const s=new T.Vector3();M.decompose(new T.Vector3(),new T.Quaternion(),s);return +s.length().toFixed(6);};return 1;})`);

// (b) guide on, nothing fitted: every slot has a red bar and no fixture is lit
let r = JSON.parse(await ev(`(()=>{const I=window.game.install;let bars=0,lit=0;
 for(let i=0;i<I.slots.length;i++){if(I.guides.vis[i]&&qs(i,I.guides.mesh)>1e-6)bars++;if(I.fx.vis[i])lit++;}
 return JSON.stringify({total:I.counts().total,fitted:I.counts().fitted,bars,lit,meshVisible:I.guides.mesh.visible,guide:I.guide});})()`));
console.log(' state:', JSON.stringify(r));
say(r.bars === r.total && r.meshVisible && r.guide, `guide on with 0 fitted: ${r.bars}/${r.total} red bars visible`);
say(r.lit === 0 && r.fitted === 0, `no fixture shown before any fit (lit=${r.lit})`);

// (c) fit two slots: their fixture instances take a real scale, everyone else's stay zero
r = JSON.parse(await ev(`(()=>{const I=window.game.install;I.fit(I.slots[0],{carry:null});I.fit(I.slots[1],{carry:null});
 const P=3,L=I.fx.leds;const sc=i=>({rib:[0,1,2].map(k=>qs(i*P+k,I.fx.ribbon)),cov:qs(i,I.fx.cover),em:qs(i*L,I.fx.emit),bar:qs(i,I.guides.mesh)});
 let others=0;for(let i=2;i<I.slots.length;i++){if(qs(i,I.fx.cover)>1e-6||qs(i*L,I.fx.emit)>1e-6||qs(i*P,I.fx.ribbon)>1e-6)others++;}
 return JSON.stringify({a:sc(0),b:sc(1),others,fitted:I.counts().fitted});})()`));
console.log(' fitted:', JSON.stringify(r));
const live = (s) => s.rib.every((x) => x > 1e-6) && s.cov > 1e-6 && s.em > 1e-6;
say(live(r.a) && live(r.b), 'slots 0 and 1: ribbon, cover and emitter instances have non-zero scale');
say(r.others === 0, `every other slot's fixture stays zero-scale (${r.others} strays)`);
say(r.a.bar === 0 && r.b.bar === 0, 'the red bar goes away where a light went in');

// (e) the cover really sits on the run line, 9 mm proud of it
r = JSON.parse(await ev(`(()=>{const I=window.game.install,F=I.fx;const M=new T.Matrix4();F.cover.getMatrixAt(0,M);
 const g=new T.BoxGeometry(1,1,1);g.computeBoundingBox();const b=g.boundingBox.clone().applyMatrix4(M);
 const c=new T.Vector3();b.getCenter(c);const s=I.slots[0];const want=s.center.clone().addScaledVector(s.normal,0.009);
 return JSON.stringify({d:+c.distanceTo(want).toFixed(4),size:[b.max.x-b.min.x,b.max.y-b.min.y,b.max.z-b.min.z].map(v=>+v.toFixed(4))});})()`));
console.log(' cover:', JSON.stringify(r));
say(r.d < 0.05, `the fitted cover sits ${r.d} m from slot.center + normal*0.009`);

// the guide's green pulse actually drives the fitted colour
r = JSON.parse(await ev(`(()=>{const F=window.game.install.fx;const g=window.game.install;const rd=()=>[...F.emit.instanceColor.array.slice(0,3)].map(v=>+v.toFixed(3));
 g.update(0); const a=rd(); g.update(1/(1.2*4)); const b=rd(); return JSON.stringify({a,b});})()`));
console.log(' pulse:', JSON.stringify(r));
say(r.a.join() !== r.b.join() && r.b[1] > r.b[0], 'guide on: the fitted colour pulses toward green');

// (d) guide off: no bars, and the fitted colour goes steady white
r = JSON.parse(await ev(`(()=>{const I=window.game.install;I.setGuide(false);const rd=()=>[...I.fx.emit.instanceColor.array.slice(0,3)].map(v=>+v.toFixed(3));
 const a=rd();I.update(0.4);const b=rd();I.update(0.9);const c=rd();
 return JSON.stringify({meshVisible:I.guides.mesh.visible,guide:I.guide,a,b,c,stored:localStorage.getItem('ngv-install-guide')});})()`));
console.log(' guide off:', JSON.stringify(r));
say(!r.meshVisible && !r.guide, 'guide off: the red bar mesh is hidden');
say(r.a.join() === r.b.join() && r.b.join() === r.c.join(), 'guide off: the fitted colour is steady');
say(r.a.join() === '1,0.93,0.82', `guide off: the fitted colour is the strip white (${r.a.join()})`);
say(r.stored === '0', `the toggle is remembered (localStorage ngv-install-guide=${r.stored})`);

// the HUD button says what it does and can be tapped
await sleep(200);   // the label is painted from install.guide in the loop, not by the click
r = JSON.parse(await ev(`(()=>{const b=document.querySelector('#guide');const cs=getComputedStyle(b);const rc=b.getBoundingClientRect();
 return JSON.stringify({text:b.textContent,pe:cs.pointerEvents,h:Math.round(rc.height),right:Math.round(innerWidth-rc.right),top:Math.round(rc.top)});})()`));
console.log(' button:', JSON.stringify(r));
say(r.text === 'Guide off' && r.pe === 'auto' && r.h >= 44, `#guide reads "${r.text}", pointer-events ${r.pe}, ${r.h} px tall`);
await ev(`document.querySelector('#guide').click()`); await sleep(150);
r = await ev(`document.querySelector('#guide').textContent + '|' + window.game.install.guide`);
say(r === 'Guide on|true', `clicking the button turns the guide back on (${r})`);

// ---- screenshots
const N1 = JSON.parse(await ev(`(()=>{const g=window.game;const p=g.hallToWorld(7.71,3.82,g.world.floorY);return JSON.stringify([p.x,p.y,p.z]);})()`));
console.log(' N1 foot:', N1.map((v) => +v.toFixed(2)).join(', '));
// 2.5 m off the foot on the run's outward normal, looking up the shaft, guide on, nothing fitted
await ev(`(()=>{const g=window.game,I=g.install;I.fitted.clear();for(let i=0;i<I.slots.length;i++){I.fx.show(i,false);I.guides.show(i,true);}I.setGuide(true);
 const run=I.runs.find(r=>r.column==='N1');const f=g.hallToWorld(7.71,3.82,g.world.floorY);const n=new T.Vector3(...run.normal).setY(0).normalize();
 const P=g.player;P.pos.set(f.x+n.x*2.5,g.world.floorY,f.z+n.z*2.5);P.eye=1.68;P.yaw=Math.atan2(-(f.x-P.pos.x),-(f.z-P.pos.z));P.pitch=0.85;})()`);
await sleep(700); const s1 = await shot('shaft-empty');
// the first three slots of that run in, mid-pulse
await ev(`(()=>{const I=window.game.install;const run=I.runs.find(r=>r.column==='N1');for(const s of run.slots.slice(0,3))I.fit(s,{carry:null});I.update(1/(1.2*2));})()`);
await sleep(700); const s2 = await shot('shaft-fitted');
// 0.4 m off a fitted section, side-on, so the 20 mm extrusion and the black cover read. The
// guide comes off for this one: at 400 mm a red bar on the next run fills half the picture
await ev(`(()=>{const g=window.game,I=g.install;I.setGuide(false);const run=I.runs.find(r=>r.column==='N1');const s=run.slots[1];
const t=s.tangent.clone().normalize(),b=new T.Vector3().crossVectors(t,s.normal).normalize(),nn=new T.Vector3().crossVectors(b,t).normalize();
 const eye=s.center.clone().addScaledVector(nn,0.30).addScaledVector(b,0.30);const P=g.player;
 P.pos.set(eye.x,g.world.floorY,eye.z);P.eye=eye.y-g.world.floorY;
 P.yaw=Math.atan2(-(s.center.x-eye.x),-(s.center.z-eye.z));P.pitch=0;})()`);
await sleep(700); const s3 = await shot('section-closeup');

// (f) frame time with all 768 in and the guide pulsing
await ev(`(()=>{const I=window.game.install;I.setGuide(true);for(const s of I.slots)if(!I.fitted.has(s.id))I.fit(s,{carry:null});})()`);
await sleep(600);
const f0 = await ev(`window.game.dbg.frames`); const t0 = Date.now();
await sleep(2000);
const f1 = await ev(`window.game.dbg.frames`); const el = (Date.now() - t0) / 1000;
const fps = (f1 - f0) / el;
const fitted = await ev(`window.game.install.counts().fitted`);
console.log(` fps: ${fps.toFixed(1)} over ${el.toFixed(2)} s with ${fitted} lights fitted and the guide on`);
say(fps > 20, `frame rate with the full install and the guide on: ${fps.toFixed(1)} fps`);

console.log('\nlogs: ' + (logs.join('\n') || 'no errors'));
say(logs.length === 0, 'no runtime exceptions');
console.log('shots:\n ' + [s1, s2, s3].join('\n '));
console.log(bad.length ? 'FAIL\n' + bad.join('\n') : 'PASS');
ws.close(); process.exit(bad.length ? 1 : 0);
