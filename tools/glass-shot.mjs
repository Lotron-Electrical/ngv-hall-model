// (2026-09-08) The canopy from the carpet: straight up by day at noon with the house at 40 %, then
// at night with the house full, then a balcony-height oblique by day. Install mode (the only
// camera a script can place). node tools/glass-shot.mjs <outdir> [page] [tag]   (CDP_PORT 9334)
import { attach } from './cdp.mjs';
const [out, page='index.html', tag='glass'] = process.argv.slice(2);
const P = await attach({ port: +(process.env.CDP_PORT || 9334) });
await P.send('Page.navigate', { url: 'http://127.0.0.1:8877/' + page + '?cb=' + Date.now() + '&install=gandel-2026' });
for (let i = 0; i < 90; i++) { await P.sleep(500); if (await P.ev('!!(window.ngv&&window.ngv.hall&&document.getElementById("install")&&window.ngv.canopy&&window.ngv.canopy.glass)').catch(()=>false)) break; }
await P.ev(`localStorage.setItem('ngv.install','gandel-2026'); document.getElementById('install').click()`);
for (let i = 0; i < 60; i++) { await P.sleep(500); if (await P.ev('!!(window.ngv&&window.ngv.game)').catch(()=>false)) break; }
await P.ev(`document.querySelector('#start').click()`); await P.sleep(800);
const setDay = async (h, house) => { await P.ev(`(()=>{const t=document.getElementById('tod');t.value=${h};t.dispatchEvent(new Event('input'));const hs=document.getElementById('house');if(hs){hs.value=${house};hs.dispatchEvent(new Event('input'));} ngv.dirty();})()`); await P.sleep(900); };
const place = (u, d, yawU, yawD, pitch) => P.ev(`(()=>{const g=ngv.game,P=g.player,L=g.lift;const p=g.hallToWorld(${u},${d},g.world.floorY);
  const q=g.hallToWorld(${u}+${yawU},${d}+${yawD},g.world.floorY); P.yaw=Math.atan2(-(q.x-p.x),-(q.z-p.z)); P.pitch=${pitch}; if(L.aboard)L.leave(P,true); P.pos.copy(p); return 1; })()`);
await setDay(12, 40); await place(18.5, 7.5, 0, -1.2, 1.5); await P.sleep(1500); await P.shot(`${out}/${tag}-day-up.jpg`);
await place(4, 7.5, 6, 0, 0.55); await P.sleep(1500); await P.shot(`${out}/${tag}-day-along.jpg`);
await setDay(21, 100); await place(18.5, 7.5, 0, -1.2, 1.5); await P.sleep(1200); await P.shot(`${out}/${tag}-night-up.jpg`);
console.log(P.errors.join('\n') || 'no errors'); P.close(); process.exit(0);
