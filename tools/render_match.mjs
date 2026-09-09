// 2026-09-10: SHOOT THE SIM FROM EVERY POSE IN render-match.json, ONE PAGE LOAD, LIVE SANDBOX.
//
// tools/pose-shot.mjs already does one pose, but it loads the page, enters install mode, starts the game
// and hides the HUD every time, which is about forty seconds of setup per shot. This does that once and
// then walks the list, changing only the viewport, the time of day and the camera. Same page, same
// controls, so nothing about the render differs between poses except the pose.
//
// THE RENDER CARRIES 720 LINES, NOT THE PHOTOGRAPH'S 2160. The scorer works on 540 lines and both
// pictures are resized down to it, so the render only has to be above that and share the photograph's
// ASPECT exactly, which is what the width rounding below protects. Shooting 4K twelve times would cost
// minutes of GPU for detail the measurement throws away.
//
// THE SPRITES AND LABELS ARE HIDDEN, and that is not cosmetic. The event layout's zone tags are unnamed
// sprites that sit exactly across the end galleries in any shot aimed down the hall, which is where these
// pairs have to be read.
//   bash ~/scripts/headless-chrome.sh start 9334
//   CDP_PORT=9334 node tools/render_match.mjs
//   bash ~/scripts/headless-chrome.sh stop 9334
import fs from 'node:fs';
import { attach } from './cdp.mjs';

const PAGE = process.env.SHOT_URL || 'https://lotron-electrical.github.io/ngv-hall-model/index.html';
const picks = JSON.parse(fs.readFileSync('render-match.json', 'utf8'));
const RH = 720;
const P = await attach({ port: +(process.env.CDP_PORT || 9334), width: 1280, height: RH });
await P.send('Network.setCacheDisabled', { cacheDisabled: true }).catch(() => {});
console.log('loading', PAGE);
await P.send('Page.navigate', { url: `${PAGE}?install=gandel-2026&cb=${Date.now()}` });
let ok = false;
for (let i = 0; i < 150; i++) { await P.sleep(500); if (await P.ev('!!(window.ngv&&window.ngv.hall&&document.getElementById("install"))').catch(() => false)) { ok = true; break; } }
if (!ok) { console.log('THE PAGE NEVER REACHED INSTALL MODE. No render can be made.'); await P.close(); process.exit(1); }
await P.ev(`localStorage.setItem('ngv.install','gandel-2026'); document.getElementById('install').click()`);
for (let i = 0; i < 60; i++) { await P.sleep(500); if (await P.ev('!!(window.ngv&&window.ngv.game)').catch(() => false)) break; }
await P.ev(`document.querySelector('#start').click()`).catch(() => {});
await P.sleep(1200);
// HIDING THE HUD BY A LIST OF NAMES IS HOW THE FIRST RUN OF THIS FAILED. The list came from another tool
// and missed the .ctl button bar along the bottom, the install panel in the top corner and the column
// labels, so every render carried a few per cent of high-contrast text that no photograph could match.
// The rule that cannot miss anything is the complement: leave the canvas visible and hide the rest.
const hidden = await P.ev(`(()=>{document.body.classList.add("immersive");
  const cb=document.getElementById("collide"); if(cb){cb.checked=false; cb.dispatchEvent(new Event("change"));}
  let n=0; const keep=document.getElementById('cv');
  document.querySelectorAll('body > *, main > *, #stage > *').forEach(e=>{ if(e===keep||e.contains(keep))return; e.style.visibility='hidden'; n++; });
  return n;})()`).catch(e => String(e.message).slice(0, 120));
console.log('overlays hidden', hidden);
await P.ev(`(()=>{let n=0; ngv.scene.traverse(o=>{ if(o.isSprite){o.visible=false;n++;} }); ngv.dirty(); return n;})()`).then(n => console.log('sprites hidden', n)).catch(() => {});

const shots = [];
for (let i = 0; i < picks.length; i++) {
  const p = picks[i];
  // A SQUARE THAT CIRCUMSCRIBES THE PHOTOGRAPH, at the photograph's own angular scale. The scorer turns
  // it by the camera's measured roll and cuts the frame out of the middle, which is the only way to
  // reproduce a handheld camera with a sim that has no roll control.
  const side = 2 * Math.round(RH * p.sqside / 2);
  await P.send('Emulation.setDeviceMetricsOverride', { width: side, height: side, deviceScaleFactor: 1, mobile: false });
  await P.ev(`window.dispatchEvent(new Event('resize'))`).catch(() => {});
  await P.sleep(700);
  // NIGHT IS SHOT AT NIGHT. The walk captures are daylight with the house lights down, the night captures
  // were made in the evening, and the balcony clips are daylight; getting this wrong would compare a lit
  // render with a dark photograph and the score would measure the lighting, not the geometry.
  const hour = p.cls === 'night' ? 21 : 13;
  const house = p.cls === 'night' ? 70 : 0;
  await P.ev(`(()=>{const t=document.getElementById('tod'); t.value=${hour}; t.dispatchEvent(new Event('input'));
    const hs=document.getElementById('house'); if(hs){hs.value=${house}; hs.dispatchEvent(new Event('input'));} ngv.dirty();})()`).catch(() => {});
  await P.sleep(700);
  const place = () => P.ev(`(()=>{const g=ngv.game,PL=g.player,L=g.lift; const a=g.hallToWorld(${p.u},${p.d},g.world.floorY);
    const b=g.hallToWorld(${p.u + p.fu},${p.d + p.fd},g.world.floorY); PL.yaw=Math.atan2(-(b.x-a.x),-(b.z-a.z)); PL.pitch=${p.pitch}*Math.PI/180;
    if(L.aboard)L.leave(PL,true); PL.pos.copy(a); PL.pos.y=g.world.floorY; PL.eye=${p.h}; return PL.eye;})()`).catch(e => String(e.message).slice(0, 120));
  const eye = await place();
  await P.sleep(1000);
  await place();
  await P.ev(`(()=>{const g=ngv.game; if(g.fx)g.fx.baseFov=${p.sqvfov}; ngv.cam.fov=${p.sqvfov}; ngv.cam.updateProjectionMatrix(); return ngv.cam.fov;})()`).catch(() => {});
  await place();
  await P.sleep(400);
  const out = `render-match/r${String(i).padStart(2, '0')}.jpg`;
  await P.shot(out);
  shots.push(out);
  console.log(`${p.cls} ${p.frame}  square ${side}  vfov ${p.sqvfov.toFixed(1)} covering the frame's ${p.vfov.toFixed(1)}  roll ${p.roll.toFixed(1)}  eye ${typeof eye === 'number' ? eye.toFixed(2) : eye}  -> ${out}`);
}
console.log('');
console.log(`${shots.length} renders written.`);
console.log(P.errors.length ? `the page reported ${P.errors.length} errors: ${P.errors.slice(0, 4).join(' | ')}`
  : 'the page reported no errors while any of this ran.');
await P.close();
process.exit(0);
