// Shoot the sim from the pose of a real posed frame (tools/pose_of.py gives the numbers), so the
// render and the photograph can be laid side by side. Install mode, HUD hidden.
// node tools/pose-shot.mjs <out.jpg> <W> <H> <vfov> <u> <d> <h> <fwdU> <fwdD> <pitchDeg> <hour> <house%>
import { attach } from './cdp.mjs';
const [out, W, H, vfov, u, d, h, fu, fd, pitch, hour, house] = process.argv.slice(2);
const P = await attach({ port: +(process.env.CDP_PORT || 9334), width: +W, height: +H });
await P.send('Network.setCacheDisabled', { cacheDisabled: true }).catch(() => {});
await P.send('Page.navigate', { url: 'http://127.0.0.1:8877/index.html?install=gandel-2026' });
for (let i = 0; i < 120; i++) { await P.sleep(500); if (await P.ev('!!(window.ngv&&window.ngv.hall&&document.getElementById("install"))').catch(() => false)) break; }
await P.ev(`localStorage.setItem('ngv.install','gandel-2026'); document.getElementById('install').click()`);
for (let i = 0; i < 60; i++) { await P.sleep(500); if (await P.ev('!!(window.ngv&&window.ngv.game)').catch(() => false)) break; }
await P.ev(`document.querySelector('#start').click()`); await P.sleep(800);
await P.ev(`document.body.classList.add("immersive"); const cb=document.getElementById("collide"); if(cb){cb.checked=false; cb.dispatchEvent(new Event("change"));} window.dispatchEvent(new Event("resize")); for(const s of ['#panel','#hint','.bar','#ghud','header','#top','#fab','#roamfab','#stkmove','#stklook','#hud','#tasks','#reticle','#labels','.label','.collbl'] ){document.querySelectorAll(s).forEach(e=>e.style.visibility='hidden');}`).catch(() => {});
await P.ev(`(()=>{const t=document.getElementById('tod');t.value=${hour};t.dispatchEvent(new Event('input'));const hs=document.getElementById('house');if(hs){hs.value=${house};hs.dispatchEvent(new Event('input'));} ngv.dirty();})()`); await P.sleep(900);
const place = () => P.ev(`(()=>{const g=ngv.game,P=g.player,L=g.lift;const p=g.hallToWorld(${u},${d},g.world.floorY);
  const q=g.hallToWorld(${u}+${fu},${d}+${fd},g.world.floorY); P.yaw=Math.atan2(-(q.x-p.x),-(q.z-p.z)); P.pitch=${pitch}*Math.PI/180; if(L.aboard)L.leave(P,true);
  P.pos.copy(p); P.pos.y=g.world.floorY; P.eye=${h}; return P.eye; })()`);
const eye = await place(); await P.sleep(1200); await place(); await P.sleep(150);
await P.ev(`(()=>{const g=ngv.game; if(g.fx)g.fx.baseFov=${vfov}; ngv.cam.fov=${vfov}; ngv.cam.updateProjectionMatrix(); return ngv.cam.fov;})()`).catch(() => {});
await place(); await P.sleep(120);
// HIDE=name1,name2 hides every mesh whose name or material name matches (an isolation aid)
if (process.env.HIDE) { const names = JSON.stringify(process.env.HIDE.split(',')); await P.ev(`(()=>{const N=${names}; let n=0; ngv.scene.traverse(o=>{ if(o.isMesh&&(N.includes(o.name)||(o.material&&N.includes(o.material.name)))){o.visible=false;n++;} }); ngv.dirty(); return n;})()`).then(n => console.log('hidden', n)); await P.sleep(600); }
await P.shot(out); console.log('shot', out, 'player.eye', eye, P.errors.join('\n') || 'no errors'); P.close(); process.exit(0);
