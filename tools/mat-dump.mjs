// Dump the materials whose name matches a pattern: opacity, transparent, side, uniforms alpha/dayGain.
// node tools/mat-dump.mjs <regex>
import { attach } from './cdp.mjs';
const [pat] = process.argv.slice(2);
const P = await attach({ port: +(process.env.CDP_PORT || 9334), width: 800, height: 600 });
await P.send('Network.setCacheDisabled', { cacheDisabled: true }).catch(() => {});
await P.send('Page.navigate', { url: 'http://127.0.0.1:8877/index.html?install=gandel-2026' });
for (let i = 0; i < 120; i++) { await P.sleep(500); if (await P.ev('!!(window.ngv&&window.ngv.hall&&document.getElementById("install"))').catch(() => false)) break; }
await P.sleep(1500);
const r = await P.ev(`(()=>{const out=new Map(); ngv.scene.traverse(o=>{ if(!o.isMesh)return; for(const m of (Array.isArray(o.material)?o.material:[o.material])){ if(!new RegExp(${JSON.stringify(pat)},'i').test(m.name||''))continue;
  out.set(m.name, m.name+' side '+m.side+' transparent '+m.transparent+' opacity '+m.opacity+' alpha '+(m.uniforms&&m.uniforms.alpha?m.uniforms.alpha.value:'-')+' dayGain '+(m.uniforms&&m.uniforms.dayGain?m.uniforms.dayGain.value:'-')+' tint '+(m.uniforms&&m.uniforms.tint?m.uniforms.tint.value.getHexString():'-')+' map '+(m.uniforms&&m.uniforms.map&&m.uniforms.map.value?m.uniforms.map.value.image&&m.uniforms.map.value.image.width:'none')); } });
  return [...out.values()].join(' | ');})()`);
console.log(r); P.close(); process.exit(0);
