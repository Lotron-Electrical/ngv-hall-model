// UI VERIFICATION (Lloyd, 2026-09-05): drives the studio in real Chrome and shoots every tab at
// phone size with touch emulation and every view at desktop size, into studio/verify/. It also
// asserts the page never scrolls sideways, from a 360 px phone up to 1440, because a horizontal
// page scroll is the failure a screenshot at one width hides.
const {chromium}=require('playwright');
const path=require('path');
const OUT=path.join(__dirname,'verify');
const BASE=process.env.BASE||'http://localhost:8878';
const VIEWS=['rack','pattern','song','mixer','fx'];

const shot=(p,name)=>p.screenshot({path:path.join(OUT,name+'.png')});

(async()=>{
 const browser=await chromium.launch({channel:'chrome',args:['--autoplay-policy=no-user-gesture-required']});
 const errs=[], widths={};

 // ---- phone: 390 x 844, touch, every tab plus the drawer states and the more sheet
 const mob=await browser.newContext({viewport:{width:390,height:844},hasTouch:true,isMobile:true,deviceScaleFactor:2});
 const p=await mob.newPage();
 p.on('pageerror',e=>errs.push('phone pageerror: '+e.message));
 p.on('console',m=>{ if(m.type()==='error'&&!/404|Failed to load resource/.test(m.text()))errs.push('phone console: '+m.text()); });
 await p.goto(BASE+'/studio.html?stub',{waitUntil:'load'});
 await p.waitForTimeout(2500);
 await p.click('#play'); await p.waitForTimeout(600);
 for(const v of VIEWS){ await p.click('#nav button[data-v="'+v+'"]'); await p.waitForTimeout(420); await shot(p,'m-'+v); }
 await p.click('#nav button[data-v="hall"]'); await p.waitForTimeout(900); await shot(p,'m-hall');
 // the drawer, shut then open, on the pattern view and on the lights machine
 await p.click('#nav button[data-v="pattern"]'); await p.waitForTimeout(400);
 await shot(p,'m-drawer-shut');
 await p.click('#drawertog'); await p.waitForTimeout(450); await shot(p,'m-drawer-open');
 const chips=await p.$$eval('#machtabs button',bs=>bs.map(b=>b.textContent.trim().toLowerCase()));
 for(let i=0;i<chips.length;i++){
  if(!/drum|light|pluck/.test(chips[i]))continue;
  await p.click('#machtabs button:nth-child('+(i+1)+')'); await p.waitForTimeout(450);
  await shot(p,'m-strip-'+chips[i].replace(/[^a-z]/g,''));
 }
 await p.click('#menubtn'); await p.waitForTimeout(400); await shot(p,'m-menu');
 await p.keyboard.press('Escape'); await p.waitForTimeout(250);
 await p.click('#nav button[data-v="rack"]'); await p.waitForTimeout(300);
 await p.click('.rackcard .dots'); await p.waitForTimeout(400); await shot(p,'m-machinemenu');
 await p.keyboard.press('Escape'); await p.waitForTimeout(200);
 // horizontal overflow at the narrow widths
 for(const w of [360,390,768]){ await p.setViewportSize({width:w,height:844}); await p.waitForTimeout(500);
  widths[w]=await p.evaluate(()=>({doc:document.documentElement.scrollWidth,win:window.innerWidth,
   body:document.body.scrollWidth})); }
 await mob.close();

 // ---- desktop: 1440 x 900, every view, plus the sheet and the drawer
 const desk=await browser.newContext({viewport:{width:1440,height:900}});
 const d=await desk.newPage();
 d.on('pageerror',e=>errs.push('desktop pageerror: '+e.message));
 d.on('console',m=>{ if(m.type()==='error'&&!/404|Failed to load resource/.test(m.text()))errs.push('desktop console: '+m.text()); });
 await d.goto(BASE+'/studio.html?stub',{waitUntil:'load'});
 await d.waitForTimeout(2500);
 await d.click('#drawertog'); await d.waitForTimeout(300);
 await d.click('#play'); await d.waitForTimeout(600);
 for(const v of VIEWS){ await d.click('#tabs button[data-v="'+v+'"]'); await d.waitForTimeout(420); await shot(d,'d-'+v); }
 const dchips=await d.$$eval('#machtabs button',bs=>bs.map(b=>b.textContent.trim().toLowerCase()));
 for(let i=0;i<dchips.length;i++){
  if(!/drum|light|pluck/.test(dchips[i]))continue;
  await d.click('#machtabs button:nth-child('+(i+1)+')'); await d.waitForTimeout(400);
  await d.click('#tabs button[data-v="pattern"]'); await d.waitForTimeout(450);
  await shot(d,'d-strip-'+dchips[i].replace(/[^a-z]/g,''));
 }
 await d.click('#menubtn'); await d.waitForTimeout(400); await shot(d,'d-menu');
 await d.keyboard.press('Escape'); await d.waitForTimeout(250);
 for(const w of [1280,1440]){ await d.setViewportSize({width:w,height:900}); await d.waitForTimeout(500);
  widths[w]=await d.evaluate(()=>({doc:document.documentElement.scrollWidth,win:window.innerWidth,
   body:document.body.scrollWidth})); }
 await desk.close();
 await browser.close();

 const overflow=Object.entries(widths).filter(([w,v])=>v.doc>v.win||v.body>v.win).map(([w])=>+w);
 console.log(JSON.stringify({ok:errs.length===0&&overflow.length===0,errors:errs,widths,overflow},null,1));
 process.exit(errs.length||overflow.length?1:0);
})();
