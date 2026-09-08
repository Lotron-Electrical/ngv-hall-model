// After the pose-shot setup, how big is the canvas against the stage and the viewport? (the 4K pose pairs came out clipped)
import { attach } from './cdp.mjs';
const P = await attach({ port: +(process.env.CDP_PORT || 9334), width: 1080, height: 1920 });
await P.send('Page.navigate', { url: 'http://127.0.0.1:8877/index.html?install=gandel-2026' });
for (let i = 0; i < 120; i++) { await P.sleep(500); if (await P.ev('!!(window.ngv&&window.ngv.hall&&document.getElementById("install"))').catch(() => false)) break; }
await P.ev(`localStorage.setItem('ngv.install','gandel-2026'); document.getElementById('install').click()`);
for (let i = 0; i < 60; i++) { await P.sleep(500); if (await P.ev('!!(window.ngv&&window.ngv.game)').catch(() => false)) break; }
await P.ev(`document.querySelector('#start').click()`); await P.sleep(800);
await P.ev(`document.body.classList.add("immersive"); window.dispatchEvent(new Event("resize"));`); await P.sleep(1500);
console.log(await P.ev(`(function(){ var c=document.getElementById('cv'), s=document.getElementById('stage'); var sz=new dbg.THREE.Vector2(); dbg.R.getSize(sz); return JSON.stringify({win:[innerWidth,innerHeight], stage:[s.clientWidth,s.clientHeight], cv:[c.clientWidth,c.clientHeight], buffer:[c.width,c.height], styleW:c.style.width, styleH:c.style.height, renderer:[sz.x,sz.y], dpr:dbg.R.getPixelRatio(), aspect:ngv.cam.aspect}); })()`).catch(e => e.message));
P.close(); process.exit(0);
