// What is under a pixel of the pose-matched view: raycast from the camera through (px, py) and name
// the meshes hit, nearest first. Same pose arguments as pose-shot.mjs, then pixel pairs.
// node tools/pose-pick.mjs <W> <H> <vfov> <u> <d> <h> <fwdU> <fwdD> <pitchDeg> <hour> <house%> px,py [px,py ...]
import { attach } from './cdp.mjs';
const [W, H, vfov, u, d, h, fu, fd, pitch, hour, house, ...pix] = process.argv.slice(2);
const P = await attach({ port: +(process.env.CDP_PORT || 9334), width: +W, height: +H });
await P.send('Network.setCacheDisabled', { cacheDisabled: true }).catch(() => {});
await P.send('Page.navigate', { url: 'http://127.0.0.1:8877/index.html?install=gandel-2026' });
for (let i = 0; i < 120; i++) { await P.sleep(500); if (await P.ev('!!(window.ngv&&window.ngv.hall&&document.getElementById("install"))').catch(() => false)) break; }
await P.ev(`localStorage.setItem('ngv.install','gandel-2026'); document.getElementById('install').click()`);
for (let i = 0; i < 60; i++) { await P.sleep(500); if (await P.ev('!!(window.ngv&&window.ngv.game)').catch(() => false)) break; }
await P.ev(`document.querySelector('#start').click()`); await P.sleep(800);
await P.ev(`document.body.classList.add("immersive"); const cb=document.getElementById("collide"); if(cb){cb.checked=false; cb.dispatchEvent(new Event("change"));} window.dispatchEvent(new Event("resize"));`).catch(() => {});
await P.ev(`(()=>{const t=document.getElementById('tod');t.value=${hour};t.dispatchEvent(new Event('input'));const hs=document.getElementById('house');if(hs){hs.value=${house};hs.dispatchEvent(new Event('input'));} ngv.dirty();})()`); await P.sleep(900);
const place = () => P.ev(`(()=>{const g=ngv.game,P=g.player,L=g.lift;const p=g.hallToWorld(${u},${d},g.world.floorY);
  const q=g.hallToWorld(${u}+${fu},${d}+${fd},g.world.floorY); P.yaw=Math.atan2(-(q.x-p.x),-(q.z-p.z)); P.pitch=${pitch}*Math.PI/180; if(L.aboard)L.leave(P,true);
  P.pos.copy(p); P.pos.y=g.world.floorY; P.eye=${h}; return P.eye; })()`);
await place(); await P.sleep(1200);
await P.ev(`(()=>{const g=ngv.game; if(g.fx)g.fx.baseFov=${vfov}; ngv.cam.fov=${vfov}; ngv.cam.updateProjectionMatrix(); return 1;})()`);
await place(); await P.sleep(300);
for (const pp of pix) {
  if (pp.startsWith('list:')) {   // list:u0,u1,d0,d1 : every visible mesh whose box overlaps that hall-frame region
    const [u0, u1, d0, d1] = pp.slice(5).split(',').map(Number);
    const r = await P.ev(`(async()=>{const T=await import('three'); const O=[-54.907447,-1.43545,3.040286],HU=[0.975681,0,0.219196],HD=[0.219196,0,-0.975681]; const out=[];
      const hc=p=>{const q=[p.x-O[0],p.y-O[1],p.z-O[2]]; return [q[0]*HU[0]+q[2]*HU[2], q[0]*HD[0]+q[2]*HD[2], q[1]];};
      ngv.scene.traverse(o=>{ if(!o.isMesh||!o.visible) return; const b=new T.Box3().setFromObject(o); if(b.isEmpty()) return;
        const cs=[]; for(const x of [b.min.x,b.max.x]) for(const y of [b.min.y,b.max.y]) for(const z of [b.min.z,b.max.z]) cs.push(hc({x,y,z}));
        const mn=[0,1,2].map(i=>Math.min(...cs.map(c=>c[i]))), mx=[0,1,2].map(i=>Math.max(...cs.map(c=>c[i])));
        if(mx[0]<${u0}||mn[0]>${u1}||mx[1]<${d0}||mn[1]>${d1}) return;
        if(mx[0]-mn[0]>60&&mx[1]-mn[1]>20) return;   // skip the whole-hall meshes
        out.push((o.name||'?')+':'+o.type+':'+(o.parent&&o.parent.name||'')+'/'+(o.material&&o.material.name||'-')+' u'+mn[0].toFixed(1)+'..'+mx[0].toFixed(1)+' d'+mn[1].toFixed(1)+'..'+mx[1].toFixed(1)+' h'+mn[2].toFixed(1)+'..'+mx[2].toFixed(1)); });
      return out.join('\\n');})()`);
    console.log(r); continue; }
  // hall:u,d,h : the ray through that hall-frame point (no pixel arithmetic); plain px,py otherwise. Points objects are skipped.
  let ndc;
  if (pp.startsWith('hall:')) { const [hu, hd, hz] = pp.slice(5).split(',').map(Number); ndc = `(()=>{const O=[-54.907447,-1.43545,3.040286],HU=[0.975681,0,0.219196],HD=[0.219196,0,-0.975681]; const v=new T.Vector3(O[0]+${hu}*HU[0]+${hd}*HD[0], O[1]+${hz}, O[2]+${hu}*HU[2]+${hd}*HD[2]); v.project(c); return new T.Vector2(v.x, v.y);})()`; }
  else { const [px, py] = pp.split(',').map(Number); ndc = `new T.Vector2(${px}/${W}*2-1, 1-${py}/${H}*2)`; }
  const r = await P.ev(`(async()=>{const T=await import('three'); const rc=new T.Raycaster(); const c=ngv.cam; c.updateMatrixWorld();
    rc.setFromCamera(${ndc}, c); const hits=rc.intersectObjects(ngv.scene.children,true).filter(x=>x.object.visible&&x.object.isMesh);
    const O=[-54.907447,-1.43545,3.040286],HU=[0.975681,0,0.219196],HD=[0.219196,0,-0.975681];
    const hc=p=>{const q=[p.x-O[0],p.y-O[1],p.z-O[2]]; return 'u'+(q[0]*HU[0]+q[2]*HU[2]).toFixed(2)+' d'+(q[0]*HD[0]+q[2]*HD[2]).toFixed(2)+' h'+q[1].toFixed(2);};
    return hits.slice(0,3).map(x=>(x.object.name||'?')+':'+x.object.type+':'+(x.object.parent&&x.object.parent.name||'')+'/'+(x.object.material&&x.object.material.name||'-')+' @'+x.distance.toFixed(2)+' '+hc(x.point)).join(' | ');})()`);
  console.log(pp, '->', r);
}
P.close(); process.exit(0);
