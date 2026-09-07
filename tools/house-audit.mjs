// THE HOUSE LIGHT'S ENERGY AUDIT (2026-09-07, "the lighting needs to be fixed"). The house light is
// now the rig's 23 fixtures (index.html RIG_PHOT, mirrored in tools/rigphot.mjs). This asks:
//  1. THE NUMBERS AGREE: the page's RIG_PHOT is the mirror's, number for number.
//  2. THE DATASHEET: each cone's flux integrated on a fine grid equals the page's own integration
//     the dim is derived from, within 1%.
//  3. LUMENS IN = LUX OUT: the rig's direct light integrated over the carpet, the two long walls
//     and the two end walls (E x dA, the JS mirror of the shader's loop) accounts for at least 85%
//     of the flux (the rest goes above the horizon, into the truss, out of the openings), and the
//     carpet takes the share the dim assumes, within 3 points.
//  4. THE CARPET'S MEAN: at house = 1 the carpet averages HOUSE_LUX (direct plus bounce) within 15%.
//  5. THE CANVAS: with the house at 1, nothing else on and the exposure pinned, the ratio of a pool
//     centre to a point between pools read off the canvas matches the JS mirror within 25%.
//  Usage: node tools/house-audit.mjs <outdir>   (serve :8877, headless Chrome :9333; NGV_PORT)
import fs from 'node:fs';
import { attach, reporter } from './cdp.mjs';
import { RIG_PHOT, HOUSE_LUX, FRAME, fixture, candela, rigLux, houseE } from './rigphot.mjs';

const out = process.argv[2] || process.env.TMP; fs.mkdirSync(out, { recursive: true });
const R = reporter(); const pct = (a, b) => Math.abs(a - b) / Math.max(Math.abs(b), 1e-9) * 100;
const hp = (u, d, y) => [FRAME.O[0] + FRAME.U[0] * u + FRAME.N[0] * d, FRAME.O[1] + y, FRAME.O[2] + FRAME.U[2] * u + FRAME.N[2] * d];

// 2. the cones
{
  for (const [name, i] of [['profile', 0], ['PAR', 1]]) {
    const f = fixture(i); let flux = 0; const n = 720;
    // integrate I dOmega over the hemisphere about the aim: theta in [0, pi/2], phi in [0, 2pi]
    const ax = (() => { const a = f.aim, U = FRAME.U; const d = a[0] * U[0] + a[1] * U[1] + a[2] * U[2]; const v = [U[0] - a[0] * d, U[1] - a[1] * d, U[2] - a[2] * d]; const l = Math.hypot(...v); return v.map(x => x / l); })();
    const ay = [f.aim[1] * ax[2] - f.aim[2] * ax[1], f.aim[2] * ax[0] - f.aim[0] * ax[2], f.aim[0] * ax[1] - f.aim[1] * ax[0]];
    for (let a = 0; a < n; a++) { const th = (a + 0.5) / n * Math.PI / 2; for (let b = 0; b < n; b++) { const ph = (b + 0.5) / n * 2 * Math.PI;
      const vn = [0, 1, 2].map(k => f.aim[k] * Math.cos(th) + ax[k] * Math.sin(th) * Math.cos(ph) + ay[k] * Math.sin(th) * Math.sin(ph));
      flux += candela(i, vn, f.aim) * Math.sin(th) * (Math.PI / 2 / n) * (2 * Math.PI / n); } }
    const closed = i === 0 ? RIG_PHOT.fluxProfile : RIG_PHOT.fluxPar;
    R.say(pct(flux, closed) < 1, `datasheet: the ${name} cone integrates to ${Math.round(flux).toLocaleString()} lm on a 720 grid against the page's 180 grid ${Math.round(closed).toLocaleString()} lm (${pct(flux, closed).toFixed(1)}% off)`);
  }
  R.note(`rig at full: 12 profiles + 11 PARs = ${Math.round(RIG_PHOT.flux).toLocaleString()} lm; house = 1 runs it at ${(RIG_PHOT.dim * 100).toFixed(1)}%`);
}

