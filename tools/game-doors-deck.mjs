// (Lloyd, 2026-09-06) doors that cannot be clipped through, the STORAGE sign, the column tags, the
// deck as a fenced tray, the ceiling cap on the lift, the height readout, the proximity ring, the
// reticle-driven prompt and pick-up from the deck. Serve on :8877, headless Chrome on :9333.
//   node tools/game-doors-deck.mjs <outdir>     (writes sign / tag / lift-top / prox / deck-drop / aboard-pick jpgs)
import fs from 'node:fs';
const out = process.argv[2] || '.';
fs.mkdirSync(out, { recursive: true });
const enter=async(ev,sleep)=>{
 for(let i=0;i<40;i++){ await sleep(500); if(await ev('!!(window.ngv&&window.ngv.hall&&document.getElementById("install"))'))break; }
 await ev(`localStorage.clear(); localStorage.setItem('ngv.install','gandel-2026'); document.getElementById('install').click()`);
 for(let i=0;i<40;i++){ await sleep(500); if(await ev('!!(window.ngv&&window.ngv.game)'))break; }
};
const port = 9333, url='http://127.0.0.1:8877/index.html?install=gandel-2026&cb='+Date.now();
const tabs=await (await fetch(`http://127.0.0.1:${port}/json`)).json(); let t=tabs.find(x=>x.type==='page'); if(!t) t=await (await fetch(`http://127.0.0.1:${port}/json/new?about:blank`,{method:'PUT'})).json();
const ws=new WebSocket(t.webSocketDebuggerUrl); let id=0; const pend={}; const logs=[];
ws.onmessage=e=>{ const m=JSON.parse(e.data); if(m.id&&pend[m.id]){pend[m.id](m.result);delete pend[m.id];} if(m.method==='Runtime.exceptionThrown')logs.push('EXC '+JSON.stringify(m.params.exceptionDetails.stackTrace?m.params.exceptionDetails.stackTrace.callFrames.map(f=>f.functionName+' '+f.url.split('/').pop()+':'+f.lineNumber):m.params.exceptionDetails).slice(0,900)); if(m.method==='Runtime.consoleAPICalled'&&m.params.type==='error')logs.push('ERR '+JSON.stringify(m.params.args.map(a=>a.value||a.description)).slice(0,300)); };
await new Promise(r=>ws.onopen=r);
const send=(method,params={})=>new Promise(r=>{ const i=++id; pend[i]=r; ws.send(JSON.stringify({id:i,method,params})); });
const ev=async expr=>{ const r=await send('Runtime.evaluate',{expression:expr,returnByValue:true,awaitPromise:true}); if(!r) return undefined; if(r.exceptionDetails) return 'EVALERR '+JSON.stringify(r.exceptionDetails).slice(0,300); return r.result?r.result.value:r; };
const sleep=ms=>new Promise(r=>setTimeout(r,ms));
const shot=async n=>{ const s=await send('Page.captureScreenshot',{format:'jpeg',quality:80}); fs.writeFileSync(`${out}/${n}.jpg`,Buffer.from(s.data,'base64')); };
await send('Network.enable'); await send('Network.setCacheDisabled',{cacheDisabled:true});
await send('Emulation.setDeviceMetricsOverride',{width:412,height:915,deviceScaleFactor:1.5,mobile:true});
await send('Page.enable'); await send('Runtime.enable'); await send('Page.navigate',{url});
await enter(ev,sleep);
await ev(`document.querySelector('#start').click()`); await sleep(600);
let bad=0; const say=(ok,msg)=>{ if(!ok)bad++; console.log((ok?'ok   ':'FAIL ')+msg); };
const label=()=>ev(`ngv.game.action?ngv.game.action.label:''`);
// face a world point from where the player stands
const face=(expr,pitch='auto')=>ev(`(()=>{const g=ngv.game,P=g.player;const q=${expr};P.yaw=Math.atan2(-(q.x-P.pos.x),-(q.z-P.pos.z));const pv=${JSON.stringify(pitch)};P.pitch=pv==='auto'?Math.atan2(q.y-(P.pos.y+P.eye),Math.hypot(q.x-P.pos.x,q.z-P.pos.z)):pv;})()`);

// ---- tags + sign
const tags=await ev(`(()=>{const w=ngv.game.world;return {tags:w.tags?w.tags.length:0, labels:[...new Set((w.tags||[]).map(t=>t.userData.label))].join(' '), sign:!!w.sign}})()`);
say(tags.tags===24,'24 column tags: '+JSON.stringify(tags));
say(tags.sign,'STORAGE sign built');

