// THE CREW YOU ALLOCATE (Lloyd, 2026-09-06: "Can we also add crew from the start. The player
// should be able to allocate tasks to the crew members"). Five of them in the corridor from 17:00
// with two lifts and two jacks; the reticle and the crew panel both open a task sheet; the seven
// jobs; the shared machines; the pack-up. Serve on :8877, headless Chrome on :9333 (NGV_PORT).
//   node tools/game-crewtasks.mjs <outdir>
//
// The long working run is stepped, not watched in real time: crew.update(dt) is called in a tight
// loop with the doors and the obstacle plan stepped alongside it, exactly as index.html's frame
// does, so a night's worth of walking takes seconds. Every step is sampled.
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
 if (m.method === 'Runtime.exceptionThrown') logs.push('EXC ' + JSON.stringify(m.params.exceptionDetails.exception && m.params.exceptionDetails.exception.description || m.params.exceptionDetails).slice(0, 900));
 if (m.method === 'Runtime.consoleAPICalled' && m.params.type === 'error') logs.push('ERR ' + JSON.stringify(m.params.args.map(a => a.value || a.description)).slice(0, 300)); };
await new Promise(r => ws.onopen = r);
const send = (method, params = {}) => new Promise(r => { const i = ++id; pend[i] = r; ws.send(JSON.stringify({ id: i, method, params })); });
const ev = async expr => { const r = await send('Runtime.evaluate', { expression: expr, returnByValue: true, awaitPromise: true });
 if (!r) return undefined; if (r.exceptionDetails) return 'EVALERR ' + JSON.stringify(r.exceptionDetails.exception && r.exceptionDetails.exception.description).slice(0, 400);
 return r.result ? r.result.value : r; };
const sleep = ms => new Promise(r => setTimeout(r, ms));
const shot = async n => { const s = await send('Page.captureScreenshot', { format: 'jpeg', quality: 82 }); fs.writeFileSync(`${out}/${n}.jpg`, Buffer.from(s.data, 'base64')); };
let bad = 0; const say = (ok, msg) => { if (!ok) bad++; console.log((ok ? 'ok   ' : 'FAIL ') + msg); };

await send('Network.enable'); await send('Network.setCacheDisabled', { cacheDisabled: true });
await send('Emulation.setDeviceMetricsOverride', { width: 412, height: 915, deviceScaleFactor: 1.5, mobile: true });
await send('Emulation.setTouchEmulationEnabled', { enabled: true });
await send('Page.enable'); await send('Runtime.enable');
await send('Page.navigate', { url: base + Date.now() });
for (let i = 0; i < 60; i++) { await sleep(500); if (await ev('!!(window.ngv&&window.ngv.hall&&document.getElementById("install"))')) break; }
await ev(`localStorage.clear(); localStorage.setItem('ngv.install','gandel-2026'); document.getElementById('install').click()`);
for (let i = 0; i < 60; i++) { await sleep(500); if (await ev('!!(window.ngv&&window.ngv.game)')) break; }
await ev(`document.querySelector('#start').click()`); await sleep(800);

const label = () => ev(`ngv.game.action?ngv.game.action.label:''`);
const toast = () => ev(`document.getElementById('toast').textContent`);
const act = async () => { await ev(`ngv.game.player.actionQueued=true`); await sleep(350); };
const at = (u, d) => ev(`(()=>{const g=ngv.game;g.player.pos.copy(g.hallToWorld(${u},${d},g.world.floorY));g.player.pos.y=g.world.floorY;})()`);
const faceHall = (u, d, y = 0) => ev(`(()=>{const g=ngv.game,P=g.player;const q=g.hallToWorld(${u},${d},g.world.floorY+${y});
 P.yaw=Math.atan2(-(q.x-P.pos.x),-(q.z-P.pos.z));P.pitch=Math.max(-1.34,Math.atan2(q.y-(P.pos.y+P.eye),Math.hypot(q.x-P.pos.x,q.z-P.pos.z)));})()`);
const hallOf = (expr) => ev(`(()=>{const g=ngv.game,h=g.mods.W.worldToHall(${expr});return [+h.u.toFixed(2),+h.d.toFixed(2)]})()`);
const crewRows = () => ev(`(()=>{const C=ngv.game.crew;return C.members.map(m=>({name:m.name,task:C.taskText(m.assign),id:m.assign.task,target:m.assign.target,status:m.status,
 lift:m.lift?ngv.game.crew.lifts.indexOf(m.lift):-1}))})()`);
const tap = (sel) => ev(`(()=>{const e=document.querySelector(${JSON.stringify(sel)});if(!e)return 'missing';e.click();return 'ok'})()`);
const sheetUp = () => ev(`document.getElementById('taskSheet').classList.contains('up')&&document.body.classList.contains('sheetOpen')`);

