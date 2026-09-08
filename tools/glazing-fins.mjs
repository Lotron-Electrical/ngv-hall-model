// Prints the u range (hall frame) and d range of every south glazing fin, mullion and glass pane in the GLB.
import { attach } from './cdp.mjs';
const P = await attach({ port: +(process.env.CDP_PORT || 9334), width: 1280, height: 800 });
await P.open('index.html');
console.log(await P.ev(`(function(){ var O=new dbg.THREE.Vector3(-54.907447,-1.43545,3.040286), HU=new dbg.THREE.Vector3(0.975681,0,0.219196), HD=new dbg.THREE.Vector3(0.219196,0,-0.975681); var out=[];
 dbg.hall.traverse(function(o){ if(!(o.isMesh&&/glazing-south-(fin|mullion|glass)/i.test(o.material&&o.material.name||'')))return; o.updateWorldMatrix(true,false); var p=o.geometry.attributes.position, v=new dbg.THREE.Vector3(), u0=1e9,u1=-1e9,d0=1e9,d1=-1e9,h0=1e9,h1=-1e9;
  for(var i=0;i<p.count;i++){ v.fromBufferAttribute(p,i).applyMatrix4(o.matrixWorld).sub(O); var u=v.dot(HU), d=v.dot(HD), h=v.y; u0=Math.min(u0,u);u1=Math.max(u1,u);d0=Math.min(d0,d);d1=Math.max(d1,d);h0=Math.min(h0,h);h1=Math.max(h1,h); }
  out.push(o.material.name+' u '+u0.toFixed(2)+'..'+u1.toFixed(2)+' d '+d0.toFixed(2)+'..'+d1.toFixed(2)+' h '+h0.toFixed(2)+'..'+h1.toFixed(2)); });
 return out.join('#'); })()`).catch(e => e.message));
P.close(); process.exit(0);
