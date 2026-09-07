// THE PHONE CONTROLS (Lloyd, 2026-09-07: "we need to improve the controls on phone", "No big
// buttons that will take up screen space"). Drives the real thing with CDP touch events, at both
// orientations: the floating move stick, free look by dragging, the run latch, a tap on the world
// as the action, the contextual cluster, the deck's mini-stick and the settings sheet.
// Section 14 holds the fifteen defects the skeptic pass found on 2026-09-07 (report.md): the
// Escape key, the viewer bar during a shift, the inventory strip, the prompt pill as an obstacle,
// the edge clamp, left-handed driving, the second finger, the idle fade and the tap window.
// Serve on :8877, headless Chrome on :9333 (NGV_PORT overrides).
//   node tools/game-phone.mjs <outdir>
import fs from 'node:fs';
const out = process.argv[2] || '.';
fs.mkdirSync(out, { recursive: true });
const port = +(process.env.NGV_PORT || 9333);
const base = 'http://127.0.0.1:8877/index.html?install=gandel-2026&cb=';
const tabs = await (await fetch(`http://127.0.0.1:${port}/json`)).json();
let t = tabs.find(x => x.type === 'page');
if (!t) t = await (await fetch(`http://127.0.0.1:${port}/json/new?about:blank`, { method: 'PUT' })).json();
const ws = new WebSocket(t.webSocketDebuggerUrl); let id = 0; const pend = {}; const logs = [];
ws.onmessage = e => { const m = JSON.parse(e.data); if (m.id && pend[m.id]) { pend[m.id](m.result); delete pend[m.id]; }
 if (m.method === 'Runtime.exceptionThrown') logs.push('EXC ' + JSON.stringify(m.params.exceptionDetails).slice(0, 900));
 if (m.method === 'Runtime.consoleAPICalled' && m.params.type === 'error') logs.push('ERR ' + JSON.stringify(m.params.args.map(a => a.value || a.description)).slice(0, 300)); };
await new Promise(r => ws.onopen = r);
const send = (method, params = {}) => new Promise(r => { const i = ++id; pend[i] = r; ws.send(JSON.stringify({ id: i, method, params })); });
const ev = async expr => { const r = await send('Runtime.evaluate', { expression: expr, returnByValue: true, awaitPromise: true });
 if (!r) return undefined; if (r.exceptionDetails) return 'EVALERR ' + JSON.stringify(r.exceptionDetails.exception && r.exceptionDetails.exception.description).slice(0, 300);
 return r.result ? r.result.value : r; };
const sleep = ms => new Promise(r => setTimeout(r, ms));
const shot = async n => { const s = await send('Page.captureScreenshot', { format: 'jpeg', quality: 82 }); fs.writeFileSync(`${out}/${n}.jpg`, Buffer.from(s.data, 'base64')); };
let bad = 0; const say = (ok, msg) => { if (!ok) bad++; console.log((ok ? 'ok   ' : 'FAIL ') + msg); };

const PORTRAIT = { width: 412, height: 915, deviceScaleFactor: 1.5, mobile: true };
const LANDSCAPE = { width: 915, height: 412, deviceScaleFactor: 1.5, mobile: true };
const SMALL = { width: 360, height: 780, deviceScaleFactor: 3, mobile: true };   // the narrow phone the skeptic measured
const metrics = async (m) => { await send('Emulation.setDeviceMetricsOverride', m); await sleep(500); };

await send('Network.enable'); await send('Network.setCacheDisabled', { cacheDisabled: true });
await send('Emulation.setTouchEmulationEnabled', { enabled: true });
await send('Page.enable'); await send('Runtime.enable');
await metrics(PORTRAIT);

// ---- touch, as a finger really does it -------------------------------------------------------
const pts = a => a.map(p => ({ x: Math.round(p.x), y: Math.round(p.y), id: p.id || 1 }));
const down = a => send('Input.dispatchTouchEvent', { type: 'touchStart', touchPoints: pts(a) });
const moveT = a => send('Input.dispatchTouchEvent', { type: 'touchMove', touchPoints: pts(a) });
const upT = (a = []) => send('Input.dispatchTouchEvent', { type: 'touchEnd', touchPoints: pts(a) });
// a drag in steps, the way a thumb draws it: one 100 px sweep is not one event on a phone
const drag = async (x, y, dx, dy, steps = 10, ms = 16, hold = 0) => {
  await down([{ x, y }]); await sleep(ms);
  for (let i = 1; i <= steps; i++) { await moveT([{ x: x + dx * i / steps, y: y + dy * i / steps }]); await sleep(ms); }
  if (hold) await sleep(hold);
  await upT();
};
const tap = async (x, y, ms = 60) => { await down([{ x, y }]); await sleep(ms); await upT(); await sleep(350); };
const key = (code) => send('Input.dispatchKeyEvent', { type: 'keyDown', code, key: code, windowsVirtualKeyCode: code === 'Escape' ? 27 : 0 })
  .then(() => send('Input.dispatchKeyEvent', { type: 'keyUp', code, key: code, windowsVirtualKeyCode: code === 'Escape' ? 27 : 0 }));

const enter = async (keep, card) => {
  await send('Page.navigate', { url: base + Date.now() });
  for (let i = 0; i < 60; i++) { await sleep(500); if (await ev('!!(window.ngv&&window.ngv.hall&&document.getElementById("install"))')) break; }
  await ev(`${keep ? '' : 'localStorage.clear();'} localStorage.setItem('ngv.install','gandel-2026'); document.getElementById('install').click()`);
  for (let i = 0; i < 60; i++) { await sleep(500); if (await ev('!!(window.ngv&&window.ngv.game)')) break; }
  if (card) { await sleep(400); await shot(card); }
  await ev(`document.querySelector('#start').click()`); await sleep(800);
};

