// 2026-09-10: THE TWO REPRESENTATIONS OF THIS BUILDING, MEASURED AGAINST EACH OTHER.
//
// THE REDUNDANCY NOBODY HAS USED. This file carries the hall twice. There is the ANALYTIC model, every
// quad of it placed by a ray or a photometric instrument and argued for in the comments above. And there
// is the BAKED SCAN, a photogrammetric mesh built from photographs of the room, which yesterday's
// visibility run showed is what a visitor actually looks at on the balconies. Two descriptions of one
// building, from different evidence, in the same file. Where they overlap they must agree, and where they
// do not, one of them is wrong. That is a redundancy the target itself provides, which this project has
// learnt is one of only three things that ever catches an error.
//
// WHAT IT MEASURES. For every analytic triangle, the signed distance from every baked vertex that lands on
// it, within a slab either side. Gathered per surface NAME, so the answer comes out as "the bake sits 8 mm
// in front of gallery-fascia over 4000 points" rather than as one number for the hall.
//
// THE CONTROL IS BUILT IN AND IT IS NOT OPTIONAL. Surfaces nobody disputes go through the same machine:
// the hall floor, the columns, the north wall face. If those do not come back near zero, then the two
// representations are not registered to each other and NOTHING about any other surface can be read. And
// if they come back near a common non-zero number, that is a global offset to be differenced out rather
// than a fault in any one surface.
//
// WHAT IT CANNOT DO. The bake has its own error, which is why every surface is reported against the bake's
// own scatter about it rather than against zero. A surface with no bake over it cannot be tested at all,
// and there are many: the corridor behind the wall was never scanned.
//   bash ~/scripts/headless-chrome.sh start 9334
//   CDP_PORT=9334 node tools/bake_vs_model.mjs
//   bash ~/scripts/headless-chrome.sh stop 9334
import fs from 'node:fs';
import { attach } from './cdp.mjs';

const PAGE = process.env.SHOT_URL || 'https://lotron-electrical.github.io/ngv-hall-model/index.html';
// WHICH MESHES ARE THE SCAN IS A QUESTION OF NAME, NOT SIZE, and the first run of this got it wrong in a
// way that made the whole thing meaningless. Splitting on vertex count put canopy-glass-pieces (308k) and
// an unnamed mesh (132k) on the scan side, and it also split the scan itself: clean-hall-textured comes in
// thirty-odd chunks and the ones under the threshold stayed on the analytic side. The result was the
// canopy compared with ITSELF, 333493 points with a noise of 0.000, which is not a measurement of anything.
// The scan is the clean-hall-textured chunks and nothing else, so that is what the split says now.
const SCAN = /^clean-hall-textured/;
const SLAB = 0.35;      // metres either side of an analytic face that a baked vertex may lie in
const CAPV = 900000;    // baked vertices kept, strided evenly if there are more
const SAMPLE = 800;     // distances returned per surface name

const P = await attach({ port: +(process.env.CDP_PORT || 9334), width: 1000, height: 700 });
await P.send('Network.setCacheDisabled', { cacheDisabled: true }).catch(() => {});
console.log('loading', PAGE);
await P.send('Page.navigate', { url: `${PAGE}?cb=${Date.now()}` });
let ready = false;
for (let i = 0; i < 150; i++) { await P.sleep(500); if (await P.ev('!!(window.ngv && window.ngv.hall)').catch(() => false)) { ready = true; break; } }
if (!ready) { console.log('THE PAGE NEVER BUILT ITS SCENE. Nothing can be compared.'); await P.close(); process.exit(1); }
await P.sleep(2500);

