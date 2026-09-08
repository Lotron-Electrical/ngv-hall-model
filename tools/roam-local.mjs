// The working tree's page on the local server: Enter, Free roam, wait for it to land, screenshot, print errors and state.
//   python tools/with_server.py node tools/roam-local.mjs <out.jpg>   (CDP_PORT 9334)
import { attach } from './cdp.mjs';
const out = process.argv[2] || 'E:/sitecapture-captures/ngv-site/agent-ref-walls/shots/pose/roam-local.jpg';
const P = await attach({ port: +(process.env.CDP_PORT || 9334), width: 1280, height: 800 });
await P.open('index.html');
await P.roam();
await P.sleep(2000);
console.log(await P.ev('JSON.stringify({roam:dbg.roam(), house:dbg.lit.house, eye:[dbg.eye.x,dbg.eye.y,dbg.eye.z].map(function(v){return +v.toFixed(2);}), fps:+dbg.fps().toFixed(0)})').catch(e => e.message));
await P.shot(out);
console.log(P.errors.length ? P.errors.join('\n') : 'no errors captured');
P.close(); process.exit(0);
