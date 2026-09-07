// THE ENERGY AUDIT (Lloyd, 2026-09-07: "the lighting looks very one-dimensional").
// Before anything in the render was changed, this asks the only question that matters: does the
// light the page puts on the floor equal the light the datasheet says the strips make? It checks
// four things and prints ok/FAIL for each, exiting 1 on any failure:
//
//  1. THE DATASHEET. The band lights carry Phi/4pi in units of HOUSE_LUX. Summed back up over one
//     column they must equal (runs per column) x (lm/m of the driven dies) x (cover transmittance)
//     x (strip length), to the lumen.
//  2. THE FLOOR. The shader's closed form, evaluated in JS off the LIVE lightPos/lightCol, against
//     the continuous analytic integral of the same vertical Lambertian line, at 1, 3 and 6 m out
//     from the foot. Within 15%.
//  3. FLUX CONSERVATION. The sum of E x dA over a 60 m sphere around one column equals that
//     column's emitted lumens x the cover's transmittance. Within 10%. (A sphere, not the hall's
//     own surfaces: the hall is not a closed box -- it opens into the courtyard and the ceiling
//     void -- so its surfaces would fail a conservation test for a reason that has nothing to do
//     with the lighting model.)
//  4. THE SHADER ITSELF. One pixel of carpet, read off the canvas three times with tone mapping
//     off -- dark, house alone, strips alone -- gives E with the albedo and the daylight term
//     divided out, and it must be the E the JS says. Within 30%, because the readback is 8-bit.
//
// and then the camera: exposure pinned at 1.0 with the house at 100%, open past 1 with it off,
// and the lumen and watt readouts byte-identical to the page before any of this was added.
//
// Usage: node tools/light-audit.mjs [outdir]
// Needs the static server on 8877 and a headless Chrome on NGV_PORT (default 9333).
import fs from 'node:fs';
import { attach, reporter } from './cdp.mjs';
import { houseE, RIG_PHOT } from './rigphot.mjs';

const out = process.argv[2];
if (out) fs.mkdirSync(out, { recursive: true });
const R = reporter();
const P = await attach({ width: 1280, height: 800 });

// ---- the JS mirror of the room shader's line-light term, so the audit and the picture cannot
// drift: same clamp, same horizon clip, same Lambertian r^4 closed form, same 4/pi.
const LAMB = 4 / Math.PI;
function segE(lp, lc, n, p, N, colR, only) {
  const E = [0, 0, 0];
  for (let i = 0; i < n; i++) {
    if (only !== undefined && Math.abs(lp[i * 4 + 3] - only) > 1e-6) continue;
    const vx = lp[i * 4] - p[0], vy = lp[i * 4 + 1] - p[1], vz = lp[i * 4 + 2] - p[2];
    const h = Math.max(lc[i * 4 + 3], 0.01);
    const hd2 = Math.max(vx * vx + vz * vz, colR * colR * 0.25), rho = Math.sqrt(hd2), e = vy;
    const aN = N[0] * vx + N[1] * vy + N[2] * vz, bN = N[1];
    let t0 = 0, t1 = h;
    if (bN > 1e-6) t0 = Math.min(Math.max(-aN / bN, 0), h);
    else if (bN < -1e-6) t1 = Math.min(Math.max(-aN / bN, 0), h);
    else if (aN <= 0) t1 = t0;
    const A = aN - bN * e, u0 = t0 + e, u1 = t1 + e;
    const r0 = hd2 + u0 * u0, r1 = hd2 + u1 * u1;
    const da = Math.atan2((u1 - u0) * hd2, rho * (hd2 + u0 * u1));
    const I = Math.max(A * (u1 / r1 - u0 / r0) / (2 * rho) + A * da / (2 * hd2) - bN * rho * 0.5 * (1 / r1 - 1 / r0), 0) * (LAMB / h);
    E[0] += lc[i * 4] * I; E[1] += lc[i * 4 + 1] * I; E[2] += lc[i * 4 + 2] * I;
  }
  return E;
}
const lum = c => 0.2126 * c[0] + 0.7152 * c[1] + 0.0722 * c[2];
const pct = (a, b) => Math.abs(a - b) / Math.max(Math.abs(b), 1e-9) * 100;

