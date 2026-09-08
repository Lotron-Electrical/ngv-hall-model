// The measured canopy's own height profile across the hall (canopy meshes only), so the surface can be read at
// the north wall and continued over the gallery behind it.
import { attach } from './cdp.mjs';
const P = await attach({ port: +(process.env.CDP_PORT || 9334), width: 900, height: 700 });
await P.open('index.html');
console.log(await P.ev(`(function(){ var O=new dbg.THREE.Vector3(-54.907447,-1.43545,3.040286), HD=new dbg.THREE.Vector3(0.219196,0,-0.975681);
 var lo={}, hi={}, names={};
 dbg.hall.traverse(function(o){ if(!o.isMesh)return; var nm=(o.name+' '+(o.material&&o.material.name||'')).toLowerCase();
  if(!/canopy/.test(nm) || /corridor/.test(nm))return; names[o.material&&o.material.name||o.name]=1;
  o.updateWorldMatrix(true,false); var p=o.geometry.attributes.position; if(!p)return; var v=new dbg.THREE.Vector3();
  for(var i=0;i<p.count;i+=5){ v.fromBufferAttribute(p,i).applyMatrix4(o.matrixWorld).sub(O); var d=v.dot(HD), h=v.y;
   var b=Math.round(d*2)/2; if(lo[b]===undefined||h<lo[b])lo[b]=h; if(hi[b]===undefined||h>hi[b])hi[b]=h; } });
 var k=Object.keys(lo).map(Number).sort(function(a,b){return a-b;});
 var prof=k.map(function(b){return b+':'+lo[b].toFixed(2)+'-'+hi[b].toFixed(2);});
 return JSON.stringify({meshes:Object.keys(names), d_from:k[0], d_to:k[k.length-1], profile:prof.slice(0,10).concat(['...']).concat(prof.slice(-4))}); })()`).catch(e => e.message));
P.close(); process.exit(0);
