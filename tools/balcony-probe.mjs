// 2026-09-09: the balconies measured against the scan, not against the plan. The GLB the sim loads IS the
// dense reconstruction of the hall; the gallery-* meshes are what this model draws over it. This reads the
// SCAN's own vertices at the two ends and, for each 0.25 m slice along the hall, reports where its
// horizontal surfaces are: the peaks of the height histogram. Those peaks are the decks and the parapet
// tops. Compare with ENDW: floors 6.33 / 8.34, front faces u 4.194 (west) and 48.056 (east), slab 0.26,
// upstand 0.56, lowUpstand 0.52.
import { attach } from './cdp.mjs';
const P = await attach({ port: +(process.env.CDP_PORT || 9334), width: 900, height: 700 });
await P.open('index.html');
const out = await P.ev(`(function(){
 var T=dbg.THREE, O=new T.Vector3(-54.907447,-1.43545,3.040286),
     HU=new T.Vector3(0.975681,0,0.219196), HD=new T.Vector3(0.219196,0,-0.975681);
 var bins={}, n=0;
 ngv.scene.traverse(function(o){ if(!o.isMesh)return; var nm=(o.name||'');
  if(!/^clean-hall-textured/.test(nm)) return;                    // the scan's own meshes only
  o.updateWorldMatrix(true,false); var p=o.geometry.attributes.position; if(!p)return; var v=new T.Vector3();
  for(var i=0;i<p.count;i+=3){ v.fromBufferAttribute(p,i).applyMatrix4(o.matrixWorld).sub(O);
   var u=v.dot(HU), d=v.dot(HD), h=v.y;
   if(d<1.5||d>13.5) continue; if(h<4.0||h>14.0) continue;
   if(!((u>-1.0&&u<6.0)||(u>46.0&&u<53.0))) continue;
   var ub=Math.round(u*4)/4, hb=Math.round(h*10)/10, k=ub+'|'+hb;
   bins[k]=(bins[k]||0)+1; n++; } });
 var byU={};
 Object.keys(bins).forEach(function(k){ var a=k.split('|'), u=+a[0], h=+a[1];
  (byU[u]=byU[u]||[]).push([h,bins[k]]); });
 var L=['scan vertices binned: '+n];
 Object.keys(byU).map(Number).sort(function(a,b){return a-b;}).forEach(function(u){
  var r=byU[u].sort(function(a,b){return b[1]-a[1];}).slice(0,4);
  L.push('u '+u.toFixed(2).padStart(6)+'   surfaces h '+r.map(function(x){return x[0].toFixed(1)+' ('+x[1]+')';}).join('  '));
 });
 return L.join(' ~ ');
})()`);
out.split(' ~ ').forEach(x => console.log(x)); P.close(); process.exit(0);
