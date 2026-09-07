// THE HOUSE LIGHT'S PHOTOMETRY, mirrored from index.html RIG_PHOT (2026-09-07). The page and this
// file must agree number for number; tools/house-audit.mjs asserts that against window.ngv.RIG_PHOT.
//
// The 23 fixtures on the permanent truss (RIG in index.html: u = 1.5 + 2 i, d = 2.2, hung 8.52 m
// above the carpet, pitched 55 degrees below level into the room, yawed (i*7 mod 5 - 2) x 0.15 rad
// along the hall, profiles on the even seats and PARs on the odd) are the house light. Each is a
// Gaussian cone: the profile an ETC Source Four 26 degree at 750 W (about 105 kcd on axis, field
// 26 degrees, sigma 11.5 degrees), the PAR a PAR64 CP62 medium flood at 1 kW (about 60 kcd on axis,
// 44 x 24 degree beam, sigma 26 x 14 degrees, the wide axis along the hall). Flux of a Gaussian
// cone is integrated numerically (the PAR's 26 degree sigma is past small-angle), the rig at full
// makes about 380,000 lm; the photographs' house level is HOUSE_LUX = 150 lux on the carpet, which
// the rig reaches dimmed to `dim` (`direct` x 150 lux over the carpet's 753 m2 with `floorShare` of
// the flux landing there, the audit's own measurement), the rest arriving as the room's first
// bounce, `bounce` x 150 lux, falling off with height; direct + bounce = 1.
export const HOUSE_LUX = 150;
export const RIG_PHOT = (() => {
  const P = { n: 23, u0: 1.5, pitch: 2.0, d: 2.2, y: 8.52, tilt: 0.96,
    profile: { I0: 105000, sigma: 11.5 * Math.PI / 180 },
    par: { I0: 60000, su: 26 * Math.PI / 180, sv: 14 * Math.PI / 180 },
    col: [1.15, 0.97, 0.80], direct: 0.75, bounce: 0.25, floorShare: 0.95, floorArea: 48.9 * 15.4 };
  // a cone's flux, integrated over its hemisphere (the PAR's 26 degree sigma is past the small-angle
 // closed form by 6%): I(theta, phi) sin(theta) dtheta dphi on a 180 x 180 grid
 const coneFlux=(I0,su,sv)=>{ let F=0; const n=180; for(let a=0;a<n;a++){ const th=(a+0.5)/n*Math.PI/2; for(let b=0;b<n;b++){ const ph=(b+0.5)/n*2*Math.PI;
   const tu=Math.atan2(Math.sin(th)*Math.cos(ph),Math.cos(th)), tv=Math.atan2(Math.sin(th)*Math.sin(ph),Math.cos(th));
   F+=I0*Math.exp(-(tu*tu/(su*su)+tv*tv/(sv*sv)))*Math.sin(th)*(Math.PI/2/n)*(2*Math.PI/n); } } return F; };
  P.fluxProfile = coneFlux(P.profile.I0, P.profile.sigma, P.profile.sigma);
  P.fluxPar = coneFlux(P.par.I0, P.par.su, P.par.sv);
  P.flux = 12 * P.fluxProfile + 11 * P.fluxPar;
  P.dim = P.direct * HOUSE_LUX * P.floorArea / (P.floorShare * P.flux);
  return P;
})();
export const FRAME = { O: [-54.907447, -1.43545, 3.040286], U: [0.975681, 0, 0.219196], N: [0.219186, 0, -0.975639] };

const add = (a, b, s = 1) => [a[0] + b[0] * s, a[1] + b[1] * s, a[2] + b[2] * s];
const dot = (a, b) => a[0] * b[0] + a[1] * b[1] + a[2] * b[2];
const norm = a => { const l = Math.hypot(...a); return [a[0] / l, a[1] / l, a[2] / l]; };
const cross = (a, b) => [a[1] * b[2] - a[2] * b[1], a[2] * b[0] - a[0] * b[2], a[0] * b[1] - a[1] * b[0]];

// one fixture's position and aim, world space
export function fixture(i) {
  const R = RIG_PHOT, { O, U, N } = FRAME;
  const yawA = ((i * 7) % 5 - 2) * 0.15, cp = Math.cos(R.tilt), sp = Math.sin(R.tilt);
  const aim = norm(add(add([N[0] * cp, N[1] * cp, N[2] * cp], U, Math.sin(yawA) * cp), [0, -sp, 0]));
  let P = add(add(O, U, R.u0 + R.pitch * i), N, R.d); P = add(P, [0, R.y, 0]); P = add(P, aim, 0.12);
  return { P, aim, profile: i % 2 === 0 };
}

// intensity toward a direction, candela, the same cone the shader evaluates
export function candela(i, vn, aim) {
  const R = RIG_PHOT, { U } = FRAME;
  const ca = dot(vn, aim); if (ca <= 0.05) return 0;
  const ax = norm(add(U, aim, -dot(U, aim))), ay = cross(aim, ax);
  const tu = Math.atan2(dot(vn, ax), ca), tv = Math.atan2(dot(vn, ay), ca);
  return i % 2 === 0 ? R.profile.I0 * Math.exp(-(tu * tu + tv * tv) / (R.profile.sigma ** 2))
    : R.par.I0 * Math.exp(-(tu * tu / R.par.su ** 2 + tv * tv / R.par.sv ** 2));
}

// direct illuminance at p with normal n, in lux, rig at FULL (multiply by RIG_PHOT.dim for house = 1)
export function rigLux(p, n) {
  let E = 0;
  for (let i = 0; i < RIG_PHOT.n; i++) {
    const f = fixture(i); const v = add(p, f.P, -1); const r2 = Math.max(dot(v, v), 1); const vn = norm(v);
    const I = candela(i, vn, f.aim); if (!I) continue;
    E += I * Math.max(-dot(n, vn), 0) / r2;
  }
  return E;
}

// the house E at p (units of HOUSE_LUX, before the colour), exactly the shader's expression
export function houseE(p, n) {
  const hy = Math.min(Math.max((p[1] - FRAME.O[1]) / 12.2, 0), 1);
  return rigLux(p, n) * RIG_PHOT.dim / HOUSE_LUX + RIG_PHOT.bounce * (1 - 0.5 * hy);
}