try {
  // ---- the readouts BEFORE any of this, straight out of git, so the audit can prove the lumen
  // and watt figures did not move by a digit. Served as its own page beside the live one.
  const before = fs.existsSync('.light-before.html');
  await P.open('index.html');
  await P.roam();     // off the object's orbit, so setCam sticks for the canvas readback
  await P.ev(`ngv.state.layers=[{on:true,anim:'solid',opacity:1,blend:'over',speed:0,A:{h:0,s:0,v:1},B:{h:0,s:0,v:0},dens:0.02}];
    ngv.state.sel=0; ngv.state.level=1; ngv.lit.house=0; ngv.dirty();`);
  await P.sleep(1600);

  const C = await P.ev(`(()=>{const mats=[]; ngv.scene.traverse(o=>{if(o.isMesh)for(const m of [].concat(o.material)) if(m.uniforms&&m.uniforms.lightPos&&!mats.includes(m))mats.push(m);});
    const u=mats[0].uniforms; const bl=u.blades.value.image.data; let mn=9,mx=0;
    for(let ci=0;ci<12;ci++)for(let b=0;b<256;b++){const v=bl[(ci*256+b)*4]/255*8; if(v<mn)mn=v; if(v>mx)mx=v;}
    return JSON.stringify({n:u.nLights.value, pos:Array.from(u.lightPos.value), col:Array.from(u.lightCol.value),
      colR:u.colR.value, alb:u.bounceAlb.value.toArray(), floorY:ngv.floorY,
      bladeMin:mn, bladeMax:mx, metres:ngv.P.metres, count:ngv.state.count, cover:ngv.state.cover,
      lm:ngv.lit.lmStrip, area:ngv.hallArea, runstat:document.getElementById('runstat').textContent});})()`);
  const S = JSON.parse(C);
  const lp = Float64Array.from(S.pos), lc = Float64Array.from(S.col);

  // the blade profile: with every gap driven the same it is flat, which is what lets this audit
  // leave the azimuthal term out of its own evaluation
  R.say(Math.abs(S.bladeMax - 1) < 0.06 && Math.abs(S.bladeMin - 1) < 0.06,
    `blade profile flat with all ${S.count} gaps lit (min ${S.bladeMin.toFixed(3)}, max ${S.bladeMax.toFixed(3)}): the audit's evaluation may drop it`);

  // ---- 1. the datasheet. One column's bands, summed.
  const w0 = lp[3];                       // the first column's blade row = its identity
  let Phi = 0, y0 = 1e9, y1 = -1e9;
  for (let i = 0; i < S.n; i++) {
    if (Math.abs(lp[i * 4 + 3] - w0) > 1e-6) continue;
    Phi += lum([lc[i * 4], lc[i * 4 + 1], lc[i * 4 + 2]]) * 4 * Math.PI * 150;   // back out of I/HOUSE_LUX
    y0 = Math.min(y0, lp[i * 4 + 1]); y1 = Math.max(y1, lp[i * 4 + 1] + lc[i * 4 + 3]);
  }
  const H = y1 - y0, LEN = S.metres / 12 / S.count;      // one run's length, from the page's own metres
  // the white scene drives the W die alone: 700 lm/m of 4000 K, through the black cover's 25%
  const T = { black: 0.25, opal: 0.65, none: 1 }[S.cover];
  const want = S.count * 700 * T * LEN;
  R.say(pct(Phi, want) < 2, `datasheet: column 1 emits ${Math.round(Phi).toLocaleString()} lm into the room, ${S.count} runs x 700 lm/m (W die) x ${T} cover x ${LEN.toFixed(2)} m = ${Math.round(want).toLocaleString()} lm (${pct(Phi, want).toFixed(2)}% off)`);
  const phiPerM = Phi / H;
  R.note(`column 1: ${H.toFixed(2)} m of lit shaft, ${Math.round(phiPerM)} lm/m into the room, foot ${y0.toFixed(2)} m, floor ${S.floorY.toFixed(2)} m`);

  // ---- 2. the floor at 1, 3 and 6 m
  const cx = lp[0], cz = lp[2];
  const rows = [];
  for (const rho of [1, 3, 6]) {
    const p = [cx + rho, S.floorY, cz];
    const E = segE(lp, lc, S.n, p, [0, 1, 0], S.colR, w0);
    const got = lum(E) * 150;                                        // back into lux
    // the continuous analytic: E = (phi/pi^2) rho/2 [1/(rho^2+a^2) - 1/(rho^2+b^2)]
    const a = y0 - S.floorY, b = y1 - S.floorY;
    const ana = (phiPerM / (Math.PI * Math.PI)) * rho * 0.5 * (1 / (rho * rho + a * a) - 1 / (rho * rho + b * b));
    rows.push([rho, got, ana]);
    R.say(pct(got, ana) < 15, `floor at ${rho} m from the foot: shader ${got.toFixed(1)} lux, analytic Lambertian line ${ana.toFixed(1)} lux (${pct(got, ana).toFixed(1)}% off)`);
  }
  // the figure the brief carried, and why it is not the reference
  R.note(`for the record: (phi/pi)(1/rho - 1/sqrt(rho^2+H^2)) at 3 m is ${((phiPerM / Math.PI) * (1 / 3 - 1 / Math.sqrt(9 + H * H))).toFixed(0)} lux.`);
  R.note(`that puts ONE Lambertian lobe's peak intensity on ALL ${S.count} gaps' flux at once and is 4x over: with the gaps facing`);
  R.note(`8 ways, a floor point sees about a quarter of the column's flux in its own direction, which is what the shader does.`);

  // ---- 3. flux conservation over a 60 m sphere
  {
    const Rs = 60, N = 20000; let sum = 0;
    for (let i = 0; i < N; i++) {
      // a Fibonacci sphere: equal solid angle per sample, no clustering at the poles
      const z = 1 - 2 * (i + 0.5) / N, r = Math.sqrt(Math.max(0, 1 - z * z)), th = Math.PI * (1 + Math.sqrt(5)) * i;
      const d = [r * Math.cos(th), z, r * Math.sin(th)];
      const mid = [cx, (y0 + y1) / 2, cz];
      const p = [mid[0] + d[0] * Rs, mid[1] + d[1] * Rs, mid[2] + d[2] * Rs];
      const E = segE(lp, lc, S.n, p, [-d[0], -d[1], -d[2]], S.colR, w0);
      sum += lum(E) * 150;
    }
    const flux = sum / N * 4 * Math.PI * Rs * Rs;
    R.say(pct(flux, Phi) < 10, `flux conservation: E x dA over a ${Rs} m sphere is ${Math.round(flux).toLocaleString()} lm against ${Math.round(Phi).toLocaleString()} lm emitted (${pct(flux, Phi).toFixed(2)}% off)`);
  }

  // ---- 4. the shader itself, read back off the canvas.
  // The carpet photograph is not one flat colour and the page's E carries an ambient floor and a
  // daylight term as well as the LEDs, so no single pixel can be divided by anything known. Three
  // reads of the SAME pixel with tone mapping off settle it with no assumptions at all:
  //   dark  = albedo x (ambient + day)
  //   house = albedo x (1 + ambient + day)
  //   led   = albedo x (ambient + day + E)
  // and E = (led - dark) / (house - dark), in units of HOUSE_LUX, albedo and daylight cancelled.
  {
    const rho = 3;
    const probe = await P.ev(`(()=>{
      const R3=ngv.R, keepTM=R3.toneMapping, keepEx=R3.toneMappingExposure, keepMode=ngv.EXPO.mode;
      const keepHouse=ngv.lit.house, keepOn=ngv.state.layers[0].on;
      ngv.EXPO.mode='fixed'; R3.toneMappingExposure=1; R3.toneMapping=0;
      const mats=[]; ngv.scene.traverse(o=>{if(o.isMesh)for(const m of [].concat(o.material))if(!mats.includes(m))mats.push(m);});
      // the JS mirror below is the DIRECT term, so the column shadows come off for the comparison
      // and go back on for the figure that follows it
      const pm=[]; ngv.scene.traverse(o=>{if(o.isMesh)for(const m of [].concat(o.material))if(m.uniforms&&m.uniforms.nOcc&&!pm.includes(m))pm.push(m);});
      const keepOcc=pm[0].uniforms.nOcc.value; for(const m of pm)m.uniforms.nOcc.value=0;
      for(const m of mats)m.needsUpdate=true;
      // straight down onto the carpet 3 m out from column 1's foot, nothing else in the way
      ngv.setCam(${cx + rho}, ${S.floorY} + 2.0, ${cz}, 0, -Math.PI/2); ngv.dirty();
      const s2l=v=>{v/=255; return v<=0.04045?v/12.92:Math.pow((v+0.055)/1.055,2.4);};
      const read=()=>{ R3.render(ngv.scene, ngv.cam);
        const cv=R3.domElement, c=document.createElement('canvas'); c.width=c.height=1;
        const g=c.getContext('2d'); g.drawImage(cv, Math.floor(cv.width/2), Math.floor(cv.height/2), 1,1, 0,0,1,1);
        const d=g.getImageData(0,0,1,1).data; return [s2l(d[0]),s2l(d[1]),s2l(d[2]),d[0],d[1],d[2]]; };
      const settle=()=>new Promise(r=>requestAnimationFrame(()=>requestAnimationFrame(()=>r())));
      return (async()=>{
        ngv.lit.house=0; ngv.state.layers[0].on=false; ngv.dirty(); await settle();
        const dark=read();
        ngv.lit.house=1; ngv.dirty(); await settle();
        const house=read();
        ngv.lit.house=0; ngv.state.layers[0].on=true; ngv.dirty(); await settle();
        const led=read();
        for(const m of pm)m.uniforms.nOcc.value=keepOcc; ngv.dirty(); await settle();
        const shad=read();
        R3.toneMapping=keepTM; R3.toneMappingExposure=keepEx; ngv.EXPO.mode=keepMode;
        ngv.lit.house=keepHouse; ngv.state.layers[0].on=keepOn; ngv.dirty();
        for(const m of mats)m.needsUpdate=true;
        return JSON.stringify({dark,house,led,shad,day:ngv.lit.day,occ:keepOcc});
      })();})()`);
    const pr = JSON.parse(probe);
    // the house pixel is albedo x H, where H is the rig's pools plus the bounce at this very
    // point (2026-09-07: the house is no longer a flat 1.0); the ratio still cancels the albedo
    const Hc = RIG_PHOT.col.map(c => c * houseE([cx + rho, S.floorY, cz], [0, 1, 0]));
    const E = [0, 1, 2].map(k => (pr.led[k] - pr.dark[k]) / Math.max(pr.house[k] - pr.dark[k], 1e-6) * Hc[k]);
    const Ejs = segE(lp, lc, S.n, [cx + rho, S.floorY, cz], [0, 1, 0], S.colR);
    const got = lum(E) * 150, exp = lum(Ejs) * 150;
    const Esh = [0, 1, 2].map(k => (pr.shad[k] - pr.dark[k]) / Math.max(pr.house[k] - pr.dark[k], 1e-6) * Hc[k]);
    R.note(`canvas readback at 3 m, the same pixel four ways: dark ${pr.dark.slice(3).join(',')} / house ${pr.house.slice(3).join(',')} / strips ${pr.led.slice(3).join(',')} / strips + ${pr.occ} column shadows ${pr.shad.slice(3).join(',')} sRGB`);
    R.note(`the shadows take ${(100 - lum(Esh) / Math.max(lum(E), 1e-9) * 100).toFixed(0)}% off this fragment (${(lum(Esh) * 150).toFixed(1)} lux with them, ${(lum(E) * 150).toFixed(1)} without)`);
    R.say(pct(got, exp) < 30, `the shader agrees with the audit: ${got.toFixed(1)} lux read off the canvas, ${exp.toFixed(1)} lux from the same formula in JS (${pct(got, exp).toFixed(1)}% off, all 12 columns)`);
  }

  // ---- the camera
  {
    await P.ev(`ngv.lit.house=1; ngv.dirty();`); await P.sleep(1800);
    const e1 = await P.ev(`ngv.EXPO.now`);
    R.say(Math.abs(e1 - 1) < 0.01, `exposure holds at 1.000 with the house at 100% (read ${e1.toFixed(4)}): every quote picture and every day shot is unchanged`);
    // a dim scene: the house off and the strips at 8%
    await P.ev(`ngv.lit.house=0; ngv.state.level=0.08; ngv.dirty();`); await P.sleep(2200);
    const e2 = await P.ev(`ngv.EXPO.now`), m2 = await P.ev(`ngv.EXPO.mean`);
    R.say(e2 > 1.5, `exposure opens to x${e2.toFixed(2)} with the house off and the strips at 8% (mean ${m2.toFixed(1)} lux on ${Math.round(S.area)} m2 of hall)`);
    await P.ev(`ngv.EXPO.mode='fixed';`); await P.sleep(1400);
    const e3 = await P.ev(`ngv.EXPO.now`);
    R.say(Math.abs(e3 - 1) < 0.01, `Menu > Camera > Exposure: Fixed pins it back at 1.000 (read ${e3.toFixed(4)})`);
    await P.ev(`ngv.EXPO.mode='auto'; ngv.state.level=1; ngv.dirty();`);
  }

  // ---- the readouts, against the page as it was before the render work
  if (before) {
    await P.open('.light-before.html');
    await P.ev(`ngv.state.layers=[{on:true,anim:'solid',opacity:1,blend:'over',speed:0,A:{h:0,s:0,v:1},B:{h:0,s:0,v:0},dens:0.02}];
      ngv.state.sel=0; ngv.state.level=1; ngv.lit.house=0; ngv.dirty();`);
    await P.sleep(1600);
    const b = await P.ev(`document.getElementById('runstat').textContent`);
    const bs = await P.ev(`document.getElementById('stat').textContent`);
    await P.open('index.html');
    await P.ev(`ngv.state.layers=[{on:true,anim:'solid',opacity:1,blend:'over',speed:0,A:{h:0,s:0,v:1},B:{h:0,s:0,v:0},dens:0.02}];
      ngv.state.sel=0; ngv.state.level=1; ngv.lit.house=0; ngv.dirty();`);
    await P.sleep(1600);
    const a = await P.ev(`document.getElementById('runstat').textContent`);
    const as = await P.ev(`document.getElementById('stat').textContent`);
    // the exposure reading is appended to the running line and is the ONLY thing allowed to differ
    const strip = x => x.replace(/ · exposure .*$/, '');
    R.say(strip(a) === strip(b), `lumens and watts unchanged`);
    R.note(`before: ${b}`);
    R.note(`after:  ${a}`);
    R.say(as === bs, `the model line unchanged`);
    R.note(`before: ${bs}`);
    R.note(`after:  ${as}`);
  } else {
    R.note('tools/.light-before.html is not there, so the readouts were not diffed against git HEAD');
    R.note(`git show HEAD:index.html > .light-before.html   (then re-run)`);
  }

  R.say(P.errors.length === 0, `no console errors or exceptions${P.errors.length ? ': ' + P.errors.join(' | ') : ''}`);
  if (out) fs.writeFileSync(out + '/audit-lights.json', JSON.stringify({ rows, Phi, phiPerM, H, area: S.area, alb: S.alb, colR: S.colR }, null, 1));
} catch (e) {
  console.log('FAIL ' + e.message);
  P.close(); process.exit(1);
}
P.close();
process.exit(R.done() ? 1 : 0);
