// FLOOR PROTECTION (Lloyd, 2026-09-06: "for the install sim, we also need to put down floor
// protection before we can drive the scissor lift on the carpet"). Board stacks in storage, ply
// sheets laid on a 1.2 m grid, the lift stopped at the end of the boards, the crew laying their
// own, the save, the night reset. Serve on :8877, headless Chrome on :9333 (NGV_PORT overrides).
//   node tools/game-boards.mjs <outdir>
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
 if (m.method === 'Runtime.exceptionThrown') logs.push('EXC ' + JSON.stringify(m.params.exceptionDetails).slice(0, 1200));
 if (m.method === 'Runtime.consoleAPICalled' && m.params.type === 'error') logs.push('ERR ' + JSON.stringify(m.params.args.map(a => a.value || a.description)).slice(0, 300)); };
await new Promise(r => ws.onopen = r);
const send = (method, params = {}) => new Promise(r => { const i = ++id; pend[i] = r; ws.send(JSON.stringify({ id: i, method, params })); });
const ev = async expr => { const r = await send('Runtime.evaluate', { expression: expr, returnByValue: true, awaitPromise: true });
 if (!r) return undefined; if (r.exceptionDetails) return 'EVALERR ' + JSON.stringify(r.exceptionDetails.exception && r.exceptionDetails.exception.description).slice(0, 300);
 return r.result ? r.result.value : r; };
const sleep = ms => new Promise(r => setTimeout(r, ms));
const shot = async n => { const s = await send('Page.captureScreenshot', { format: 'jpeg', quality: 82 }); fs.writeFileSync(`${out}/${n}.jpg`, Buffer.from(s.data, 'base64')); };
let bad = 0; const say = (ok, msg) => { if (!ok) bad++; console.log((ok ? 'ok   ' : 'FAIL ') + msg); };

await send('Network.enable'); await send('Network.setCacheDisabled', { cacheDisabled: true });
await send('Emulation.setDeviceMetricsOverride', { width: 412, height: 915, deviceScaleFactor: 1.5, mobile: true });
await send('Emulation.setTouchEmulationEnabled', { enabled: true });   // the phone layout: coarse pointer, so the TURN button and the phone grid on the card are what the shots show
await send('Page.enable'); await send('Runtime.enable');
// enter install mode; `keep` leaves localStorage alone, for the reload check
const enter = async (keep, card) => {
 await send('Page.navigate', { url: base + Date.now() });
 for (let i = 0; i < 60; i++) { await sleep(500); if (await ev('!!(window.ngv&&window.ngv.hall&&document.getElementById("install"))')) break; }
 await ev(`${keep ? '' : 'localStorage.clear();'} localStorage.setItem('ngv.install','gandel-2026'); document.getElementById('install').click()`);
 for (let i = 0; i < 60; i++) { await sleep(500); if (await ev('!!(window.ngv&&window.ngv.game)')) break; }
 if (card) { await sleep(400); await shot(card);
  const fit = await ev(`(()=>{const c=document.getElementById('card'),body=document.getElementById('cardbody');
   const b=document.getElementById('start').getBoundingClientRect(),cr=c.getBoundingClientRect();
   return {bodyScrolls:body.scrollHeight>body.clientHeight+1,inCard:b.bottom<=cr.bottom+1&&b.top>=cr.top,
    onScreen:b.bottom<=window.innerHeight&&b.top>=0,rows:c.querySelectorAll('.keys.phone b').length}})()`);
  say(fit.onScreen && fit.inCard, 'Start Shift stays on the phone card while the controls scroll: ' + JSON.stringify(fit)); }
 await ev(`document.querySelector('#start').click()`); await sleep(700);
};
await enter(false, 'start-card-phone');

const label = () => ev(`ngv.game.action?ngv.game.action.label:''`);
const act = async () => { await ev(`ngv.game.player.actionQueued=true`); await sleep(300); };
const at = (u, d) => ev(`(()=>{const g=ngv.game;g.player.pos.copy(g.hallToWorld(${u},${d},g.world.floorY));g.player.pos.y=g.world.floorY;})()`);
// look at a hall point on the floor (or `y` above it)
const faceHall = (u, d, y = 0) => ev(`(()=>{const g=ngv.game,P=g.player;const q=g.hallToWorld(${u},${d},g.world.floorY+${y});
 P.yaw=Math.atan2(-(q.x-P.pos.x),-(q.z-P.pos.z));P.pitch=Math.max(-1.34,Math.atan2(q.y-(P.pos.y+P.eye),Math.hypot(q.x-P.pos.x,q.z-P.pos.z)));})()`);
const sheets = () => ev(`ngv.game.world.sheets.map(s=>[+s.u.toFixed(3),+s.d.toFixed(3),s.along])`);
const ghost = () => ev(`(()=>{const g=ngv.game.items.ghost;return {on:g.visible,col:g.material.color.getHexString()}})()`);
// why the ghost says no, for a failure that needs explaining
const why = () => ev(`(()=>{const s=ngv.game.items.ghostSpot;return s?{u:+s.u.toFixed(2),d:+s.d.toFixed(2),along:s.along,why:s.why||null}:null})()`);
const inv = () => ev(`(()=>{const P=ngv.game.player;return {slots:P.inv.map(i=>i?i.type:null),used:P.used(),hand:P.carry?P.carry.type:null,wrap:P.canTake('wrap')}})()`);

