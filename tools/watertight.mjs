// 2026-09-10: IS THE CORRIDOR A CLOSED SOLID? THE OPEN-EDGE TEST, RUN ON THE SHIPPED PAGE.
//
// WHY THIS AND WHY NOW. tools/model_consistency.py compared the constants with each other and found two
// surfaces missing from the corridor: no downstand over an opening and no upstand under it. It found them
// because I guessed which relations to check. This does the same job WITHOUT guessing: it takes the
// geometry the browser actually built and runs the standard test for whether a surface encloses anything.
// No constant is trusted, because nothing is read from the source: the vertices come out of the scene
// graph after every matrix has been applied. And it runs against the LIVE SANDBOX, not a local copy, so
// what is audited is the file Lloyd opens.
//
// AN EDGE COUNT ALONE IS THE WRONG TEST, AND THE FIRST VERSION OF THIS FILE LEARNED IT THE EXPENSIVE WAY.
// It counted 148 once-used edges over 311 m and almost none of them were holes. Two reasons, both mine.
// First, T-JUNCTIONS: the corridor floor is ONE quad running u 3.0 to 47.0 while the wall back face is
// drawn in twelve short pieces between the openings. Those surfaces touch along the whole line, but a long
// edge and a short edge are not the same edge, so every join read as a boundary. Second, I hand-picked
// which meshes to include, so wherever a chosen mesh met an unchosen one its edge read as open too.
//
// THE RIGHT TEST IS COVERAGE. For every edge used by only one triangle, take its midpoint and ask whether
// any OTHER triangle in the model contains that point, within 2 mm of its plane. If one does, the surface
// is continuous there and the edge is a T-junction, not a hole. If none does, the surface really stops.
// Every analytic mesh goes in, not a subset, so nothing reads as open merely because I left its neighbour
// out of the list.
//
// WHAT IT CANNOT DO. It only sees the ANALYTIC quads. The wall itself is a baked scan mesh whose triangles
// were never meant to share edges with hand-built ones, so anything over 4000 vertices is skipped and the
// skips are printed. A closed surface can still be the wrong shape, and this says nothing about whether
// any of it is in the right place.
//   bash ~/scripts/headless-chrome.sh start 9334
//   CDP_PORT=9334 node tools/watertight.mjs
//   bash ~/scripts/headless-chrome.sh stop 9334
import { attach } from './cdp.mjs';

const O = [-54.907447, -1.43545, 3.040286];
const HU = [0.975681, 0, 0.219196];
const HD = [0.219196, 0, -0.975681];
const PAGE = process.env.SHOT_URL || 'https://lotron-electrical.github.io/ngv-hall-model/index.html';

const P = await attach({ port: +(process.env.CDP_PORT || 9334), width: 1200, height: 800 });
await P.send('Network.setCacheDisabled', { cacheDisabled: true }).catch(() => {});
console.log('loading', PAGE);
await P.send('Page.navigate', { url: `${PAGE}?cb=${Date.now()}` });
let ready = false;
for (let i = 0; i < 150; i++) {
  await P.sleep(500);
  if (await P.ev('!!(window.ngv && window.ngv.hall)').catch(() => false)) { ready = true; break; }
}
if (!ready) { console.log('THE PAGE NEVER BUILT ITS SCENE. Nothing can be audited.'); await P.close(); process.exit(1); }
await P.sleep(2000);

const data = await P.ev(`(()=>{
  const tris = []; const skipped = {}; const kept = {};
  ngv.hall.traverse(o => {
    if (!o.isMesh || !o.geometry) return;
    const nm = o.name || (o.material && o.material.name) || '(unnamed)';
    const pos = o.geometry.attributes && o.geometry.attributes.position;
    if (!pos) return;
    if (pos.count > 4000) { skipped[nm] = (skipped[nm]||0) + pos.count; return; }
    const idx = o.geometry.index ? o.geometry.index.array : null;
    const n = idx ? idx.length : pos.count;
    o.updateWorldMatrix(true, false);
    const M = o.matrixWorld.elements;
    const get = k => {
      const j = idx ? idx[k] : k;
      const x = pos.getX(j), y = pos.getY(j), z = pos.getZ(j);
      const w = M[3]*x + M[7]*y + M[11]*z + M[15];
      return [(M[0]*x+M[4]*y+M[8]*z+M[12])/w, (M[1]*x+M[5]*y+M[9]*z+M[13])/w, (M[2]*x+M[6]*y+M[10]*z+M[14])/w];
    };
    for (let k = 0; k + 2 < n; k += 3) { tris.push([get(k), get(k+1), get(k+2), nm]); kept[nm] = (kept[nm]||0) + 1; }
  });
  return { tris, skipped, kept };
})()`).catch(e => ({ err: String(e.message).slice(0, 400) }));

