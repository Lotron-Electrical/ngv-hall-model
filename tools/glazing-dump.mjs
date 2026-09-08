// Prints every glazing material on the page: name, transparent, depthWrite, frost, and the mesh's vertex count.
import { attach } from './cdp.mjs';
const P = await attach({ port: +(process.env.CDP_PORT || 9334), width: 1280, height: 800 });
await P.open('index.html');
console.log(await P.ev(`(function(){ var out=[]; dbg.hall.traverse(function(o){ if(o.isMesh&&/glaz/i.test(o.name+' '+(o.material&&o.material.name||''))) out.push([o.name, o.material.name, o.material.transparent, o.material.depthWrite, o.material.uniforms&&o.material.uniforms.frost?o.material.uniforms.frost.value:null, o.geometry.attributes.position.count, o.visible].join(' | ')); }); return out.join('#')||'none'; })()`).catch(e => e.message));
P.close(); process.exit(0);