// 3 and 4. lumens in = lux out, over the room's surfaces at full
let carpetMean = 0;
{
  const step = 0.25, L = 48.9, D = 15.4, H = 12.2; let onCarpet = 0, onWalls = 0, onEnds = 0, cells = 0;
  for (let u = step / 2; u < L; u += step) for (let d = step / 2; d < D; d += step) { const E = rigLux(hp(u, d, 0), [0, 1, 0]); onCarpet += E * step * step; carpetMean += E; cells++; }
  carpetMean /= cells;
  for (let u = step / 2; u < L; u += step) for (let y = step / 2; y < H; y += step) {
    onWalls += rigLux(hp(u, 0, y), FRAME.N) * step * step;                      // north wall faces +d
    onWalls += rigLux(hp(u, D, y), FRAME.N.map(x => -x)) * step * step; }       // south wall faces -d
  for (let d = step / 2; d < D; d += step) for (let y = step / 2; y < H; y += step) {
    onEnds += rigLux(hp(0, d, y), FRAME.U) * step * step; onEnds += rigLux(hp(L, d, y), FRAME.U.map(x => -x)) * step * step; }
  const landed = onCarpet + onWalls + onEnds, share = onCarpet / RIG_PHOT.flux;
  R.say(landed / RIG_PHOT.flux > 0.85 && landed / RIG_PHOT.flux < 1.02, `lumens in = lux out: ${Math.round(landed).toLocaleString()} lm land on the room's surfaces of ${Math.round(RIG_PHOT.flux).toLocaleString()} lm emitted (${(landed / RIG_PHOT.flux * 100).toFixed(1)}%: carpet ${Math.round(onCarpet).toLocaleString()}, long walls ${Math.round(onWalls).toLocaleString()}, end walls ${Math.round(onEnds).toLocaleString()})`);
  R.say(Math.abs(share - RIG_PHOT.floorShare) < 0.03, `the carpet takes ${(share * 100).toFixed(0)}% of the flux; the dim assumes ${(RIG_PHOT.floorShare * 100).toFixed(0)}%`);
  const meanHouse = carpetMean * RIG_PHOT.dim + RIG_PHOT.bounce * HOUSE_LUX;
  R.say(pct(meanHouse, HOUSE_LUX) < 15, `the carpet's mean at house = 1: ${meanHouse.toFixed(0)} lux (${(carpetMean * RIG_PHOT.dim).toFixed(0)} direct + ${(RIG_PHOT.bounce * HOUSE_LUX).toFixed(0)} bounce) against the photographs' ${HOUSE_LUX}`);
  // the pool the canvas check reads: the brightest carpet point under fixture 11 (a profile, yaw 0)
}