if (data.err) { console.log('the page threw:', data.err); await P.close(); process.exit(1); }
const sk = Object.entries(data.skipped || {}).sort((a, b) => b[1] - a[1]);
console.log(`${data.tris.length} analytic triangles kept, over ${Object.keys(data.kept).length} names`);
console.log(`${sk.length} meshes skipped as baked: ${sk.slice(0, 6).map(t => t[0] + ' ' + t[1]).join(', ')}`);

const toHall = w => {
  const q = [w[0] - O[0], w[1] - O[1], w[2] - O[2]];
  return [q[0] * HU[0] + q[2] * HU[2], q[0] * HD[0] + q[2] * HD[2], q[1]];
};
const T = data.tris.map(t => [toHall(t[0]), toHall(t[1]), toHall(t[2]), t[3]]);
const key = p => p.map(v => Math.round(v * 1000)).join(',');
const edges = new Map();
T.forEach((t, ti) => {
  for (let i = 0; i < 3; i++) {
    const a = key(t[i]), b = key(t[(i + 1) % 3]);
    const k = a < b ? `${a}|${b}` : `${b}|${a}`;
    const e = edges.get(k) || { n: 0, a: t[i], b: t[(i + 1) % 3], who: new Set(), ti };
    e.n++; e.who.add(t[3]); edges.set(k, e);
  }
});
const open = [...edges.values()].filter(e => e.n === 1);
const shared = [...edges.values()].filter(e => e.n === 2);
const over = [...edges.values()].filter(e => e.n > 2);
const len = e => Math.hypot(e.a[0] - e.b[0], e.a[1] - e.b[1], e.a[2] - e.b[2]);
console.log(`${edges.size} distinct edges: ${shared.length} shared, ${open.length} used once, ${over.length} used more than twice`);

const sub = (a, b) => [a[0] - b[0], a[1] - b[1], a[2] - b[2]];
const cross = (a, b) => [a[1]*b[2] - a[2]*b[1], a[2]*b[0] - a[0]*b[2], a[0]*b[1] - a[1]*b[0]];
const dot = (a, b) => a[0]*b[0] + a[1]*b[1] + a[2]*b[2];
function covers(t, p) {
  const u = sub(t[1], t[0]), v = sub(t[2], t[0]), w = sub(p, t[0]);
  const nrm = cross(u, v);
  const nl = Math.hypot(nrm[0], nrm[1], nrm[2]);
  if (nl < 1e-9) return false;
  if (Math.abs(dot(w, nrm)) / nl > 0.002) return false;
  const uu = dot(u, u), uv = dot(u, v), vv = dot(v, v), wu = dot(w, u), wv = dot(w, v);
  const den = uv * uv - uu * vv;
  if (Math.abs(den) < 1e-12) return false;
  const s = (uv * wv - vv * wu) / den, r = (uv * wu - uu * wv) / den;
  return s >= -0.001 && r >= -0.001 && s + r <= 1.001;
}
const tj = []; const holes = [];
for (const e of open) {
  const mid = [0.5 * (e.a[0] + e.b[0]), 0.5 * (e.a[1] + e.b[1]), 0.5 * (e.a[2] + e.b[2])];
  let hit = false;
  for (let i = 0; i < T.length; i++) { if (i === e.ti) continue; if (covers(T[i], mid)) { hit = true; break; } }
  if (hit) { tj.push(e); } else { holes.push(e); }
}
const sum = arr => arr.reduce((s, e) => s + len(e), 0);
console.log('');
console.log(`${tj.length} of the once-used edges are T-JUNCTIONS: another triangle covers the midpoint, so`);
console.log(`the surface is continuous there. ${sum(tj).toFixed(1)} m of them, and none is a hole.`);
console.log(`${holes.length} are REAL BOUNDARIES, ${sum(holes).toFixed(1)} m, where the model simply stops.`);