// ---- doors: sprint at the shut doors from 4 m out
const U=()=>ev(`(()=>{const g=ngv.game;const h=g.mods.W.worldToHall(g.player.pos);return [+h.u.toFixed(3),+h.d.toFixed(3),g.world.doorsClear,g.world.doorsShut,g.world.doors.map(d=>+d.open.toFixed(2))]})()`);
await ev(`(()=>{const g=ngv.game;g.player.pos.copy(g.hallToWorld(44.5,7.5,g.world.floorY));g.player.yaw=Math.atan2(-0.975681,-0.219196);g.player.pitch=0;})()`); await sleep(400);
await ev(`ngv.game.player.keys.add('KeyW');ngv.game.player.keys.add('ShiftLeft')`);
let crossedEarly=false, uBefore=-1, samples=[];
for(let i=0;i<40;i++){ await sleep(100); const s=await U(); const pv=samples[samples.length-1]; samples.push(s); if(pv&&pv[0]<48.9&&s[0]>=48.9){ if(!s[2]&&!pv[2])crossedEarly=true; uBefore=pv[0]; } }
await ev(`ngv.game.player.keys.delete('KeyW');ngv.game.player.keys.delete('ShiftLeft')`);
const last=samples[samples.length-1];
say(!crossedEarly,'crossed the door line only once the leaves were clear (u before crossing '+uBefore+')');
say(last[0]>49.5,'got through once open: final u '+last[0]);
await ev(`(()=>{const g=ngv.game;g.player.pos.copy(g.hallToWorld(40,7.5,g.world.floorY));})()`); await sleep(2500);
const shut=await U(); say(shut[3],'doors shut again when far: '+JSON.stringify(shut));
// shut doors held against a slow walk from 1 m: the line and the leaf segments both hold
await ev(`(()=>{const g=ngv.game;g.player.pos.copy(g.hallToWorld(47.9,7.2,g.world.floorY));g.player.yaw=Math.atan2(-0.975681,-0.219196);})()`); await sleep(100);
await ev(`ngv.game.player.keys.add('KeyW')`); const trace=[]; for(let i=0;i<8;i++){ await sleep(100); trace.push((await U())[0]); } await ev(`ngv.game.player.keys.delete('KeyW')`);
say(trace.every(u=>u<48.9)||trace.findIndex(u=>u>=48.9)>2,'a walk from a metre out waits for the leaves: u '+trace.join(' '));
// jamb: walk into the wall beside the door
await ev(`(()=>{const g=ngv.game;g.player.pos.copy(g.hallToWorld(47.5,5.0,g.world.floorY));})()`); await sleep(300);
await ev(`ngv.game.player.keys.add('KeyW')`); await sleep(2500); await ev(`ngv.game.player.keys.delete('KeyW')`);
const jamb=await U(); say(jamb[0]<48.9,'the wall beside the doorway holds: u '+jamb[0]+' d '+jamb[1]);

// ---- screenshots: the sign from inside the hall, a column tag
await ev(`(()=>{const g=ngv.game;g.player.pos.copy(g.hallToWorld(43.5,7.5,g.world.floorY));g.player.yaw=Math.atan2(-0.975681,-0.219196);g.player.pitch=0.25;})()`); await sleep(700); await shot('sign');
await ev(`(()=>{const g=ngv.game;g.player.pos.copy(g.hallToWorld(44.54,6.8,g.world.floorY));})()`); await face(`g.world.columns.find(c=>c.label==='N6').pos`,0.35); await sleep(700); await shot('tag');

// ---- reticle-driven prompt: a pallet in view vs looking away
await ev(`(()=>{const g=ngv.game;const pal=g.items.pallets[0];const h=g.mods.W.worldToHall(pal.mesh.position);g.player.pos.copy(g.hallToWorld(h.u,h.d+1.9,g.world.floorY));})()`);
await face(`g.items.pallets[0].mesh.position`,-0.6); await sleep(400); const l1=await label();
say(/Take box from N1 pallet/.test(l1),'pointing at the N1 pallet offers its box: "'+l1+'"');
await ev(`ngv.game.player.yaw+=Math.PI`); await sleep(400); const l2=await label();
say(!/Take box/.test(l2),'looking away from it offers nothing from it: "'+l2+'"');

