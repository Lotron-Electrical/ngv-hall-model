// UI VERIFICATION (Lloyd, 2026-09-05): drives the studio in real Chrome and shoots every view at
// both target sizes into studio/verify/. Run with the repo served on 8878. It also prints any
// console error the page raised, because a silent throw in a render is the failure that a
// screenshot alone can hide.
const {chromium}=require('playwright');
const path=require('path');
const OUT=path.join(__dirname,'verify');
const BASE=process.env.BASE||'http://localhost:8878';

const VIEWS=['rack','pattern','song','mixer','fx'];
const SIZES=[{w:1440,h:900,tag:'1440'},{w:1280,h:720,tag:'1280'}];

(async()=>{
 const browser=await chromium.launch({channel:'chrome',args:['--autoplay-policy=no-user-gesture-required']});
 const errs=[];
 for(const size of SIZES){
  const ctx=await browser.newContext({viewport:{width:size.w,height:size.h},deviceScaleFactor:1});
  const page=await ctx.newPage();
  page.on('pageerror',e=>errs.push(size.tag+' pageerror: '+e.message));
  page.on('console',m=>{ if(m.type()==='error')errs.push(size.tag+' console: '+m.text()); });
  await page.goto(BASE+'/studio.html?stub',{waitUntil:'load'});
  await page.waitForTimeout(2500);
  // start the clock so the playheads and the meter are in a real state for the shots
  await page.click('#play');
  await page.waitForTimeout(700);
  for(const v of VIEWS){
   await page.click('#tabs button[data-v="'+v+'"]');
   await page.waitForTimeout(450);
   await page.screenshot({path:path.join(OUT,v+'-'+size.tag+'.png')});
  }
  // the play strip changes per machine: shoot the drum pads and the lights desk too
  const labels=await page.$$eval('#machtabs button',bs=>bs.map(b=>b.textContent.trim()));
  for(let i=0;i<labels.length;i++){
   const label=labels[i].toLowerCase();
   if(!/drum|light|pluck/.test(label))continue;
   // the tab strip is rebuilt on every click, so address it by position, never by a stale handle
   await page.click('#machtabs button:nth-child('+(i+1)+')'); await page.waitForTimeout(400);
   await page.click('#tabs button[data-v="pattern"]'); await page.waitForTimeout(500);
   await page.screenshot({path:path.join(OUT,'strip-'+label.replace(/[^a-z]/g,'')+'-'+size.tag+'.png')});
  }
  // and the sim hidden, so the wide layout is checked as well
  await page.click('#simtoggle'); await page.waitForTimeout(400);
  await page.screenshot({path:path.join(OUT,'nosim-'+size.tag+'.png')});
  await ctx.close();
 }
 await browser.close();
 console.log(JSON.stringify({ok:errs.length===0,errors:errs},null,1));
})();
