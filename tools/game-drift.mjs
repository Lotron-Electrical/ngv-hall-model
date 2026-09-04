// drift check (Lloyd, 2026-09-04: "the camera is literally moving towards one of the walls"):
// with NO input, nothing may move: the player between two pallets by the wall, the player at the
// lift, the lift at rest with the controls held, the lift let go
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
ws.onmessage=e=>{ const m=JSON.parse(e.data); if(m.id&&pend[m.id]){pend[m.id](m.result);delete pend[m.id];} if(m.method==='Runtime.exceptionThrown')logs.push('EXC '+JSON.stringify(m.params.exceptionDetails).slice(0,300)); };
await new Promise(r=>ws.onopen=r);
const send=(method,params={})=>new Promise(r=>{ const i=++id; pend[i]=r; ws.send(JSON.stringify({id:i,method,params})); });
const ev=async expr=>{ const r=await send('Runtime.evaluate',{expression:expr,returnByValue:true,awaitPromise:true}); return r.result?r.result.value:r; };
const sleep=ms=>new Promise(r=>setTimeout(r,ms));
await send('Emulation.setDeviceMetricsOverride',{width:412,height:915,deviceScaleFactor:1.5,mobile:true});
await send('Page.enable'); await send('Runtime.enable'); await send('Page.navigate',{url});
await enter(ev,sleep);
await ev(`document.querySelector('#start').click()`); await sleep(400);
const P=()=>ev(`(()=>{const g=ngv.game;return [g.player.pos.x,g.player.pos.z,g.lift.pos.x,g.lift.pos.z].map(v=>+v.toFixed(3))})()`);
let bad=0;
const hold=async(name,secs=3)=>{ const a=await P(); await sleep(secs*1000); const b=await P(); const dp=Math.hypot(b[0]-a[0],b[1]-a[1]), dl=Math.hypot(b[2]-a[2],b[3]-a[3]); const ok=dp<0.01&&dl<0.01; if(!ok)bad++; console.log((ok?'ok  ':'DRIFT')+' '+name+'  player moved '+dp.toFixed(3)+' m, lift '+dl.toFixed(3)+' m in '+secs+' s'); };
// 1: between the first two N-row pallets, hard against the wall
await ev(`(()=>{const g=ngv.game;const h=g.items.pallets[0].home, k=g.items.pallets[1].home;const m=h.clone().add(k).multiplyScalar(0.5);g.player.pos.copy(g.hallToWorld(50.0,3.3,g.world.floorY));})()`); await sleep(300); await hold('player between pallets at the wall');
await ev(`(()=>{const g=ngv.game;g.player.pos.copy(g.hallToWorld(52.3,4.9,g.world.floorY));})()`); await sleep(300); await hold('player inside the pallet row');
// 2: lift squeezed between pallets, at rest with the controls held, then let go
await ev(`(()=>{const g=ngv.game,L=g.lift,P=g.player;L.pos.copy(g.hallToWorld(53.5,5.4,g.world.floorY));L.yaw=2.92;L.refresh();L.board(P,true);L.takeControls(P);})()`); await sleep(300); await hold('lift at rest, controls held, by the pallet row');
await ev(`ngv.game.lift.letGo()`); await sleep(300); await hold('lift let go, player on deck');
await ev(`(()=>{const g=ngv.game,L=g.lift,P=g.player;L.leave(P,true);})()`); await sleep(300); await hold('player just off the lift');
// 3: drive into a pallet and release: the lift must stop and stay
await ev(`(()=>{const g=ngv.game,L=g.lift,P=g.player;L.board(P,true);L.takeControls(P);L.yaw=2.92-Math.PI/2;L.refresh();P.keys.add('KeyW');})()`); await sleep(3000); await ev(`ngv.game.player.keys.delete('KeyW')`); await sleep(1500); await hold('lift after bumping a pallet and releasing');
console.log(bad?`${bad} DRIFT case(s)`:'no drift'); console.log(logs.join('\n')||'no errors');
ws.close(); process.exit(bad?1:0);
