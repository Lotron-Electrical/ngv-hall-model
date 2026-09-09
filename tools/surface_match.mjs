// 2026-09-10: WHICH SURFACE AGREES WITH THE PHOTOGRAPH, NOT WHICH PICTURE. THE IDENTITY PASS.
//
// tools/render_match.py put the sim camera where a real camera stood and scored the whole frame. That can
// only ever say "this picture agrees" or "this picture does not", and a hall frame is mostly ceiling and
// floor, so a balcony fascia drawn in the wrong place is a per cent of the score and invisible inside it.
//
// SO SHOOT THE SAME POSE TWICE. Once normally, and once with the surfaces this goal names replaced by a
// flat identity colour, one colour per NAME, everything else painted black. The second pass is not a
// picture of the hall, it is a map: each pixel says which named surface the model drew there. Scoring the
// photograph inside one surface's mask asks whether THAT surface is where the photograph puts it, and the
// answer cannot be diluted by the ceiling.
//
// THE COLOURS ARE FOUR LEVELS A CHANNEL AND NOTHING FINER, because the screenshot comes back as JPEG and
// a fine grid would let compression slide one surface into its neighbour. Eighty-five levels between
// neighbours against a tolerance of twenty-eight is the margin, and only the balcony, wall and corridor
// surfaces get a colour at all. The scorer prints what fraction of the
// picture it could classify; if that is poor, nothing downstream is worth reading and the number is shown
// rather than hidden. NOTHING HERE CHANGES THE PAGE ON DISK: the materials are swapped in the live browser
// and put back before it closes, and the run says so at the end.
//   bash ~/scripts/headless-chrome.sh start 9334
//   CDP_PORT=9334 node tools/surface_match.mjs
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
if (!ok) { console.log('THE PAGE NEVER REACHED INSTALL MODE. Nothing can be rendered.'); await P.close(); process.exit(1); }
await P.ev(`localStorage.setItem('ngv.install','gandel-2026'); document.getElementById('install').click()`);
for (let i = 0; i < 60; i++) { await P.sleep(500); if (await P.ev('!!(window.ngv&&window.ngv.game)').catch(() => false)) break; }
await P.ev(`document.querySelector('#start').click()`).catch(() => {});
await P.sleep(1200);
await P.ev(`(()=>{document.body.classList.add("immersive");
  const cb=document.getElementById("collide"); if(cb){cb.checked=false; cb.dispatchEvent(new Event("change"));}
  const keep=document.getElementById('cv');
  document.querySelectorAll('body > *, main > *, #stage > *').forEach(e=>{ if(e===keep||e.contains(keep))return; e.style.visibility='hidden'; });
  let n=0; ngv.scene.traverse(o=>{ if(o.isSprite){o.visible=false;n++;} }); ngv.dirty(); return n;})()`)
  .then(n => console.log('sprites hidden', n)).catch(e => console.log('hide failed', String(e.message).slice(0, 120)));

// WHICH SURFACES GET A COLOUR. The goal names three things, so the filter names three things, and the
// list of what matched is printed so nobody has to trust the pattern. Everything else goes black, which
// also makes the background unambiguous.
const WANT = 'gallery|corridor|wall|rail|fascia|parapet|upstand|downstand|soffit|deck|reveal|jamb|opening|pier|tier|balcon|brick';
const table = await P.ev(`(()=>{ const T=window.dbg&&window.dbg.THREE; if(!T) return {err:'no THREE handle'};
  const L=[0,85,170,255]; const pool=[];
  for(const r of L) for(const g of L) for(const b of L){ if(r+g+b<85) continue; pool.push([r,g,b]); }
  const re=new RegExp('${WANT}','i'); const names=[]; const others=[];
  ngv.scene.traverse(o=>{ if(!o.isMesh) return; const nm=o.name||(o.material&&o.material.name)||'(unnamed)';
    if(re.test(nm)){ if(!names.includes(nm)) names.push(nm); } else if(!others.includes(nm)) others.push(nm); });
  window.__idmap={}; window.__saved=[];
  names.slice(0,pool.length).forEach((nm,i)=>{ window.__idmap[nm]=pool[i]; });
  return {names, colours: names.map(n=>window.__idmap[n]||null), pool:pool.length, others:others.length}; })()`)
  .catch(e => ({ err: String(e.message).slice(0, 200) }));
