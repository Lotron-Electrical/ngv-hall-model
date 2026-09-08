// After roam-errors.mjs: probe the page left in the same tab (context lost? flash? layers? draw calls?)
import { attach } from './cdp.mjs';
const P = await attach({ port: +(process.env.CDP_PORT || 9334), width: 1280, height: 800 });
const q = 'JSON.stringify({lost:(function(){var c=document.getElementById("cv"); var g=c.getContext("webgl2")||c.getContext("webgl"); return g?g.isContextLost():"nogl";})(), flash:getComputedStyle(document.getElementById("flash")).opacity, house:dbg.lit.house, day:dbg.lit.day, layers:dbg.state.layers.map(function(l){return l.name+":"+l.opacity;}), calls:dbg.R.info.render.calls, tris:dbg.R.info.render.triangles, eye:[dbg.eye.x,dbg.eye.y,dbg.eye.z].map(function(v){return +v.toFixed(2);}), yaw:dbg.yaw(), fps:dbg.fps(), hallVis:dbg.hall?dbg.hall.visible:null, idle:dbg.idle, roam:dbg.roam()})';
console.log(await P.ev(q).catch(e => e.message));
await P.shot('E:/sitecapture-captures/ngv-site/agent-ref-walls/shots/pose/roam-live2.jpg');
P.close(); process.exit(0);