const label = () => ev(`ngv.game.action?ngv.game.action.label:''`);
const act = async () => { await ev(`ngv.game.player.actionQueued=true`); await sleep(300); };
const at = (u, d) => ev(`(()=>{const g=ngv.game;g.player.pos.copy(g.hallToWorld(${u},${d},g.world.floorY));g.player.pos.y=g.world.floorY;})()`);
const faceHall = (u, d, y = 0) => ev(`(()=>{const g=ngv.game,P=g.player;const q=g.hallToWorld(${u},${d},g.world.floorY+${y});
 P.yaw=Math.atan2(-(q.x-P.pos.x),-(q.z-P.pos.z));P.pitch=Math.max(-1.34,Math.atan2(q.y-(P.pos.y+P.eye),Math.hypot(q.x-P.pos.x,q.z-P.pos.z)));})()`);
const inv = () => ev(`(()=>{const P=ngv.game.player;return {slots:P.inv.map(i=>i?i.type:null),hand:P.carry?P.carry.type:null}})()`);
const yaw = () => ev(`ngv.game.player.yaw`);
const pitch = () => ev(`ngv.game.player.pitch`);
const hall = () => ev(`(()=>{const g=ngv.game,h=g.mods.W.worldToHall(g.player.pos);return [+h.u.toFixed(3),+h.d.toFixed(3)]})()`);
const deg = r => r * 180 / Math.PI;
// where a world point lands on the glass
const screenOf = expr => ev(`(()=>{const g=ngv.game,p=(${expr}).clone();const v=p.project(ngv.cam||g.player.camera);
 const r=document.getElementById('cv').getBoundingClientRect();
 return {x:r.left+(v.x*0.5+0.5)*r.width,y:r.top+(-v.y*0.5+0.5)*r.height,z:v.z}})()`);
const rects = () => ev(`(()=>{const ids=['stats','bars','inv','ghud','crewBtn','guide','ctlBtn','pauseBtn','prompt','reticle','move','look','drop','turn','letGo','deckStick','wheels','deckh','toast'];
 const o={};for(const i of ids){const e=document.getElementById(i);if(!e)continue;const st=getComputedStyle(e);
  const b=e.getBoundingClientRect();o[i]={x:b.x,y:b.y,w:b.width,h:b.height,shown:st.display!=='none'&&st.visibility!=='hidden'&&+st.opacity>0.02&&!e.hidden&&b.width>0};}
 return o})()`);

await enter(false, 'start-card-portrait');

console.log('--- 1. immersive, and the page cannot scroll behind the shift');
const imm = await ev(`({body:document.body.classList.contains('immersive'),html:document.documentElement.classList.contains('immersive'),full:!!document.fullscreenElement,
 stage:getComputedStyle(document.getElementById('stage')).position})`);
say(imm.body || imm.full, 'the shift is immersive (fullscreen, or the stage pinned over the page): ' + JSON.stringify(imm));
await ev(`scrollTo(0,600); window.dispatchEvent(new Event('scroll'))`); await sleep(300);
say((await ev(`scrollY`)) === 0, 'a scroll of 600 px moves nothing: scrollY=' + await ev(`scrollY`));

console.log('--- 2. what is on screen when nothing is happening');
let R = await rects();
say(R.look === undefined || !R.look.shown, 'no look stick in drag mode');
say(R.drop && !R.drop.shown && R.turn && !R.turn.shown && R.deckStick && !R.deckStick.shown, 'no DROP, no TURN, no deck stick with empty hands on the floor');
say(!!(R.move && R.move.shown), 'the resting move stick is up until the first touch');
say(!R.prompt.shown, 'no prompt with nothing in range');
const upNow = () => Object.entries(R).filter(([k, v]) => v.shown && k !== 'reticle' && k !== 'ghud');   // ghud is the header ROW itself: it is not drawn, its children are
const overlaps = () => { const e = upNow(); const out = [];
 for (let i = 0; i < e.length; i++) for (let j = i + 1; j < e.length; j++) { const a = e[i][1], b = e[j][1];
  if (a.x < b.x + b.w - 1 && b.x < a.x + a.w - 1 && a.y < b.y + b.h - 1 && b.y < a.y + a.h - 1) out.push(e[i][0] + '/' + e[j][0]); }
 return out; };
say(overlaps().length === 0, 'nothing on screen overlaps anything else: ' + JSON.stringify(overlaps()));
const HIT = ['crewBtn', 'guide', 'ctlBtn', 'pauseBtn', 'drop', 'turn', 'letGo', 'deckStick'];   // the pill takes no pointers now, so it is not a hit area
const small = () => HIT.filter(k => R[k] && R[k].shown && (R[k].w < 47.5 || R[k].h < 47.5)).map(k => k + ' ' + Math.round(R[k].w) + 'x' + Math.round(R[k].h));
say(small().length === 0, 'every control up has 48 dp of hit area: ' + JSON.stringify(small()));
await shot('play-idle-portrait');

console.log('--- 3. the floating move stick');
const W = 412, H = 915;
const bx = 0.2 * W, by = 0.75 * H;
await at(24, 7.5); await faceHall(10, 7.5); await sleep(400);
const p0 = await hall();
await down([{ x: bx, y: by }]); await sleep(120);
const stick = await ev(`(()=>{const m=document.getElementById('move'),b=m.getBoundingClientRect();return {cx:b.x+b.width/2,cy:b.y+b.height/2,r:b.width/2,cls:m.className}})()`);
say(Math.abs(stick.cx - bx) < 2 && Math.abs(stick.cy - by) < 2, `the base appears under the thumb: asked ${Math.round(bx)},${Math.round(by)} got ${Math.round(stick.cx)},${Math.round(stick.cy)}`);
say(stick.cls.includes('held') && !stick.cls.includes('ghost'), 'and it is held, not a ghost: ' + stick.cls);
for (let i = 1; i <= 7; i++) { await moveT([{ x: bx + i * 10, y: by }]); await sleep(30); }
await sleep(700);
const p1 = await hall();
say(Math.hypot(p1[0] - p0[0], p1[1] - p0[1]) > 0.4, `a 70 px push walks: ${JSON.stringify(p0)} -> ${JSON.stringify(p1)}`);
await shot('stick-mid-drag-portrait');
await upT(); await sleep(400);
R = await rects();
const p2 = await hall(); await sleep(500); const p3 = await hall();
say(!R.move.shown || R.move.shown === false, 'the base hides on release');
say(Math.hypot(p3[0] - p2[0], p3[1] - p2[1]) < 0.02, 'and the walking stops: ' + JSON.stringify([p2, p3]));

