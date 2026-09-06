// (Lloyd, 2026-09-06: "we should have an inventory system", "be able to move the rubbish
// containers") four slots: take a wrapped light from a pallet box, then a wrap, switch slots with
// the keys and the strip, drop the active one, carry a part-full bag. Serve :8877, Chrome :9333.
import fs from 'node:fs';
const out = process.argv[2] || '.'; fs.mkdirSync(out, { recursive: true });
const port = 9333, url='http://127.0.0.1:8877/index.html?install=gandel-2026&cb='+Date.now();
const tabs=await (await fetch(`http://127.0.0.1:${port}/json`)).json(); let t=tabs.find(x=>x.type==='page'); if(!t) t=await (await fetch(`http://127.0.0.1:${port}/json/new?about:blank`,{method:'PUT'})).json();
const ws=new WebSocket(t.webSocketDebuggerUrl); let id=0; const pend={}; const logs=[];
ws.onmessage=e=>{ const m=JSON.parse(e.data); if(m.id&&pend[m.id]){pend[m.id](m.result);delete pend[m.id];} if(m.method==='Runtime.exceptionThrown')logs.push('EXC '+JSON.stringify(m.params.exceptionDetails).slice(0,500)); };
await new Promise(r=>ws.onopen=r);
const send=(method,params={})=>new Promise(r=>{ const i=++id; pend[i]=r; ws.send(JSON.stringify({id:i,method,params})); });
const ev=async expr=>{ const r=await send('Runtime.evaluate',{expression:expr,returnByValue:true,awaitPromise:true}); if(!r) return undefined; if(r.exceptionDetails) return 'EVALERR '+JSON.stringify(r.exceptionDetails.exception&&r.exceptionDetails.exception.description).slice(0,300); return r.result?r.result.value:r; };
const sleep=ms=>new Promise(r=>setTimeout(r,ms));
const shot=async n=>{ const s=await send('Page.captureScreenshot',{format:'jpeg',quality:80}); fs.writeFileSync(`${out}/${n}.jpg`,Buffer.from(s.data,'base64')); };
await send('Network.enable'); await send('Network.setCacheDisabled',{cacheDisabled:true});
await send('Emulation.setDeviceMetricsOverride',{width:412,height:915,deviceScaleFactor:1.5,mobile:true});
await send('Page.enable'); await send('Runtime.enable'); await send('Page.navigate',{url});
for(let i=0;i<40;i++){ await sleep(500); if(await ev('!!(window.ngv&&window.ngv.hall&&document.getElementById("install"))'))break; }
await ev(`localStorage.clear(); localStorage.setItem('ngv.install','gandel-2026'); document.getElementById('install').click()`);
for(let i=0;i<40;i++){ await sleep(500); if(await ev('!!(window.ngv&&window.ngv.game)'))break; }
await ev(`document.querySelector('#start').click()`); await sleep(600);
let bad=0; const say=(ok,msg)=>{ if(!ok)bad++; console.log((ok?'ok   ':'FAIL ')+msg); };
const label=()=>ev(`ngv.game.action?ngv.game.action.label:''`);
const face=(expr)=>ev(`(()=>{const g=ngv.game,P=g.player;const q=${expr};P.yaw=Math.atan2(-(q.x-P.pos.x),-(q.z-P.pos.z));P.pitch=Math.atan2(q.y-(P.pos.y+P.eye),Math.hypot(q.x-P.pos.x,q.z-P.pos.z));})()`);
const act=async()=>{ await ev(`ngv.game.player.actionQueued=true`); await sleep(350); };
const inv=()=>ev(`(()=>{const P=ngv.game.player;return {slots:P.inv.map(i=>i?i.type:null),active:P.active,hand:P.carry?P.carry.type:null,strip:[...document.querySelectorAll('#inv .slot')].map(s=>s.className.replace('slot','').trim()+':'+s.textContent.trim()),shown:P.inv.map(i=>i&&i.mesh?i.mesh.visible:null)}})()`);