// one step of the shift for the crew alone: the obstacle plan, the doors and crew.update, exactly
// the order index.html's frame runs them in, sampled every step
const STEP = (n, dt) => `(()=>{const g=ngv.game,W=g.mods.W,C=g.crew,I=g.items;
 const R=g._r; try{
 for(let i=0;i<${n};i++){
  g.mods.ITEMm.refreshObstacles(I,[g.lift].concat(C.lifts));
  W.updateDoors(${dt},g.world,C.points().concat([g.player.pos]));
  const was=C.members.map(m=>[m.pos.x,m.pos.z,m.mesh.position.y]);
  C.update(${dt},g.clock,g.player,g.install.counts().columnsDone);
  R.frames++;
  for(const L of C.lifts) if(g.world.liftOnBoards(L)){ R.off++; if(!R.first)R.first=[C.lifts.indexOf(L),+W.worldToHall(L.pos).u.toFixed(2),+W.worldToHall(L.pos).d.toFixed(2)]; }
  // NOBODY TELEPORTS: the biggest step any member takes in one frame, over every run. A walking
  // pace is 0.105 m a frame and a sidestep doubles it, but the plan collider can also SHOVE a
  // walker out of a circle something was just set down on -- at most that circle's radius plus
  // his own, and the widest on the floor is the skip at 1.9. So the horizontal cap is what a
  // shove cannot reach, and the VERTICAL one is exact: only a ladder moves a man up or down, and
  // the ladder now takes a second (the boarding snap was 1.29 m in one frame)
  C.members.forEach((m,k)=>{ const j=Math.hypot(m.pos.x-was[k][0],m.pos.z-was[k][1]);
   if(j>R.jump){ R.jump=j; R.jumpWho=[m.name,+j.toFixed(2),m.status,R.frames]; }
   const jy=Math.abs(m.mesh.position.y-was[k][2]);
   if(jy>R.jumpY){ R.jumpY=jy; R.jumpYWho=[m.name,+jy.toFixed(2),m.status,R.frames]; } });
  // NOTHING IS LEFT FLAGGED AS CARRIED THAT NOBODY IS CARRYING
  const held=new Set(); for(const m of C.members) if(m.carry) held.add(m.carry);
  if(g.player.carry) held.add(g.player.carry); for(const it of (g.player.inv||[])) if(it) held.add(it);
  for(const b of I.boxes) if(b.carried&&!held.has(b)){ R.orphan++; if(!R.orphan1)R.orphan1=[b.type,b.lights,+W.worldToHall(b.mesh.position).u.toFixed(1)]; }
  for(const m of C.members){ (R.st[m.name]=R.st[m.name]||{})[m.status]=((R.st[m.name]||{})[m.status]||0)+1; R.all[m.status]=1; }
  while(C.toasts.length)R.toasts.push(C.toasts.shift());
 }}catch(e){ R.err=String(e&&e.stack||e); }
 return {frames:R.frames,off:R.off,first:R.first||null,err:R.err,
  sheets:g.world.sheets.length,
  n1:g.install.slots.filter(s=>s.column==='N1'&&g.install.fitted.has(s.id)).length,
  fitted:g.install.fitted.size,
  palletsIn:I.pallets.filter(p=>W.worldToHall(p.mesh.position).u<48.4).map(p=>p.column),
  playerLift:[+g.lift.pos.x.toFixed(3),+g.lift.pos.z.toFixed(3),+g.lift.height.toFixed(2)],
  lifts:C.lifts.map(L=>{const h=W.worldToHall(L.pos);return [+h.u.toFixed(2),+h.d.toFixed(2),+L.height.toFixed(2),L.by?L.by.name:null]})}})()`;
const reset = () => ev(`(()=>{const R=ngv.game._r;ngv.game._r={frames:0,off:0,st:{},all:(R&&R.all)||{},toasts:[],err:null,first:null,jump:0,jumpWho:null,jumpY:0,jumpYWho:null,orphan:0,orphan1:null};return true})()`);
// what one 50 ms frame may move a man: PACE is a walk plus a sidestep (a deliberate one-frame
// check), SHOVE is the most the plan collider can push him out of a circle, and RISE is the
// vertical, which only a ladder changes and the ladder takes a second now
const PACE = 0.4, SHOVE = 2.5, RISE = 0.25;
const run = async (seconds, dt = 0.05, chunk = 400) => { let r = null; const n = Math.round(seconds / dt);
 for (let done = 0; done < n; done += chunk) { r = await ev(STEP(Math.min(chunk, n - done), dt)); if (typeof r === 'string') { say(false, 'the stepper threw: ' + r); break; } if (r.err) break; }
 return r; };
const seen = (name) => ev(`Object.keys(ngv.game._r.st[${JSON.stringify(name)}]||{})`);
const toasts = () => ev(`ngv.game._r.toasts`);

