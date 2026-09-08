// 2026-09-09: the ceiling pixel map, verified in the built page: how many panes it holds, what the patch
// works out to, and whether the map's texels actually change when a pattern runs.
import { attach } from './cdp.mjs';
const P = await attach({ port: +(process.env.CDP_PORT || 9334), width: 900, height: 700 });
await P.open('index.html');
for (let i = 0; i < 60; i++) { await P.sleep(500); if (await P.ev('!!(window.PIX && PIX.n)').catch(() => false)) break; }
const out = await P.ev(`(function(){
 const L=[];
 L.push('panes '+PIX.n+'  texture '+PIX.side+'x'+PIX.side+'  channels '+(PIX.n*4));
 L.push('hall u '+PIX.u0.toFixed(2)+' to '+PIX.u1.toFixed(2)+'   v '+PIX.v0.toFixed(2)+' to '+PIX.v1.toFixed(2));
 const g=ngv.scene.getObjectByName('canopy-glass-pieces');
 L.push('glass mesh '+(g?'present':'MISSING')+', pid attribute '+(g&&g.geometry.attributes.pid?g.geometry.attributes.pid.count+' vertices':'MISSING'));
 if(g&&g.geometry.attributes.pid){ const a=g.geometry.attributes.pid.array; let mx=0; for(let i=0;i<a.length;i++)if(a[i]>mx)mx=a[i];
  L.push('highest pane id in the geometry '+mx+' (expected '+(PIX.n-1)+')'); }
 L.push('uniforms '+(PIX.uni?Object.keys(PIX.uni).filter(k=>k.indexOf('pix')===0).join(' '):'MISSING'));
 const ppu=128,u0=200,nU=Math.ceil(PIX.n/ppu);
 L.push('patch: '+nU+' universes from '+u0+' to '+(u0+nU-1)+' with '+ppu+' panes each');
 // run a pattern for a moment and see the map actually change
 PIX.pattern='rainbow'; PIX.on=1; PIX.t=0; PIX.step(0.5);
 let a1=0; for(let i=0;i<PIX.n*4;i++)a1+=PIX.data[i];
 PIX.t=6.0; PIX.step(0.0);
 let a2=0; for(let i=0;i<PIX.n*4;i++)a2+=PIX.data[i];
 L.push('map fills: sum at t=0.5 is '+a1+', at t=6 is '+a2+' ('+(a1>0&&a1!==a2?'live':'NOT ANIMATING')+')');
 PIX.pattern='off'; PIX.on=0; PIX.step(0.0);
 let a3=0; for(let i=0;i<PIX.n*4;i++)a3+=PIX.data[i];
 L.push('off clears the map: '+(a3===0?'yes':'NO, sum '+a3));
 return L.join(' ~ ');
})()`);
out.split(' ~ ').forEach(x => console.log(x)); P.close(); process.exit(0);
