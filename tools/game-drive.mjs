// lift check (2026-09-04): board, walk the deck to the controls, drive like a scissor lift
// (ramp, steer only while rolling, creep when raised, brake on release), let go, walk back, get off
import fs from 'node:fs';
const port=9333, url='http://127.0.0.1:8877/game.html?cb='+Date.now();
const tabs=await (await fetch(`http://127.0.0.1:${port}/json`)).json(); let t=tabs.find(x=>x.type==='page'); if(!t) t=await (await fetch(`http://127.0.0.1:${port}/json/new?about:blank`,{method:'PUT'})).json();
const ws=new WebSocket(t.webSocketDebuggerUrl); let id=0; const pend={}; const logs=[];
ws.onmessage=e=>{ const m=JSON.parse(e.data); if(m.id&&pend[m.id]){pend[m.id](m.result);delete pend[m.id];} if(m.method==='Runtime.exceptionThrown')logs.push('EXC '+JSON.stringify(m.params.exceptionDetails).slice(0,400)); if(m.method==='Runtime.consoleAPICalled'&&m.params.type==='error')logs.push('ERR '+JSON.stringify(m.params.args.map(a=>a.value||a.description)).slice(0,300)); };
await new Promise(r=>ws.onopen=r);
const send=(method,params={})=>new Promise(r=>{ const i=++id; pend[i]=r; ws.send(JSON.stringify({id:i,method,params})); });
const ev=async expr=>{ const r=await send('Runtime.evaluate',{expression:expr,returnByValue:true,awaitPromise:true}); return r.result?r.result.value:r; };
const sleep=ms=>new Promise(r=>setTimeout(r,ms));
const shot=async n=>{ const s=await send('Page.captureScreenshot',{format:'jpeg',quality:70}); fs.writeFileSync(process.env.TMP+`/drive-${n}.jpg`,Buffer.from(s.data,'base64')); };
await send('Emulation.setDeviceMetricsOverride',{width:412,height:915,deviceScaleFactor:1.5,mobile:true});
await send('Page.enable'); await send('Runtime.enable'); await send('Page.navigate',{url});
for(let i=0;i<30;i++){ await sleep(1000); if(await ev('!!window.game'))break; }
await ev(`localStorage.clear(); document.querySelector('#start').click()`); await sleep(400);
const prompt=()=>ev(`document.querySelector('#prompt').textContent`);
const act=async()=>{ await ev('window.game.player.actionQueued=true'); await sleep(150); };
const key=async(codes,ms)=>{ await ev(`for(const c of ${JSON.stringify(codes)}) window.game.player.keys.add(c)`); await sleep(ms); await ev(`for(const c of ${JSON.stringify(codes)}) window.game.player.keys.delete(c)`); };
const st=()=>ev(`(()=>{const L=window.game.lift,P=window.game.player;return {aboard:L.aboard,driving:L.driving,deck:[+L.deckLocal.x.toFixed(2),+L.deckLocal.y.toFixed(2)],speed:+L.speed.toFixed(2),steer:+L.steer.toFixed(2),yaw:+L.yaw.toFixed(2),pyaw:+P.yaw.toFixed(2),h:+L.height.toFixed(2),pos:[+L.pos.x.toFixed(2),+L.pos.z.toFixed(2)],ppos:[+P.pos.x.toFixed(2),+P.pos.y.toFixed(2),+P.pos.z.toFixed(2)]}})()`);
// stand at the back of the lift, looking along it
await ev(`(()=>{const g=window.game,L=g.lift;L.yaw=2.92;L.refresh();const o=L.offboardWorld();g.player.pos.set(o.x,g.world.floorY,o.z);g.player.yaw=1.35;g.player.pitch=0;})()`); await sleep(300);
console.log('1 prompt:', await prompt()); await act(); console.log('  ->', await prompt(), JSON.stringify(await st()));
await key(['KeyW'],1600); console.log('2 walked fwd:', await prompt(), JSON.stringify(await st()));
await key(['KeyD'],500); console.log('   strafed:', await prompt(), JSON.stringify(await st()));
await act(); console.log('3 took controls:', await prompt(), JSON.stringify(await st()));
await shot('controls');
await ev(`window.game.player.keys.add('KeyW')`); await sleep(600); console.log('4 ramp 0.6s speed', (await st()).speed); await sleep(2400); console.log('   3s:', JSON.stringify(await st()));
await ev(`window.game.player.keys.add('KeyD')`); await sleep(2500); console.log('5 steering:', JSON.stringify(await st()));
await ev(`window.game.player.keys.delete('KeyD');window.game.player.keys.delete('KeyW')`); await sleep(1500); console.log('6 released:', JSON.stringify(await st()));
await key(['KeyA'],1500); console.log('7 steer w/o drive (yaw must not change):', JSON.stringify(await st()));
await ev(`window.game.player.liftUp=true`); await sleep(3000); await ev(`window.game.player.liftUp=false`); console.log('8 raised:', JSON.stringify(await st()));
await key(['KeyW'],3000); console.log('9 creep at height:', JSON.stringify(await st()));
await shot('raised');
await ev(`window.game.player.liftDown=true`); await sleep(3500); await ev(`window.game.player.liftDown=false`);
await act(); console.log('10 let go:', await prompt(), JSON.stringify(await st()));
await key(['KeyS'],2500); console.log('11 walked back:', await prompt(), JSON.stringify(await st()));
await act(); console.log('12 got off:', await prompt(), JSON.stringify(await st()));
await ev(`(()=>{const g=window.game,L=g.lift;const P=g.player;P.pos.copy(L.pos.clone().add(new P.pos.constructor(3,0,3)));P.pos.y=g.world.floorY;P.yaw=Math.atan2(-(L.pos.x-P.pos.x),-(L.pos.z-P.pos.z));P.pitch=0.1;})()`); await sleep(400); await shot('outside');
console.log(logs.join('\n')||'no errors');
ws.close(); process.exit(0);
