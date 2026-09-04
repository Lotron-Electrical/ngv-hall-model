// floor check (Lloyd, 2026-09-04: "the wheels are clipping into the floor"): the scanned floor
// is levelled at load (world.js levelScan). This samples the real floor surface under a grid of
// hall points and under each lift wheel, and fails if any lift part sits below the surface it
// stands on, stowed, raised, and after a drive into the hall. Needs the :8877 serve and
// headless Chrome on :9333 (bash ~/scripts/headless-chrome.sh start 9333).
const port=9333, url='http://127.0.0.1:8877/game.html?cb='+Date.now();
const tabs=await (await fetch(`http://127.0.0.1:${port}/json`)).json(); let t=tabs.find(x=>x.type==='page'); if(!t) t=await (await fetch(`http://127.0.0.1:${port}/json/new?about:blank`,{method:'PUT'})).json();
const ws=new WebSocket(t.webSocketDebuggerUrl); let id=0; const pend={}; const logs=[];
ws.onmessage=e=>{ const m=JSON.parse(e.data); if(m.id&&pend[m.id]){pend[m.id](m.result);delete pend[m.id];} if(m.method==='Runtime.exceptionThrown')logs.push('EXC '+JSON.stringify(m.params.exceptionDetails).slice(0,400)); };
await new Promise(r=>ws.onopen=r);
const send=(method,params={})=>new Promise(r=>{ const i=++id; pend[i]=r; ws.send(JSON.stringify({id:i,method,params})); });
const ev=async expr=>{ const r=await send('Runtime.evaluate',{expression:expr,returnByValue:true,awaitPromise:true}); return r.result?r.result.value:r; };
const sleep=ms=>new Promise(r=>setTimeout(r,ms));
await send('Page.enable'); await send('Runtime.enable'); await send('Network.enable'); await send('Network.setCacheDisabled',{cacheDisabled:true}); await send('Page.navigate',{url});
for(let i=0;i<30;i++){ await sleep(1000); if(await ev('!!window.game'))break; }
await ev(`localStorage.clear(); document.querySelector('#start').click()`); await sleep(400);
const report=JSON.parse(await ev(`(async()=>{const T=await import('three');const g=window.game;const scene=g.lift.group.parent;const out={floorY:g.world.floorY,levelling:null,hall:{min:1e9,max:-1e9,n:0},lift:{}};
try{const W=await import('./game/world.js');out.levelling=W.scanLevelling();}catch(e){out.levelling='n/a '+e.message;}
const ground=[];scene.traverse(o=>{if(o.isMesh&&o.visible&&!g.lift.group.getObjectById(o.id))ground.push(o);});
const floorAt=(x,z)=>{const rc=new T.Raycaster(new T.Vector3(x,g.world.floorY+0.6,z),new T.Vector3(0,-1,0));const hs=rc.intersectObjects(ground,false).filter(h=>Math.abs(h.point.y-g.world.floorY)<0.35);return hs.length?hs[hs.length-1].point.y:null;};
for(let u=2;u<=64;u+=2)for(let d=2.5;d<=12.5;d+=1.25){const p=g.hallToWorld(u,d,0);const y=floorAt(p.x,p.z);if(y==null)continue;out.hall.n++;out.hall.min=Math.min(out.hall.min,y);out.hall.max=Math.max(out.hall.max,y);}
const liftCheck=()=>{g.lift.group.updateMatrixWorld(true);let worst=1e9,part='';const b=new T.Box3();g.lift.group.traverse(o=>{if(!o.isMesh)return;b.setFromObject(o);const c=new T.Vector3();b.getCenter(c);const f=floorAt(c.x,c.z);if(f==null)return;const gap=b.min.y-f;if(gap<worst){worst=gap;part=o.name||o.geometry.type;}});return {worst:+worst.toFixed(4),part};};
g.lift.height=0;g.lift.refresh();out.lift.stowed=liftCheck();
g.lift.height=1.5;g.lift.refresh();out.lift.raised=liftCheck();g.lift.height=0;g.lift.refresh();
// park it in the hall proper, on the scan
const save=g.lift.pos.clone();g.lift.pos.copy(g.hallToWorld(30,7.5,g.world.floorY));g.lift.refresh();out.lift.inHall=liftCheck();g.lift.pos.copy(save);g.lift.refresh();
return JSON.stringify(out);})()`));
console.log(JSON.stringify(report,null,1));
const dev=Math.max(Math.abs(report.hall.max-report.floorY),Math.abs(report.hall.min-report.floorY));
const bad=[];
if(report.hall.n<50)bad.push('too few floor samples '+report.hall.n);
if(dev>0.02)bad.push('floor surface deviates '+dev.toFixed(3)+' m from floorY');
for(const k of ['stowed','raised','inHall']){const r=report.lift[k];if(!r||r.worst<-0.001)bad.push(`lift ${k}: ${r&&r.part} is ${r&&r.worst} m below the floor`);}
console.log(logs.join('\n')||'no errors');
console.log(bad.length?'FAIL\n'+bad.join('\n'):'PASS: floor level within '+dev.toFixed(3)+' m, no lift part below the floor');
ws.close(); process.exit(bad.length?1:0);