console.log('--- 1. the board stacks on the plan');
const st1 = await ev(`(()=>{const g=ngv.game,W=g.mods.W;
 const hallBox=(mesh,sx,sz)=>{const h=W.worldToHall(mesh.position);const e=new (mesh.position.constructor)(1,0,0).applyQuaternion(mesh.quaternion);
  const ang=Math.atan2(e.z,e.x)-Math.atan2(W.HALL.u.z,W.HALL.u.x);const c=Math.abs(Math.cos(ang)),s=Math.abs(Math.sin(ang));
  return {u:h.u,d:h.d,hu:sx*0.5*c+sz*0.5*s,hd:sx*0.5*s+sz*0.5*c};};
 const over=(a,b)=>Math.abs(a.u-b.u)<a.hu+b.hu-0.001&&Math.abs(a.d-b.d)<a.hd+b.hd-0.001;
 const stacks=g.items.stacks.map(s=>Object.assign(hallBox(s.mesh,2.4,1.2),{n:s.sheets}));
 const pallets=g.items.pallets.map(p=>hallBox(p.mesh,1.25,0.95));
 const lifts=[g.lift].concat(g.crew.lifts).map(L=>hallBox(L.group,2.4,1.15));
 const jacks=[g.items.jack].concat(g.items.jacks||[]).map(j=>hallBox(j.mesh,0.8,1.6));
 const bags=g.items.bags.map(b=>hallBox(b.mesh,0.66,0.66));
 const clashes=[];
 for(const s of stacks){ for(const p of pallets) if(over(s,p))clashes.push('pallet@'+p.u.toFixed(1));
  for(const L of lifts) if(over(s,L))clashes.push('lift@'+L.u.toFixed(1));
  for(const j of jacks) if(over(s,j))clashes.push('jack@'+j.u.toFixed(1));
  for(const bg of bags) if(over(s,bg))clashes.push('bag@'+bg.u.toFixed(1));
  for(const o of stacks) if(o!==s&&over(s,o))clashes.push('stack@'+o.u.toFixed(1)); }
 return {stacks:stacks.map(s=>[+s.u.toFixed(2),+s.d.toFixed(2),s.n]),clashes,liftPark:lifts.map(L=>[+L.u.toFixed(2),+L.d.toFixed(2)])}})()`);
say(st1.stacks.length === 5, 'five board stacks: ' + JSON.stringify(st1.stacks));
say(st1.stacks.every(s => s[2] === 30), 'thirty sheets on each');
say(st1.stacks.every(s => s[0] > 48.9 && s[0] < 71 && s[1] > 3 && s[1] < 12), 'all five stand in the storage corridor');
say(st1.clashes.length === 0, 'no stack overlaps a pallet, a lift, a jack, a bag or another stack: ' + JSON.stringify(st1.clashes));

console.log('--- 2. taking a sheet off a stack');
await ev(`(()=>{const g=ngv.game,h=g.mods.W.worldToHall(g.items.stacks[0].mesh.position);g.player.pos.copy(g.hallToWorld(h.u,h.d+2.1,g.world.floorY));})()`);
await faceHall(66.6, 5.6, 0.5); await sleep(400);
say(/Take a sheet \(30 left\)/.test(await label()), 'at the stack: ' + await label());
await act();
let s = await inv();
say(s.hand === 'sheet' && s.used === 4, 'a sheet takes both hands: ' + JSON.stringify(s));
say(s.wrap === false, 'nothing else fits while a sheet is held (canTake wrap false)');
say((await ev(`ngv.game.items.stacks[0].sheets`)) === 29, 'the stack shows 29');
say((await ev(`ngv.game.items.stacks[0].pile.scale.y`)).toFixed(3) === (29 / 30).toFixed(3), 'the pile shrank with the count');

console.log('--- 3. the first sheet, butted against the door line');
await at(47.5, 7.5); await sleep(1400);   // the doors have to swing clear before a board may cross the line
await faceHall(48.3, 7.5); await sleep(400);
say(/Lay the sheet here/.test(await label()), 'aimed just inside the doors: ' + await label());
let g1 = await ghost();
say(g1.on && g1.col === '35d06a', 'ghost up and green: ' + JSON.stringify(g1));
await act();
let S = await sheets();
say(S.length === 1, 'one sheet down: ' + JSON.stringify(S));
say(S.length === 1 && Math.abs((S[0][0] + 0.6) - 48.9) < 0.03, 'its +u edge sits on the door line: ' + (S[0] ? (S[0][0] + 0.6).toFixed(3) : '-'));
say((await inv()).hand === null, 'hands empty again');
say((await ghost()).on === false, 'ghost hidden with nothing in hand');

