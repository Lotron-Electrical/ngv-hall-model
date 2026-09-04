// crew check: complete N1 by script (helper joins), then N2 (a team joins); watch both work
import fs from 'node:fs';
// (2026-09-04) the game is a mode of the proposal sim now, not a page of its own: ?install=<key>
// stores the key and reloads clean, then the Install row's checkbox builds it. See AGENTS.md.
const enter=async(ev,sleep)=>{
 for(let i=0;i<40;i++){ await sleep(500); if(await ev('!!(window.ngv&&window.ngv.hall&&document.getElementById("install"))'))break; }
 await ev(`localStorage.clear(); localStorage.setItem('ngv.install','gandel-2026'); document.getElementById('install').click()`);
 for(let i=0;i<40;i++){ await sleep(500); if(await ev('!!(window.ngv&&window.ngv.game)'))break; }
};
const port = 9333, url='http://127.0.0.1:8877/index.html?install=gandel-2026&cb='+Date.now();
const tabs=await (await fetch(`http://127.0.0.1:${port}/json`)).json(); let t=tabs.find(x=>x.type==='page'); if(!t) t=await (await fetch(`http://127.0.0.1:${port}/json/new?about:blank`,{method:'PUT'})).json();
const ws=new WebSocket(t.webSocketDebuggerUrl); let id=0; const pend={}; const logs=[];
ws.onmessage=e=>{ const m=JSON.parse(e.data); if(m.id&&pend[m.id]){pend[m.id](m.result);delete pend[m.id];} if(m.method==='Runtime.exceptionThrown')logs.push('EXC '+JSON.stringify(m.params.exceptionDetails).slice(0,400)); };
await new Promise(r=>ws.onopen=r);
const send=(method,params={})=>new Promise(r=>{ const i=++id; pend[i]=r; ws.send(JSON.stringify({id:i,method,params})); });
const ev=async expr=>{ const r=await send('Runtime.evaluate',{expression:expr,returnByValue:true,awaitPromise:true}); return r.result?r.result.value:r; };
const sleep=ms=>new Promise(r=>setTimeout(r,ms));
const shot=async n=>{ const s=await send('Page.captureScreenshot',{format:'jpeg',quality:70}); fs.writeFileSync(process.env.TMP+`/crew-${n}.jpg`,Buffer.from(s.data,'base64')); };
await send('Emulation.setDeviceMetricsOverride',{width:412,height:915,deviceScaleFactor:1.5,mobile:true});
await send('Page.enable'); await send('Runtime.enable'); await send('Page.navigate',{url});
await enter(ev,sleep);
await ev(`document.querySelector('#start').click()`); await sleep(400);
const fitColumn=(c)=>ev(`(()=>{const g=ngv.game; for(const s of g.install.slots){ if(s.column==='${c}'&&!g.install.fitted.has(s.id)) g.install.fit(s,{carry:null}); } return g.install.counts();})()`);
const hd=async(expr)=>ev(`(()=>{const g=ngv.game; const p=${expr}; const v=p.clone().sub(new g.player.pos.constructor(-54.907447,-1.43545,3.040286)); return [+(v.x*0.975681+v.z*0.219196).toFixed(1),+(v.x*0.219186-v.z*0.975639).toFixed(1)];})()`);
console.log('N1 done ->', JSON.stringify(await fitColumn('N1')));
// park the player's lift at N2's foot, down, so the helper works N2
await ev(`(()=>{const g=ngv.game; g.lift.pos.copy(g.hallToWorld(14.9,6.2,g.world.floorY)); g.lift.height=0; g.lift.refresh(); g.player.pos.copy(g.hallToWorld(17,7.5,g.world.floorY)); g.player.yaw=1.35;})()`);
await sleep(1500); console.log('helper', await ev('ngv.game.crew.helper&&ngv.game.crew.helper.name'), 'at', await hd('g.crew.helper.pos'), 'toast:', await ev(`document.querySelector('#toast').textContent`));
await sleep(2000); const f0=await ev('ngv.game.dbg.frames'); await sleep(3000); console.log('fps', ((await ev('ngv.game.dbg.frames'))-f0)/3, 'dt', await ev('ngv.game.dbg.dt'));
for(const s of [6,12,18,24,30]){ await sleep(6000); console.log('t+'+s, 'helper at', await hd('g.crew.helper.pos'), 'jack', await ev('!!ngv.game.crew.helper.jack'), 'carry', await ev('ngv.game.crew.helper.carry&&ngv.game.crew.helper.carry.type'), 'N2 pallet at', await hd('g.items.pallets[1].mesh.position'), 'deck box', await ev('!!ngv.game.lift.box')); }
await ev(`(()=>{const g=ngv.game; const H=g.crew.helper; g.player.pos.copy(H.pos.clone().add(new g.player.pos.constructor(2.5,0,2))); g.player.pos.y=g.world.floorY; g.player.yaw=Math.atan2(-(H.pos.x-g.player.pos.x),-(H.pos.z-g.player.pos.z)); g.player.pitch=0;})()`); await sleep(300); await shot('helper');
console.log('N2 done ->', JSON.stringify(await fitColumn('N2'))); await sleep(1500);
console.log('teams', await ev('ngv.game.crew.teams.length'), 'toast:', await ev(`document.querySelector('#toast').textContent`));
for(const s of [10,20,30,45,60]){ await sleep(s===10?10000:s===45?15000:10000); console.log('t+'+s, 'team col', await ev('ngv.game.crew.teams[0].column&&ngv.game.crew.teams[0].column.label'), 'lift at', await hd('g.crew.teams[0].lift.pos'), 'h', await ev('ngv.game.crew.teams[0].lift.height.toFixed(1)'), 'fitted', await ev('ngv.game.install.counts().fitted'), 'feeder at', await hd('g.crew.teams[0].b.pos'), 'bjack', await ev('!!ngv.game.crew.teams[0].b.jack'), 'S6 pallet', await hd('g.items.pallets[11].mesh.position'), 'box', await ev('ngv.game.crew.teams[0].box')); }
await ev(`(()=>{const g=ngv.game; const L=g.crew.teams[0].lift.pos; g.player.pos.copy(g.hallToWorld(7.5+ (L?0:0),7.5,g.world.floorY)); const P=g.player; P.pos.copy(L.clone().add(new P.pos.constructor(6,0,4))); P.pos.y=g.world.floorY; P.yaw=Math.atan2(-(L.x-P.pos.x),-(L.z-P.pos.z)); P.pitch=0.25;})()`); await sleep(300); await shot('team');
console.log(logs.join('\n')||'no errors');
ws.close(); process.exit(0);