// MODE 'dump': HAND BOTH DESCRIPTIONS TO PYTHON AND STOP. The slab test above answers "does the scan lie
// on this surface, and where", and with the scan properly identified the answer for almost every surface
// the goal names is NO POINTS AT ALL. That is not nothing, but it is the wrong question asked twice. The
// right one is HOW FAR AWAY the scan is, and whether it is even present nearby, because a surface with the
// scan half a metre off it is a contradiction while a surface with no scan for three metres around is
// simply a place nobody scanned. Neither can be got from a fixed slab, so both descriptions come out here
// and the distances are worked offline where the search radius is free.
if (process.argv[2] === 'dump') {
  const g = await P.ev(`(()=>{
    const O=[-54.907447,-1.43545,3.040286], HU=[0.975681,0,0.219196], HD=[0.219196,0,-0.975681];
    const toHall = w => { const q=[w[0]-O[0], w[1]-O[1], w[2]-O[2]];
      return [q[0]*HU[0]+q[2]*HU[2], q[0]*HD[0]+q[2]*HD[2], q[1]]; };
    const scan=[]; const tri={}; const counts={};
    ngv.scene.traverse(o=>{
      if(!o.isMesh||!o.geometry) return;
      const pos=o.geometry.attributes&&o.geometry.attributes.position; if(!pos) return;
      const nm=o.name||(o.material&&o.material.name)||'(unnamed)';
      o.updateWorldMatrix(true,false); const M=o.matrixWorld.elements;
      const get=j=>{ const x=pos.getX(j), y=pos.getY(j), z=pos.getZ(j);
        const w=M[3]*x+M[7]*y+M[11]*z+M[15];
        return toHall([(M[0]*x+M[4]*y+M[8]*z+M[12])/w,(M[1]*x+M[5]*y+M[9]*z+M[13])/w,(M[2]*x+M[6]*y+M[10]*z+M[14])/w]); };
      if(/^clean-hall-textured/.test(nm)){ for(let j=0;j<pos.count;j++){ const q=get(j);
        scan.push(Math.round(q[0]*1000)/1000, Math.round(q[1]*1000)/1000, Math.round(q[2]*1000)/1000); } return; }
      counts[nm]=(counts[nm]||0)+1;
      const idx=o.geometry.index?o.geometry.index.array:null;
      const n=idx?idx.length:pos.count;
      const arr=tri[nm]||(tri[nm]=[]);
      if(arr.length>60000) return;                 // a name this large is not a surface this goal names
      for(let k=0;k+2<n;k+=3){ const a=get(idx?idx[k]:k), b=get(idx?idx[k+1]:k+1), cc=get(idx?idx[k+2]:k+2);
        for(const q of [a,b,cc]) arr.push(Math.round(q[0]*1000)/1000, Math.round(q[1]*1000)/1000, Math.round(q[2]*1000)/1000); }
    });
    const big=Object.keys(tri).filter(k=>tri[k].length>60000);
    for(const k of big) delete tri[k];
    return {scan, tri, dropped:big}; })()`).catch(e => ({ err: String(e.message).slice(0, 300) }));
  if (g.err) { console.log('the dump failed:', g.err); await P.close(); process.exit(1); }
  fs.writeFileSync('render-match/geom.json', JSON.stringify(g));
  console.log(`${g.scan.length / 3} scan vertices and ${Object.keys(g.tri).length} analytic names written to render-match/geom.json`);
  console.log(`${g.dropped.length} names were too large to be a surface this goal names and were dropped: ${g.dropped.join(', ')}`);
  await P.close();
  process.exit(0);
}

