// 2026-09-09: what the built end galleries actually span, so a change to ENDW can be checked in the scene
// rather than in the source. Prints every gallery-* mesh's height range and where along the hall it sits.
import { attach } from './cdp.mjs';
const P = await attach({ port: +(process.env.CDP_PORT || 9334), width: 900, height: 700 });
await P.open('index.html');
const out = await P.ev(`(function(){
 var T=dbg.THREE, O=new T.Vector3(-54.907447,-1.43545,3.040286),
     HU=new T.Vector3(0.975681,0,0.219196);
 var acc={};
 ngv.scene.traverse(function(o){ if(!o.isMesh)return; var nm=o.name||''; if(!/^gallery-/.test(nm))return;
  o.updateWorldMatrix(true,false); var p=o.geometry.attributes.position; if(!p)return; var v=new T.Vector3();
  for(var i=0;i<p.count;i++){ v.fromBufferAttribute(p,i).applyMatrix4(o.matrixWorld).sub(O);
   var u=v.dot(HU), y=v.y, e=(u<26?'west':'east'), k=nm+' '+e;
   var a=acc[k]||(acc[k]={lo:1e9,up:-1e9,ul:1e9,uu:-1e9,n:0});
   if(y<a.lo)a.lo=y; if(y>a.up)a.up=y; if(u<a.ul)a.ul=u; if(u>a.uu)a.uu=u; a.n++; } });
 return Object.keys(acc).sort().map(function(k){ var a=acc[k];
  return k.padEnd(28)+' h '+a.lo.toFixed(2)+'-'+a.up.toFixed(2)+'   u '+a.ul.toFixed(2)+'-'+a.uu.toFixed(2);
 }).join(' ~ ');
})()`);
out.split(' ~ ').forEach(x => console.log(x)); P.close(); process.exit(0);
