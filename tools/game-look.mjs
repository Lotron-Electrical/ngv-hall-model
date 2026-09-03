// visual checks: the lift from the corridor, the doors swinging, the small hours
import fs from 'node:fs';
const port=9333, url='http://127.0.0.1:8877/game.html?cb='+Date.now();
const tabs=await (await fetch(`http://127.0.0.1:${port}/json`)).json(); let t=tabs.find(x=>x.type==='page'); if(!t) t=await (await fetch(`http://127.0.0.1:${port}/json/new?about:blank`,{method:'PUT'})).json();
const ws=new WebSocket(t.webSocketDebuggerUrl); let id=0; const pend={}; const logs=[];
ws.onmessage=e=>{ const m=JSON.parse(e.data); if(m.id&&pend[m.id]){pend[m.id](m.result);delete pend[m.id];} if(m.method==='Runtime.exceptionThrown')logs.push('EXC '+JSON.stringify(m.params.exceptionDetails).slice(0,300)); };
await new Promise(r=>ws.onopen=r);
const send=(method,params={})=>new Promise(r=>{ const i=++id; pend[i]=r; ws.send(JSON.stringify({id:i,method,params})); });
const ev=async expr=>{ const r=await send('Runtime.evaluate',{expression:expr,returnByValue:true,awaitPromise:true}); return r.result?r.result.value:r; };
const sleep=ms=>new Promise(r=>setTimeout(r,ms));
const shot=async n=>{ const s=await send('Page.captureScreenshot',{format:'jpeg',quality:70}); fs.writeFileSync(process.env.TMP+`/look-${n}.jpg`,Buffer.from(s.data,'base64')); };
await send('Emulation.setDeviceMetricsOverride',{width:412,height:915,deviceScaleFactor:1.5,mobile:true});
await send('Page.enable'); await send('Runtime.enable'); await send('Page.navigate',{url});
for(let i=0;i<30;i++){ await sleep(1000); if(await ev('!!window.game'))break; }
await ev(`document.querySelector('#start').click()`); await sleep(300);
// (1) stand 4 m from the lift, look at it
await ev(`(()=>{const g=window.game, L=g.lift.pos, P=g.player; P.pos.set(L.x+3.5,g.world.floorY,L.z+2.5); P.yaw=Math.atan2(-(L.x-P.pos.x),-(L.z-P.pos.z)); P.pitch=-0.1;})()`); await sleep(400); await shot('lift');
// (2) raise the lift to 6 m and look from further
await ev(`(()=>{const g=window.game; g.lift.height=6; g.lift.refresh(); const L=g.lift.pos, P=g.player; P.pos.set(L.x+7,g.world.floorY,L.z+5); P.yaw=Math.atan2(-(L.x-P.pos.x),-(L.z-P.pos.z)); P.pitch=0.35;})()`); await sleep(400); await shot('lift-up');
// (3) the doors: stand 6 m off in the corridor looking at them, then step up to 2 m
await ev(`(()=>{const g=window.game; g.lift.height=0; g.lift.refresh(); const {hallToWorld}=g; })()`);
await ev(`(()=>{const g=window.game, D=g.world.doorCentre, P=g.player; const u=g.world.HALL||null; P.pos.copy(D); P.pos.x+=6*0.975681; P.pos.z+=6*0.219196; P.yaw=Math.atan2(-(D.x-P.pos.x),-(D.z-P.pos.z)); P.pitch=0;})()`); await sleep(1500); await shot('doors-shut');
console.log('shut?', await ev('window.game.world.doorsShut'));
await ev(`(()=>{const g=window.game, D=g.world.doorCentre, P=g.player; P.pos.copy(D); P.pos.x+=2.2*0.975681; P.pos.z+=2.2*0.219196;})()`); await sleep(1500); await shot('doors-open');
console.log('shut after approach?', await ev('window.game.world.doorsShut'));
// (4) the small hours: 04:20, from the hall floor looking down the hall
await ev(`(()=>{const g=window.game; g.clock.minute=28.33*60; const P=g.player; const p=g.world.doorCentre.clone(); P.pos.set(p.x-10*0.975681,g.world.floorY,p.z-10*0.219196); P.yaw=Math.PI/2+0.2; P.pitch=0.1;})()`); await sleep(2500); await shot('late');
console.log('fx level', await ev('window.game.fx.level'), 'hud', await ev(`document.querySelector('#stats').innerText.replace(/\n/g,' | ')`));
console.log(logs.join('\n')||'no errors');
ws.close(); process.exit(0);
