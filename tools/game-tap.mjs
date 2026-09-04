// prompt-as-button check (2026-09-04): on a phone the prompt sits on the right, and a TAP on it runs the action
import fs from 'node:fs';
const port=9333, url='http://127.0.0.1:8877/game.html?cb='+Date.now();
const tabs=await (await fetch(`http://127.0.0.1:${port}/json`)).json(); let t=tabs.find(x=>x.type==='page'); if(!t) t=await (await fetch(`http://127.0.0.1:${port}/json/new?about:blank`,{method:'PUT'})).json();
const ws=new WebSocket(t.webSocketDebuggerUrl); let id=0; const pend={}; const logs=[];
ws.onmessage=e=>{ const m=JSON.parse(e.data); if(m.id&&pend[m.id]){pend[m.id](m.result);delete pend[m.id];} if(m.method==='Runtime.exceptionThrown')logs.push('EXC '+JSON.stringify(m.params.exceptionDetails).slice(0,400)); };
await new Promise(r=>ws.onopen=r);
const send=(method,params={})=>new Promise(r=>{ const i=++id; pend[i]=r; ws.send(JSON.stringify({id:i,method,params})); });
const ev=async expr=>{ const r=await send('Runtime.evaluate',{expression:expr,returnByValue:true,awaitPromise:true}); return r.result?r.result.value:r; };
const sleep=ms=>new Promise(r=>setTimeout(r,ms));
await send('Emulation.setDeviceMetricsOverride',{width:412,height:915,deviceScaleFactor:1.5,mobile:true});
await send('Emulation.setTouchEmulationEnabled',{enabled:true});
await send('Page.enable'); await send('Runtime.enable'); await send('Page.navigate',{url});
for(let i=0;i<30;i++){ await sleep(1000); if(await ev('!!window.game'))break; }
await ev(`localStorage.clear(); document.querySelector('#start').click()`); await sleep(400);
await ev(`(()=>{const g=window.game,L=g.lift;const o=L.offboardWorld();g.player.pos.set(o.x,g.world.floorY,o.z);g.player.yaw=1.35;})()`); await sleep(300);
const box=await ev(`(()=>{const r=document.querySelector('#prompt').getBoundingClientRect();return {x:r.x,y:r.y,w:r.width,h:r.height,right:innerWidth-r.right,text:document.querySelector('#prompt').textContent,action:!!document.querySelector('#action')}})()`);
console.log('prompt box', JSON.stringify(box));
if(box.action) console.log('FAIL: #action still in the DOM');
if(box.x < innerWidthGuess(412)/2) console.log('FAIL: prompt not on the right half');
function innerWidthGuess(w){return w}
const cx=box.x+box.w/2, cy=box.y+box.h/2;
await send('Input.dispatchTouchEvent',{type:'touchStart',touchPoints:[{x:cx,y:cy}]}); await sleep(60);
await send('Input.dispatchTouchEvent',{type:'touchEnd',touchPoints:[]}); await sleep(400);
const after=await ev(`({aboard:window.game.lift.aboard,text:document.querySelector('#prompt').textContent})`);
console.log('after tap', JSON.stringify(after), after.aboard?'ok  tap ran the action':'FAIL: tap did not run the action');
const s=await send('Page.captureScreenshot',{format:'jpeg',quality:70}); fs.writeFileSync(process.env.TMP+'/tap.jpg',Buffer.from(s.data,'base64'));
console.log(logs.join('\n')||'no errors');
ws.close(); process.exit(0);