console.log('--- 4. the run latches at the rim, and stays latched to a third of the ring');
const rim = 0.95 * 60;
await down([{ x: bx, y: by }]); await sleep(60);
await moveT([{ x: bx, y: by - rim }]); await sleep(700);
const runOn = await ev(`({run:ngv.game.touch.run,sprint:!!ngv.game.player.sprinting})`);
const r0 = await hall(); await sleep(1000); const r1 = await hall();
const speed = Math.hypot(r1[0] - r0[0], r1[1] - r0[1]);
say(runOn.run && runOn.sprint, 'held at 95 % for half a second: the run latches ' + JSON.stringify(runOn));
say(speed > 3.6, `and the walk is a run: ${speed.toFixed(2)} m/s against a 3.3 m/s walk`);
await moveT([{ x: bx, y: by - 0.5 * 60 }]); await sleep(400);
say((await ev(`ngv.game.touch.run`)) === true, 'back to half deflection: still running');
await moveT([{ x: bx, y: by - 0.1 * 60 }]); await sleep(400);
say((await ev(`ngv.game.touch.run`)) === false, 'under a third of the ring: the run drops');
await upT(); await sleep(300);

console.log('--- 5. free look: pixels are degrees');
const lookDrag = async (dx, dy) => { const y0 = await yaw(), p_0 = await pitch();
  await drag(300, 500, dx, dy, Math.max(1, Math.round((Math.abs(dx) + Math.abs(dy)) / 10)), 16);
  await sleep(250); return { dyaw: deg(Math.abs((await yaw()) - y0)), dpitch: deg((await pitch()) - p_0) }; };
let L = await lookDrag(100, 0);
say(Math.abs(L.dyaw - 22) <= 22 * 0.15, `a 100 px drag across turns 22 deg: ${L.dyaw.toFixed(1)}`);
L = await lookDrag(0, -100);
say(Math.abs(Math.abs(L.dpitch) - 18) <= 18 * 0.2 && L.dpitch > 0, `a 100 px drag up tilts 18 deg up: ${L.dpitch.toFixed(1)}`);
await ev(`(()=>{const g=ngv.game;g.touch.ctl.sensH=2;})()`);
L = await lookDrag(100, 0);
say(Math.abs(L.dyaw - 44) <= 44 * 0.15, `at sensitivity 2.0 the same drag turns 44 deg: ${L.dyaw.toFixed(1)}`);
await ev(`(()=>{const g=ngv.game;g.touch.ctl.sensH=1;g.touch.ctl.invY=1;})()`);
L = await lookDrag(0, -100);
say(L.dpitch < 0, `invert Y flips it: ${L.dpitch.toFixed(1)} deg`);
await ev(`(()=>{ngv.game.touch.ctl.invY=0;})()`);

console.log('--- 6. the look stick is an option, not the default');
await ev(`(()=>{const g=ngv.game;g.touch.ctl.look='stick';g.touch.apply();})()`); await sleep(200);
const y0 = await yaw();
await down([{ x: 300, y: 500 }]); await sleep(80);
await moveT([{ x: 360, y: 500 }]); await sleep(900);
const lk = await ev(`(()=>{const l=document.getElementById('look'),b=l.getBoundingClientRect();return {shown:getComputedStyle(l).display!=='none'&&+getComputedStyle(l).opacity>0.02,cx:b.x+b.width/2}})()`);
const turned = deg(Math.abs((await yaw()) - y0));
await upT(); await sleep(200);
say(lk.shown, 'look mode "stick": the ring is on screen');
say(turned > 60, `and a held stick keeps turning at a rate: ${turned.toFixed(0)} deg in 0.9 s`);
await ev(`(()=>{const g=ngv.game;g.touch.ctl.look='drag';g.touch.apply();})()`); await sleep(200);

console.log('--- 7. both thumbs at once');
await at(24, 7.5); await faceHall(10, 7.5); await sleep(300);
const b0 = await hall(), yy0 = await yaw();
await down([{ x: 90, y: 700, id: 1 }]);
await moveT([{ x: 90, y: 640, id: 1 }]);
await down([{ x: 90, y: 640, id: 1 }, { x: 320, y: 500, id: 2 }]);
for (let i = 1; i <= 8; i++) { await moveT([{ x: 90, y: 640, id: 1 }, { x: 320 + i * 10, y: 500, id: 2 }]); await sleep(30); }
await sleep(400);
const b1 = await hall(), yy1 = await yaw();
await upT([{ x: 90, y: 640, id: 1 }]); await upT(); await sleep(300);
say(Math.hypot(b1[0] - b0[0], b1[1] - b0[1]) > 0.3 && deg(Math.abs(yy1 - yy0)) > 10,
  `walking and looking together: moved ${Math.hypot(b1[0] - b0[0], b1[1] - b0[1]).toFixed(2)} m, turned ${deg(Math.abs(yy1 - yy0)).toFixed(0)} deg`);