console.log('--- 4. the same spot again, and the corridor');
const grab = async (i = 0) => { const back = await ev(`(()=>{const g=ngv.game,h=g.mods.W.worldToHall(g.player.pos);return [h.u,h.d]})()`);
 const su = await ev(`ngv.game.mods.W.worldToHall(ngv.game.items.stacks[${i}].mesh.position).u`);
 const sd = await ev(`ngv.game.mods.W.worldToHall(ngv.game.items.stacks[${i}].mesh.position).d`);
 const side = sd < 7.5 ? 1 : -1;
 await at(su, sd + side * 2.1); await faceHall(su, sd + side * 1.0, 0.5); await sleep(400); await act();
 if ((await inv()).hand !== 'sheet') say(false, 'could not take a sheet off stack ' + i + ': ' + await label());
 return back; };
let back = await grab(0);
await at(back[0], back[1]); await faceHall(48.3, 7.5); await sleep(1400);
say(/No room for a sheet there/.test(await label()), 'on top of the first one: ' + await label());
g1 = await ghost(); say(g1.on && g1.col === 'd94a3a', 'ghost red: ' + JSON.stringify(g1));
await faceHall(50.2, 7.5); await sleep(350);
say(/concrete/.test(await label()), 'aimed through the doors: ' + await label());

console.log('--- 5. TURN, and the grid');
// step 4 left a sheet in the hands: R turns it, and the turned board goes down on clear carpet
const along0 = await ev(`ngv.game.items.sheetAlong`);
await ev(`window.dispatchEvent(new KeyboardEvent('keydown',{code:'KeyR'}))`); await sleep(250);
const along1 = await ev(`ngv.game.items.sheetAlong`);
say(along0 === 'd' && along1 === 'u', `R turns the sheet: ${along0} -> ${along1}`);
await at(47.7, 6.2); await faceHall(47.7, 4.5); await sleep(500);
say(/Lay the sheet here/.test(await label()), 'a turned sheet on clear carpet: ' + await label() + ' ' + JSON.stringify(await why()));
await act();
S = await sheets();
say(S.length === 2 && S[1][2] === 'u', 'two sheets, the second turned: ' + JSON.stringify(S[1]));
const grid = await ev(`(()=>{const g=ngv.game,W=g.mods.W;const bad=[];
 for(const s of g.world.sheets){const r=W.sheetRect(s);
  for(const u of [r.u0,r.u1]){const k=(48.9-u)/1.2; if(Math.abs(k-Math.round(k))>0.01/1.2)bad.push('u '+u.toFixed(3));}
  for(const d of [r.d0,r.d1]){const k=(d-0.3)/1.2; if(Math.abs(k-Math.round(k))>0.01/1.2)bad.push('d '+d.toFixed(3));}}
 for(let i=0;i<g.world.sheets.length;i++)for(let j=i+1;j<g.world.sheets.length;j++){
  const a=W.sheetRect(g.world.sheets[i]),b=W.sheetRect(g.world.sheets[j]);
  if(Math.abs(a.u0+a.hu-(b.u0+b.hu))<a.hu+b.hu-0.02&&Math.abs(a.d0+a.hd-(b.d0+b.hd))<a.hd+b.hd-0.02)bad.push('overlap '+i+'/'+j);}
 return bad})()`);
say(grid.length === 0, 'every edge lands on the 1.2 m grid and nothing overlaps: ' + JSON.stringify(grid));
await grab(0);   // a fresh board in the hands, so R has something to turn
await ev(`window.dispatchEvent(new KeyboardEvent('keydown',{code:'KeyR'}))`); await sleep(250);
say((await ev(`ngv.game.items.sheetAlong`)) === 'd', 'R again turns it back to across the hall');

console.log('--- 6. a run of six from the doors, 7.2 m up the hall');
const layAt = async (u, d) => {
 if (!(await inv()).hand) await grab(0);
 const side = d + 2.0 < 14 ? d + 2.0 : d - 2.0;
 await at(u, side); await faceHall(u, d); await sleep(550);
 const l = await label();
 await act(); await sleep(150);
 return l + (/Lay the sheet here/.test(l) ? '' : ' ' + JSON.stringify(await why()));
};
for (const u of [47.1, 45.9, 44.7, 43.5, 42.3]) {
 const l = await layAt(u, 7.5);
 say(/Lay the sheet here/.test(l), `sheet at u ${u}: ${l}`);
}
S = await sheets();
const run = S.filter(x => Math.abs(x[1] - 7.5) < 0.01 && x[2] === 'd').map(x => x[0]).sort((a, b) => a - b);
say(run.length === 6 && Math.abs(Math.min(...run) - 42.3) < 0.01 && Math.abs(Math.max(...run) - 48.3) < 0.01,
 'six sheets in a line from the door line to u 41.7: ' + JSON.stringify(run));

console.log('--- 7. the lift stops at the end of the boards');
await ev(`(()=>{const g=ngv.game,L=g.lift;L.pos.copy(g.hallToWorld(50.6,7.7,g.world.floorY));L.yaw=2.9207;L.height=0;L.refresh();
 L.board(g.player,true);L.takeControls(g.player);})()`); await sleep(400);
const drv = () => ev(`(()=>{const g=ngv.game,L=g.lift,W=g.mods.W;const h=W.worldToHall(L.pos);
 return {u:+h.u.toFixed(3),d:+h.d.toFixed(3),blocked:L.blocked,speed:+L.speed.toFixed(2),
  off:g.world.liftOnBoards(L),wheels:g.world.liftWheels(L).map(w=>[+w.u.toFixed(2),+w.d.toFixed(2)])}})()`);
