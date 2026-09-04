// lift look (2026-09-04): screenshots of the stowed lift from the back quarter, and a frame mid-climb
import fs from 'node:fs';
const port=9333, url='http://127.0.0.1:8877/game.html?cb='+Date.now();
const tabs=await (await fetch(`http://127.0.0.1:${port}/json`)).json(); let t=tabs.find(x=>x.type==='page'); if(!t) t=await (await fetch(`http://127.0.0.1:${port}/json/new?about:blank`,{method:'PUT'})).json();
const ws=new WebSocket(t.webSocketDebuggerUrl); let id=0; const pend={}; const logs=[];
ws.onmessage=e=>{ const m=JSON.parse(e.data); if(m.id&&pend[m.id]){pend[m.id](m.result);delete pend[m.id];} if(m.method==='Runtime.exceptionThrown')logs.push('EXC '+JSON.stringify(m.params.exceptionDetails).slice(0,400)); };
await new Promise(r=>ws.onopen=r);
const send=(method,params={})=>new Promise(r=>{ const i=++id; pend[i]=r; ws.send(JSON.stringify({id:i,method,params})); });
const ev=async expr=>{ const r=await send('Runtime.evaluate',{expression:expr,returnByValue:true,awaitPromise:true}); return r.result?r.result.value:r; };
const sleep=ms=>new Promise(r=>setTimeout(r,ms));
const out=process.argv[2]||process.env.TMP;
const shot=async n=>{ const s=await send('Page.captureScreenshot',{format:'jpeg',quality:75}); fs.writeFileSync(`${out}/lift-${n}.jpg`,Buffer.from(s.data,'base64')); };
await send('Emulation.setDeviceMetricsOverride',{width:900,height:600,deviceScaleFactor:1,mobile:false});
await send('Page.enable'); await send('Runtime.enable'); await send('Page.navigate',{url});
for(let i=0;i<30;i++){ await sleep(1000); if(await ev('!!window.game'))break; }
await ev(`localStorage.clear(); document.querySelector('#start').click()`); await sleep(400);
// stand behind and to the side of the parked lift, looking at its back end
await ev(`(()=>{const g=window.game,L=g.lift,P=g.player;L.yaw=2.92;L.refresh();const o=L.group.localToWorld(new P.pos.constructor(-4.2,0,2.6));P.pos.set(o.x,g.world.floorY,o.z);P.yaw=Math.atan2(-(L.pos.x-P.pos.x),-(L.pos.z-P.pos.z));P.pitch=-0.05;})()`); await sleep(400); await shot('back');
// raised a little so the stack shows
await ev(`(()=>{const L=window.game.lift;L.height=1.2;L.refresh();})()`); await sleep(300); await shot('raised');
await ev(`(()=>{const L=window.game.lift;L.height=0;L.refresh();})()`);
// mid-climb: board from the foot and freeze on the tread
await ev(`(()=>{const g=window.game,L=g.lift,P=g.player;const o=L.offboardWorld();P.pos.set(o.x,g.world.floorY,o.z);P.yaw=L.yaw-Math.PI/2;P.pitch=-0.2;P.actionQueued=true;})()`); await sleep(2300); await shot('midclimb');
// the open gate from the deck side
await ev(`(()=>{const g=window.game,L=g.lift,P=g.player;L.anim=null;L.aboard=true;P.onLift=true;L.gate.rotation.y=1.2;L.aboard=false;P.onLift=false;const o=L.group.localToWorld(new P.pos.constructor(-3.2,0,1.2));P.pos.set(o.x,g.world.floorY,o.z);P.eye=1.68;P.yaw=L.yaw-Math.PI/2+0.35;P.pitch=0.05;})()`); await sleep(300); await shot('gateopen');
await ev(`(()=>{const g=window.game,L=g.lift,P=g.player;L.gate.rotation.y=0;L.aboard=false;P.onLift=false;const o=L.offboardWorld();P.pos.set(o.x,g.world.floorY,o.z);P.yaw=L.yaw-Math.PI/2;P.pitch=-0.2;P.actionQueued=true;})()`);
await sleep(2500); await shot('aboard');
console.log(logs.join('\n')||'no errors');
ws.close(); process.exit(0);