console.log('--- 8. a tap on the world is the action');
await at(51.6, 6.0); await faceHall(51.6, 4.5, 0.4); await sleep(500);
say(/Take box from/.test(await label()), 'facing a light pallet: ' + await label());
await shot('prompt-under-reticle-portrait');
const pr = (await rects()).prompt;
const ret = (await rects()).reticle;
say(pr.shown && Math.abs(pr.y - (ret.y + ret.h / 2 + 56)) < 14, `the pill sits 56 px under the +: reticle ${Math.round(ret.y + ret.h / 2)}, pill ${Math.round(pr.y)}`);
// look LEVEL over the pallet: the reticle is on nothing and the pallet sits low on the glass
await at(51.6, 7.0); await faceHall(51.6, 4.5, 1.68); await sleep(500);
const offLabel = await label();
say(!/Take box from/.test(offLabel), 'looking over it, the reticle offers nothing: ' + offLabel);
const sp = await screenOf(`ngv.game.items.pallets.map(p=>p.mesh).sort((a,b)=>a.position.distanceTo(ngv.game.player.pos)-b.position.distanceTo(ngv.game.player.pos))[0].position.clone().setY(ngv.game.world.floorY+0.35)`);
say(sp.x > 412 * 0.4, 'the pallet is in the look half of the screen, not the stick half: x=' + Math.round(sp.x));
await tap(sp.x, sp.y); await sleep(400);
say((await inv()).hand === 'box', `a tap on the pallet itself takes a box, with no button and no prompt: hand=${(await inv()).hand}`);
await ev(`ngv.game.player.dropQueued=true`); await sleep(400);
// a tap on nothing is a look gesture
const before = JSON.stringify(await inv());
await faceHall(20, 7.5, 6); await sleep(400);
await tap(206, 200); await sleep(400);
say(JSON.stringify(await inv()) === before, 'a tap on empty air does nothing: ' + before);
// and the pill is still a button
await at(51.6, 6.0); await faceHall(51.6, 4.5, 0.4); await sleep(500);
const pb = (await rects()).prompt;
await tap(pb.x + pb.w / 2, pb.y + pb.h / 2); await sleep(400);
say((await inv()).hand === 'box', 'and tapping the pill still runs the reticle action');

console.log('--- 9. the contextual cluster');
R = await rects();
say(R.drop.shown, 'holding a box: DROP is up');
say(!R.turn.shown, 'and TURN is not');
await ev(`ngv.game.player.dropQueued=true`); await sleep(400);
R = await rects();
say(!R.drop.shown, 'hands empty: DROP is gone');
// a ply sheet in the hands
const grab = async (i = 0) => { const su = await ev(`ngv.game.mods.W.worldToHall(ngv.game.items.stacks[${i}].mesh.position).u`);
 const sd = await ev(`ngv.game.mods.W.worldToHall(ngv.game.items.stacks[${i}].mesh.position).d`);
 const side = sd < 7.5 ? 1 : -1;
 await at(su, sd + side * 2.1); await faceHall(su, sd + side * 1.0, 0.5); await sleep(450); await act(); };
await grab(0);
R = await rects();
say((await inv()).hand === 'sheet' && R.turn.shown && R.drop.shown, 'a ply sheet in the hands: TURN and DROP are both up');
const a0 = await ev(`ngv.game.items.sheetAlong`);
await tap(R.turn.x + R.turn.w / 2, R.turn.y + R.turn.h / 2);
const a1 = await ev(`ngv.game.items.sheetAlong`);
say(a0 !== a1, `TURN turns the sheet: ${a0} -> ${a1}`);
await ev(`ngv.game.player.dropQueued=true`); await sleep(400);

console.log('--- 10. the lift: one mini-stick, no UP / DOWN / FAST');
say((await ev(`!document.getElementById('liftUp')&&!document.getElementById('liftDown')&&!document.getElementById('liftMode')`)) === true,
  'the UP, DOWN and FAST buttons do not exist any more');
await ev(`(()=>{const g=ngv.game,L=g.lift;L.height=0;L.refresh();L.board(g.player,true);L.takeControls(g.player);})()`); await sleep(600);
R = await rects();
say(R.deckStick.shown && R.letGo.shown, 'driving: the deck stick and LET GO are up');
say(!R.inv.shown && !R.drop.shown, 'and the slots and DROP stand down while your hands are on the controls');
await shot('driving-portrait');
const h0 = await ev(`ngv.game.lift.height`);
const dcx = R.deckStick.x + R.deckStick.w / 2, dcy = R.deckStick.y + R.deckStick.h / 2;
await down([{ x: dcx, y: dcy }]); await sleep(60);
await moveT([{ x: dcx, y: dcy - 50 }]); await sleep(1500);
const h1 = await ev(`ngv.game.lift.height`);
await upT();
// the deck is still rising between the reading and the release, so "it stopped" is measured from a
// height read AFTER the thumb came off, not before it
const hRel = await ev(`ngv.game.lift.height`);
await sleep(500);
const h2 = await ev(`ngv.game.lift.height`);
say(h1 - h0 > 0.2, `dragging the mini-stick up raises the deck: ${h0.toFixed(2)} -> ${h1.toFixed(2)} m`);
say(Math.abs(h2 - hRel) < 0.01, `and it stops the moment the thumb comes off: ${hRel.toFixed(3)} -> ${h2.toFixed(3)} m`);
await down([{ x: dcx, y: dcy }]); await sleep(60);
await moveT([{ x: dcx, y: dcy + 50 }]); await sleep(1200); await upT(); await sleep(200);
say((await ev(`ngv.game.lift.height`)) < h1 - 0.1, 'dragging it down lowers the deck');
R = await rects();
await tap(R.letGo.x + R.letGo.w / 2, R.letGo.y + R.letGo.h / 2); await sleep(400);
say((await ev(`ngv.game.lift.driving`)) === false, 'LET GO leaves the controls');
await ev(`ngv.game.lift.leave(ngv.game.player,true)`); await sleep(300);

console.log('--- 11. the settings sheet');
let cb = (await rects()).ctlBtn;
await tap(cb.x + cb.w / 2, cb.y + cb.h / 2); await sleep(400);
say((await ev(`document.getElementById('ctlSheet').classList.contains('up')&&document.body.classList.contains('sheetOpen')`)) === true, 'the gear opens the sheet and pauses the input');
await shot('settings-portrait');
const fits = await ev(`(()=>{const c=document.getElementById('ctlSheet').getBoundingClientRect(),b=document.getElementById('csClose').getBoundingClientRect();
 return {inCard:b.bottom<=c.bottom+1,onScreen:c.top>=0&&c.bottom<=innerHeight}})()`);
