// A local notes tool for the tour storyboard (Lloyd, 2026-09-01): one page, every camera path
// with its three frames, its notes, a Play button and a Generate button.
//  - Every shot has a permanent KEY (the `<!-- shot: party-celebrate -->` line under its heading
//    in tour-storyboard.md). The number in the heading is only its place in the tour today and
//    moves when a shot is cut; the key never does, so a note or a request is never mistaken for
//    another shot's (Lloyd: a cut shot's slot was filled by the next one and things got confused).
//  - Notes are rounds. The box on the page is the DRAFT for the next round; it saves as typed
//    into the shot's Notes block in tour-storyboard.md. Generate stamps the draft as a sent
//    round (kept above the box, read-only) and gives a fresh empty box (Lloyd).
//  - Play opens the real viewer (HEAD's index.html, served as /viewer.html) on that one shot,
//    looping, so the camera path can be watched as it is.
//  - Generate queues the round for Claude in storyboard/requests.json; the page shows the
//    request's status (queued, working, done) as Claude updates it.
//   node tools/storyboard-notes.js [--port 8890]
const http=require('http'), fs=require('fs'), path=require('path'), os=require('os'), {execSync}=require('child_process');
const ROOT=path.join(__dirname,'..'), MD=path.join(ROOT,'tour-storyboard.md'), REQ=path.join(ROOT,'storyboard','requests.json'), TITLES=path.join(ROOT,'storyboard','titles.json');
const port=+(process.argv[process.argv.indexOf('--port')+1])||8890;
const MIME={'.html':'text/html; charset=utf-8','.js':'text/javascript','.mjs':'text/javascript','.json':'application/json','.glb':'model/gltf-binary','.png':'image/png','.jpg':'image/jpeg','.bin':'application/octet-stream','.css':'text/css','.wasm':'application/wasm'};