console.log('--- 1. five crew, two lifts and two jacks, all standing by');
const start = await ev(`(()=>{const g=ngv.game,W=g.mods.W,C=g.crew;
 const hall=(p)=>{const h=W.worldToHall(p);return [+h.u.toFixed(2),+h.d.toFixed(2)]};
 return {names:C.members.map(m=>m.name), tasks:C.members.map(m=>m.assign.task), status:C.members.map(m=>m.status),
  colours:C.members.map(m=>m.colour), where:C.members.map(m=>hall(m.pos)),
  lifts:C.lifts.map(L=>hall(L.pos)), jacks:C.jacks.map(j=>hall(j.mesh.position)),
  liftsFree:C.lifts.every(L=>!L.by), teams:('teams' in C), helper:('helper' in C)}})()`);
say(start.names.length === 5 && start.names.join(',') === 'Dave,Priya,Marco,Jules,Tom', 'five by name: ' + start.names.join(', '));
say(start.tasks.every(t => t === 'standby') && start.status.every(s => s === 'standing by'), 'all five on standby: ' + JSON.stringify(start.status));
say(new Set(start.colours).size === 5, 'five different vest colours: ' + start.colours.map(c => '#' + c.toString(16)).join(' '));
say(start.where.every(w => w[0] > 51.906 && w[0] < 74 && w[1] > 0.5 && w[1] < 12), 'all five wait in the corridor: ' + JSON.stringify(start.where));
say(start.lifts.length === 2 && start.lifts.every(w => w[0] > 51.906), 'two crew lifts in storage: ' + JSON.stringify(start.lifts));
say(start.jacks.length === 2 && start.jacks.every(w => w[0] > 51.906), 'two crew jacks in storage: ' + JSON.stringify(start.jacks));
say(start.liftsFree, 'neither crew lift is claimed yet');
say(!start.teams && !start.helper, 'the old unlock-by-columns shape is gone (no crew.teams, no crew.helper)');
const p0 = await ev(`ngv.game.crew.members.map(m=>[+m.pos.x.toFixed(3),+m.pos.z.toFixed(3)])`);
await sleep(5000);
const p1 = await ev(`ngv.game.crew.members.map(m=>[+m.pos.x.toFixed(3),+m.pos.z.toFixed(3)])`);
const moved = p0.map((p, i) => Math.hypot(p[0] - p1[i][0], p[1] - p1[i][1]));
say(Math.max(...moved) < 0.02, 'nobody moves for 5 s on standby: ' + JSON.stringify(moved.map(m => +m.toFixed(3))));

console.log('--- 2. the reticle: talk to Dave and give him a column');
// stand 2 m off Dave on the side where nobody and nothing else is in the line of sight (the five
// wait in a block, so a straight line to Dave can easily run through Marco)
const dave = await hallOf('g.crew.byName("Dave").pos');
const stand = await ev(`(()=>{const g=ngv.game,W=g.mods.W,C=g.crew,D=C.byName('Dave');const hd=W.worldToHall(D.pos);
 const near=(u,d,h,pad)=>{const ax=hd.u-u,ad=hd.d-d,l2=ax*ax+ad*ad||1;const t=Math.max(0,Math.min(1,((h.u-u)*ax+(h.d-d)*ad)/l2));
  return Math.hypot(u+ax*t-h.u,d+ad*t-h.d)-pad;};
 let best=null,bd=-9;
 for(let a=0;a<24;a++){const th=a*Math.PI/12,u=hd.u+2.0*Math.cos(th),d=hd.d+2.0*Math.sin(th);
  if(u<49.6||u>70||d<3.6||d>11.4)continue;
  let m=99;
  for(const o of C.members) if(o!==D) m=Math.min(m,near(u,d,W.worldToHall(o.pos),0));
  for(const p of g.items.pallets.concat(g.items.stacks)) m=Math.min(m,near(u,d,W.worldToHall(p.mesh.position),0.8));
  for(const L of C.lifts.concat([g.lift])) m=Math.min(m,near(u,d,W.worldToHall(L.pos),1.2));
  if(m>bd){bd=m;best=[+u.toFixed(2),+d.toFixed(2)];}}
 return {best,clear:+bd.toFixed(2)}})()`);
console.log('     standing at ' + JSON.stringify(stand.best) + ', nearest thing in the way ' + stand.clear + ' m');
await at(stand.best[0], stand.best[1]);
await faceHall(dave[0], dave[1], 1.2); await sleep(500);
say(/Talk to Dave/.test(await label()), 'pointing at Dave from 2 m: ' + (await label()).replace(/<[^>]*>/g, ' | '));
say(/standing by/.test(await label()), 'and the prompt carries his status');
await act();
say((await sheetUp()) === true, 'ACTION opened the task sheet');
say((await ev(`document.getElementById('tsName').textContent`)) === 'Dave', 'the sheet is Dave\'s');
const before2 = await ev(`[+ngv.game.player.pos.x.toFixed(4),+ngv.game.player.pos.z.toFixed(4)]`);
await ev(`ngv.game.player.keys.add('KeyW')`); await sleep(600); await ev(`ngv.game.player.keys.delete('KeyW')`);
const after2 = await ev(`[+ngv.game.player.pos.x.toFixed(4),+ngv.game.player.pos.z.toFixed(4)]`);
say(before2[0] === after2[0] && before2[1] === after2[1], `W does nothing while the sheet is open: ${JSON.stringify(before2)} -> ${JSON.stringify(after2)}`);
say((await ev(`document.getElementById('paused').offsetParent!==null`)) === false, 'and the game is NOT paused behind it');
say((await tap('#tsTasks [data-task="fit"]')) === 'ok', 'tapped Fit column');
say((await ev(`document.getElementById('tsCols').hidden===false&&document.querySelectorAll('#tsCols button').length>=12`)) === true, 'the column picker came up with all twelve');
say((await tap('#tsCols [data-col="N1"]')) === 'ok', 'tapped N1');
await sleep(400);
say((await sheetUp()) === false, 'the sheet closed on assigning');
let rows = await crewRows();
say(rows[0].id === 'fit' && rows[0].target === 'N1', 'Dave is on fit / N1: ' + JSON.stringify(rows[0]));
say(/Dave: fit N1/.test(await toast()), 'and a toast said so: ' + await toast());

