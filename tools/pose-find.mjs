// Which mesh paints a pixel of the pose-matched view: hide each mesh in turn, render, read the pixel
// block back, restore. Prints the meshes whose removal changes the block most.
// node tools/pose-find.mjs <W> <H> <vfov> <u> <d> <h> <fwdU> <fwdD> <pitchDeg> <hour> <house%> px,py [px,py ...]
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
await place(); await P.sleep(400);
for (const pp of pix) {
  const [px, py] = pp.split(',').map(Number);
  const r = await P.ev(`(()=>{const R=ngv.R, gl=R.getContext(), cam=ngv.cam, sc=ngv.scene; const pr=R.getPixelRatio(); 
    const cw=R.domElement.width, ch=R.domElement.height; const x=Math.round(${px}*cw/${W}), y=Math.round(ch-${py}*ch/${H}); const buf=new Uint8Array(8*8*4);
    const read=()=>{ R.render(sc,cam); gl.readPixels(x-4,y-4,8,8,gl.RGBA,gl.UNSIGNED_BYTE,buf); let s=0; for(let i=0;i<buf.length;i+=4)s+=buf[i]+buf[i+1]+buf[i+2]; return s/(64*3); };
    const base=read(); const out=[]; const meshes=[]; sc.traverse(o=>{ if(o.isMesh&&o.visible) meshes.push(o); });
    // by material (overlapping duplicates share one), then by parent group
    const groups=new Map(); for(const m of meshes){ const k='mat:'+(m.material&&(m.material.name||m.material.uuid)||'-'); (groups.get(k)||groups.set(k,[]).get(k)).push(m); const pk='par:'+(m.parent&&(m.parent.name||m.parent.uuid)||'-'); (groups.get(pk)||groups.set(pk,[]).get(pk)).push(m); }
    for(const [k,ms] of groups){ for(const m of ms)m.visible=false; const v=read(); for(const m of ms)m.visible=true; if(Math.abs(v-base)>6) out.push([Math.abs(v-base).toFixed(0),k+' ('+ms.length+': '+ms.slice(0,3).map(m=>m.name||'?').join(',')+')', v.toFixed(0)]); }
    // and everything that is not a mesh (sprites, lines, points)
    const others=[]; sc.traverse(o=>{ if(!o.isMesh&&o.visible&&(o.isSprite||o.isLine||o.isPoints)) others.push(o); });
    for(const o of others){ o.visible=false; const v=read(); o.visible=true; if(Math.abs(v-base)>6) out.push([Math.abs(v-base).toFixed(0),'other '+o.type+' '+(o.name||'?')+':'+(o.parent&&o.parent.name||''), v.toFixed(0)]); }
    // solo pass: everything off, each mesh alone (finds overlapping duplicates)
    for(const m of meshes)m.visible=false; const dark=read();
    for(const m of meshes){ m.visible=true; const v=read(); m.visible=false; if(Math.abs(v-dark)>6) out.push([Math.abs(v-dark).toFixed(0),'SOLO '+(m.name||'?')+':'+(m.parent&&m.parent.name||'')+'/'+(m.material&&m.material.name||'-')+' tris '+((m.geometry.index?m.geometry.index.count:m.geometry.attributes.position.count)/3|0), v.toFixed(0)]); }
    for(const m of meshes)m.visible=true;
    out.sort((a,b)=>b[0]-a[0]); return 'base '+base.toFixed(0)+' of '+meshes.length+' meshes, '+others.length+' others\\n'+out.slice(0,10).map(o=>o.join('  ')).join('\\n'); })()`);
  console.log(pp, '->', r);
}
P.close(); process.exit(0);