say(fits.inCard && fits.onScreen, 'Close is reachable and the card is on the screen: ' + JSON.stringify(fits));
// left-handed mirrors the zones
const zoneL = await ev(`(()=>{const t=ngv.game.touch;return {right:t.inMoveZone(innerWidth*0.8,600),left:t.inMoveZone(innerWidth*0.2,600)}})()`);
await ev(`(()=>{const b=[...document.querySelectorAll('#csLefty button')].find(x=>x.dataset.v==='1');b.click();})()`); await sleep(300);
const zoneR = await ev(`(()=>{const t=ngv.game.touch;return {right:t.inMoveZone(innerWidth*0.8,600),left:t.inMoveZone(innerWidth*0.2,600)}})()`);
const ghostR = await ev(`(()=>{ngv.game.touch.park();const b=document.getElementById('move').getBoundingClientRect();return b.x+b.width/2>innerWidth/2})()`);
say(zoneL.left && !zoneL.right && zoneR.right && !zoneR.left, 'left-handed mirrors the stick zone: ' + JSON.stringify([zoneL, zoneR]));
say(ghostR, 'and the resting stick moves to the other corner');
const clusterR = await ev(`(()=>{document.body.classList.add('carrying');const b=document.getElementById('drop').getBoundingClientRect();
 const l=b.x+b.width/2<innerWidth/2;document.body.classList.remove('carrying');return l})()`);
say(clusterR, 'and so does the cluster');
await ev(`(()=>{const b=[...document.querySelectorAll('#csLefty button')].find(x=>x.dataset.v==='0');b.click();})()`); await sleep(200);
// every other control writes something a reload will read back
await ev(`(()=>{const q=(s,v)=>{const b=[...document.querySelectorAll(s+' button')].find(x=>x.dataset.v===v);b.click();};
 q('#csStick','L'); q('#csLook','stick'); q('#csRun','0'); q('#csInv','1');
 const h=document.getElementById('csH');h.value=1.6;h.dispatchEvent(new Event('input'));
 const o=document.getElementById('csOp');o.value=0.5;o.dispatchEvent(new Event('input'));})()`); await sleep(300);
const applied = await ev(`(()=>{const t=ngv.game.touch;return {r:t.radius(),look:t.ctl.look,run:+t.ctl.autorun,inv:+t.ctl.invY,h:+t.ctl.sensH,
 op:getComputedStyle(document.getElementById('installUi')).getPropertyValue('--ctlop').trim(),stickShown:getComputedStyle(document.getElementById('look')).display!=='none'}})()`);
say(applied.r === 72 && applied.look === 'stick' && applied.run === 0 && applied.inv === 1 && Math.abs(applied.h - 1.6) < 0.01 && applied.op === '0.5' && applied.stickShown,
  'every row changes something measurable: ' + JSON.stringify(applied));
const stored = await ev(`(()=>{const o={};for(const k of ['look','sensH','sensV','invY','stick','autorun','lefty','opacity'])o[k]=localStorage.getItem('ngv.ctl.'+k);return o})()`);
say(stored.stick === 'L' && stored.look === 'stick' && stored.opacity === '0.5', 'and writes it to localStorage: ' + JSON.stringify(stored));
await ev(`document.getElementById('csClose').click()`); await sleep(300);
say((await ev(`!document.body.classList.contains('sheetOpen')&&!document.getElementById('ctlSheet').classList.contains('up')`)) === true, 'Close puts the input back');

console.log('--- 12. the settings survive a reload');
await enter(true);
const back = await ev(`(()=>{const t=ngv.game.touch;return {r:t.radius(),look:t.ctl.look,op:+t.ctl.opacity,run:+t.ctl.autorun}})()`);
say(back.r === 72 && back.look === 'stick' && back.op === 0.5 && back.run === 0, 'read back on load: ' + JSON.stringify(back));
await ev(`(()=>{for(const k of ['look','sensH','sensV','invY','stick','autorun','lefty','opacity'])localStorage.removeItem('ngv.ctl.'+k);})()`);

console.log('--- 13. landscape');
await enter(false, 'start-card-landscape-pre');
await metrics(LANDSCAPE); await sleep(900);
await at(24, 7.5); await faceHall(10, 7.5); await sleep(400);
R = await rects();
say(overlaps().length === 0, 'landscape: nothing overlaps: ' + JSON.stringify(overlaps()));
say(small().length === 0, 'landscape: every control up has 48 dp: ' + JSON.stringify(small()));
say(!!(R.move && R.move.shown && R.move.y + R.move.h <= (await ev('innerHeight'))), 'the resting stick is on the glass');
await shot('play-idle-landscape');
const lbx = 0.2 * 915, lby = 0.75 * 412;
await down([{ x: lbx, y: lby }]); await sleep(120);
const ls = await ev(`(()=>{const b=document.getElementById('move').getBoundingClientRect(),z=document.getElementById('tzone').getBoundingClientRect();
 return {cx:b.x+b.width/2,cy:b.y+b.height/2,fits:b.bottom<=z.bottom+0.5&&b.top>=z.top-0.5}})()`);
say(Math.abs(ls.cx - lbx) < 2 && ls.cy <= lby + 1 && ls.cy > lby - 16 && ls.fits,
  `landscape: the base lands under the thumb, pulled up only as far as the ring needs: asked ${Math.round(lbx)},${Math.round(lby)} got ${Math.round(ls.cx)},${Math.round(ls.cy)}`);
