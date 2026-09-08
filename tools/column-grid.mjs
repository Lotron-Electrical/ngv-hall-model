// The hall columns' positions in the hall frame (u, d), so the canopy's module grid can be read against them.
import { attach } from './cdp.mjs';
const P = await attach({ port: +(process.env.CDP_PORT || 9334), width: 900, height: 700 });
await P.open('index.html');
console.log(await P.ev(`(function(){ var O=new dbg.THREE.Vector3(-54.907447,-1.43545,3.040286), HU=new dbg.THREE.Vector3(0.975681,0,0.219196), HD=new dbg.THREE.Vector3(0.219196,0,-0.975681);
 var ds={}, us={};
 dbg.hall.traverse(function(o){ if(!o.isMesh)return; var nm=(o.name+' '+(o.material&&o.material.name||'')).toLowerCase(); if(!/column/.test(nm))return;
  o.updateWorldMatrix(true,false); var p=o.geometry.attributes.position; if(!p)return; var v=new dbg.THREE.Vector3(), su=0, sd=0, n=0;
  for(var i=0;i<p.count;i+=11){ v.fromBufferAttribute(p,i).applyMatrix4(o.matrixWorld).sub(O); su+=v.dot(HU); sd+=v.dot(HD); n++; }
  if(!n)return; var d=Math.round(sd/n*10)/10, u=Math.round(su/n*10)/10; ds[d]=(ds[d]||0)+1; us[u]=(us[u]||0)+1; });
 var dk=Object.keys(ds).map(Number).sort(function(a,b){return a-b;});
 var uk=Object.keys(us).map(Number).sort(function(a,b){return a-b;});
 return JSON.stringify({d_lines:dk, u_lines:uk.slice(0,14)}); })()`).catch(e => e.message));
P.close(); process.exit(0);