await ev(`ngv.game.player.keys.add('KeyW')`); await sleep(14000);
const d1 = await drv();
await sleep(2500);
const d2 = await drv();
await ev(`ngv.game.player.keys.delete('KeyW')`);
say(d2.u < 48.9, 'the machine drove through the doors onto the boards: u ' + d2.u);
say(d2.off === null, 'every wheel is on protected floor: ' + JSON.stringify(d2.wheels));
say(/wheels stay on the boards/.test(d2.blocked || ''), 'stopped with the boards message: ' + d2.blocked);
say(Math.abs(d2.u - d1.u) < 0.06, `two more seconds of W move it no further (${d1.u} -> ${d2.u})`);
await shot('lift-stopped');

console.log('--- 8. two more boards, and it drives on');
const stopU = d2.u;
await ev(`ngv.game.lift.leave(ngv.game.player,true)`); await sleep(300);
for (const u of [41.1, 39.9]) {
 const l = await layAt(u, 7.5);
 say(/Lay the sheet here/.test(l), `sheet ahead of the machine at u ${u}: ${l}`);
}
await ev(`(()=>{const g=ngv.game,L=g.lift;L.board(g.player,true);L.takeControls(g.player);})()`); await sleep(300);
await ev(`ngv.game.player.keys.add('KeyW')`); await sleep(6000); await ev(`ngv.game.player.keys.delete('KeyW')`);
const d3 = await drv();
say(d3.u < stopU - 1.5, `it advanced onto the new boards: ${stopU} -> ${d3.u}`);
say(d3.off === null, 'still every wheel on the boards: ' + JSON.stringify(d3.wheels));

console.log('--- 9. picking a sheet back up');
const under = await ev(`(()=>{const g=ngv.game;const wh=g.world.liftWheels(g.lift);
 for(const s of g.world.sheets){const hu=(s.along==='u'?2.4:1.2)*0.5+0.05,hd=(s.along==='u'?1.2:2.4)*0.5+0.05;
  for(const w of wh) if(Math.abs(w.u-s.u)<=hu&&Math.abs(w.d-s.d)<=hd) return [+s.u.toFixed(2),+s.d.toFixed(2),s.along];}
 return null})()`);
say(!!under, 'found the sheet the machine is standing on: ' + JSON.stringify(under));
await ev(`ngv.game.lift.leave(ngv.game.player,true)`); await sleep(200);
await at(under[0], under[1] + 1.9); await faceHall(under[0], under[1] + 0.9); await sleep(500);
say(/A lift is standing on it/.test(await label()), 'under the wheels: ' + await label());
const nSheets = (await sheets()).length;
await at(48.3, 9.6); await faceHall(48.3, 8.4); await sleep(1400);
say(/Pick up the sheet/.test(await label()), 'a free one by the doors: ' + await label());
await act();
say((await sheets()).length === nSheets - 1, `world.sheets went ${nSheets} -> ${(await sheets()).length}`);
say((await inv()).hand === 'sheet', 'the sheet is in your hands');
const before9 = await ev(`ngv.game.items.stacks[0].sheets`);
await at(66.6, 6.7); await faceHall(66.6, 5.6, 0.5); await sleep(400);
say(/Put the sheet back/.test(await label()), 'back at the stack: ' + await label());
await act();
say((await ev(`ngv.game.items.stacks[0].sheets`)) === before9 + 1, `the stack went ${before9} -> ${before9 + 1}`);

console.log('--- 10. the layout survives a reload');
const saved = await ev(`(()=>{const j=JSON.parse(localStorage.getItem('ngv-install-phase1')||'{}');
 return {sheets:(j.sheets||[]).length,stacks:j.stackSheets||null}})()`);
const live = (await sheets()).length;
say(saved.sheets === live, `the save holds ${saved.sheets} sheets, the world has ${live}`);
say(Array.isArray(saved.stacks) && saved.stacks.length === 5, 'and what is left on each stack: ' + JSON.stringify(saved.stacks));
await enter(true);
const after = await ev(`(()=>{const g=ngv.game;return {n:g.world.sheets.length,meshes:g.world.sheets.filter(s=>s.mesh&&s.mesh.parent).length,stacks:g.items.stacks.map(s=>s.sheets)}})()`);
say(after.n === live, `after the reload the hall still has ${after.n} sheets`);
say(after.meshes === after.n, 'every one of them has its mesh in the scene');
say(JSON.stringify(after.stacks) === JSON.stringify(saved.stacks), 'the stacks came back at ' + JSON.stringify(after.stacks));