for (let i = 1; i <= 7; i++) { await moveT([{ x: lbx + i * 10, y: lby }]); await sleep(30); }
await sleep(500);
await shot('stick-mid-drag-landscape');
await upT(); await sleep(300);
const ly0 = await yaw();
await drag(600, 200, 100, 0, 10, 16); await sleep(250);
say(Math.abs(deg(Math.abs((await yaw()) - ly0)) - 22) <= 22 * 0.15, `landscape: 100 px is still 22 deg: ${deg(Math.abs((await yaw()) - ly0)).toFixed(1)}`);
await at(51.6, 6.0); await faceHall(51.6, 4.5, 0.4); await sleep(500);
await shot('prompt-under-reticle-landscape');
say((await rects()).prompt.shown, 'landscape: the pill is up at a pallet');
await ev(`(()=>{const g=ngv.game,L=g.lift;L.height=0;L.refresh();L.board(g.player,true);L.takeControls(g.player);})()`); await sleep(600);
R = await rects();
say(R.deckStick.shown && R.letGo.shown && overlaps().length === 0, 'landscape driving: the deck stick and LET GO are up and clash with nothing: ' + JSON.stringify(overlaps()));
await shot('driving-landscape');
await ev(`ngv.game.lift.letGo(); ngv.game.lift.leave(ngv.game.player,true)`); await sleep(300);
const cb2 = (await rects()).ctlBtn;
await tap(cb2.x + cb2.w / 2, cb2.y + cb2.h / 2); await sleep(400);
await shot('settings-landscape');
const fitsL = await ev(`(()=>{const c=document.getElementById('ctlSheet').getBoundingClientRect(),b=document.getElementById('csClose').getBoundingClientRect();
 return {inCard:b.bottom<=c.bottom+1,onScreen:c.top>=-1&&c.bottom<=innerHeight+1,scrolls:(()=>{const y=document.querySelector('#ctlSheet .csbody');return y.scrollHeight>y.clientHeight})()}})()`);
say(fitsL.inCard && fitsL.onScreen && !fitsL.scrolls, 'landscape: the whole sheet fits, nothing clipped, Close reachable: ' + JSON.stringify(fitsL));
await ev(`document.getElementById('csClose').click()`); await sleep(200);
await metrics(PORTRAIT);
await enter(false, 'start-card-portrait-final');
await shot('play-idle-final');

console.log('--- 14. the fifteen the skeptic found (report.md, 2026-09-07)');
// d13 the resting ghost is not born faded: the one hint about where the stick lives, at full strength
const fresh = await ev(`({idle:document.body.classList.contains('ctlIdle'),op:+getComputedStyle(document.getElementById('move')).opacity})`);
say(!fresh.idle && fresh.op > 0.2, 'd13 the resting ghost is not born faded: ' + JSON.stringify(fresh));

// d2 / d7 / d8 / d15 the viewer's bar stands down for the shift, and its three grenades are inert
const bar = await ev(`(()=>{const e=document.querySelector('#stage .ctl'),b=e.getBoundingClientRect(),cv=document.getElementById('cv').getBoundingClientRect();
 return {disp:getComputedStyle(e).display,h:b.height,cvh:cv.height,ih:innerHeight}})()`);
say(bar.disp === 'none' && Math.abs(bar.cvh - bar.ih) < 2, 'd2/7 Menu, Tour, Full screen, Stats and Phone remote are off the screen and the hall has all of it: ' + JSON.stringify(bar));
const inert = await ev(`(()=>{document.getElementById('tourbtn').click();document.getElementById('hudb').click();document.getElementById('remote').click();
 return {tour:document.getElementById('tourbtn').textContent,stats:!document.getElementById('hud').hidden,qr:!document.getElementById('qr').hidden}})()`);
say(inert.tour === 'Tour' && !inert.stats && !inert.qr, 'd2/8/15 and clicking them mid-shift does nothing: ' + JSON.stringify(inert));

// d9 the pause glyph: it holds the night, opens the panel, and Close hands the hall back immersive
R = await rects();
say(R.pauseBtn.shown && R.pauseBtn.w >= 47.5 && R.pauseBtn.h >= 47.5, 'd9 the pause glyph is up beside the gear, 48 dp: ' + JSON.stringify({ w: R.pauseBtn.w, h: R.pauseBtn.h }));
await tap(R.pauseBtn.x + R.pauseBtn.w / 2, R.pauseBtn.y + R.pauseBtn.h / 2); await sleep(500);
const held = await ev(`({panel:!document.getElementById('panel').hidden,halted:document.body.classList.contains('halted')})`);
const c0 = await ev(`ngv.game.clock.minute`); await sleep(1000); const c1 = await ev(`ngv.game.clock.minute`);
say(held.panel && held.halted && c1 === c0, `d9 it holds the night and opens the menu: ${JSON.stringify(held)}, clock ${c0} -> ${c1}`);
const down2 = await ev(`(()=>{const g=id=>getComputedStyle(document.getElementById(id)).display;
 return {touch:g('touch'),inv:g('inv'),prompt:g('prompt'),reticle:g('reticle')}})()`);
say(Object.values(down2).every(v => v === 'none'), 'd9 and the play layer, the slots, the pill and the + all stand down while it is held: ' + JSON.stringify(down2));
await shot('paused-menu-portrait');
const pc = await ev(`(()=>{const b=document.getElementById('panelClose').getBoundingClientRect();return {x:b.x+b.width/2,y:b.y+b.height/2,h:b.height}})()`);
say(pc.h >= 47.5, 'd9 the panel carries its own Close, 48 dp: ' + Math.round(pc.h));
await tap(pc.x, pc.y); await sleep(600);
const backIn = await ev(`({panel:!document.getElementById('panel').hidden,halted:document.body.classList.contains('halted'),
 imm:document.body.classList.contains('immersive'),scroll:scrollY})`);
say(!backIn.panel && !backIn.halted && backIn.imm && backIn.scroll === 0, 'd9 and Close puts you back in immersive play: ' + JSON.stringify(backIn));

// d1 Escape closes whichever card is up, and leaves no card standing over a live hall
R = await rects();
await tap(R.ctlBtn.x + R.ctlBtn.w / 2, R.ctlBtn.y + R.ctlBtn.h / 2); await sleep(400);
await key('Escape'); await sleep(400);
const esc = await ev(`({disp:getComputedStyle(document.getElementById('ctlSheet')).display,sheetOpen:document.body.classList.contains('sheetOpen')})`);
say(esc.disp === 'none' && !esc.sheetOpen, 'd1 Escape closes the Controls sheet and the state matches: ' + JSON.stringify(esc));