const out = await P.ev(`(()=>{
  const O=[-54.907447,-1.43545,3.040286], HU=[0.975681,0,0.219196], HD=[0.219196,0,-0.975681];
  const toHall = w => { const q=[w[0]-O[0], w[1]-O[1], w[2]-O[2]];
    return [q[0]*HU[0]+q[2]*HU[2], q[0]*HD[0]+q[2]*HD[2], q[1]]; };
  const tris=[]; const bake=[]; const bakeNames={}; let rawBake=0;
  ngv.scene.traverse(o=>{
    if(!o.isMesh||!o.geometry) return;
    const pos=o.geometry.attributes&&o.geometry.attributes.position; if(!pos) return;
    const nm=o.name||(o.material&&o.material.name)||'(unnamed)';
    o.updateWorldMatrix(true,false); const M=o.matrixWorld.elements;
    const get=j=>{ const x=pos.getX(j), y=pos.getY(j), z=pos.getZ(j);
      const w=M[3]*x+M[7]*y+M[11]*z+M[15];
      return toHall([(M[0]*x+M[4]*y+M[8]*z+M[12])/w,(M[1]*x+M[5]*y+M[9]*z+M[13])/w,(M[2]*x+M[6]*y+M[10]*z+M[14])/w]); };
    if(/^clean-hall-textured/.test(nm)){ rawBake+=pos.count; bakeNames[nm]=(bakeNames[nm]||0)+pos.count;
      for(let j=0;j<pos.count;j++) bake.push(get(j)); return; }
    const idx=o.geometry.index?o.geometry.index.array:null;
    const n=idx?idx.length:pos.count;
    for(let k=0;k+2<n;k+=3){ tris.push([get(idx?idx[k]:k), get(idx?idx[k+1]:k+1), get(idx?idx[k+2]:k+2), nm]); }
  });
  // strided down if the scan is larger than this can carry, and the stride is reported
  let stride=1; if(bake.length>${CAPV}) stride=Math.ceil(bake.length/${CAPV});
  const B=[]; for(let i=0;i<bake.length;i+=stride) B.push(bake[i]);
  // a hash grid so each analytic face only looks at the vertices near it
  const CELL=0.5; const grid=new Map();
  const key=(a,b,c)=>a+','+b+','+c;
  for(let i=0;i<B.length;i++){ const p=B[i];
    const k=key(Math.floor(p[0]/CELL),Math.floor(p[1]/CELL),Math.floor(p[2]/CELL));
    let e=grid.get(k); if(!e){ e=[]; grid.set(k,e); } e.push(i); }
  const per={};
  const sub=(a,b)=>[a[0]-b[0],a[1]-b[1],a[2]-b[2]];
  const cross=(a,b)=>[a[1]*b[2]-a[2]*b[1], a[2]*b[0]-a[0]*b[2], a[0]*b[1]-a[1]*b[0]];
  const dot=(a,b)=>a[0]*b[0]+a[1]*b[1]+a[2]*b[2];
  for(const t of tris){
    const u=sub(t[1],t[0]), v=sub(t[2],t[0]); const nr=cross(u,v);
    const nl=Math.hypot(nr[0],nr[1],nr[2]); if(nl<1e-9) continue;
    const N=[nr[0]/nl,nr[1]/nl,nr[2]/nl];
    const mn=[0,1,2].map(k=>Math.min(t[0][k],t[1][k],t[2][k])-${SLAB});
    const mx=[0,1,2].map(k=>Math.max(t[0][k],t[1][k],t[2][k])+${SLAB});
    const uu=dot(u,u), uv=dot(u,v), vv=dot(v,v), den=uv*uv-uu*vv; if(Math.abs(den)<1e-12) continue;
    const e=per[t[3]]||(per[t[3]]={n:0, tris:0, s:[], sum:0});
    e.tris++;
    for(let a=Math.floor(mn[0]/CELL);a<=Math.floor(mx[0]/CELL);a++)
    for(let b=Math.floor(mn[1]/CELL);b<=Math.floor(mx[1]/CELL);b++)
    for(let c=Math.floor(mn[2]/CELL);c<=Math.floor(mx[2]/CELL);c++){
      const cell=grid.get(key(a,b,c)); if(!cell) continue;
      for(const i of cell){ const p=B[i]; const w=sub(p,t[0]); const d=dot(w,N);
        if(d>${SLAB}||d<-${SLAB}) continue;
        const wu=dot(w,u), wv=dot(w,v);
        const s=(uv*wv-vv*wu)/den, r=(uv*wu-uu*wv)/den;
        if(s<-0.02||r<-0.02||s+r>1.02) continue;
        e.n++; e.sum+=d;
        if(e.s.length<${SAMPLE}) e.s.push(Math.round(d*10000)/10000);
        else { const j=Math.floor(Math.random()*e.n); if(j<${SAMPLE}) e.s[j]=Math.round(d*10000)/10000; } }
    }
  }
  const bb={min:[1e9,1e9,1e9],max:[-1e9,-1e9,-1e9]};
  for(const p of B) for(let k=0;k<3;k++){ if(p[k]<bb.min[k])bb.min[k]=p[k]; if(p[k]>bb.max[k])bb.max[k]=p[k]; }
  return {per, tris:tris.length, rawBake, kept:B.length, stride, bakeNames, bbox:bb};
})()`).catch(e => ({ err: String(e.message).slice(0, 400) }));

if (out.err) { console.log('the page threw:', out.err); await P.close(); process.exit(1); }
console.log(`${out.tris} analytic triangles, ${out.rawBake} scan vertices over ${Object.keys(out.bakeNames).length} clean-hall-textured chunks`);
console.log(`the scan spans u ${out.bbox.min[0].toFixed(2)} to ${out.bbox.max[0].toFixed(2)}, d ${out.bbox.min[1].toFixed(2)} to ${out.bbox.max[1].toFixed(2)}, h ${out.bbox.min[2].toFixed(2)} to ${out.bbox.max[2].toFixed(2)}`);
console.log(`${out.kept} kept after a stride of ${out.stride}`);
const hit = Object.entries(out.per).filter(([, e]) => e.n > 0);
console.log(`${hit.length} named analytic surfaces have baked vertices lying on them`);
fs.writeFileSync('render-match/bake-vs-model.json', JSON.stringify(out));
console.log('written to render-match/bake-vs-model.json; now run python tools/bake_vs_model.py');
console.log(P.errors.length ? `the page reported ${P.errors.length} errors: ${P.errors.slice(0, 3).join(' | ')}`
  : 'the page reported no errors while this ran.');
await P.close();
process.exit(0);