console.log('--- 3. the panel: the other four from the Tasks tab');
await ev(`document.getElementById('crewBtn').click()`); await sleep(300);
const panel = await ev(`(()=>{const p=document.getElementById('crewPanel');return {open:!p.hidden,tasksTab:!document.getElementById('crewTasksTab').hidden,
 rows:[...document.querySelectorAll('#crewTaskList button')].map(b=>b.textContent.trim().replace(/\\s+/g,' '))}})()`);
say(panel.open && panel.tasksTab, 'the Crew button opens on the Tasks tab');
say(panel.rows.length === 5, 'five rows: ' + JSON.stringify(panel.rows));
say(/Dave/.test(panel.rows[0]) && /fit N1/.test(panel.rows[0]), 'Dave\'s row reads his job: ' + panel.rows[0]);
const give = async (i, task, col) => {
 await ev(`document.getElementById('crewPanel').hidden=false;`);
 await ev(`(()=>{const b=document.querySelector('#crewTaskList [data-crew="${i}"]');if(b)b.click();})()`); await sleep(250);
 await tap(`#tsTasks [data-task="${task}"]`); await sleep(200);
 if (col) { await tap(`#tsCols [data-col="${col}"]`); }
 await sleep(300);
 return sheetUp();
};
say((await ev(`document.getElementById('crewBtn').click(),1`)) === 1, 'panel reopened');
say((await give(1, 'boards', 'N1')) === false, 'Priya: lay boards to N1');
await ev(`document.getElementById('crewBtn').click()`);
say((await give(2, 'feed', 'N1')) === false, 'Marco: feed N1');
await ev(`document.getElementById('crewBtn').click()`);
say((await give(3, 'pallets', null)) === false, 'Jules: bring pallets in');
await ev(`document.getElementById('crewBtn').click()`);
say((await give(4, 'rubbish', null)) === false, 'Tom: rubbish');
rows = await crewRows();
say(JSON.stringify(rows.map(r => r.task)) === JSON.stringify(['fit N1', 'boards to N1', 'feed N1', 'bring pallets in', 'rubbish']),
 'the five jobs are in: ' + JSON.stringify(rows.map(r => r.name + ' = ' + r.task)));

console.log('--- 4. a shift\'s work, stepped');
// The road to N1 is 41 m of ply: a night is 12 hours and one worker carrying one board at a time
// cannot lay it and fit the column in the same night. The SPINE is put down by script, the way a
// previous night would have left it (the protection stays down for the whole job), and the
// column's PATCH -- the part that is missing -- is what Priya has to lay
const road = await ev(`(()=>{const g=ngv.game,W=g.mods.W,C=g.crew;
 const plan=C.boardPlan('N1').filter(s=>Math.abs(s.d-7.5)<0.01);
 let n=0; for(const s of plan){ const st=g.items.stacks.find(x=>x.sheets>0); if(!st)break; st.sheets--; g.items.updateStackPile(st); W.laySheet(g.world,s.u,s.d,s.along); n++; }
 g.player.pos.copy(g.hallToWorld(30,13.6,g.world.floorY)); g.player.pos.y=g.world.floorY;   // out of the road and out of the doorway
 return {laid:n,total:g.world.sheets.length,patch:C.boardPlan('N1').length-n,stacks:g.items.stacks.map(s=>s.sheets)}})()`);
