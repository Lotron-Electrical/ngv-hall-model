// touch check: hold the move stick up for 2 s and the look stick right for 1 s, report the player
const port=9333, url='http://127.0.0.1:8877/game.html?cb='+Date.now();
const tabs=await (await fetch(`http://127.0.0.1:${port}/json`)).json(); let t=tabs.find(x=>x.type==='page'); if(!t) t=await (await fetch(`http://127.0.0.1:${port}/json/new?about:blank`,{method:'PUT'})).json();
const ws=new WebSocket(t.webSocketDebuggerUrl); let id=0; const pend={}; const logs=[];
ws.onmessage=e=>{ const m=JSON.parse(e.data); if(m.id&&pend[m.id]){pend[m.id](m.result);delete pend[m.id];} if(m.method==='Runtime.exceptionThrown')logs.push('EXC '+JSON.stringify(m.params.exceptionDetails).slice(0,300)); };
await new Promise(r=>ws.onopen=r);
const send=(method,params={})=>new Promise(r=>{ const i=++id; pend[i]=r; ws.send(JSON.stringify({id:i,method,params})); });
const ev=async expr=>{ const r=await send('Runtime.evaluate',{expression:expr,returnByValue:true,awaitPromise:true}); return r.result?r.result.value:r; };
const sleep=ms=>new Promise(r=>setTimeout(r,ms));
await send('Emulation.setDeviceMetricsOverride',{width:412,height:915,deviceScaleFactor:2,mobile:true});
await send('Emulation.setTouchEmulationEnabled',{enabled:true});
await send('Page.enable'); await send('Runtime.enable'); await send('Page.navigate',{url});
for(let i=0;i<30;i++){ await sleep(1000); if(await ev('!!window.game'))break; }
await ev(`document.querySelector('#start').click()`); await sleep(500);
const rect=async sel=>JSON.parse(await ev(`JSON.stringify(document.querySelector('${sel}').getBoundingClientRect())`));
const hold=async(sel,dx,dy,ms)=>{ const r=await rect(sel); const cx=r.x+r.width/2, cy=r.y+r.height/2;
 await send('Input.dispatchTouchEvent',{type:'touchStart',touchPoints:[{x:cx,y:cy,id:1}]});
 await send('Input.dispatchTouchEvent',{type:'touchMove',touchPoints:[{x:cx+dx,y:cy+dy,id:1}]});
 await sleep(ms); await send('Input.dispatchTouchEvent',{type:'touchEnd',touchPoints:[]}); };
const state=async()=>JSON.parse(await ev(`JSON.stringify({x:+window.game.player.pos.x.toFixed(2),z:+window.game.player.pos.z.toFixed(2),yaw:+window.game.player.yaw.toFixed(2),move:window.game.player.move,look:window.game.player.look})`));
console.log('before', await state());
await hold('#move',0,-40,2000); console.log('after move', await state());
await hold('#look',40,0,1000); console.log('after look', await state());
console.log(logs.join('\n')||'no errors');
ws.close(); process.exit(0);