if (table.err) { console.log('the identity pass cannot be built:', table.err); await P.close(); process.exit(1); }
console.log(`${table.names.length} named surfaces match the goal, ${table.pool} colours available, ${table.others} other names go black`);
if (table.names.length > table.pool) console.log(`ONLY THE FIRST ${table.pool} GET A COLOUR, the rest are black and unscored: ${table.names.slice(table.pool).join(', ')}`);
console.log('   ' + table.names.slice(0, table.pool).join(', '));
fs.writeFileSync('render-match/idmap.json', JSON.stringify(table, null, 1));

// MODE 'bounds': EXPORT WHERE EACH NAMED SURFACE ACTUALLY IS, then stop. The first run of this tool
// scored ten frames chosen for how much OPENING they showed, and discovered that the balcony surfaces
// never fill a readable share of any of them: gallery-fascia, gallery-rail, gallery-floor and the rest
// returned zero pixels in all ten. That is not a fault in the scoring, it is the frame set being aimed at
// the wrong thing, and it cannot be fixed by looking at pictures. So each mesh gives up its own world
// bounding box here, in hall coordinates, and the frames get chosen per SURFACE from those boxes.
if (process.argv[2] === 'bounds') {
  const O = [-54.907447, -1.43545, 3.040286];
  const HU = [0.975681, 0, 0.219196];
  const HD = [0.219196, 0, -0.975681];
  const box = await P.ev(`(()=>{ const O=${JSON.stringify(O)}, HU=${JSON.stringify(HU)}, HD=${JSON.stringify(HD)};
    const toHall = w => { const q=[w[0]-O[0], w[1]-O[1], w[2]-O[2]];
      return [q[0]*HU[0]+q[2]*HU[2], q[0]*HD[0]+q[2]*HD[2], q[1]]; };
    const out={};
    ngv.scene.traverse(o=>{ if(!o.isMesh||!o.geometry) return;
      const nm=o.name||(o.material&&o.material.name)||'(unnamed)';
      const pos=o.geometry.attributes&&o.geometry.attributes.position; if(!pos) return;
      o.geometry.computeBoundingBox(); const bb=o.geometry.boundingBox; if(!bb) return;
      o.updateWorldMatrix(true,false); const M=o.matrixWorld.elements;
      const put=(x,y,z)=>{ const w=M[3]*x+M[7]*y+M[11]*z+M[15];
        return toHall([(M[0]*x+M[4]*y+M[8]*z+M[12])/w,(M[1]*x+M[5]*y+M[9]*z+M[13])/w,(M[2]*x+M[6]*y+M[10]*z+M[14])/w]); };
      // ONE BOX PER PART, NOT ONE PER NAME. gallery-fascia is two meshes forty metres apart, one on each
      // end gallery, and a box round both of them is a box round the whole hall: no camera can frame it
      // and the surface would never be selectable. Grouping back by name happens in the scorer.
      const e=out[nm]||(out[nm]={parts:[]});
      const mn=[1e9,1e9,1e9], mx=[-1e9,-1e9,-1e9];
      for(const x of [bb.min.x,bb.max.x]) for(const y of [bb.min.y,bb.max.y]) for(const z of [bb.min.z,bb.max.z]){
        const q=put(x,y,z); for(let k=0;k<3;k++){ if(q[k]<mn[k])mn[k]=q[k]; if(q[k]>mx[k])mx[k]=q[k]; } }
      e.parts.push({min:mn, max:mx, verts:pos.count}); });
    return out; })()`).catch(e => ({ err: String(e.message).slice(0, 200) }));
  if (box.err) { console.log('the bounds export failed:', box.err); await P.close(); process.exit(1); }
  const names = Object.keys(box);
  for (const nm of names) box[nm].baked = box[nm].parts.some(t => t.verts > 4000);
  fs.writeFileSync('render-match/bounds.json', JSON.stringify(box, null, 1));
  const np = names.reduce((s, n) => s + box[n].parts.length, 0);
  console.log(`${names.length} named meshes over ${np} parts, boxes written to render-match/bounds.json`);
  console.log(`${names.filter(n => box[n].baked).length} of them are baked scan pieces and are marked as such`);
  await P.close();
  process.exit(0);
}

