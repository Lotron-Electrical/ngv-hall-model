import fs from 'node:fs';
// (2026-09-04) the game is a mode of the proposal sim now, not a page of its own: ?install=<key>
// stores the key and reloads clean, then the Install row's checkbox builds it. See AGENTS.md.
const enter=async(ev,sleep)=>{
 for(let i=0;i<40;i++){ await sleep(500); if(await ev('!!(window.ngv&&window.ngv.hall&&document.getElementById("install"))'))break; }
 await ev(`localStorage.clear(); localStorage.setItem('ngv.install','gandel-2026'); document.getElementById('install').click()`);
 for(let i=0;i<40;i++){ await sleep(500); if(await ev('!!(window.ngv&&window.ngv.game)'))break; }
};
const port=9333, url='http://127.0.0.1:8877/index.html?install=gandel-2026&cb='+Date.now();
const tabs=await (await fetch(`http://127.0.0.1:${port}/json`)).json(); let t=tabs.find(x=>x.type==='page'); if(!t) t=await (await fetch(`http://127.0.0.1:${port}/json/new?about:blank`,{method:'PUT'})).json();
const ws=new WebSocket(t.webSocketDebuggerUrl); let id=0; const pend={}; const logs=[];
ws.onmessage=e=>{ const m=JSON.parse(e.data); if(m.id&&pend[m.id]){pend[m.id](m.result);delete pend[m.id];} if(m.method==='Runtime.exceptionThrown')logs.push('EXC '+JSON.stringify(m.params.exceptionDetails).slice(0,400)); if(m.method==='Runtime.consoleAPICalled')logs.push(m.params.type+' '+m.params.args.map(a=>a.value||a.description).join(' ').slice(0,300)); };
await new Promise(r=>ws.onopen=r);
const send=(method,params={})=>new Promise(r=>{ const i=++id; pend[i]=r; ws.send(JSON.stringify({id:i,method,params})); });
const ev=async expr=>{ const r=await send('Runtime.evaluate',{expression:expr,returnByValue:true,awaitPromise:true}); return r.result?r.result.value:r; };
const sleep=ms=>new Promise(r=>setTimeout(r,ms));
await send('Emulation.setDeviceMetricsOverride',{width:412,height:915,deviceScaleFactor:2,mobile:true});
await send('Emulation.setTouchEmulationEnabled',{enabled:true});
await send('Page.enable'); await send('Runtime.enable'); await send('Page.navigate',{url});
await enter(ev,sleep);
await sleep(3000);
console.log('title', await ev('document.title'), 'body', (await ev('document.body.innerText')).slice(0,400).replace(/\n/g,' | '));
let s=await send('Page.captureScreenshot',{format:'jpeg',quality:70}); fs.writeFileSync(process.env.TMP+'/game-0.jpg',Buffer.from(s.data,'base64'));
// try to start
// the shift's own Start card, by id: the sim page has its own "Start again" button and a loose
// text match picked that one up instead (2026-09-04)
await ev(`(()=>{const b=document.querySelector('#installUi #start'); if(b)b.click(); return b?b.textContent:'no start button';})()`).then(v=>console.log('start:',v));
await sleep(3000);
s=await send('Page.captureScreenshot',{format:'jpeg',quality:70}); fs.writeFileSync(process.env.TMP+'/game-1.jpg',Buffer.from(s.data,'base64'));
console.log(logs.join('\n')||'no console output');
ws.close(); process.exit(0);