console.log('--- 11. a crew fitter and feeder lay their own boards');
await ev(`(()=>{const g=ngv.game;
 // (Claude, 2026-09-07) the crew are told what to do now: a fitter on S6 and a feeder with him.
 // The feeder is the one who lays the ply in front of the fitter's machine
 g.crew.assignTask('Dave','fit','S6'); g.crew.assignTask('Priya','feed','S6');
 // sample every frame: a crew wheel on bare carpet at any moment is a fail
 g._probe={off:0,frames:0,inHall:false,boards:0,minU:99,stop:false,err:null};
 const tick=()=>{ if(g._probe.stop)return; try{ const W=g.crew.byName('Dave');
   if(W&&W.lift){ const h=g.mods.W.worldToHall(W.lift.pos);
    g._probe.frames++; if(g.world.liftOnBoards(W.lift))g._probe.off++; g._probe.minU=Math.min(g._probe.minU,h.u);
    if(h.u<48.9)g._probe.inHall=true; g._probe.boards=g.crew.byName('Priya').boards||0; } }catch(e){ g._probe.err=String(e&&e.message||e); }
  requestAnimationFrame(tick);};
 requestAnimationFrame(tick);})()`);
const sheets0 = (await sheets()).length;
await sleep(62000);
const probe = await ev(`ngv.game._probe`);
const crewInfo = await ev(`(()=>{const g=ngv.game,W=g.mods.W,F=g.crew.byName('Dave'),B=g.crew.byName('Priya');const h=W.worldToHall(F.lift?F.lift.pos:F.pos);
 return {col:F.assign.target,u:+h.u.toFixed(2),d:+h.d.toFixed(2),boards:B.boards||0,need:!!(F.lift&&F.lift.needBoards),carry:B.carry?B.carry.type:null,status:F.status}})()`);
say(probe.frames > 400, `sampled the fitter every frame for 62 s (${probe.frames} frames)`);
say(probe.off === 0, `the crew lift never had a wheel on bare carpet (${probe.off} frames off the boards)`);
say((await sheets()).length > sheets0, `the feeder laid boards: ${sheets0} -> ${(await sheets()).length} sheets, feeder count ${crewInfo.boards}`);
say(probe.inHall, `the crew lift got into the hall (nearest u reached ${probe.minU.toFixed(2)}) ` + JSON.stringify(crewInfo));
say(!probe.err, 'the sampler itself never threw: ' + (probe.err || 'clean'));
await ev(`ngv.game._probe.stop=true`);
// back on standby, so nobody lays a board in the middle of the checks below
await ev(`ngv.game.crew.members.forEach(m=>ngv.game.crew.assignTask(m,'standby'))`); await sleep(1200);

console.log('--- 12. the night reset and the clean-up rule');
const reset = await ev(`(()=>{const g=ngv.game,W=g.mods.W,I=g.items;
 const n0=g.world.sheets.length;
 // a stack left standing in the hall
 I.stacks[0].mesh.position.copy(g.hallToWorld(30,7.5,g.world.floorY));
 const dirty=g.mods.ITEMm.cleanupClear(I,g.lift);
 g.mods.ITEMm.resetForNight(g.player,g.lift,I);
 g.crew.resetForNight();
 const homes=I.stacks.every(s=>s.mesh.position.distanceTo(s.home)<0.01);
 const clean=g.mods.ITEMm.cleanupClear(I,g.lift);
 return {dirty:dirty.left,clean:clean.left,homes,n0,n1:g.world.sheets.length}})()`);
say(reset.dirty.includes('board stacks'), 'a stack left in the hall is called out: ' + JSON.stringify(reset.dirty));
say(reset.homes, 'resetForNight puts every stack back on its home spot');
say(reset.n1 === reset.n0, `the laid sheets stay down over the night (${reset.n0} -> ${reset.n1})`);
say(!reset.clean.includes('board stacks'), 'with the stacks home nothing about boards is left: ' + JSON.stringify(reset.clean));

console.log('--- 13. the phone pictures');
await grab(0);
await at(40.0, 6.2); await faceHall(40.0, 4.0); await sleep(900);
const gs = await ghost();
say(gs.on && gs.col === '35d06a', 'ghost green over the carpet for the shot: ' + JSON.stringify(gs) + ' ' + JSON.stringify(await why()));
const btn = await ev(`(()=>{const b=document.getElementById('turn');const r=b.getBoundingClientRect();
 return {shown:getComputedStyle(b).display!=='none',w:Math.round(r.width),top:Math.round(r.top),bottom:Math.round(window.innerHeight-r.bottom),cls:document.body.classList.contains('sheet')}})()`);
say(btn.shown && btn.cls && btn.w > 40, 'the TURN button is up on the phone while a sheet is held: ' + JSON.stringify(btn));
await shot('ghost-green');
await act();   // hands empty again, so the lift shot carries the boards message alone
// the machine back on the path, driving until the boards run out
await ev(`(()=>{const g=ngv.game,L=g.lift;L.pos.copy(g.hallToWorld(44.0,7.5,g.world.floorY));L.yaw=2.9207;L.height=0;L.refresh();
 L.board(g.player,true);L.takeControls(g.player);})()`); await sleep(300);
// the message belongs to the moment you are pushing at the boards, so the shot is taken with the
// stick still over (Claude, 2026-09-07: it used to be read 700 ms after letting go, which is now
// null on purpose -- see the next block)
await ev(`ngv.game.player.keys.add('KeyW')`); await sleep(9000);
const last = await drv();
say(/wheels stay on the boards/.test(last.blocked || ''), 'stopped at the end of the boards for the shot: ' + last.blocked);
await shot('lift-at-the-end');
console.log('   prompt on the last shot: ' + await ev(`document.getElementById('prompt').textContent`));
console.log('   wheel plan outline: ' + await ev(`document.getElementById('wchassis').getAttribute('stroke')`));
await ev(`ngv.game.player.keys.delete('KeyW')`); await sleep(900);
// (Claude, 2026-09-07, the feel review's blocker) a reason is for while you are pushing at it: the
// boards line used to be written once and never cleared, so it stood in the prompt's place for the
// rest of the night -- every action after the first stop was invisible
const letGo = await ev(`(()=>{const g=ngv.game;return {blocked:g.lift.blocked,prompt:document.getElementById('prompt').textContent,
 action:g.action?g.action.label:null}})()`);
