import fs from 'node:fs';
const port=9333, url='http://127.0.0.1:8877/game.html?cb='+Date.now();
const tabs=await (await fetch(`http://127.0.0.1:${port}/json`)).json(); let t=tabs.find(x=>x.type==='page'); if(!t) t=await (await fetch(`http://127.0.0.1:${port}/json/new?about:blank`,{method:'PUT'})).json();
const ws=new WebSocket(t.webSocketDebuggerUrl); let id=0; const pend={}; const logs=[];
ws.onmessage=e=>{ const m=JSON.parse(e.data); if(m.id&&pend[m.id]){pend[m.id](m.result);delete pend[m.id];} if(m.method==='Runtime.exceptionThrown')logs.push('EXC '+JSON.stringify(m.params.exceptionDetails).slice(0,300)); };
await new Promise(r=>ws.onopen=r);
const send=(method,params={})=>new Promise(r=>{ const i=++id; pend[i]=r; ws.send(JSON.stringify({id:i,method,params})); });
const ev=async expr=>{ const r=await send('Runtime.evaluate',{expression:expr,returnByValue:true,awaitPromise:true}); return r.result?r.result.value:r; };
const sleep=ms=>new Promise(r=>setTimeout(r,ms));
const shot=async n=>{ const s=await send('Page.captureScreenshot',{format:'jpeg',quality:70}); fs.writeFileSync(process.env.TMP+`/look2-${n}.jpg`,Buffer.from(s.data,'base64')); };
await send('Emulation.setDeviceMetricsOverride',{width:412,height:915,deviceScaleFactor:1.5,mobile:true});
await send('Emulation.setTouchEmulationEnabled',{enabled:true});
await send('Page.enable'); await send('Runtime.enable'); await send('Page.navigate',{url});
for(let i=0;i<30;i++){ await sleep(1000); if(await ev('!!window.game'))break; }
await ev(`document.querySelector('#start').click()`); await sleep(300);
const place=async(u,d,lookU,lookD,pitch=0)=>ev(`(()=>{const g=window.game,P=g.player; P.pos.copy(g.hallToWorld(${u},${d},g.world.floorY)); const T=g.hallToWorld(${lookU},${lookD},g.world.floorY+1.6); P.yaw=Math.atan2(-(T.x-P.pos.x),-(T.z-P.pos.z)); P.pitch=${pitch};})()`);
// lift in the hall at 6 m, seen from 9 m
await ev(`(()=>{const g=window.game; g.lift.pos.copy(g.hallToWorld(40,7.5,g.world.floorY)); g.lift.height=6; g.lift.refresh();})()`);
await place(31,7.5,40,7.5,0.35); await sleep(400); await shot('lift-hall');
await ev(`(()=>{const g=window.game; g.lift.height=0; g.lift.refresh();})()`); await place(36,7.5,40,7.5,-0.05); await sleep(400); await shot('lift-down');
// the doors: from the hall side 5 m off
await place(44,7.5,48.9,7.5); await sleep(2000); await shot('door-hall'); console.log('shut at 5m', await ev('window.game.world.doorsShut'));
// walk through: hold the move stick up for 5 s from 4 m out
const r=JSON.parse(await ev(`JSON.stringify(document.querySelector('#move').getBoundingClientRect())`)); const cx=r.x+r.width/2, cy=r.y+r.height/2;
await place(45,7.5,48.9,7.5);
await send('Input.dispatchTouchEvent',{type:'touchStart',touchPoints:[{x:cx,y:cy,id:1}]}); await send('Input.dispatchTouchEvent',{type:'touchMove',touchPoints:[{x:cx,y:cy-40,id:1}]});
await sleep(1500); await shot('door-approach'); await sleep(2500); await send('Input.dispatchTouchEvent',{type:'touchEnd',touchPoints:[]});
console.log('after walk u=', await ev(`(()=>{const g=window.game,P=g.player; const v=P.pos.clone().sub(g.world.HALL?g.world.HALL.origin:new g.player.pos.constructor(-54.907447,-1.43545,3.040286)); return (v.x*0.975681+v.z*0.219196).toFixed(2);})()`));
await shot('door-through');
console.log(logs.join('\n')||'no errors');
ws.close(); process.exit(0);