console.log(`     spine pre-laid by script: ${road.laid} boards from the stacks (${JSON.stringify(road.stacks)} left), ${road.patch} in the N1 patch for Priya`);
await reset();
const r1 = await run(60);
say(!r1.err, 'the stepper ran clean: ' + (r1.err || 'no exception'));
const r2 = await run(360);
const daveSeen = await seen('Dave'), marcoSeen = await seen('Marco'), priyaSeen = await seen('Priya');
const r = await ev(`ngv.game._r`);
say(r.frames > 8000, `stepped ${r.frames} crew frames (${(r.frames * 0.05).toFixed(0)} s of shift)`);
say(r.off === 0, `no crew lift ever had a wheel on bare carpet (${r.off} frames off the boards${r.first ? ', first at ' + JSON.stringify(r.first) : ''})`);
say(r.jump < SHOVE, `nobody teleported across the floor: the biggest step in one frame was ${JSON.stringify(r.jumpWho)}`);
say(r.jumpY < RISE, `and nobody jumped on or off a deck: the biggest rise in one frame was ${JSON.stringify(r.jumpYWho)}`);
say(r.orphan === 0, `no carton is left flagged as carried with nobody carrying it (${r.orphan} frames${r.orphan1 ? ', first ' + JSON.stringify(r.orphan1) : ''})`);
say(r2.sheets > road.total, `Priya laid boards: ${road.total} -> ${r2.sheets} sheets down`);
say(daveSeen.includes('rolling to N1') || daveSeen.includes('waiting for boards near N1'), 'Dave went through rolling / waiting for boards: ' + JSON.stringify(daveSeen));
say(daveSeen.some(s => /^fitting N1 \(/.test(s)), 'and then fitting N1: ' + JSON.stringify(daveSeen.filter(s => /fitting/.test(s))));
say(r2.n1 > 0, `lights went in on N1: ${r2.n1} fitted`);
const daveLift = Math.max(0, await ev(`ngv.game.crew.lifts.indexOf(ngv.game.crew.byName('Dave').lift)`));
say((await ev(`ngv.game.crew.lifts.indexOf(ngv.game.crew.byName('Dave').lift)`)) >= 0, 'Dave is on a CREW lift, index ' + daveLift);
say(r2.playerLift[0] === r1.playerLift[0] && r2.playerLift[1] === r1.playerLift[1] && r2.playerLift[2] === 0,
 `the player's own lift never moved: ${JSON.stringify(r2.playerLift)}`);
say(r2.palletsIn.length > 0, `Jules jacked pallets into the hall: ${JSON.stringify(r2.palletsIn)}`);
say(marcoSeen.some(s => /^feeding N1/.test(s)), 'Marco fed the column: ' + JSON.stringify(marcoSeen));
say(priyaSeen.some(s => /^laying boards to N1/.test(s)), 'Priya\'s status counted the boards down: ' + JSON.stringify(priyaSeen.filter(s => /laying/.test(s))));
// the hall with two of them at work. (Claude, 2026-09-07) It used to stand back from Dave and
// whoever was nearest HIM, and fail when that happened to be somebody 35 m away on a rubbish run to
// the skip. The shot is composed instead: the crew who are actually IN THE HALL, camera behind the
// furthest of them down the middle, and a few more seconds of shift if fewer than two are inside
let frame = null, inView = [];
for (let tries = 0; tries < 8; tries++) {
 frame = await ev(`(()=>{const g=ngv.game,W=g.mods.W,C=g.crew,P=g.player;
  const inHall=C.members.map(m=>({m,h:W.worldToHall(m.lift&&m.onDeck?m.lift.pos:m.pos)})).filter(x=>x.h.u<W.HALL.doorU-0.5);
  if(inHall.length<2)return {n:inHall.length,who:inHall.map(x=>x.m.name)};
  const back=Math.min(W.HALL.doorU-1.2,Math.max(...inHall.map(x=>x.h.u))+7.0);
  const mid=inHall.reduce((a,x)=>a+x.h.u,0)/inHall.length;
  P.pos.copy(g.hallToWorld(back,7.5,g.world.floorY)); P.pos.y=g.world.floorY;
  return {n:inHall.length,who:inHall.map(x=>x.m.name),back:+back.toFixed(1),mid:[+mid.toFixed(2),7.5]}})()`);
 if (frame.n >= 2) {
  await faceHall(frame.mid[0], frame.mid[1], 1.2); await sleep(500);
  inView = await ev(`(()=>{const g=ngv.game,C=g.crew,cam=g.player.camera;cam.updateMatrixWorld(true);
   const v=new (g.player.pos.constructor)();
   return C.members.filter(m=>{v.copy(m.lift&&m.onDeck?m.lift.pos:m.pos);v.y+=1.1;v.project(cam);return v.z<1&&Math.abs(v.x)<0.95&&Math.abs(v.y)<0.95;}).map(m=>m.name)})()`);
  if (inView.length >= 2) break;
 }
 await run(15);   // fifteen more seconds of shift: they come back to the column
}
say(inView.length >= 2, 'the hall shot has two of the crew in frame: ' + JSON.stringify(inView) + ' (in the hall: ' + JSON.stringify(frame.who) + ')');
await shot('hall-at-work');

console.log('--- 5. reassigning a fitter mid-column');
const wasAt = await hallOf('g.crew.byName("Dave").lift.pos');
await ev(`ngv.game.crew.assignTask('Dave','standby')`);
await reset(); await run(20);
const off5 = await ev(`(()=>{const g=ngv.game,C=g.crew,D=C.byName('Dave'),L=C.lifts[${daveLift}],W=g.mods.W;
 const h=W.worldToHall(L.pos),p=W.worldToHall(D.pos);
 return {lift:!!D.lift,by:L.by?L.by.name:null,h:+L.height.toFixed(2),liftAt:[+h.u.toFixed(2),+h.d.toFixed(2)],daveAt:[+p.u.toFixed(2),+p.d.toFixed(2)],status:D.status,onDeck:D.onDeck}})()`);
say(off5.h < 0.02, 'his deck came down: ' + off5.h + ' m');
say(!off5.lift && off5.by === null, 'the machine went back on the free list');
say(off5.liftAt[0] < 48.4, 'and it is left standing in the hall at ' + JSON.stringify(off5.liftAt) + ' (was ' + JSON.stringify(wasAt) + ')');
say(!off5.onDeck, 'Dave has both feet on the floor: ' + JSON.stringify(off5.daveAt) + ' ' + off5.status);
await run(4);
const walk5 = await ev(`+ngv.game.mods.W.worldToHall(ngv.game.crew.byName('Dave').pos).u.toFixed(2)`);
say(walk5 > off5.daveAt[0] + 1.0, `and he is walking back out: u ${off5.daveAt[0]} -> ${walk5}`);
await ev(`ngv.game.crew.assignTask('Tom','fit','N1')`);
await run(4);
const tom = await ev(`(()=>{const C=ngv.game.crew,T=C.byName('Tom');return {i:C.lifts.indexOf(T.lift),status:T.status}})()`);
say(tom.i >= 0, 'Tom took a free crew lift (index ' + tom.i + '), status: ' + tom.status);

console.log('--- 6. a third fitter with both machines out');
await ev(`ngv.game.crew.assignTask('Marco','fit','N2')`);
await run(4);
const taken = await ev(`ngv.game.crew.lifts.map(L=>L.by?L.by.name:null)`);
say(taken.every(Boolean), 'both crew lifts are out: ' + JSON.stringify(taken));
await reset();
await ev(`ngv.game.crew.assignTask('Jules','fit','N3')`);
await run(6);
const jules = await ev(`ngv.game.crew.byName('Jules').status`);
const tt = await toasts();
const nolift = tt.filter(x => /No free lift for Jules/.test(x));
say(jules === 'waiting for a lift', 'Jules waits: "' + jules + '"');
say(nolift.length === 1, `and the line is said once, not every frame (${nolift.length}): ` + JSON.stringify(nolift));

console.log('--- 7. a lone fitter, nobody feeding him and nobody on boards');
// (the skeptic's D3) The ring round a shaft cannot be boarded -- a sheet must clear the column by
// 0.6 m -- so no machine ever reaches a run's own spot. A fitter on his own used to stand on the
// spine saying `waiting for boards near N6` for the rest of the night. He parks and works now
await ev(`(()=>{const g=ngv.game,C=g.crew,W=g.mods.W;
 C.members.forEach(m=>C.assignTask(m,'standby')); C.resetForNight(); g.clock.minute=17*60;
 for(const s of C.boardPlan('N6')){ const st=g.items.stacks.find(x=>x.sheets>0); if(!st)break; st.sheets--; g.items.updateStackPile(st); W.laySheet(g.world,s.u,s.d,s.along); }
 g.player.pos.copy(g.hallToWorld(30,13.6,g.world.floorY)); g.player.pos.y=g.world.floorY;
 C.assignTask('Dave','fit','N6'); return 1})()`);
await reset();
const n6start = await ev(`ngv.game.install.slots.filter(s=>s.column==='N6'&&ngv.game.install.fitted.has(s.id)).length`);
let parked7 = false;
for (let s = 0; s < 300; s += 20) { await run(20); if (await ev(`ngv.game.crew.lifts.some(L=>L.parked)`)) parked7 = true; }
const lone = await ev(`(()=>{const g=ngv.game,C=g.crew,W=g.mods.W,D=C.byName('Dave'),L=D.lift;
 return {n6:g.install.slots.filter(s=>s.column==='N6'&&g.install.fitted.has(s.id)).length,status:D.status,
  atCol:L?+L.pos.distanceTo(C.columnOf('N6').pos).toFixed(2):null,
  seen:Object.keys(ngv.game._r.st.Dave||{}),jump:ngv.game._r.jumpWho,jumpY:ngv.game._r.jumpY,jumpYWho:ngv.game._r.jumpYWho,orphan:ngv.game._r.orphan}})()`);
say(lone.n6 - n6start >= 16, `he got past the first run on his own: N6 ${n6start} -> ${lone.n6} of 64 in 300 s`);
say(!/waiting for boards/.test(lone.status), `and he is not stalled waiting for a boards worker who is not coming: "${lone.status}"`);
say(parked7, 'his machine parked at the column instead of pushing at the last metre (L.parked)');
say(lone.atCol !== null && lone.atCol < 4.6, `and it is standing at the column: ${lone.atCol} m off the shaft`);
say((lone.jump === null || lone.jump[1] < SHOVE) && lone.jumpY < RISE, `nobody teleported: ${JSON.stringify(lone.jump)} / up ${JSON.stringify(lone.jumpYWho)}`);
say(lone.orphan === 0, `no carton left flagged as carried (${lone.orphan})`);

console.log('--- 8. reassigning a fitter who is AWAY from his machine');
// (the skeptic's D1) The N6 pallet and every open carton go back out to the corridor, so the same
// fitter has to walk the hall for his boxes. Reassigned out there he used to be snapped back to
// the ladder foot -- 11 m in one 50 ms frame
await ev(`(()=>{const g=ngv.game,I=g.items,C=g.crew;
 const p=I.pallets.find(x=>x.column==='N6'); p.mesh.position.copy(p.home); p.mesh.rotation.y=0;
 I.boxes.forEach((b,i)=>{ if(b.disposed||b.onLift||b.carried)return; b.mesh.position.copy(g.hallToWorld(53.4+(i%6)*0.62,11.4-Math.floor(i/6)*0.5,g.world.floorY+0.2)); });
 return 1})()`);
await reset();
let away = null;
for (let s = 0; s < 400 && !away; s += 5) { await run(5);
  away = await ev(`(()=>{const C=ngv.game.crew,D=C.byName('Dave');
   return (D.lift&&!D.onDeck&&!D.climb&&D.pos.distanceTo(D.lift.pos)>6)?{status:D.status,off:+D.pos.distanceTo(D.lift.pos).toFixed(2)}:null})()`); }
say(!!away, away ? `he walked out for his own boxes, ${away.off} m from the machine: "${away.status}"` : 'he never left the deck to fetch boxes');
if (away) {
  const b8 = await hallOf('g.crew.byName("Dave").pos');
  await ev(`ngv.game.crew.assignTask('Dave','standby')`);
  await run(0.05);
  const a8 = await hallOf('g.crew.byName("Dave").pos');
  say(Math.hypot(a8[0] - b8[0], a8[1] - b8[1]) < PACE, `reassigned out there he stays put: ${JSON.stringify(b8)} -> ${JSON.stringify(a8)}`);
  await run(3);
  const free8 = await ev(`(()=>{const C=ngv.game.crew,D=C.byName('Dave'),L=C.lifts.find(l=>!l.by);
   return {his:!!D.lift,free:C.lifts.filter(l=>!l.by).length,h:Math.max(...C.lifts.map(l=>+l.height.toFixed(2))),jump:ngv.game._r.jumpWho,jumpY:ngv.game._r.jumpY}})()`);
  say(!free8.his && free8.free === 2, `and the machine goes back on the free list where it stands (${free8.free} free)`);
  say(free8.h < 0.02, 'with its deck down: ' + free8.h + ' m');
  say((free8.jump === null || free8.jump[1] < SHOVE) && free8.jumpY < RISE, `nobody teleported on the way out: ${JSON.stringify(free8.jump)}`);
}

console.log('--- 9. 04:30, pack up');
const wasIn = await ev(`ngv.game.items.pallets.filter(p=>ngv.game.mods.W.worldToHall(p.mesh.position).u<48.4).map(p=>p.column)`);
console.log(`     ${wasIn.length} pallets standing at column feet when the clock hits 04:30: ${JSON.stringify(wasIn)}`);
await ev(`ngv.game.clock.minute=28.5*60+1`);
await reset();
let packed = null, took = 0;
const packState = `(()=>{const g=ngv.game,C=g.crew,W=g.mods.W;
 const inHall=(m)=>W.worldToHall(m.position).u<48.4;
 return {left:C.leftInHall(), members:C.members.map(m=>+W.worldToHall(m.pos).u.toFixed(2)), status:C.members.map(m=>m.status),
  pallets:g.items.pallets.filter(p=>inHall(p.mesh)).map(p=>p.column), stacks:g.items.stacks.filter(s=>inHall(s.mesh)).length,
  clean:g.mods.ITEMm.cleanupClear(g.items,g.lift).left,
  lifts:C.lifts.map(L=>+W.worldToHall(L.pos).u.toFixed(2)), jacks:C.jacks.map(j=>+W.worldToHall(j.mesh.position).u.toFixed(2))}})()`;
for (let s = 20; s <= 700; s += 20) { await run(20); took = s; packed = await ev(packState);
 if (!packed.left.length && !packed.pallets.length && !packed.stacks && packed.members.every(u => u > 51.906)) break; }
say(packed.left.length === 0, `everything of the crew's is out of the hall after ${took} s: lifts ${JSON.stringify(packed.lifts)}, jacks ${JSON.stringify(packed.jacks)}` + (packed.left.length ? ' LEFT: ' + JSON.stringify(packed.left) : ''));
// (the skeptic's D2) the pack-up used to walk home only a pallet that was already in the air
say(wasIn.length >= 8 && packed.pallets.length === 0, `and every pallet the crew wheeled in went back out (${wasIn.length} -> ${packed.pallets.length})` + (packed.pallets.length ? ' LEFT: ' + JSON.stringify(packed.pallets) : ''));
say(packed.stacks === 0, `no stack of ply is left in the hall either (${packed.stacks})`);
say(!packed.clean.includes('pallets') && !packed.clean.includes('board stacks'), `the night's clean-up reads neither pallets nor board stacks: ${JSON.stringify(packed.clean)}`);
say(packed.members.every(u => u > 51.906), 'and all five stand in the corridor: ' + JSON.stringify(packed.members));
const packR = await ev(`ngv.game._r`);
say(!packR.err, 'the pack-up threw nothing: ' + (packR.err || 'clean'));
say(packR.jump < SHOVE && packR.jumpY < RISE, `nobody teleported packing up: ${JSON.stringify(packR.jumpWho)} / up ${JSON.stringify(packR.jumpYWho)}`);

console.log('--- 10. the pictures');
await ev(`ngv.game.clock.minute=20*60`);   // back to the middle of the night for the shots
await ev(`document.getElementById('crewBtn').click()`); await sleep(500);
const panelShot = await ev(`(()=>{const p=document.getElementById('crewPanel').getBoundingClientRect();
 return {on:!document.getElementById('crewPanel').hidden,inView:p.top>=0&&p.bottom<=window.innerHeight+1,rows:document.querySelectorAll('#crewTaskList button').length,
  minH:Math.min(...[...document.querySelectorAll('#crewTaskList button')].map(b=>Math.round(b.getBoundingClientRect().height)))}})()`);
say(panelShot.on && panelShot.rows === 5 && panelShot.minH >= 44, 'the Tasks tab: five rows, 44 px targets: ' + JSON.stringify(panelShot));
await shot('panel-tasks');
await ev(`(()=>{const b=document.querySelector('#crewTaskList [data-crew="0"]');if(b)b.click();})()`); await sleep(250);
await tap('#tsTasks [data-task="fit"]'); await sleep(350);
const fit8 = await ev(`(()=>{const sh=document.getElementById('taskSheet'),body=sh.querySelector('.tsbody');
 const btns=[...sh.querySelectorAll('button')];
 const r=sh.getBoundingClientRect(), last=btns[btns.length-1].getBoundingClientRect(), close=document.getElementById('tsClose').getBoundingClientRect();
 return {n:btns.length,minH:Math.min(...btns.map(b=>Math.round(b.getBoundingClientRect().height))),
  sheetIn:r.top>=-1&&r.bottom<=window.innerHeight+1, closeIn:close.top>=0&&close.bottom<=window.innerHeight+1,
  lastIn:last.bottom<=r.bottom+1, scrolls:body.scrollHeight>body.clientHeight+1, H:window.innerHeight}})()`);
say(fit8.sheetIn && fit8.closeIn, 'the whole sheet is on a 915 px screen and Close is reachable: ' + JSON.stringify(fit8));
say(fit8.lastIn || fit8.scrolls, 'every button is inside the card, or the card scrolls to it');
say(fit8.minH >= 44, 'every target is at least 44 px: ' + fit8.minH);
await shot('task-sheet-phone');
await tap('#tsClose'); await sleep(300);
say((await sheetUp()) === false, 'Close shuts the sheet');
await ev(`(()=>{const b=document.querySelector('#crewTaskList [data-crew="0"]');document.getElementById('crewBtn').click();if(b)b.click();})()`); await sleep(300);
await ev(`window.dispatchEvent(new KeyboardEvent('keydown',{code:'Escape'}))`); await sleep(300);
say((await sheetUp()) === false, 'Esc shuts it too');

console.log('--- 11. the status a player reads');
// the whole vocabulary, and nothing outside it: a new status has to be added HERE and to the
// AGENTS.md list on purpose, not slipped in (the skeptic's D4 found one that was neither)
const COL = '(N[1-6]|S[1-6])';
const SAYS = [
  'standing by', 'waiting for a lift', 'walking to the lift', 'stepping off the lift',
  `rolling to ${COL}`, `waiting for boards near ${COL}`, `fitting ${COL} \\(\\d+/\\d+\\)`,
  'fetching boxes', 'waiting for boxes', `feeding ${COL}`, `bringing the ${COL} pallet in`,
  `laying boards to (the hall|${COL})( \\(\\d+ to go\\))?`, 'bagging wrap', 'running rubbish',
  'helping you', 'putting the jack back', 'packing up', `taking the (${COL} pallet|ply) back`
].map((s) => new RegExp('^' + s + '$'));
const heard = Object.keys(await ev(`ngv.game._r.all`));
const odd = heard.filter((s) => !SAYS.some((re) => re.test(s)));
say(heard.length > 12, `the crew said ${heard.length} different things across every run`);
say(odd.length === 0, 'every one of them is in the declared list' + (odd.length ? ': NOT DECLARED ' + JSON.stringify(odd) : ''));

console.log(bad ? `${bad} FAIL` : 'all ok');
console.log(logs.join(String.fromCharCode(10)) || 'no errors');
ws.close(); process.exit(bad ? 1 : 0);