// AND THE PASS THAT TELLS YOU WHY A SURFACE HAS NO PIXELS. The first scored run found every goal surface
// drawing a thousandth of the picture its own bounding box fills, which is either a thin surface seen
// edge-on or a surface hidden behind something else, and those are very different facts.
// THE FIRST X-RAY WAS BUILT WRONG AND ITS OWN OUTPUT CAUGHT IT. Turning DEPTH TESTING OFF let the goal
// surfaces draw over each other in traversal order, so end-ground-wall came back showing 937k pixels
// normally and 266k with nothing supposed to be covering it: a surface cannot be more visible than its own
// silhouette, and a negative hidden fraction is a broken instrument, not a finding.
// THE RIGHT X-RAY HIDES EVERYTHING THAT IS NOT A GOAL SURFACE and leaves depth testing alone. The goal
// surfaces then occlude each other exactly as they really do, nothing else can cover them, and the
// shortfall against the ordinary pass is what the rest of the model hides. Measured, not assumed.
const XRAY = process.argv[2] === 'xray';
const idOn = () => P.ev(`(()=>{ const T=dbg.THREE; window.__saved=[]; window.__bg=ngv.scene.background;
  ngv.scene.background=new T.Color(0,0,0); window.__fog=ngv.scene.fog; ngv.scene.fog=null;
  ngv.scene.traverse(o=>{ if(!o.isMesh) return; const nm=o.name||(o.material&&o.material.name)||'(unnamed)';
    const c=window.__idmap[nm]; window.__saved.push([o,o.material,o.visible]);
    const m=new T.MeshBasicMaterial({side:T.DoubleSide, fog:false, toneMapped:false});
    m.color.setRGB((c?c[0]:0)/255,(c?c[1]:0)/255,(c?c[2]:0)/255); o.material=m;
    if(${XRAY} && !c) o.visible=false; });
  ngv.dirty(); return window.__saved.length; })()`).catch(e => String(e.message).slice(0, 160));
const idOff = () => P.ev(`(()=>{ for(const [o,m,v] of (window.__saved||[])){ o.material=m; if(v!==undefined)o.visible=v; } window.__saved=[];
  if(window.__bg!==undefined) ngv.scene.background=window.__bg; if(window.__fog!==undefined) ngv.scene.fog=window.__fog;
  ngv.dirty(); return 'restored'; })()`).catch(() => 'restore failed');

for (let i = 0; i < picks.length; i++) {
  const p = picks[i];
  const side = 2 * Math.round(RH * p.sqside / 2);
  await P.send('Emulation.setDeviceMetricsOverride', { width: side, height: side, deviceScaleFactor: 1, mobile: false });
  await P.ev(`window.dispatchEvent(new Event('resize'))`).catch(() => {});
  await P.sleep(700);
  const hour = p.cls === 'night' ? 21 : 13;
  const house = p.cls === 'night' ? 70 : 0;
  await P.ev(`(()=>{const t=document.getElementById('tod'); t.value=${hour}; t.dispatchEvent(new Event('input'));
    const hs=document.getElementById('house'); if(hs){hs.value=${house}; hs.dispatchEvent(new Event('input'));} ngv.dirty();})()`).catch(() => {});
  await P.sleep(700);
  const place = () => P.ev(`(()=>{const g=ngv.game,PL=g.player,L=g.lift; const a=g.hallToWorld(${p.u},${p.d},g.world.floorY);
    const b=g.hallToWorld(${p.u + p.fu},${p.d + p.fd},g.world.floorY); PL.yaw=Math.atan2(-(b.x-a.x),-(b.z-a.z)); PL.pitch=${p.pitch}*Math.PI/180;
    if(L.aboard)L.leave(PL,true); PL.pos.copy(a); PL.pos.y=g.world.floorY; PL.eye=${p.h}; return PL.eye;})()`).catch(e => String(e.message).slice(0, 120));
  await place();
  await P.sleep(1000);
  await place();
  await P.ev(`(()=>{const g=ngv.game; if(g.fx)g.fx.baseFov=${p.sqvfov}; ngv.cam.fov=${p.sqvfov}; ngv.cam.updateProjectionMatrix(); return ngv.cam.fov;})()`).catch(() => {});
  await place();
  await P.sleep(400);
  await P.shot(`render-match/r${String(i).padStart(2, '0')}.jpg`);
  const n = await idOn();
  await P.sleep(900);
  await place();
  await P.sleep(500);
  await P.shot(`render-match/${XRAY ? 'xr' : 'id'}${String(i).padStart(2, '0')}.jpg`);
  await idOff();
  await P.sleep(400);
  console.log(`${p.cls} ${p.frame}  square ${side}  ${n} meshes recoloured  -> r${String(i).padStart(2, '0')}.jpg + id${String(i).padStart(2, '0')}.jpg`);
}
console.log('');
console.log('materials restored:', await idOff());
console.log(P.errors.length ? `the page reported ${P.errors.length} errors: ${P.errors.slice(0, 4).join(' | ')}`
  : 'the page reported no errors while any of this ran.');
await P.close();
process.exit(0);