// d3 the inventory strip: bottom centre, 44 dp, inside a thumb arc, gaps pass through, second finger works
await ev(`(()=>{const P=ngv.game.player;P.inv=[{type:'light'},{type:'light'},{type:'wrap'},{type:'bag',wraps:3}];P.active=0;})()`); await sleep(400);
const iv = await ev(`(()=>{const e=document.getElementById('inv'),b=e.getBoundingClientRect();
 const sl=[...e.querySelectorAll('.slot')].map(s=>{const r=s.getBoundingClientRect();return {x:r.x,y:r.y,w:r.width,h:r.height,cx:r.x+r.width/2,cy:r.y+r.height/2}});
 return {x:b.x,y:b.y,w:b.width,h:b.height,pe:getComputedStyle(e).pointerEvents,slots:sl,iw:innerWidth,ih:innerHeight}})()`);
say(iv.slots.length === 4 && Math.abs(iv.slots[0].y - iv.slots[3].y) < 1 && iv.pe === 'none',
  'd3 four slots in one row, and the strip itself takes no pointers: ' + JSON.stringify({ n: iv.slots.length, pe: iv.pe }));
say(Math.abs((iv.x + iv.w / 2) - iv.iw / 2) < 4 && iv.ih - (iv.y + iv.h) < 70, 'd3 it runs along the bottom centre, between the two thumbs: ' + JSON.stringify({ cx: Math.round(iv.x + iv.w / 2), bottom: Math.round(iv.ih - (iv.y + iv.h)) }));
say(iv.slots.every(s => s.w >= 43.5 && s.h >= 43.5), 'd3 every slot is a 44 px target: ' + JSON.stringify(iv.slots.map(s => Math.round(s.w) + 'x' + Math.round(s.h))));
// the skeptic's own reach measure: a right thumb pivots near (354,869) and its arc is about 45 mm
const reach = iv.slots.map(s => Math.round(Math.hypot(s.cx - 354, s.cy - 869) * 0.172));
say(reach.every(r => r <= 45), 'd3 every slot is inside a 45 mm thumb arc, in mm: ' + JSON.stringify(reach));
const gapX = (iv.slots[2].x + iv.slots[2].w + iv.slots[3].x) / 2;
const gy = await yaw();
await drag(gapX, iv.slots[2].cy, 80, 0, 8, 16); await sleep(300);
say(deg(Math.abs((await yaw()) - gy)) > 8, `d3 a drag through the gap between two slots is still a look: ${deg(Math.abs((await yaw()) - gy)).toFixed(1)} deg`);
await ev(`ngv.game.player.active=0`);
await down([{ x: 82, y: 700, id: 1 }]); await sleep(80);
await moveT([{ x: 82, y: 640, id: 1 }]); await sleep(200);
await down([{ x: 82, y: 640, id: 1 }, { x: iv.slots[3].cx, y: iv.slots[3].cy, id: 2 }]); await sleep(200);
const sel2 = await ev(`ngv.game.player.active`);
await upT([{ x: 82, y: 640, id: 1 }]); await upT(); await sleep(300);
say(sel2 === 3, `d3 a slot tapped as a SECOND finger, with the move stick held, selects it: active=${sel2}`);
await shot('inventory-strip-portrait');
await ev(`(()=>{const P=ngv.game.player;P.inv=[null,null,null,null];P.active=0;})()`); await sleep(300);

// d4 the pill takes taps and passes drags through to the look layer
await at(51.6, 6.0); await faceHall(51.6, 4.5, 0.4); await sleep(600);
const pp = (await rects()).prompt;
const py = await yaw();
await drag(pp.x + pp.w / 2, pp.y + pp.h / 2, 100, 0, 10, 16); await sleep(300);
say(deg(Math.abs((await yaw()) - py)) > 15, `d4 a drag started ON the pill turns the camera: ${deg(Math.abs((await yaw()) - py)).toFixed(1)} deg`);
await at(51.6, 6.0); await faceHall(51.6, 4.5, 0.4); await sleep(600);
const pp2 = (await rects()).prompt;
await tap(pp2.x + pp2.w / 2, pp2.y + pp2.h / 2); await sleep(400);
say((await inv()).hand === 'box', 'd4 and a tap on it still runs the reticle action');
await at(51.6, 6.0); await faceHall(51.6, 4.5, 0.4); await sleep(500);
const pp3 = (await rects()).prompt;
await down([{ x: pp3.x + 6, y: pp3.y + pp3.h / 2 }]); await sleep(150);
const stuck = await ev(`document.getElementById('move').className`);
await upT(); await sleep(200);
say(stuck.includes('held'), `d4 and a thumb landing on its left edge, inside the move zone, still raises the stick: ${stuck}`);
await ev(`ngv.game.player.dropQueued=true`); await sleep(400);

// d10 a deliberate 400 ms press acts: the 10 px gate is what separates a tap from a look
await at(51.6, 6.0); await faceHall(51.6, 4.5, 0.4); await sleep(600);
const sp2 = await screenOf(`ngv.game.items.pallets.map(p=>p.mesh).sort((a,b)=>a.position.distanceTo(ngv.game.player.pos)-b.position.distanceTo(ngv.game.player.pos))[0].position.clone().setY(ngv.game.world.floorY+0.35)`);
await tap(sp2.x, sp2.y, 400); await sleep(400);
say((await inv()).hand === 'box', 'd10 a 400 ms press on a pallet takes a box');
await ev(`ngv.game.player.dropQueued=true`); await sleep(400);

