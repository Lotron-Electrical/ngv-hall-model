// The built canopy's extent in the hall frame: how far north (d<0) and south it reaches, and its height there.
import { attach } from './cdp.mjs';
const P = await attach({ port: +(process.env.CDP_PORT || 9334), width: 900, height: 700 });
await P.open('index.html');
console.log(await P.ev(`(function(){ var O=new dbg.THREE.Vector3(-54.907447,-1.43545,3.040286), HU=new dbg.THREE.Vector3(0.975681,0,0.219196), HD=new dbg.THREE.Vector3(0.219196,0,-0.975681);
 var u0=1e9,u1=-1e9,d0=1e9,d1=-1e9,h0=1e9,h1=-1e9,n=0, bins={};
 dbg.hall.traverse(function(o){ if(!o.isMesh)return; var nm=(o.name+' '+(o.material&&o.material.name||'')).toLowerCase(); if(!/canopy|ceiling|glass|pane|rib/.test(nm))return;
  o.updateWorldMatrix(true,false); var p=o.geometry.attributes.position; if(!p)return; var v=new dbg.THREE.Vector3();
  for(var i=0;i<p.count;i+=7){ v.fromBufferAttribute(p,i).applyMatrix4(o.matrixWorld).sub(O); var u=v.dot(HU), d=v.dot(HD), h=v.y;
   if(h<8)continue; n++; u0=Math.min(u0,u);u1=Math.max(u1,u);d0=Math.min(d0,d);d1=Math.max(d1,d);h0=Math.min(h0,h);h1=Math.max(h1,h);
   var b=Math.round(d); if(!bins[b]||h<bins[b])bins[b]=h; } });
 var keys=Object.keys(bins).map(Number).sort(function(a,b){return a-b;});
 var low=keys.slice(0,4).map(function(k){return k+':'+bins[k].toFixed(2);}).join(' ');
 var high=keys.slice(-4).map(function(k){return k+':'+bins[k].toFixed(2);}).join(' ');
 return JSON.stringify({verts:n, u:[+u0.toFixed(2),+u1.toFixed(2)], d:[+d0.toFixed(2),+d1.toFixed(2)], h:[+h0.toFixed(2),+h1.toFixed(2)], lowest_d_bins:low, highest_d_bins:high}); })()`).catch(e => e.message));
P.close(); process.exit(0);