// 1 and 5. the page
const P = await attach({ width: 1280, height: 800 });
try {
  await P.open('index.html'); await P.roam();
  const page = JSON.parse(await P.ev(`JSON.stringify({n:ngv.RIG_PHOT.n,u0:ngv.RIG_PHOT.u0,pitch:ngv.RIG_PHOT.pitch,d:ngv.RIG_PHOT.d,y:ngv.RIG_PHOT.y,tilt:ngv.RIG_PHOT.tilt,pI0:ngv.RIG_PHOT.profile.I0,ps:ngv.RIG_PHOT.profile.sigma,aI0:ngv.RIG_PHOT.par.I0,su:ngv.RIG_PHOT.par.su,sv:ngv.RIG_PHOT.par.sv,col:ngv.RIG_PHOT.col,bounce:ngv.RIG_PHOT.bounce,dim:ngv.RIG_PHOT.dim,flux:ngv.RIG_PHOT.flux,lux:ngv.HOUSE_LUX})`));
  const mine = { n: RIG_PHOT.n, u0: RIG_PHOT.u0, pitch: RIG_PHOT.pitch, d: RIG_PHOT.d, y: RIG_PHOT.y, tilt: RIG_PHOT.tilt, pI0: RIG_PHOT.profile.I0, ps: RIG_PHOT.profile.sigma, aI0: RIG_PHOT.par.I0, su: RIG_PHOT.par.su, sv: RIG_PHOT.par.sv, col: RIG_PHOT.col, bounce: RIG_PHOT.bounce, dim: RIG_PHOT.dim, flux: RIG_PHOT.flux, lux: HOUSE_LUX };
  // to 1e-6: the page's V8 and node's may differ in the last bits of exp and atan2
  const near = (a, b) => Array.isArray(a) ? a.every((v, i) => near(v, b[i])) : Math.abs(a - b) <= 1e-6 * Math.max(Math.abs(a), 1e-9);
  const same = Object.keys(mine).every(k => near(mine[k], page[k]));
  R.say(same, `the page's RIG_PHOT is the mirror's, number for number (dim ${page.dim.toFixed(4)}, flux ${Math.round(page.flux).toLocaleString()} lm)`);
  // the pool: walk fixture 11's aim to the carpet
  const f = fixture(11); const t = -(f.P[1] - FRAME.O[1]) / f.aim[1]; const pool = [f.P[0] + f.aim[0] * t, FRAME.O[1], f.P[2] + f.aim[2] * t];
  const between = [(pool[0] + fixture(12).P[0] + fixture(12).aim[0] * t) / 2, FRAME.O[1], (pool[2] + fixture(12).P[2] + fixture(12).aim[2] * t) / 2];
  const Hp = houseE(pool, [0, 1, 0]), Hb = houseE(between, [0, 1, 0]);
  const probe = JSON.parse(await P.ev(`(()=>{
    const R3=ngv.R, keepTM=R3.toneMapping, keepEx=R3.toneMappingExposure, keepMode=ngv.EXPO.mode, keepHouse=ngv.lit.house, keepLayers=ngv.state.layers;
    ngv.EXPO.mode='fixed'; R3.toneMappingExposure=1; R3.toneMapping=0; ngv.state.layers=[]; ngv.lit.house=1;
    const s2l=v=>{v/=255; return v<=0.04045?v/12.92:Math.pow((v+0.055)/1.055,2.4);};
    const read=()=>{ R3.render(ngv.scene, ngv.cam); const cv=R3.domElement, c=document.createElement('canvas'); c.width=c.height=1;
      const g=c.getContext('2d'); g.drawImage(cv, Math.floor(cv.width/2), Math.floor(cv.height/2), 1,1, 0,0,1,1);
      const d=g.getImageData(0,0,1,1).data; return 0.2126*s2l(d[0])+0.7152*s2l(d[1])+0.0722*s2l(d[2]); };
    const settle=()=>new Promise(r=>requestAnimationFrame(()=>requestAnimationFrame(()=>r())));
    return (async()=>{
      ngv.setCam(${pool[0]}, ${pool[1]}+2.0, ${pool[2]}, 0, -Math.PI/2); ngv.dirty(); await settle(); const a=read();
      ngv.setCam(${between[0]}, ${between[1]}+2.0, ${between[2]}, 0, -Math.PI/2); ngv.dirty(); await settle(); const b=read();
      R3.toneMapping=keepTM; R3.toneMappingExposure=keepEx; ngv.EXPO.mode=keepMode; ngv.lit.house=keepHouse; ngv.state.layers=keepLayers; ngv.dirty();
      return JSON.stringify({a,b}); })();})()`));
  const ratioCanvas = probe.a / Math.max(probe.b, 1e-6), ratioJs = Hp / Hb;
  R.say(pct(ratioCanvas, ratioJs) < 25, `canvas: a pool centre reads ${ratioCanvas.toFixed(2)}x the carpet between pools; the JS mirror says ${ratioJs.toFixed(2)}x (${pct(ratioCanvas, ratioJs).toFixed(1)}% off; pool ${(Hp * HOUSE_LUX).toFixed(0)} lux, between ${(Hb * HOUSE_LUX).toFixed(0)} lux)`);
  // the pictures
  await P.ev(`for(const s of ['#panel','#hint','.bar','#ghud','header','#top','#fab','#roamfab','#stkmove','#stklook']){document.querySelectorAll(s).forEach(e=>e.style.visibility='hidden');}`);
  await P.ev(`ngv.state.layers=[]; ngv.lit.house=1; ngv.dirty();`); await P.sleep(1200);
  for (const [name, x, y, z, yw, pt] of [['hall-end', -6.0, 1.70, 1.2, Math.PI, 0.06], ['north-wall', -20, 2.0, 0.5, -Math.PI / 2, 0.1], ['high-down', -24.0, 8.60, 2.2, Math.PI, -0.55], ['floor-low', -20.0, 0.45, 2.6, Math.PI, -0.14]]) {
    await P.ev(`ngv.setCam(${x},${y},${z},${yw},${pt}); ngv.dirty();`); await P.sleep(1300); await P.shot(`${out}/house-${name}.jpg`); }
  R.say(P.errors.length === 0, P.errors.length ? P.errors.join('\n') : 'no console errors or exceptions');
} catch (e) { R.say(false, 'page: ' + e.message); }
P.close();
console.log(R.done() ? 'FAIL' : 'PASS'); process.exit(R.done() ? 1 : 0);