// ---- lift: get on needs the lift in view; ceiling cap; readouts; ring
await ev(`(()=>{const g=ngv.game,L=g.lift,P=g.player;L.pos.copy(g.hallToWorld(9.0,7.0,g.world.floorY));L.yaw=0;L.height=0;L.refresh();const o=L.offboardWorld();P.pos.set(o.x,g.world.floorY,o.z);})()`);
await face(`g.lift.pos`,-0.2); await sleep(400); const l3=await label(); say(/Get on lift/.test(l3),'pointing at the lift from the steps: "'+l3+'"');
await ev(`(()=>{const g=ngv.game,L=g.lift,P=g.player;L.board(P,true);L.takeControls(P);P.liftUp=true;})()`);
await sleep(30000); await ev(`ngv.game.player.liftUp=false`);
const lift=await ev(`(()=>{const L=ngv.game.lift,f=ngv.game.world.floorY;return {h:+L.height.toFixed(2),max:+L.maxHeight().toFixed(2),ceil:+(L.ceilingY-f).toFixed(2),eye:+(ngv.game.player.pos.y+ngv.game.player.eye-f).toFixed(2),txt:document.getElementById('deckh').textContent,wht:document.getElementById('wht').textContent}})()`);
say(lift.h<=lift.max+0.001&&lift.h>3,'lift stopped at its cap: '+JSON.stringify(lift));
say(lift.eye<lift.ceil,'eye below the ceiling: eye '+lift.eye+' ceiling '+lift.ceil);
say(/DECK/.test(lift.txt)&&/m/.test(lift.wht),'height readouts: '+lift.txt+' | '+lift.wht);
await shot('lift-top');
await ev(`(()=>{const g=ngv.game,L=g.lift;L.height=0;L.pos.copy(g.hallToWorld(7.71,5.2,g.world.floorY));L.yaw=Math.atan2(0.219196,0.975681)+Math.PI/2;L.refresh();})()`); await sleep(600);
const prox=await ev(`(()=>{const pr=ngv.game.mods.W.proximity(ngv.game.world,ngv.game.lift,24,1.6);return {hits:pr.filter(p=>p.dist!=null).length,dots:document.getElementById('wprox').children.length}})()`);
say(prox.hits>0&&prox.dots>0,'proximity ring sees the column: '+JSON.stringify(prox));
await shot('prox');

// ---- drops on the deck 4 m up: a light and a bag land inside the rails and ride the deck
await ev(`(()=>{const g=ngv.game,L=g.lift;L.pos.copy(g.hallToWorld(20,7.5,g.world.floorY));L.yaw=0;L.height=4;L.refresh();L.letGo();})()`); await sleep(300);
const drop=(type)=>ev(`(()=>{const g=ngv.game,P=g.player,I=g.items,M=g.mods.ITEMm,L=g.lift;
    L.deckLocal.set(0.2,0); P.yaw=L.yaw-Math.PI/2; P.pitch=-0.3;
    if('${type}'==='light'){ const mesh=I.bags[0].mesh.clone(); g.player.camera.add(mesh); P.carry={type:'light',mesh}; }
    else { const b=I.bags[0]; b.mesh.removeFromParent(); g.player.camera.add(b.mesh); b.carried=true; P.carry=b; }
    M.dropCarry(P,I); return 'dropped'; })()`);
for (const type of ['light','bag']) {
  await drop(type); await sleep(2500);
  const st=await ev(`(()=>{const g=ngv.game,L=g.lift,I=g.items;const o=('${type}'==='light')?I.lights[I.lights.length-1]:I.bags[0];const d=L.toDeck(o.mesh.position);const top=L.floorY+L.deckY+L.height+0.07;return {deck:!!o.deck,dx:+d.x.toFixed(2),dz:+d.y.toFixed(2),above:+(o.mesh.position.y-top).toFixed(3),yaw:+(o.mesh.rotation.y-L.yaw).toFixed(2)}})()`);
  say(st.deck&&Math.abs(st.dx)<1.2&&Math.abs(st.dz)<0.55&&st.above>-0.01&&st.above<0.6,type+' lands on the deck inside the rails: '+JSON.stringify(st));
  if(type==='light') say(Math.abs(((st.yaw%Math.PI)+Math.PI)%Math.PI)<0.05,'bar lies along the chassis (yaw '+st.yaw+')');
}
await shot('deck-drop');
// pick it back up while aboard: point the reticle at the bar
await face(`g.items.lights[g.items.lights.length-1].mesh.position`); await sleep(400);
const l4=await label(); say(/Pick up light/.test(l4),'aboard, pointing at the bar on the deck: "'+l4+'"');
const ret=await ev(`document.getElementById('reticle').className+' '+getComputedStyle(document.getElementById('reticle')).display`);
say(/can/.test(ret)&&/block/.test(ret),'reticle shows and is green: '+ret);
await shot('aboard-pick');
await face(`g.items.bags[0].mesh.position.clone().setY(g.items.bags[0].mesh.position.y+0.3)`); await sleep(400);
const l5=await label(); say(/Take empty bag/.test(l5),'pointing at the bag on the deck: "'+l5+'"');

console.log(bad?`${bad} FAIL`:'all ok'); console.log(logs.join('\n')||'no errors');
ws.close(); process.exit(bad?1:0);
