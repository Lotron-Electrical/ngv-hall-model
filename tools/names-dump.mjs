// 2026-09-09: what the built scene calls its meshes, grouped, so a shot can hide a whole subsystem.
import { attach } from './cdp.mjs';
const P = await attach({ port: +(process.env.CDP_PORT || 9334), width: 900, height: 600 });
await P.send('Page.navigate', { url: 'http://127.0.0.1:8877/index.html?install=gandel-2026' });
for (let i = 0; i < 120; i++) { await P.sleep(500); if (await P.ev('!!(window.ngv&&window.ngv.hall)').catch(() => false)) break; }
await P.ev(`localStorage.setItem('ngv.install','gandel-2026'); const b=document.getElementById('install'); if(b)b.click()`);
await P.sleep(4000);
const out = await P.ev(`(()=>{const c={}; ngv.scene.traverse(o=>{ if(!o.isMesh)return; const n=(o.name||'(none)').replace(/[0-9]+$/,''); c[n]=(c[n]||0)+1; }); return Object.entries(c).sort((a,b)=>b[1]-a[1]).slice(0,70).map(e=>e[0]+' x'+e[1]).join(' | ');})()`);
console.log(out); P.close(); process.exit(0);