// stand at the N1 pallet, take a box, set it down, take a wrapped light from it, then a second
await ev(`(()=>{const g=ngv.game;const pal=g.items.pallets[0];const h=g.mods.W.worldToHall(pal.mesh.position);g.player.pos.copy(g.hallToWorld(h.u,h.d+1.9,g.world.floorY));})()`);
await face(`g.items.pallets[0].mesh.position.clone().setY(g.items.pallets[0].mesh.position.y+0.5)`); await sleep(400);
say(/Take box from N1 pallet/.test(await label()),'pallet in view: '+await label()); await act();
let s=await inv(); say(s.hand==='box'&&s.slots.filter(Boolean).length===1,'box in hand: '+JSON.stringify(s.slots));
say(/Set down box/.test(await label()),'box in hand, nothing else in view: '+await label());
// with a box (2 units) in hand there is room for 2 more units: point at the pallet again
say(/Hands full|Take box|Set down/.test(await label()),'prompt while holding a box: '+await label());
await ev(`ngv.game.player.dropQueued=true`); await sleep(1500);
s=await inv(); say(s.hand===null,'box dropped: '+JSON.stringify(s.slots));
await face(`g.items.boxes[0].mesh.position`); await sleep(400);
say(/Take wrapped light from box/.test(await label()),'box on the floor in view: '+await label()); await act();
s=await inv(); say(s.hand==='wrapped','wrapped light in slot 1: '+JSON.stringify(s));
await face(`g.items.boxes[0].mesh.position`); await sleep(400);
say(/Take wrapped light from box/.test(await label()),'room for another: '+await label()); await act();
s=await inv(); say(s.slots.filter(x=>x==='wrapped').length===2&&s.active===1,'two wrapped lights, slot 2 active: '+JSON.stringify(s.slots)+' active '+s.active);
say(s.shown[0]===false&&s.shown[1]===true,'only the active one shows in the hands: '+JSON.stringify(s.shown));
say(/on:2/.test(s.strip[1])&&/WRAPPED/.test(s.strip[1]),'strip marks slot 2: '+JSON.stringify(s.strip));
await shot('inv-two');
// unwrap the active one: it becomes a light in the same slot, the wrap lands on the floor
await ev(`ngv.game.player.yaw+=Math.PI;ngv.game.player.pitch=-0.5`); await sleep(400);
say(/Unwrap light/.test(await label()),'nothing in view, wrapped in hand: '+await label()); await act();
s=await inv(); say(s.slots[1]==='light'&&s.slots[0]==='wrapped','unwrapped in place: '+JSON.stringify(s.slots));
// key 1 switches hands
await ev(`window.dispatchEvent(new KeyboardEvent('keydown',{code:'Digit1'}))`); await sleep(300);
s=await inv(); say(s.active===0&&s.hand==='wrapped'&&s.shown[0]===true&&s.shown[1]===false,'key 1 switches to slot 1: '+JSON.stringify(s));
// a tap on the strip switches back
await ev(`document.querySelector('#inv [data-slot="1"]').click()`); await sleep(300);
s=await inv(); say(s.active===1&&s.hand==='light','tap on slot 2 switches back: active '+s.active+' hand '+s.hand);
// pick up the wrap too: three things carried
await face(`g.items.wraps[0].mesh.position`); await sleep(400);
say(/Pick up wrap/.test(await label()),'wrap in view: '+await label()); await act();
s=await inv(); say(s.slots.filter(Boolean).length===3,'three items: '+JSON.stringify(s.slots));
// a bag: carry a part-full one
await ev(`(()=>{const g=ngv.game;const b=g.items.bags[0];b.wraps=3;g.player.pos.copy(b.mesh.position.clone().add(g.hallToWorld(0,0,0).sub(g.hallToWorld(1.6,0,0))));g.player.pos.y=g.world.floorY;})()`);
await face(`g.items.bags[0].mesh.position.clone().setY(g.items.bags[0].mesh.position.y+0.3)`); await sleep(400);
say(/Bag the wrap/.test(await label()),'wrap in hand, bag in view: '+await label()); await act();
s=await inv(); say(s.slots.filter(Boolean).length===2,'wrap bagged: '+JSON.stringify(s.slots));
await face(`g.items.bags[0].mesh.position.clone().setY(g.items.bags[0].mesh.position.y+0.3)`); await sleep(400);
say(/Take rubbish bag \(4\/8\)/.test(await label()),'part-full bag can be carried: '+await label()); await act();
s=await inv(); say(s.hand==='bag','bag in hand: '+JSON.stringify(s.slots));
await shot('inv-bag');
await ev(`ngv.game.player.dropQueued=true`); await sleep(1500);
const bag=await ev(`(()=>{const b=ngv.game.items.bags[0];return {carried:b.carried,y:+(b.mesh.position.y-ngv.game.world.floorY).toFixed(2),parent:b.mesh.parent&&b.mesh.parent.type}})()`);
say(!bag.carried&&bag.y<0.6&&bag.y>0.3,'bag put down on the floor: '+JSON.stringify(bag));
console.log(bad?`${bad} FAIL`:'all ok'); console.log(logs.join('\n')||'no errors');
ws.close(); process.exit(bad?1:0);
