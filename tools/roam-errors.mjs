// Load the LIVE page, press Free roam, print every console error and uncaught exception.
//   node tools/roam-errors.mjs [seconds]   (CDP_PORT 9334)
import { attach } from './cdp.mjs';
const secs = +(process.argv[2] || 12);
const P = await attach({ port: +(process.env.CDP_PORT || 9334), width: 1280, height: 800 });
await P.send('Network.setCacheDisabled', { cacheDisabled: true }).catch(() => {});
await P.send('Page.navigate', { url: 'https://lotron-electrical.github.io/ngv-hall-model/index.html' });
for (let i = 0; i < 120; i++) { await P.sleep(500); if (await P.ev('!!(window.ngv&&window.ngv.hall)').catch(() => false)) break; }
await P.ev('document.getElementById("enter").click()').catch(function(){}); await P.sleep(2500);
console.log('entered; errors before Free roam:', P.errors.length);
console.log('pressed:', await P.ev('(function(){ var b=document.getElementById("roamfab"); if(!b) return "no button"; b.click(); return "ok"; })()').catch(function (e) { return e.message; }));
for (let i = 0; i < secs * 2; i++) { await P.sleep(500); if (P.errors.length) break; }
console.log('eye:', await P.ev('window.eye ? [eye.x, eye.y, eye.z].map(function(v){ return +v.toFixed(2); }).join(",") : "none"').catch(function (e) { return e.message; }));
await P.shot('E:/sitecapture-captures/ngv-site/agent-ref-walls/shots/pose/roam-live.jpg');
console.log('state:', await P.ev('JSON.stringify({roam:window.dbg?dbg.roam():"nodbg", eye:window.dbg?[dbg.eye.x,dbg.eye.y,dbg.eye.z].map(function(v){return +v.toFixed(2);}):null, fps:window.dbg?dbg.fps():null, fab:document.getElementById("roamfab").className, veil:getComputedStyle(document.getElementById("enter")).visibility})').catch(function (e) { return e.message; }));
console.log(P.errors.length ? P.errors.join('\n') : 'no errors captured');
P.close(); process.exit(0);