// the Notes block of a section is rounds: "V1 (sent 2026-09-01 19:49):" then the text, and so
// on; the last round is "(draft)" and is what the box on the page edits. A block with no round
// markers (the old free text) reads as one sent round with an empty draft after it.
const RM=/^V(\d+) \((sent [^)]*|draft)\):\n?/m;
function rounds(notes){
 const t=notes.replace(/\r/g,'').trim(); const out=[]; if(!t)return out;
 const bits=t.split(/^(?=V\d+ \((?:sent [^)]*|draft)\):)/m);
 for(const b of bits){ const m=b.match(RM); if(!m){ out.push({n:out.length+1,sent:'earlier',text:b.trim()}); continue; }
  out.push({n:+m[1],sent:m[2]==='draft'?null:m[2].slice(5),text:b.slice(m[0].length).trim()}); }
 return out;
}
const fmt=rs=>rs.map(r=>`V${r.n} (${r.sent?'sent '+r.sent:'draft'}):\n${r.text}`).join('\n\n');
const stamp=()=>new Date().toLocaleString('en-AU',{hour12:false}).replace(',','');
// the sections: everything from a "## " heading to the next one; the key from the comment line
// under the heading; the Notes text is what follows "**Notes:**" up to the "---" rule
function parse(){
 const md=fs.readFileSync(MD,'utf8'); const parts=md.split(/\n(?=## )/); const head=parts.shift();
 const secs=parts.map((s,i)=>{ const title=s.match(/^## (.*)/)[1]; const key=(s.match(/<!-- shot: ([\w-]+) -->/)||[])[1]||('s'+i);
  const m=s.match(/\*\*Notes:\*\*([\s\S]*?)(?=\n---|$)/); const rs=rounds(m?m[1]:'');
  if(!rs.length||rs[rs.length-1].sent)rs.push({n:(rs[rs.length-1]||{n:0}).n+1,sent:null,text:''});
  const imgs=[...s.matchAll(/!\[\]\(([^)]+)\)/g)].map(x=>x[1]);
  const body=s.replace(/^## .*\n/,'').replace(/<!-- shot: [\w-]+ -->\n?/,'').split('| start |')[0].trim(); const shot=(title.match(/^(\d+)\./)||[])[1];
  return {i,key,title,rounds:rs,imgs,body,shot:shot?+shot:null}; });
 return {head,parts,secs};
}
function writeNotes(key,rs){
 const {head,parts,secs}=parse(); const s=secs.find(x=>x.key===key); if(!s)return false;
 const re=/\*\*Notes:\*\*([\s\S]*?)(?=\n---|$)/; if(!re.test(parts[s.i]))return false;
 parts[s.i]=parts[s.i].replace(re,'**Notes:**\n'+fmt(rs)+'\n');
 fs.writeFileSync(MD,[head,...parts].join('\n')); return true;
}
// typing goes into the draft round, or into a filed round by its number (Lloyd: every text on
// the page can be edited)
function save(key,text,n){
 const s=parse().secs.find(x=>x.key===key); if(!s)return false;
 const r=n?s.rounds.find(x=>x.n===n):s.rounds[s.rounds.length-1]; if(!r)return false;
 r.text=text.replace(/\r/g,'').trim(); return writeNotes(key,s.rounds);
}
const readReq=()=>{ try{ return JSON.parse(fs.readFileSync(REQ,'utf8')); }catch(e){ return []; } };
// THE TEXT a shot shows (Lloyd): storyboard/titles.json, by shot key, [text, from, to] per line;
// the viewer reads the same file, so Play clip shows an edit at once. Publish text commits and
// pushes just that file so the live page gets it.
const readTitles=()=>{ try{ return JSON.parse(fs.readFileSync(TITLES,'utf8')); }catch(e){ return {}; } };
function saveTitle(key,idx,text){ const T=readTitles(); if(!T[key]||!T[key][idx])return false; T[key][idx][0]=text.replace(/[\r\n]/g,' ').trim(); fs.writeFileSync(TITLES,JSON.stringify(T,null,1)+'\n'); return true; }
function publishTitles(){ try{ execSync('git add storyboard/titles.json && git diff --cached --quiet -- storyboard/titles.json || git commit -q -m "The tour\'s text, edited in the storyboard tool (Lloyd)" -- storyboard/titles.json',{cwd:ROOT,shell:'bash',stdio:'pipe'}); execSync('git push -q origin HEAD:main',{cwd:ROOT,stdio:'pipe'}); return true; }catch(e){ console.error(String(e.stderr||e)); return false; } }
// a request: the shot's key, title and the round being sent; one live request per shot. The
// draft becomes a sent round and a new empty draft follows it.
function generate(key){
 const s=parse().secs.find(x=>x.key===key); if(!s)return false; const d=s.rounds[s.rounds.length-1]; if(!d.text)return false;
 // a round that repeats an earlier one word for word is a box the browser refilled, not a note
 if(s.rounds.slice(0,-1).some(r=>r.text===d.text))return false;
 d.sent=stamp(); s.rounds.push({n:d.n+1,sent:null,text:''}); if(!writeNotes(key,s.rounds))return false;
 const list=readReq().filter(r=>!(r.key===key&&r.status!=='done'));
 list.push({id:Date.now().toString(36),key,round:d.n,i:s.i,shot:s.shot,title:s.title,notes:d.text,status:'queued',at:new Date().toISOString()});
 fs.writeFileSync(REQ,JSON.stringify(list,null,1)); return true;
}
function page(){
 const {secs}=parse(); const T=readTitles();
 const esc=s=>s.replace(/[&<>]/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;'}[c]));
 const cards=secs.map(s=>{ const d=s.rounds[s.rounds.length-1], sent=s.rounds.slice(0,-1);
  return `<section id="s-${s.key}"><h2>${esc(s.title)} <span class="key">${esc(s.key)}</span><span class="req" id="rq-${s.key}"></span></h2><p>${esc(s.body).replace(/`([^`]+)`/g,'<code>$1</code>').replace(/\n+/g,'<br>')}</p>
  ${s.imgs.length?`<div class="row">${s.imgs.map(u=>`<img src="/${u}" loading="lazy">`).join('')}</div>`:''}
  ${s.shot?`<div class="clip" id="clip-${s.key}"></div><div class="btns"><button class="play" data-shot="${s.shot}" data-key="${s.key}">Play clip</button><button class="gen" data-key="${s.key}">Generate</button></div>`:''}
  ${(T[s.key]||[]).length?`<div class="tx"><b>Text</b>${T[s.key].map((l,idx)=>`<div class="line"><input autocomplete="off" data-key="${s.key}" data-idx="${idx}" value="${esc(l[0]).replace(/"/g,'&quot;')}"><span>${l[2]?esc(l[1]+' to '+l[2]+' s'):''} <i class="st" id="tx-${s.key}-${idx}"></i></span></div>`).join('')}</div>`:''}
  ${sent.length?`<details class="hist"><summary>${sent.length} round${sent.length>1?'s':''} sent</summary>${sent.map(r=>`<div class="round"><b>V${r.n}</b> <span>sent ${esc(r.sent)}</span> <span class="st" id="st-${s.key}-${r.n}"></span><textarea autocomplete="off" class="old" data-key="${s.key}" data-n="${r.n}">${esc(r.text)}</textarea></div>`).join('')}</details>`:''}
  <label>V${d.n} <span class="st" id="st-${s.key}"></span></label><textarea autocomplete="off" data-key="${s.key}" placeholder="Type your notes for round ${d.n} of this shot">${esc(d.text)}</textarea></section>`; }).join('');
 return `<!doctype html><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>Tour storyboard notes</title>
<style>body{margin:0;background:#111;color:#eee;font:15px/1.5 system-ui,sans-serif}main{max-width:1100px;margin:0 auto;padding:16px}
h1{font-size:20px;margin:8px 0 4px}h2{font-size:17px;margin:0 0 6px}section{background:#1b1b1b;border:1px solid #333;border-radius:8px;padding:14px;margin:14px 0}
p{margin:0 0 10px;color:#bbb}code{color:#9cf}.row{display:flex;gap:6px;margin-bottom:10px}.row img{width:calc((100% - 12px)/3);border-radius:4px;background:#000}
label{display:block;font-weight:600;margin-bottom:4px}textarea{width:100%;min-height:90px;box-sizing:border-box;background:#0d0d0d;color:#fff;border:1px solid #444;border-radius:6px;padding:10px;font:inherit;resize:vertical}
textarea:focus{outline:none;border-color:#7af}.st{font-weight:400;color:#8c8;font-size:13px}.top{color:#999;font-size:13px}
.key{font-size:12px;font-weight:400;color:#9cf;background:#1e2a3a;border-radius:10px;padding:1px 9px;margin-left:8px;vertical-align:middle;font-family:ui-monospace,monospace}
.btns{display:flex;gap:8px;margin:0 0 10px}button{background:#2a2a2a;color:#fff;border:1px solid #555;border-radius:6px;padding:8px 14px;font:inherit;cursor:pointer}button:hover{border-color:#7af}
button.gen{background:#173a17;border-color:#2e6b2e}button.gen:disabled{opacity:.5;cursor:default}
.hist{margin:0 0 10px;border:1px solid #333;border-radius:6px;padding:6px 10px;background:#161616}.hist summary{cursor:pointer;color:#aaa;font-size:13px}
.round{border-top:1px solid #2a2a2a;padding:8px 0 2px}.round span{color:#888;font-size:12px;margin-left:6px}textarea.old{min-height:60px;margin-top:4px;color:#ccc;background:#111;border-color:#333}
.tx{margin:0 0 10px;border:1px solid #3a3320;border-radius:6px;padding:8px 10px;background:#1a1810}.tx b{font-size:13px;color:#dc9}.line{display:flex;gap:8px;align-items:center;margin-top:6px}.line input{flex:1;background:#0d0d0d;color:#fff;border:1px solid #554;border-radius:6px;padding:8px 10px;font:inherit;min-width:0}.line input:focus{outline:none;border-color:#dc9}.line span{color:#887;font-size:12px;white-space:nowrap}.line i{font-style:normal}
#pub{position:sticky;top:8px;float:right;background:#3a2e10;border-color:#a80;margin-left:8px}
.clip{margin-bottom:10px;display:flex;gap:8px;align-items:flex-start}.clip iframe{border:0;border-radius:4px;background:#000;display:block}.clip .pc{flex:1;aspect-ratio:16/9;min-width:0}.clip .ph{width:26%;aspect-ratio:9/19}
@media(max-width:700px){.clip{flex-wrap:wrap}.clip .pc,.clip .ph{width:100%}}
.req{font-size:12px;font-weight:400;color:#111;background:#8c8;border-radius:10px;padding:1px 9px;margin-left:8px;vertical-align:middle;display:none}.req.queued{display:inline;background:#ec5}.req.working{display:inline;background:#8bf}.req.done{display:inline;background:#8c8}
@media(max-width:700px){.row{flex-wrap:wrap}.row img{width:100%}}</style>
<main><button id="pub" type="button">Publish text</button><h1>Gandel Hall tour: camera storyboard</h1><div class="top">The blue tag is the shot's permanent name; the number is only its place in the tour today. The box is the next round's notes and saves as you type. Generate sends that round to Claude, files it above the box, and opens a fresh box; the chip shows where the round is up to. The Text lines are what the shot shows: edit them, Play clip shows the change at once, and Publish text puts it on the live page.</div>
<section id="s-all"><h2>The whole tour</h2><p>Every shot in order, on a loop, as the tour plays it.</p><div class="clip" id="clip-all"></div><div class="btns"><button class="play" data-shot="all" data-key="all">Play the whole tour</button></div></section>${cards}</main>
<script>
const timers={};
document.querySelectorAll('textarea').forEach(t=>{ t.addEventListener('input',()=>{ const k=t.dataset.key, n=+t.dataset.n||0, id=k+(n?'-'+n:''), st=document.getElementById('st-'+id); st.textContent='…'; clearTimeout(timers[id]);
 timers[id]=setTimeout(async()=>{ const r=await fetch('/save',{method:'POST',headers:{'content-type':'application/json'},body:JSON.stringify({key:k,n,text:t.value})}); st.textContent=r.ok?'saved':'NOT SAVED'; },500); }); });
// one clip at a time: the viewer is the whole 3D hall, so a second one would halve the frame rate
document.querySelectorAll('button.play').forEach(b=>{ b.addEventListener('click',()=>{ const box=document.getElementById('clip-'+b.dataset.key); const open=box.querySelector('iframe');
 document.querySelectorAll('.clip').forEach(c=>{ c.innerHTML=''; }); document.querySelectorAll('button.play').forEach(x=>x.textContent='Play clip');
 if(open)return; // the same shot twice, side by side: the computer's frame and a phone's (Lloyd)
 const src=b.dataset.shot==='all'?'/viewer.html?embed=1&tour=1':'/viewer.html?embed=1&shot='+b.dataset.shot; box.innerHTML='<iframe class="pc" src="'+src+'" allow="autoplay"></iframe><iframe class="ph" src="'+src+'" allow="autoplay"></iframe>'; b.textContent='Stop clip'; }); });
// Generate waits for a pending save, sends, then reloads the page so the round files itself and
// a fresh box appears
document.querySelectorAll('button.gen').forEach(b=>{ b.addEventListener('click',async()=>{ const k=b.dataset.key; const t=document.querySelector('textarea[data-key="'+k+'"]'); if(!t.value.trim()){ t.focus(); return; }
 b.disabled=true; b.textContent='Sending…'; clearTimeout(timers[k]); await fetch('/save',{method:'POST',headers:{'content-type':'application/json'},body:JSON.stringify({key:k,text:t.value})});
 const r=await fetch('/generate',{method:'POST',headers:{'content-type':'application/json'},body:JSON.stringify({key:k})}); if(!r.ok){ b.disabled=false; b.textContent='Not sent: same as an earlier round'; setTimeout(()=>{ b.textContent='Generate'; },4000); return; } location.reload(); }); });
document.querySelectorAll('.line input').forEach(t=>{ t.addEventListener('input',()=>{ const k=t.dataset.key, idx=+t.dataset.idx, id='tx-'+k+'-'+idx, st=document.getElementById(id); st.textContent='…'; clearTimeout(timers[id]);
 timers[id]=setTimeout(async()=>{ const r=await fetch('/title',{method:'POST',headers:{'content-type':'application/json'},body:JSON.stringify({key:k,idx,text:t.value})}); st.textContent=r.ok?'saved':'NOT SAVED'; },500); }); });
document.getElementById('pub').addEventListener('click',async()=>{ const b=document.getElementById('pub'); b.disabled=true; b.textContent='Publishing…'; const r=await fetch('/publish',{method:'POST'}); b.textContent=r.ok?'Published (live in a minute)':'Publish FAILED'; setTimeout(()=>{ b.disabled=false; b.textContent='Publish text'; },6000); });
async function status(){ const list=await (await fetch('/requests')).json(); document.querySelectorAll('.req').forEach(c=>{ c.className='req'; c.textContent=''; });
 for(const r of list){ if(!r.key)continue; const c=document.getElementById('rq-'+r.key); if(!c)continue; c.className='req '+r.status; c.textContent='V'+r.round+' '+r.status; const b=document.querySelector('button.gen[data-key="'+r.key+'"]'); if(b){ b.disabled=r.status!=='done'; b.textContent=r.status==='done'?'Generate':'Sent…'; } } }
status(); setInterval(status,5000);
</script>`;
}
http.createServer((req,res)=>{
 const url=req.url.split('?')[0];
 if(req.method==='POST'&&(url==='/save'||url==='/generate'||url==='/title')){ let b=''; req.on('data',d=>b+=d); req.on('end',()=>{ try{ const j=JSON.parse(b); res.writeHead((url==='/save'?save(j.key,j.text,j.n):url==='/title'?saveTitle(j.key,j.idx,j.text):generate(j.key))?200:400); }catch(e){ res.writeHead(400); } res.end(); }); return; }
 if(req.method==='POST'&&url==='/publish'){ res.writeHead(publishTitles()?200:500); res.end(); return; }
 if(url==='/'){ res.writeHead(200,{'content-type':'text/html; charset=utf-8'}); res.end(page()); return; }
 if(url==='/requests'){ res.writeHead(200,{'content-type':'application/json'}); res.end(JSON.stringify(readReq())); return; }
 // the viewer as committed, never the working copy (it may carry another session's unfinished hunks)
 if(url==='/viewer.html'){ try{ const html=execSync('git show HEAD:index.html',{cwd:ROOT,maxBuffer:64e6}); res.writeHead(200,{'content-type':'text/html; charset=utf-8'}); res.end(html); }catch(e){ res.writeHead(500); res.end(String(e)); } return; }
 const f=path.join(ROOT,decodeURIComponent(url)); if(f.startsWith(ROOT)&&fs.existsSync(f)&&fs.statSync(f).isFile()){ res.writeHead(200,{'content-type':MIME[path.extname(f)]||'application/octet-stream'}); fs.createReadStream(f).pipe(res); return; }
 res.writeHead(404); res.end();
}).listen(port,'0.0.0.0',()=>{ const lan=Object.values(os.networkInterfaces()).flat().find(a=>a.family==='IPv4'&&!a.internal); console.log(`storyboard notes: http://localhost:${port}/  ${lan?'phone: http://'+lan.address+':'+port+'/':''}`); });
