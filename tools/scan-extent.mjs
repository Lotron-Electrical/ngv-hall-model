// 2026-09-09: what the loaded scan actually covers, so a probe knows where it can measure at all.
import { attach } from './cdp.mjs';
const P = await attach({ port: +(process.env.CDP_PORT || 9334), width: 900, height: 700 });
await P.open('index.html');
const out = await P.ev(`(function(){
 var T=dbg.THREE, O=new T.Vector3(-54.907447,-1.43545,3.040286),
     HU=new T.Vector3(0.975681,0,0.219196), HD=new T.Vector3(0.219196,0,-0.975681);
 var names={}, tot=0, uMin=1e9,uMax=-1e9,hMin=1e9,hMax=-1e9,dMin=1e9,dMax=-1e9, roots=[];
 ngv.scene.traverse(function(o){ if(!o.isMesh)return; var nm=(o.name||'(none)');
  if(nm!=='(none)' && !/^clean-hall-textured/.test(nm)) return;
  names[nm.replace(/[0-9_]+$/,'')]=(names[nm.replace(/[0-9_]+$/,'')]||0)+1;
  o.updateWorldMatrix(true,false); var p=o.geometry.attributes.position; if(!p)return; tot+=p.count;
  var v=new T.Vector3();
  for(var i=0;i<p.count;i+=97){ v.fromBufferAttribute(p,i).applyMatrix4(o.matrixWorld).sub(O);
   var u=v.dot(HU), d=v.dot(HD), h=v.y;
   if(u<uMin)uMin=u; if(u>uMax)uMax=u; if(d<dMin)dMin=d; if(d>dMax)dMax=d; if(h<hMin)hMin=h; if(h>hMax)hMax=h; } });
 return 'meshes '+JSON.stringify(names)+' ~ vertices '+tot+' ~ u '+uMin.toFixed(2)+'..'+uMax.toFixed(2)+
        ' ~ d '+dMin.toFixed(2)+'..'+dMax.toFixed(2)+' ~ h '+hMin.toFixed(2)+'..'+hMax.toFixed(2);
})()`);
out.split(' ~ ').forEach(x => console.log(x)); P.close(); process.exit(0);