const byplane = new Map();
for (const e of holes) {
  let k = 'not on one plane';
  if (Math.abs(e.a[0] - e.b[0]) < 0.01) k = `u ${e.a[0].toFixed(3)}`;
  else if (Math.abs(e.a[1] - e.b[1]) < 0.01) k = `d ${e.a[1].toFixed(3)}`;
  else if (Math.abs(e.a[2] - e.b[2]) < 0.01) k = `h ${e.a[2].toFixed(3)}`;
  const g = byplane.get(k) || { n: 0, m: 0, who: new Set() };
  g.n++; g.m += len(e); for (const w of e.who) g.who.add(w);
  byplane.set(k, g);
}
console.log('');
console.log('where the model stops, by plane, longest first:');
for (const [k, g] of [...byplane.entries()].sort((a, b) => b[1].m - a[1].m).slice(0, 16)) {
  console.log(`   ${k.padEnd(20)} ${String(g.n).padStart(4)} edges ${g.m.toFixed(1).padStart(8)} m   ${[...g.who].slice(0, 4).join(' ')}`);
}

// AND THE OTHER SIGNAL IN THE SAME NUMBERS, WHICH IS NOT A HOLE BUT A DOUBLING. An edge shared by more
// than two triangles means surfaces meet three ways or lie on top of each other. In a hand-built model
// that is usually one quad drawn twice, which costs a draw call and can flicker where the two fight for
// the same depth. It is worth naming even when it is harmless.
console.log('');
if (!over.length) {
  console.log('NO EDGE IS USED MORE THAN TWICE: nothing here is drawn on top of itself.');
} else {
  const byname = new Map();
  for (const e of over) {
    const k = [...e.who].sort().join(' + ');
    const g = byname.get(k) || { n: 0, m: 0, times: 0 };
    g.n++; g.m += len(e); g.times = Math.max(g.times, e.n); byname.set(k, g);
  }
  console.log(`${over.length} EDGES ARE USED MORE THAN TWICE, ${sum(over).toFixed(1)} m, so something is`);
  console.log('drawn three ways or on top of itself:');
  for (const [k, g] of [...byname.entries()].sort((a, b) => b[1].m - a[1].m).slice(0, 8)) {
    console.log(`   ${g.n} edges, ${g.m.toFixed(1)} m, up to ${g.times} triangles: ${k}`);
  }
}

const CN = ['corridor-floor', 'corridor-ceiling', 'corridor-near', 'corridor-downstand',
  'corridor-upstand', 'corridor-back'];
const atR = holes.filter(e => Math.abs(e.a[1] + 0.930) < 0.01 && Math.abs(e.b[1] + 0.930) < 0.01
  && [...e.who].some(w => CN.includes(w)));
console.log('');
console.log(`ON THE BACK OF THE REVEAL, d -0.930, the corridor has ${atR.length} real boundary edges.`);
if (!atR.length) {
  console.log('None at all, so the downstand and upstand added earlier today did close it: every join');
  console.log('along that plane is either shared or a T-junction, and the corridor stops only where it');
  console.log('is meant to. That is the fix verified in the shipped page rather than in my reasoning.');
} else {
  console.log('Which is not none, so something on that plane still does not meet its neighbour:');
  for (const e of atR.slice(0, 8)) {
    console.log(`   u ${e.a[0].toFixed(3)} to ${e.b[0].toFixed(3)}, h ${e.a[2].toFixed(3)} to ${e.b[2].toFixed(3)} on ${[...e.who].join(' ')}`);
  }
}

console.log('');
if (P.errors.length) {
  console.log(`the page reported ${P.errors.length} errors while this ran:`);
  for (const e of P.errors.slice(0, 6)) console.log('   ' + e);
} else {
  console.log('the page reported no errors while this ran.');
}
await P.close();
