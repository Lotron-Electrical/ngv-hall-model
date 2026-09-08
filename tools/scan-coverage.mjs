// 2026-09-09: where the loaded scan actually HAS surface, along the hall and up the height. A probe that
// reads the scan at a place the scan never reconstructed returns a confident number about nothing, so
// this is the map that says which parts of this model can be checked against the building at all.
import { attach } from './cdp.mjs';
const P = await attach({ port: +(process.env.CDP_PORT || 9334), width: 900, height: 700 });
await P.open('index.html');
const out = await P.ev(`(function(){
 var T=dbg.THREE, O=new T.Vector3(-54.907447,-1.43545,3.040286),
     HU=new T.Vector3(0.975681,0,0.219196), HD=new T.Vector3(0.219196,0,-0.975681);
 var byU={}, byH={}, tot=0, inHall=0;
 ngv.scene.traverse(function(o){ if(!o.isMesh)return; if(!/^clean-hall-textured/.test(o.name||'')) return;
  o.updateWorldMatrix(true,false); var p=o.geometry.attributes.position; if(!p)return; var v=new T.Vector3();
  for(var i=0;i<p.count;i++){ v.fromBufferAttribute(p,i).applyMatrix4(o.matrixWorld).sub(O);
   var u=v.dot(HU), d=v.dot(HD), h=v.y; tot++;
   if(d<-1||d>16.4||u<-1||u>53||h<-0.5||h>15.6) continue; inHall++;
   var ub=Math.floor(u/2)*2; byU[ub]=(byU[ub]||0)+1;
   var hb=Math.floor(h);     byH[hb]=(byH[hb]||0)+1; } });
 var L=['scan vertices '+tot+', inside the hall box '+inHall];
 L.push('along the hall (2 m bins, u : vertices)');
 Object.keys(byU).map(Number).sort(function(a,b){return a-b;}).forEach(function(u){ L.push('  u '+String(u).padStart(4)+'  '+byU[u]); });
 L.push('up the height (1 m bins, h : vertices)');
 Object.keys(byH).map(Number).sort(function(a,b){return a-b;}).forEach(function(h){ L.push('  h '+String(h).padStart(4)+'  '+byH[h]); });
 return L.join(' ~ ');
})()`);
out.split(' ~ ').forEach(x => console.log(x)); P.close(); process.exit(0);