say(!letGo.blocked, 'and the boards line clears the moment the stick is let go: ' + JSON.stringify(letGo.blocked));
say(letGo.prompt.indexOf(letGo.action) === 0, 'the prompt is the action again: ' + JSON.stringify(letGo.prompt));

// ---- the four defects the skeptical tester found, one check each so they cannot come back ----
console.log('--- 14. a board laid with DROP is in the save (defect 2)');
await ev(`ngv.game.lift.leave(ngv.game.player,true)`); await sleep(300);   // off the machine: on the deck the lift owns where you stand
// every sheet in the game, wherever it is: on a stack, on the floor, in your hands or in a crew's
const total = () => ev(`(()=>{const g=ngv.game;return g.items.stacks.reduce((n,s)=>n+s.sheets,0)+g.world.sheets.length
 +g.player.inv.filter(i=>i&&i.type==='sheet').length+g.crew.members.reduce((n,m)=>n+(m.carry&&m.carry.type==='sheet'?1:0),0)})()`);
say((await total()) === 150, 'the 150 sheets are all accounted for before the check: ' + await total());
await grab(0);
await at(38.0, 8.0); await faceHall(38.0, 6.0); await sleep(600);
const dropLabel = await label();
const nBefore = (await sheets()).length;
await ev(`ngv.game.player.dropQueued=true`); await sleep(600);
const nAfter = (await sheets()).length;
say(/Lay the sheet here/.test(dropLabel) && nAfter === nBefore + 1, `DROP lays the board it is standing over: ${nBefore} -> ${nAfter} (${dropLabel})`);
const savedNow = await ev(`(JSON.parse(localStorage.getItem('ngv-install-phase1')||'{}').sheets||[]).length`);
say(savedNow === nAfter, `and the save has it without an ACTION: ${savedNow} saved, ${nAfter} down`);

console.log('--- 15. a full stack takes no board (defect 3)');
await grab(0);
const full = await ev(`(()=>{const I=ngv.game.items;const i=I.stacks.findIndex(s=>s.sheets>=30);return i})()`);
say(full >= 0, 'a full stack to try it on: stack ' + full);
const fu = await ev(`ngv.game.mods.W.worldToHall(ngv.game.items.stacks[${full}].mesh.position).u`);
const fd = await ev(`ngv.game.mods.W.worldToHall(ngv.game.items.stacks[${full}].mesh.position).d`);
const fside = fd < 7.5 ? 1 : -1;
await at(fu, fd + fside * 2.1); await faceHall(fu, fd + fside * 1.0, 0.5); await sleep(450);
say(/That stack is full/.test(await label()), 'at a full stack with a board in hand: ' + await label());
await act();
say((await ev(`ngv.game.items.stacks[${full}].sheets`)) === 30, 'the full stack still holds 30');
say((await inv()).hand === 'sheet', 'and the board is still in your hands, not gone');
say((await total()) === 150, 'no sheet was destroyed: ' + await total());
const room = await ev(`(()=>{const I=ngv.game.items;return I.stacks.findIndex(s=>s.sheets<30)})()`);
const ru = await ev(`ngv.game.mods.W.worldToHall(ngv.game.items.stacks[${room}].mesh.position).u`);
const rd = await ev(`ngv.game.mods.W.worldToHall(ngv.game.items.stacks[${room}].mesh.position).d`);
const rside = rd < 7.5 ? 1 : -1;
const roomBefore = await ev(`ngv.game.items.stacks[${room}].sheets`);
await at(ru, rd + rside * 2.1); await faceHall(ru, rd + rside * 1.0, 0.5); await sleep(450);
say(/Put the sheet back/.test(await label()), 'a stack with room takes it: ' + await label());
await act();
say((await ev(`ngv.game.items.stacks[${room}].sheets`)) === roomBefore + 1 && (await total()) === 150, `stack ${room} went ${roomBefore} -> ${roomBefore + 1}, still 150 sheets in the game`);

console.log('--- 16. the prompt answers the reticle with full hands (defect 4)');
await at(51.6, 6.0); await faceHall(51.6, 4.5, 0.4); await sleep(450);
say(/Take box from/.test(await label()), 'at a light pallet: ' + await label());
await act();
say((await inv()).hand === 'box', 'a box in the hands');
await at(ru, rd + rside * 2.1); await faceHall(ru, rd + rside * 1.0, 0.5); await sleep(450);
say(/Hands full: a sheet takes both hands/.test(await label()), 'pointing at the ply with a box in hand: ' + await label());
await ev(`ngv.game.player.dropQueued=true`); await sleep(400);