// d5 the edge clamp: a base never starts deflected, wherever the thumb lands
await at(40, 7.5); await faceHall(10, 7.5); await sleep(400);
const edge = [];
for (const [ex, ey] of [[82, 905], [6, 700], [82, 120], [82, 700]]) {
  const e0 = await hall();
  await down([{ x: ex, y: ey }]); await sleep(120);
  await moveT([{ x: ex + 1, y: ey }]); await sleep(600);
  const mv = await ev(`[+ngv.game.player.move.x.toFixed(2),+ngv.game.player.move.y.toFixed(2)]`);
  await upT(); await sleep(200);
  const e1 = await hall();
  edge.push({ at: [ex, ey], v: mv, walked: +Math.hypot(e1[0] - e0[0], e1[1] - e0[1]).toFixed(2) });
}
say(edge.every(e => Math.hypot(e.v[0], e.v[1]) < 0.1 && e.walked < 0.2), 'd5 one pixel of jitter walks nobody, at any edge of the zone: ' + JSON.stringify(edge));

// d11 a second finger in the move zone is a palm, not a look
await down([{ x: 82, y: 686, id: 1 }]); await sleep(100);
const q0 = await yaw();
await down([{ x: 82, y: 686, id: 1 }, { x: 60, y: 400, id: 2 }]); await sleep(60);
for (let i = 1; i <= 8; i++) { await moveT([{ x: 82, y: 686, id: 1 }, { x: 60, y: 400 - i * 10, id: 2 }]); await sleep(30); }
await sleep(200);
const q1 = await yaw();
await upT([{ x: 82, y: 686, id: 1 }]); await upT(); await sleep(300);
say(deg(Math.abs(q1 - q0)) < 1, `d11 a palm on the left rail while the stick is held drifts nothing: ${deg(Math.abs(q1 - q0)).toFixed(1)} deg`);

// d12 the deck stick fades with everything else
await ev(`(()=>{const g=ngv.game,L=g.lift;L.height=0;L.refresh();L.board(g.player,true);L.takeControls(g.player);})()`); await sleep(700);
await ev(`(()=>{ngv.game.touch.lastTouch=0;})()`); await sleep(600);
const faded = await ev(`({idle:document.body.classList.contains('ctlIdle'),deck:+getComputedStyle(document.getElementById('deckStick')).opacity,
 letGo:+getComputedStyle(document.getElementById('letGo')).opacity})`);
say(faded.idle && Math.abs(faded.deck - faded.letGo) < 0.02, 'd12 the deck stick takes the idle fade with LET GO: ' + JSON.stringify(faded));
await ev(`ngv.game.lift.letGo(); ngv.game.lift.leave(ngv.game.player,true)`); await sleep(400);

// d14 the run costs stamina: the latch was free, so a full-thumb walk was always a sprint
await ev(`(()=>{const b=ngv.game.body;b.stamina=100;b.fatigue=0;b.max=100;})()`);
const walkS = await ev(`(()=>{const b=ngv.game.body,s=b.stamina;b.update(2,ngv.game.clock,1,true,false);const d=s-b.stamina;b.stamina=s;return +d.toFixed(2)})()`);
const runS = await ev(`(()=>{const b=ngv.game.body,s=b.stamina;b.update(2,ngv.game.clock,1,true,true);const d=s-b.stamina;b.stamina=s;return +d.toFixed(2)})()`);
say(runS > walkS * 1.5, `d14 two seconds of running costs more than walking: ${walkS} against ${runS} stamina`);

// d6 left-handed while driving: the wheel plan mirrors with LET GO, at all three viewports
const driveClash = async () => {
  await ev(`(()=>{const g=ngv.game,L=g.lift;L.height=0;L.refresh();L.board(g.player,true);L.takeControls(g.player);})()`); await sleep(700);
  const o = await ev(`(()=>{const r={};for(const i of ['letGo','deckStick','wheels','drop','turn','inv','deckh','move']){const e=document.getElementById(i);if(!e)continue;
   const s=getComputedStyle(e),b=e.getBoundingClientRect(); if(s.display==='none'||s.visibility==='hidden'||+s.opacity<0.02||!b.width)continue; r[i]={x:b.x,y:b.y,w:b.width,h:b.height};}
   const k=Object.entries(r),out=[];for(let i=0;i<k.length;i++)for(let j=i+1;j<k.length;j++){const a=k[i][1],b=k[j][1];
    if(a.x<b.x+b.w-1&&b.x<a.x+a.w-1&&a.y<b.y+b.h-1&&b.y<a.y+a.h-1)out.push(k[i][0]+'/'+k[j][0]);}return out})()`);
  await ev(`ngv.game.lift.letGo(); ngv.game.lift.leave(ngv.game.player,true)`); await sleep(300);
  return o;
};
for (const m of [PORTRAIT, SMALL, LANDSCAPE]) {
  await metrics(m);
  await ev(`(()=>{const t=ngv.game.touch;t.ctl.lefty=1;t.apply();})()`); await sleep(300);
  const o = await driveClash();
  say(o.length === 0, `d6 left-handed driving at ${m.width}x${m.height}: nothing overlaps: ` + JSON.stringify(o));
  // the pause glyph made the header five wide: every one of them has to stay on the glass
  const hdr = await ev(`(()=>{const o={};for(const i of ['crewBtn','guide','ctlBtn','pauseBtn']){const b=document.getElementById(i).getBoundingClientRect();
   o[i]={r:Math.round(b.right),w:Math.round(b.width),h:Math.round(b.height)};}o.iw=innerWidth;return o})()`);
  const off = Object.entries(hdr).filter(([k, v]) => v && v.r !== undefined && (v.r > hdr.iw + 0.5 || v.w < 47.5 || v.h < 47.5)).map(([k]) => k);
  say(off.length === 0, `the header row fits and keeps 48 dp at ${m.width}x${m.height}: ` + JSON.stringify(hdr));
  if (m === SMALL) await shot('lefty-driving-360');
  await ev(`(()=>{const t=ngv.game.touch;t.ctl.lefty=0;t.apply();})()`); await sleep(200);
}
await metrics(PORTRAIT); await sleep(400);
await shot('play-idle-portrait-check');

console.log('--- 15. console');
say(logs.length === 0, 'no console errors: ' + JSON.stringify(logs.slice(0, 3)));
console.log(bad ? `FAILED ${bad}` : 'ALL OK');
ws.close();
process.exit(bad ? 1 : 0);
