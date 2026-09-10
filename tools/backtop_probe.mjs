// 2026-09-10: WHAT STOPS THE WEST GALLERY'S LIT BACK WALL IN THE SIM. tools/back_wall_top.py measured the
// photographs' lit cream reaching h 12.90 and the render through b3_000161 stopping at h 11.45; this names
// the mesh that stops it. From the pick's own eye it raycasts at the back wall plane (u 0.356, d 7.0) over a
// ladder of heights and prints every hit in order, so the occluder is read by name and distance rather than
// guessed from the picture.
//   bash ~/scripts/headless-chrome.sh start 9334
//   CDP_PORT=9334 SHOT_URL=http://127.0.0.1:8877/index.html node tools/backtop_probe.mjs
import { attach } from './cdp.mjs';

const PAGE = process.env.SHOT_URL || 'http://127.0.0.1:8877/index.html';
const EYE = { u: 48.248, d: 7.497, h: 9.886 };
const P = await attach({ port: +(process.env.CDP_PORT || 9334), width: 1280, height: 720 });
await P.send('Network.setCacheDisabled', { cacheDisabled: true }).catch(() => {});
await P.send('Page.navigate', { url: `${PAGE}?install=gandel-2026&cb=${Date.now()}` });
let ok = false;
for (let i = 0; i < 150; i++) { await P.sleep(500); if (await P.ev('!!(window.ngv&&window.ngv.hall&&document.getElementById("install"))').catch(() => false)) { ok = true; break; } }
if (!ok) { console.log('the page never reached install mode'); await P.close(); process.exit(1); }
await P.ev(`localStorage.setItem('ngv.install','gandel-2026'); document.getElementById('install').click()`);
for (let i = 0; i < 60; i++) { await P.sleep(500); if (await P.ev('!!(window.ngv&&window.ngv.game)').catch(() => false)) break; }
await P.ev(`document.querySelector('#start').click()`).catch(() => {});
await P.sleep(1500);
// sprites carry no matrixWorld until they are drawn and the raycaster throws on them; they are labels, not geometry.
await P.ev(`(()=>{let n=0; ngv.scene.traverse(o=>{ if(o.isSprite){o.visible=false;o.raycast=()=>{};n++;} }); ngv.dirty(); return n;})()`).then(n=>console.log('sprites hidden',n)).catch(()=>{});

const out = await P.ev(`(()=>{
  const g=ngv.game, TH=window.dbg.THREE;
  const P3=(u,d,h)=>{ const p=g.hallToWorld(u,d,g.world.floorY); p.y=g.world.floorY+h; return p; };
  const eye=P3(${EYE.u},${EYE.d},${EYE.h});
  const rc=new TH.Raycaster(); rc.far=200;
  const rows=[];
  for(let h=11.0; h<=13.4001; h+=0.20){
    const tgt=P3(0.356,7.0,h);
    const dir=tgt.clone().sub(eye).normalize();
    rc.set(eye,dir);
    const hits=rc.intersectObjects(ngv.scene.children,true).filter(x=>x.object.visible&&x.distance>0.5);
    const seen=[]; const names=[];
    for(const x of hits){ const n=x.object.name||x.object.type; if(!seen.includes(n)){seen.push(n); names.push(n+' @'+x.distance.toFixed(1));} if(names.length>=4)break; }
    rows.push(h.toFixed(2)+'  '+names.join('  |  '));
  }
  return rows.join('\\n');
})()`).catch(e => 'PROBE FAILED: ' + String(e.message).slice(0, 200));
console.log(out);
await P.close();
process.exit(0);