console.log('--- 17. the wheel plan does not print over the UP button (defect 5)');
await ev(`(()=>{const g=ngv.game,L=g.lift;L.height=0;L.refresh();L.board(g.player,true);L.takeControls(g.player);})()`); await sleep(500);
// everything that can be up while you drive: both sticks, UP / DOWN / FAST, the stats, the
// inventory, the deck height, a two-line prompt, a toast, DROP and TURN, the reticle
const hudCheck = `(()=>{document.body.classList.add('carrying','sheet');
 const t=document.getElementById('toast');t.textContent='A team of two has joined: Dave and Priya, with their own lift';t.classList.add('up');
 const r=(id)=>{const e=document.getElementById(id);const b=e.getBoundingClientRect();
  return {id,x:b.left,y:b.top,w:b.width,h:b.height,shown:getComputedStyle(e).display!=='none'}};
 const over=(a,b)=>a.x<b.x+b.w-1&&b.x<a.x+a.w-1&&a.y<b.y+b.h-1&&b.y<a.y+a.h-1;
 const w=r('wheels');
 const others=['stats','inv','liftUp','liftDown','liftMode','prompt','deckh','move','look','drop','turn','toast','reticle'].map(r);
 return {W:window.innerWidth,box:[Math.round(w.x),Math.round(w.y),Math.round(w.w),Math.round(w.h)],shown:w.shown,
  clash:others.filter(e=>e.shown&&over(w,e)).map(e=>e.id),
  onScreen:w.y>=0&&w.y+w.h<=window.innerHeight&&w.x>=0&&w.x+w.w<=window.innerWidth}})()`;
const hud = await ev(hudCheck);
say(hud.shown && hud.clash.length === 0, 'at 412 the plan is up and touches nothing: ' + JSON.stringify(hud));
say(hud.onScreen, 'and the whole plan is on the screen: ' + JSON.stringify(hud.box));
await shot('hud-plan-clear');
// and again at 360, the narrow phone (Lloyd's rule: a HUD that reads on a wide phone can still pile up on a narrow one)
await send('Emulation.setDeviceMetricsOverride', { width: 360, height: 780, deviceScaleFactor: 1.5, mobile: true }); await sleep(700);
const hud360 = await ev(hudCheck);
say(hud360.shown && hud360.clash.length === 0 && hud360.onScreen, 'at 360 as well: ' + JSON.stringify(hud360));
await shot('hud-plan-360');
await send('Emulation.setDeviceMetricsOverride', { width: 412, height: 915, deviceScaleFactor: 1.5, mobile: true }); await sleep(600);
await ev(`document.getElementById('toast').classList.remove('up')`);
await ev(`ngv.game.lift.leave(ngv.game.player,true)`); await sleep(300);

console.log('--- 18. every cell sheetCells names really does cover the point');
const cells = await ev(`(()=>{const W=ngv.game.mods.W,bad=[];
 for(let u=1;u<48.9;u+=3.7)for(let d=0.6;d<15;d+=2.3)for(const a of ['u','d']){
  for(const c of W.sheetCells(u,d,a)){const r=W.sheetRect(c);
   if(u<r.u0-0.001||u>r.u1+0.001||d<r.d0-0.001||d>r.d1+0.001)bad.push([+u.toFixed(1),+d.toFixed(1),a,c.u,c.d]);}}
 return bad})()`);
say(cells.length === 0, 'a board on any of them lands under the point that asked for it: ' + JSON.stringify(cells).slice(0, 200));

console.log('--- 19. the crew board their own way in from a BARE hall (defect 1)');
await enter(false);
const crewRun = await ev(`(()=>{const g=ngv.game;
 g.player.pos.copy(g.hallToWorld(12,7.5,g.world.floorY));       // out of the way, and out of the doors
 g.crew.assignTask('Dave','fit','S6'); g.crew.assignTask('Priya','feed','S6');
 g._c={off:0,frames:0,path:[],start:null,err:null,stop:false};
 const tick=()=>{ if(g._c.stop)return; try{ const W=g.crew.byName('Dave');
   if(W&&W.lift){ const h=g.mods.W.worldToHall(W.lift.pos);
    g._c.frames++; if(g.world.liftOnBoards(W.lift))g._c.off++;
    if(!g._c.start)g._c.start=[h.u,h.d];
    const last=g._c.path[g._c.path.length-1];
    if(!last||Math.hypot(last[0]-h.u,last[1]-h.d)>0.15)g._c.path.push([h.u,h.d]); } }catch(e){ g._c.err=String(e&&e.message||e); }
  requestAnimationFrame(tick);};
 requestAnimationFrame(tick); return true})()`);
say(crewRun === true, 'a fitter and a feeder on the floor with no ply down at all');
await sleep(115000);
const crew2 = await ev(`(()=>{const g=ngv.game,W=g.mods.W,F=g.crew.byName('Dave'),B=g.crew.byName('Priya');const h=W.worldToHall(F.lift.pos);
 // how far each board they laid is from the machine's own path: a board laid off to one side is a
 // board that never carried a wheel
 const far=g.world.sheets.map(s=>{let m=99;for(const p of g._c.path)m=Math.min(m,Math.hypot(p[0]-s.u,p[1]-s.d));return +m.toFixed(2);});
 return {off:g._c.off,frames:g._c.frames,err:g._c.err,start:g._c.start,now:[+h.u.toFixed(2),+h.d.toFixed(2)],
  boards:B.boards||0,sheets:g.world.sheets.length,far,worst:Math.max(0,...far),
  wheels:g.world.liftWheels(F.lift).map(w=>[+w.u.toFixed(2),+w.d.toFixed(2)])}})()`);
