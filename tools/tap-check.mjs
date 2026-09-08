// Prints each tapestry mesh's corner d and u (hall frame) as built in the page, and whether its texture loaded.
import { attach } from './cdp.mjs';
const P = await attach({ port: +(process.env.CDP_PORT || 9334), width: 1280, height: 720 });
await P.send('Network.setCacheDisabled', { cacheDisabled: true }).catch(() => {});
await P.send('Page.navigate', { url: 'http://127.0.0.1:8877/index.html?install=gandel-2026' });
for (let i = 0; i < 120; i++) { await P.sleep(500); if (await P.ev('!!(window.ngv&&window.ngv.hall&&document.getElementById("install"))').catch(() => false)) break; }
await P.ev(`localStorage.setItem('ngv.install','gandel-2026'); document.getElementById('install').click()`);
for (let i = 0; i < 60; i++) { await P.sleep(500); if (await P.ev('!!(window.ngv&&window.ngv.game)').catch(() => false)) break; }
await P.sleep(4000);
const r = await P.ev(`(()=>{const out=[]; const O=[-54.907447,-1.43545,3.040286], HD=[0.219196,0,-0.975681], HU=[0.975681,0,0.219196];
 ngv.scene.traverse(o=>{ if(o.isMesh&&/^tapestry-/.test(o.name)){ const p=o.geometry.attributes.position.array; const ds=[],us=[];
  for(let i=0;i<4;i++){ const q=[p[3*i]-O[0],p[3*i+1]-O[1],p[3*i+2]-O[2]]; ds.push((q[0]*HD[0]+q[2]*HD[2]).toFixed(3)); us.push((q[0]*HU[0]+q[2]*HU[2]).toFixed(2)); }
  const im=o.material.map?o.material.map.image:null;
  out.push(o.name+' d '+ds.join(',')+' u '+us.join(',')+' visible '+o.visible+' map '+(im?im.width+'x'+im.height+' '+(im.currentSrc||im.src||''):'none')+' renderOrder '+o.renderOrder+' depthTest '+o.material.depthTest+' transparent '+o.material.transparent); } });
 return out.join(' / '); })()`);
console.log(r);
process.exit(0);
