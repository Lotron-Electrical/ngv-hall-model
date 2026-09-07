// THE LIGHTING SHOTS (Lloyd, 2026-09-07). Seven fixed views of the hall at night, so the render
// work can be looked at rather than argued about. The camera numbers live HERE, not on the command
// line, so the before and the after are the same frame:
//   hall-end      down the hall from the east end, the whole colonnade
//   column-close  a metre and a half off one shaft, the fixture and its wash
//   floor-low     knee height, the carpet filling the bottom of the frame
//   high-down     up on the lift, looking down the room
//   wall          across the hall at the stone wall and a tapestry
//   warm-white    hall-end again on the warm white scene, not the rainbow
//   phone         hall-end at 412 x 915, device pixel ratio 1.5, mobile metrics
//
// Usage: node tools/light-shots.mjs <outdir> [page]
//   page defaults to index.html; pass .light-before.html (git show HEAD:index.html > that) to
//   shoot the same seven views of the page as it was.
import fs from 'node:fs';
import { attach } from './cdp.mjs';

const out = process.argv[2];
if (!out) { console.log('usage: node tools/light-shots.mjs <outdir> [page]'); process.exit(1); }
const page = process.argv[3] || 'index.html';
fs.mkdirSync(out, { recursive: true });

// x, y, z, yaw, pitch. The hall runs along -x from the east end at x = 0; the two column rows sit
// either side of the centre line, which drifts in z as the hall is not axis-aligned.
const VIEWS = [
  ['hall-end', -6.0, 1.70, 1.2, Math.PI, 0.06],
  ['column-close', -28.8, 1.55, 5.6, Math.PI * 0.80, 0.26],
  ['floor-low', -20.0, 0.45, 2.6, Math.PI, -0.14],
  ['high-down', -24.0, 8.60, 2.2, Math.PI, -0.55],
  ['wall', -27.0, 2.10, 4.4, -Math.PI / 2 - 0.25, 0.05],
];

const P = await attach({ width: 1280, height: 800 });
const scene = async which => {
  // the rainbow show at 0.3, the house off: the night the proposal sells
  if (which === 'rainbow') await P.ev(`ngv.state.layers=[{on:true,anim:'rainbow',opacity:1,blend:'over',speed:0.3,A:{h:0,s:1,v:1},B:{h:0,s:1,v:0},dens:0.02}]; ngv.state.sel=0; ngv.lit.house=0; ngv.dirty();`);
  // warm white at full: the same room lit as a room, not as a show
  else await P.ev(`ngv.state.layers=[{on:true,anim:'solid',opacity:1,blend:'over',speed:0,A:{h:30,s:0.35,v:1},B:{h:0,s:0,v:0},dens:0.02}]; ngv.state.sel=0; ngv.lit.house=0; ngv.dirty();`);
  await P.sleep(1800);
};
const hideUI = () => P.ev(`for(const s of ['#panel','#hint','.bar','#ghud','header','#top','#fab','#roamfab','#stkmove','#stklook']){document.querySelectorAll(s).forEach(e=>e.style.visibility='hidden');}`);

try {
  await P.open(page);
  await P.roam();
  await hideUI();
  await scene('rainbow');
  console.log('state', await P.ev(`JSON.stringify({house:ngv.lit.house,n:ngv.lit.nLights,exposure:+ngv.EXPO.now.toFixed(2),mean:Math.round(ngv.EXPO.mean),fps:Math.round(window.dbg.fps()||0)})`).catch(() => 'n/a'));
  for (const [name, x, y, z, yw, pt] of VIEWS) {
    await P.ev(`ngv.setCam(${x},${y},${z},${yw},${pt}); ngv.dirty();`);
    await P.sleep(1500);
    await P.shot(`${out}/${name}.jpg`); console.log('shot', name);
  }
  // the same first view on the warm white scene
  await scene('warm');
  await P.ev(`ngv.setCam(${VIEWS[0].slice(1).join(',')}); ngv.dirty();`); await P.sleep(1500);
  await P.shot(`${out}/warm-white.jpg`); console.log('shot warm-white');
  // and the phone: 412 x 915, dsf 1.5, mobile metrics, which is the cheap path in every new pass
  await P.send('Emulation.setDeviceMetricsOverride', { width: 412, height: 915, deviceScaleFactor: 1.5, mobile: true });
  await scene('rainbow');
  await P.ev(`ngv.setCam(${VIEWS[0].slice(1).join(',')}); ngv.dirty();`); await P.sleep(2500);
  await P.shot(`${out}/phone.jpg`); console.log('shot phone');
  console.log('fps at 412x915:', await P.ev(`Math.round(window.dbg.fps()||0)`).catch(() => 'n/a'));
  console.log(P.errors.length ? P.errors.join('\n') : 'no console errors');
} catch (e) {
  console.log('FAIL ' + e.message);
}
P.close();
process.exit(0);