await ev(`ngv.game._c.stop=true`);
say(crew2.frames > 400, `sampled the crew lift every frame for 115 s (${crew2.frames} frames)`);
say(crew2.off === 0, `never a wheel on bare carpet (${crew2.off} frames off the boards)`);
say(crew2.sheets >= 4, `the feeder laid its own road: ${crew2.sheets} sheets, team count ${crew2.boards}`);
say(crew2.now[0] < 48.9 - 1.3, `the whole machine is inside the hall: u ${crew2.now[0]}, wheels ` + JSON.stringify(crew2.wheels));
say(crew2.start[0] - crew2.now[0] > 2.5, `and it kept moving up the hall: ${crew2.start[0].toFixed(2)} -> ${crew2.now[0]}`);
say(crew2.worst < 2.4, 'every board they laid is under the path the machine took (worst ' + crew2.worst + ' m): ' + JSON.stringify(crew2.far));
say(!crew2.err, 'the sampler itself never threw: ' + (crew2.err || 'clean'));

console.log('--- 20. the feeder walks back out through the doorway (defect 1, the deadlock)');
const walkOut = await ev(`(()=>{const g=ngv.game,B=g.crew.byName('Priya');
 // the exact spot the feeder used to freeze on: inside the hall, a little off the door's centre
 if(B.carry&&B.carry.type==='sheet'){ if(B.carry.mesh)B.carry.mesh.removeFromParent(); g.items.returnSheet(B.pos); }
 B.carry=null; B.pos.copy(g.hallToWorld(47.6,8.1,g.world.floorY)); B.pos.y=g.world.floorY;
 g._w={u0:47.6,best:47.6}; return true})()`);
say(walkOut === true, 'the feeder put back on the spot it used to freeze on: hall (47.6, 8.1)');
for (let i = 0; i < 30; i++) { await sleep(1000);
 const u = await ev(`ngv.game.mods.W.worldToHall(ngv.game.crew.byName('Priya').pos).u`);
 await ev(`ngv.game._w.best=Math.max(ngv.game._w.best,${u})`);
 if (u > 50) break; }
const outU = await ev(`ngv.game._w.best`);
say(outU > 50, `it walked out through the doors for the next board: u reached ${(+outU).toFixed(2)}`);

// (Claude, 2026-09-07, the feel review) a crew machine parked on the road stopped the player dead
// with the stick still forward and nothing on screen: a crew lift cannot be aimed at, so the only
// hint was the proximity ring. It says what happened now
console.log('--- 21. a machine stopped by another machine says why');
// both machines on the corridor's concrete, nose to nose down the middle of the aisle: no ply is
// involved, so the only thing that can stop the player is the other machine
await ev(`ngv.game.lift.leave(ngv.game.player,true)`); await sleep(300);
const set21 = await ev(`(()=>{const g=ngv.game,L=g.lift,C=g.crew,W=g.mods.W;
 C.members.forEach(m=>C.assignTask(m,'standby'));
 L.pos.copy(g.hallToWorld(61.0,7.5,g.world.floorY)); L.yaw=Math.PI; L.height=0; L.anim=null; L.steer=0; L.speed=0; L.refresh();
 const X=C.lifts.find(l=>!l.by)||C.lifts[0];
 X.pos.copy(g.hallToWorld(57.0,7.5,g.world.floorY)); X.yaw=0; X.height=0; X.refresh();
 L.board(g.player,true); L.takeControls(g.player);
 return {aboard:L.aboard,driving:L.driving,u:+W.worldToHall(L.pos).u.toFixed(2),
  crew:C.lifts.map(l=>+W.worldToHall(l.pos).u.toFixed(2))}})()`); await sleep(500);
say(set21.aboard && set21.driving, 'at the controls in the corridor: ' + JSON.stringify(set21));
await ev(`ngv.game.player.keys.add('KeyW')`); await sleep(6000);
const bump = await ev(`(()=>{const g=ngv.game,W=g.mods.W;return {blocked:g.lift.blocked,
 u:+W.worldToHall(g.lift.pos).u.toFixed(2),prompt:document.getElementById('prompt').textContent}})()`);
await ev(`ngv.game.player.keys.delete('KeyW')`);
say(/Something is in the way/.test(bump.blocked || ''), 'held by a crew machine on the road: ' + JSON.stringify(bump));
say(bump.prompt.indexOf('Something is in the way') === 0, 'and the pill carries it: ' + JSON.stringify(bump.prompt));
await shot('bumped');
await sleep(1200);
say(!(await ev(`ngv.game.lift.blocked`)), 'it clears when the stick is let go too');

console.log(bad ? `${bad} FAIL` : 'all ok');
console.log(logs.join(String.fromCharCode(10)) || 'no errors');
ws.close(); process.exit(bad ? 1 : 0);
