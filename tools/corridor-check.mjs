// Confirms the gallery behind the north wall is built to its stated roof height, and that nothing of it shows
// above the opening head from the hall floor.
import { attach } from './cdp.mjs';
const P = await attach({ port: +(process.env.CDP_PORT || 9334), width: 900, height: 700 });
await P.open('index.html');
console.log(await P.ev(`(function(){ var O=new dbg.THREE.Vector3(-54.907447,-1.43545,3.040286), HD=new dbg.THREE.Vector3(0.219196,0,-0.975681);
 var out={};
 dbg.hall.traverse(function(o){ if(!o.isMesh||!/corridor/.test(o.name))return; o.updateWorldMatrix(true,false);
  var p=o.geometry.attributes.position, v=new dbg.THREE.Vector3(), hi=-1e9, lo=1e9, dl=1e9, dh=-1e9;
  for(var i=0;i<p.count;i++){ v.fromBufferAttribute(p,i).applyMatrix4(o.matrixWorld).sub(O); hi=Math.max(hi,v.y); lo=Math.min(lo,v.y); var d=v.dot(HD); dl=Math.min(dl,d); dh=Math.max(dh,d); }
  var k=o.name; if(!out[k])out[k]={h:[lo,hi], d:[dl,dh], n:0}; out[k].h=[Math.min(out[k].h[0],lo),Math.max(out[k].h[1],hi)]; out[k].d=[Math.min(out[k].d[0],dl),Math.max(out[k].d[1],dh)]; out[k].n++; });
 var r={}; for(var k in out) r[k]='h '+out[k].h[0].toFixed(2)+'-'+out[k].h[1].toFixed(2)+'  d '+out[k].d[0].toFixed(2)+'-'+out[k].d[1].toFixed(2)+'  x'+out[k].n;
 return JSON.stringify(r,null,1); })()`).catch(e => e.message));
P.close(); process.exit(0);
