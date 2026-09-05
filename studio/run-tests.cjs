#!/usr/bin/env node
// THE STUDIO'S TESTS (Lloyd, 2026-09-05): one command, `npm test` in studio/. Serves the repo on a
// spare port, drives the two browser test pages in real Chrome (WebAudio needs a browser, so the
// tests are pages), and exits non-zero on any failed assert. Playwright comes from the godmode-site
// install on this PC (PLAYWRIGHT_DIR overrides), real Chrome from E:\caches\ms-playwright.
'use strict';
const path=require('path'), {spawn}=require('child_process');
const ROOT=path.join(__dirname,'..');
const PORT=+(process.env.PORT||8891);
process.env.PLAYWRIGHT_BROWSERS_PATH=process.env.PLAYWRIGHT_BROWSERS_PATH||'E:\caches\ms-playwright';
const PW=process.env.PLAYWRIGHT_DIR||'C:/Users/Lloyd Gibbs/Claude Projects/godmode-site/node_modules';
const {chromium}=require(require.resolve('playwright',{paths:[PW,ROOT]}));

(async()=>{
 const server=spawn(process.execPath,[path.join(ROOT,'tools','serve.js'),'--port',String(PORT)],{stdio:'ignore',windowsHide:true});
 const base='http://127.0.0.1:'+PORT+'/studio/';
 for(let i=0;i<40;i++){ try{ await fetch(base+'model.js'); break; }catch(e){ await new Promise(r=>setTimeout(r,250)); } }
 const browser=await chromium.launch({channel:'chrome',headless:true,args:['--autoplay-policy=no-user-gesture-required']});
 let failed=0;
 const run=async(page,globalName,pick)=>{
  const p=await browser.newPage({viewport:{width:1280,height:720}});
  const errs=[]; p.on('pageerror',e=>errs.push(e.message));
  await p.goto(base+page+'?cb='+Date.now(),{waitUntil:'load'});
  await p.waitForFunction(g=>!!window[g],globalName,{timeout:900000}).catch(()=>{});
  const R=await p.evaluate(g=>window[g]||null,globalName);
  const ok=!!R&&pick(R)&&errs.length===0;
  console.log((ok?'PASS ':'FAIL ')+page+' '+JSON.stringify(R?pick.summary(R):{noResult:true})+(errs.length?' pageErrors='+JSON.stringify(errs):''));
  if(!ok)failed++;
  await p.close();
 };
 const engPick=R=>R.ok===true&&(!R.fails||R.fails.length===0); engPick.summary=R=>({peak:R.peak,rms:R.rms,live:R.live,fails:R.fails});
 const ltPick=R=>R.ok===true&&[1,2,3,4,5,6].every(i=>R['assert'+i]===true); ltPick.summary=R=>({engine:R.engine,asserts:[1,2,3,4,5,6].map(i=>R['assert'+i]),frameT:R.steps&&R.steps.frameT});
 const tlPick=R=>R.ok===true&&[1,2,3,4,5,6,7].every(i=>R['assert'+i]===true); tlPick.summary=R=>({asserts:[1,2,3,4,5,6,7].map(i=>R['assert'+i]),live:R.live,rebuild:R.rebuild,fails:R.fails});
 const prPick=R=>R.ok===true&&(!R.fails||R.fails.length===0); prPick.summary=R=>({counts:R.counts,song:R.numbers&&R.numbers.song,stacks:R.numbers&&R.numbers.stacks,fails:R.fails});
 try{ await run('test-engine.html','RESULT',engPick); await run('test-lights.html','LIGHTS_TEST',ltPick); await run('test-timeline.html','TIMELINE_TEST',tlPick); await run('test-presets.html','PRESETS_TEST',prPick); }
 finally{ await browser.close(); server.kill(); }
 // the lights test exports a `verify` show: leave the folder as it was
 const fs=require('fs'); for(const f of ['verify.wav','verify.cues.json','verify.project.json']){ try{ fs.unlinkSync(path.join(ROOT,'show',f)); }catch(e){} }
 try{ const sj=path.join(ROOT,'show','shows.json'); const list=JSON.parse(fs.readFileSync(sj,'utf8')).filter(n=>n!=='verify'); fs.writeFileSync(sj,JSON.stringify(list)); }catch(e){}
 console.log(failed?'FAILED '+failed:'ALL PASS'); process.exit(failed?1:0);
})().catch(e=>{ console.error('runner error',e); process.exit(2); });
