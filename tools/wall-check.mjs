// (2026-09-08) THE WALL SHOTS: the same six views of the walls on any page, so a wall pass can be
// looked at before and after. Install mode (the only camera a script can place), the house at 40 %
// by day at noon and full at 21:00. Hall frame: u along the hall from the west end wall (0.344),
// d across from the north wall (about 0) to the south (15.36). Views:
//   north-wide   from the south side of the hall, the north wall's windows, grilles and door
//   north-window under the openings looking up at the corridor windows
//   north-door   the foyer door and the inscription
//   south-glass  the pleated glazing from the north side
//   west-end     the west gallery from mid hall
//   east-end     the east gallery from mid hall
//   south-door   the lit door in the south wall's east stretch (u 38-39.7)
//   north-east-door the dark door at the east end of the north wall (u 46-47.8)
//   window-close under opening 2 (u 8.3) looking up the reveal
// node tools/wall-check.mjs <outdir> [page] [tag]   (CDP_PORT 9334, server :8877)
import fs from 'node:fs';
import { attach } from './cdp.mjs';
const [out, page = 'index.html', tag = 'wall'] = process.argv.slice(2);
if (!out) { console.log('usage: node tools/wall-check.mjs <outdir> [page] [tag]'); process.exit(1); }
fs.mkdirSync(out, { recursive: true });
const P = await attach({ port: +(process.env.CDP_PORT || 9334), width: 1600, height: 1000 });
await P.send('Page.navigate', { url: 'http://127.0.0.1:8877/' + page + '?cb=' + Date.now() + '&install=gandel-2026' });
for (let i = 0; i < 120; i++) { await P.sleep(500); if (await P.ev('!!(window.ngv&&window.ngv.hall&&document.getElementById("install"))').catch(() => false)) break; }
await P.ev(`localStorage.setItem('ngv.install','gandel-2026'); document.getElementById('install').click()`);
for (let i = 0; i < 60; i++) { await P.sleep(500); if (await P.ev('!!(window.ngv&&window.ngv.game)').catch(() => false)) break; }
await P.ev(`document.querySelector('#start').click()`); await P.sleep(800);
await P.ev(`for(const s of ['#panel','#hint','.bar','#ghud','header','#top','#fab','#roamfab','#stkmove','#stklook','#hud','#tasks']){document.querySelectorAll(s).forEach(e=>e.style.visibility='hidden');}`).catch(() => {});
const setDay = async (h, house) => { await P.ev(`(()=>{const t=document.getElementById('tod');t.value=${h};t.dispatchEvent(new Event('input'));const hs=document.getElementById('house');if(hs){hs.value=${house};hs.dispatchEvent(new Event('input'));} ngv.dirty();})()`); await P.sleep(900); };
// stand at (u, d), look towards (u+yawU, d+yawD), eye height + pitch
const place = (u, d, yawU, yawD, pitch, eye = 0) => P.ev(`(()=>{const g=ngv.game,P=g.player,L=g.lift;const p=g.hallToWorld(${u},${d},g.world.floorY);
  const q=g.hallToWorld(${u}+${yawU},${d}+${yawD},g.world.floorY); P.yaw=Math.atan2(-(q.x-p.x),-(q.z-p.z)); P.pitch=${pitch}; if(L.aboard)L.leave(P,true); P.pos.copy(p); P.pos.y+=${eye}; return 1; })()`);
const VIEWS = [
  ['north-wide', 20, 13.5, 0, -1, 0.28],
  ['north-window', 11.4, 4.0, 0, -1, 0.95],
  ['north-door', 20, 6.5, 0, -1, 0.12],
  ['south-glass', 26, 3.0, 0, 1, 0.22],
  ['west-end', 14, 7.7, -1, 0, 0.25],
  ['east-end', 38, 7.7, 1, 0, 0.25],
  ['south-door', 38.8, 9.5, 0, 1, 0.05],
  ['north-east-door', 46.9, 6.0, 0, -1, 0.05],
  ['window-close', 8.3, 2.5, 0, -1, 1.15],
];
for (const [h, house, when] of [[12, 40, 'day'], [21, 100, 'night']]) {
  await setDay(h, house);
  for (const [name, u, d, yu, yd, pitch] of VIEWS) { await place(u, d, yu, yd, pitch); await P.sleep(1400); await P.shot(`${out}/${tag}-${name}-${when}.jpg`); console.log('shot', name, when); }
}
console.log(P.errors.join('\n') || 'no errors'); P.close(); process.exit(0);
