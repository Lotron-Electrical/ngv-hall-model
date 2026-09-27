#!/usr/bin/env node
// THE STUDIO'S TESTS (Lloyd, 2026-09-05): one command, `npm test` in studio/. Serves the repo on a
// spare port, drives the two browser test pages in real Chrome (WebAudio needs a browser, so the
// tests are pages), and exits non-zero on any failed assert. Playwright comes from the godmode-site
// install on this PC (PLAYWRIGHT_DIR overrides), real Chrome from E:\caches\ms-playwright.
'use strict';
const path=require('path'), {spawn}=require('child_process');
const ROOT=path.join(__dirname,'..');
// `node run-tests.cjs test-lights` runs only the pages whose name holds that text. CPU_THROTTLE=6
// slows every page six times over (Chrome's own CPU throttle), which is how a loaded PC or a
// GPU-less sandbox runs them, so a test that only passes on a fast idle desk shows up red here.
const ONLY=process.argv.slice(2), THROTTLE=+(process.env.CPU_THROTTLE||0);
process.env.PLAYWRIGHT_BROWSERS_PATH=process.env.PLAYWRIGHT_BROWSERS_PATH||'E:/caches/ms-playwright';
const PW=process.env.PLAYWRIGHT_DIR||'C:/Users/Lloyd Gibbs/Claude Projects/godmode-site/node_modules';
const {chromium}=require(require.resolve('playwright',{paths:[PW,ROOT]}));

// A FREE PORT, NOT A FIXED ONE (2026-09-27): with 8891 hard coded, a server some other checkout
// already had on it would answer the fetch below and the pages would be measured against THAT
// checkout's files. PORT still overrides.
const freePort=()=>new Promise((res,rej)=>{ const s=require('net').createServer(); s.unref(); s.on('error',rej);
 s.listen(0,'127.0.0.1',()=>{ const p=s.address().port; s.close(()=>res(p)); }); });

(async()=>{
 const PORT=+(process.env.PORT||await freePort());
 const server=spawn(process.execPath,[path.join(ROOT,'tools','serve.js'),'--port',String(PORT)],{stdio:'ignore',windowsHide:true});
 let serverGone=false; server.on('exit',()=>{ serverGone=true; });
 const base='http://127.0.0.1:'+PORT+'/studio/';
 for(let i=0;i<40;i++){ if(serverGone)break; try{ await fetch(base+'model.js'); break; }catch(e){ await new Promise(r=>setTimeout(r,250)); } }
 // our own server must be the one answering: if it died (port taken) the fetch hit a stranger
 if(serverGone){ console.error('runner error: tools/serve.js exited, port '+PORT+' is taken'); process.exit(2); }
 const browser=await chromium.launch({channel:'chrome',headless:true,args:['--autoplay-policy=no-user-gesture-required']});
 let failed=0;
 const run=async(page,globalName,pick)=>{
  if(ONLY.length&&!ONLY.some(o=>page.indexOf(o)>=0))return;
  const p=await browser.newPage({viewport:{width:1280,height:720}});
  if(THROTTLE>1){ const cdp=await p.context().newCDPSession(p); await cdp.send('Emulation.setCPUThrottlingRate',{rate:THROTTLE}); }
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
 const ltN=R=>Object.keys(R).filter(k=>/^assert\d+$/.test(k)).map(k=>+k.slice(6)).sort((a,b)=>a-b);
 const ltPick=R=>R.ok===true&&ltN(R).length>=9&&ltN(R).every(i=>R['assert'+i]===true); ltPick.summary=R=>Object.assign({engine:R.engine,asserts:ltN(R).map(i=>R['assert'+i]),frameT:R.steps&&R.steps.frameT,tries:R.steps&&R.steps.tries,exportParity:R.steps&&R.steps.syncParity&&{compared:R.steps.syncParity.compared,mismatches:R.steps.syncParity.mismatches},solo:R.steps&&R.steps.solo,oneLayer:R.steps&&R.steps.oneLayer},ltPick(R)?{}:{steps:R.steps,error:R.error});
 const tlPick=R=>R.ok===true&&[1,2,3,4,5,6,7].every(i=>R['assert'+i]===true); tlPick.summary=R=>({asserts:[1,2,3,4,5,6,7].map(i=>R['assert'+i]),live:R.live,rebuild:R.rebuild,fails:R.fails});
 const prPick=R=>R.ok===true&&(!R.fails||R.fails.length===0); prPick.summary=R=>({counts:R.counts,song:R.numbers&&R.numbers.song,stacks:R.numbers&&R.numbers.stacks,fails:R.fails});
 const lyPick=R=>R.ok===true&&R.fails.length===0; lyPick.summary=R=>({numbers:R.numbers,fails:R.fails});
 const coPick=R=>R.ok===true&&R.fails.length===0; coPick.summary=R=>({results:(R.numbers.results||[]).map(r=>({pal:r.pal,hall:r.hall,map:r.map,ratio:r.ratio,cols:r.cols,perCol:R.ok?undefined:r.perCol})),fails:R.fails});
 try{ await run('test-engine.html','RESULT',engPick); await run('test-lights.html','LIGHTS_TEST',ltPick); await run('test-timeline.html','TIMELINE_TEST',tlPick); await run('test-presets.html','PRESETS_TEST',prPick); await run('test-layers.html','LAYERS_TEST',lyPick); await run('test-columns.html','COLUMNS_TEST',coPick); }
 finally{ await browser.close(); server.kill(); }
 // the lights test exports a `verify` show: leave the folder as it was
 const fs=require('fs'); for(const f of ['verify.wav','verify.cues.json','verify.project.json']){ try{ fs.unlinkSync(path.join(ROOT,'show',f)); }catch(e){} }
 try{ const sj=path.join(ROOT,'show','shows.json'); const list=JSON.parse(fs.readFileSync(sj,'utf8')).filter(n=>n!=='verify'); fs.writeFileSync(sj,JSON.stringify(list)+'\n'); }catch(e){}
 console.log(failed?'FAILED '+failed:'ALL PASS'); process.exit(failed?1:0);
})().catch(e=>{ console.error('runner error',e); process.exit(2); });
