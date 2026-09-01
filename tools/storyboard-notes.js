// A local notes tool for the tour storyboard (Lloyd, 2026-09-01): one page, every camera path
// with its three frames, a text box, a Play button and a Generate button.
//  - Notes are saved as typed straight into the Notes line of that path in tour-storyboard.md,
//    so the markdown stays the single copy.
//  - Play opens the real viewer (HEAD's index.html, served as /viewer.html) on that one shot,
//    looping, so the camera path can be watched as it is.
//  - Generate queues the shot's notes for Claude in storyboard/requests.json; the page shows the
//    request's status (queued, working, done) as Claude updates it.
//   node tools/storyboard-notes.js [--port 8890]
const http=require('http'), fs=require('fs'), path=require('path'), os=require('os'), {execSync}=require('child_process');
const ROOT=path.join(__dirname,'..'), MD=path.join(ROOT,'tour-storyboard.md'), REQ=path.join(ROOT,'storyboard','requests.json');
const port=+(process.argv[process.argv.indexOf('--port')+1])||8890;
const MIME={'.html':'text/html; charset=utf-8','.js':'text/javascript','.mjs':'text/javascript','.json':'application/json','.glb':'model/gltf-binary','.png':'image/png','.jpg':'image/jpeg','.bin':'application/octet-stream','.css':'text/css','.wasm':'application/wasm'};

// the sections: everything from a "## " heading to the next one; the Notes text is what follows
// "**Notes:**" up to the "---" rule (or the end of the section)
function parse(){
 const md=fs.readFileSync(MD,'utf8'); const parts=md.split(/\n(?=## )/); const head=parts.shift();
 const secs=parts.map((s,i)=>{ const title=s.match(/^## (.*)/)[1]; const m=s.match(/\*\*Notes:\*\*([\s\S]*?)(?=\n---|$)/);
  const notes=m?m[1].trim():''; const imgs=[...s.matchAll(/!\[\]\(([^)]+)\)/g)].map(x=>x[1]);
  const body=s.replace(/^## .*\n/,'').split('| start |')[0].trim(); const shot=(title.match(/^(\d+)\./)||[])[1];
  return {i,title,notes,imgs,body,shot:shot?+shot:null}; });
 return {head,parts,secs};
}
function save(i,text){
 const {head,parts}=parse(); const s=parts[i]; const t=text.replace(/\r/g,'').trim();
 const re=/\*\*Notes:\*\*([\s\S]*?)(?=\n---|$)/; if(!re.test(s))return false;
 parts[i]=s.replace(re,'**Notes:**'+(t?' '+t:'')+'\n');
 fs.writeFileSync(MD,[head,...parts].join('\n')); return true;
}
const readReq=()=>{ try{ return JSON.parse(fs.readFileSync(REQ,'utf8')); }catch(e){ return []; } };
// a request: the shot's title and its notes as they stand now; one live request per section
function generate(i){
 const {secs}=parse(); const s=secs[i]; if(!s)return false; const list=readReq().filter(r=>!(r.i===i&&r.status!=='done'));
 list.push({id:Date.now().toString(36),i,shot:s.shot,title:s.title,notes:s.notes,status:'queued',at:new Date().toISOString()});
 fs.writeFileSync(REQ,JSON.stringify(list,null,1)); return true;
}
function page(){
 const {secs}=parse();
 const esc=s=>s.replace(/[&<>]/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;'}[c]));
 const cards=secs.map(s=>`<section id="s${s.i}" data-i="${s.i}"><h2>${esc(s.title)} <span class="req" id="rq${s.i}"></span></h2><p>${esc(s.body).replace(/`([^`]+)`/g,'<code>$1</code>').replace(/\n+/g,'<br>')}</p>
  ${s.imgs.length?`<div class="row">${s.imgs.map(u=>`<img src="/${u}" loading="lazy">`).join('')}</div>`:''}
  ${s.shot?`<div class="clip" id="clip${s.i}"></div><div class="btns"><button class="play" data-shot="${s.shot}" data-i="${s.i}">Play clip</button><button class="gen" data-i="${s.i}">Generate</button></div>`:''}
  <label>Notes <span class="st" id="st${s.i}"></span></label><textarea data-i="${s.i}" placeholder="Type your notes for this shot">${esc(s.notes)}</textarea></section>`).join('');
 return `<!doctype html><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>Tour storyboard notes</title>
<style>body{margin:0;background:#111;color:#eee;font:15px/1.5 system-ui,sans-serif}main{max-width:1100px;margin:0 auto;padding:16px}
h1{font-size:20px;margin:8px 0 4px}h2{font-size:17px;margin:0 0 6px}section{background:#1b1b1b;border:1px solid #333;border-radius:8px;padding:14px;margin:14px 0}
p{margin:0 0 10px;color:#bbb}code{color:#9cf}.row{display:flex;gap:6px;margin-bottom:10px}.row img{width:calc((100% - 12px)/3);border-radius:4px;background:#000}
label{display:block;font-weight:600;margin-bottom:4px}textarea{width:100%;min-height:90px;box-sizing:border-box;background:#0d0d0d;color:#fff;border:1px solid #444;border-radius:6px;padding:10px;font:inherit;resize:vertical}
textarea:focus{outline:none;border-color:#7af}.st{font-weight:400;color:#8c8;font-size:13px}.top{color:#999;font-size:13px}
.btns{display:flex;gap:8px;margin:0 0 10px}button{background:#2a2a2a;color:#fff;border:1px solid #555;border-radius:6px;padding:8px 14px;font:inherit;cursor:pointer}button:hover{border-color:#7af}
button.gen{background:#173a17;border-color:#2e6b2e}button.gen:disabled{opacity:.5;cursor:default}
.clip{margin-bottom:10px;display:flex;gap:8px;align-items:flex-start}.clip iframe{border:0;border-radius:4px;background:#000;display:block}.clip .pc{flex:1;aspect-ratio:16/9;min-width:0}.clip .ph{width:26%;aspect-ratio:9/19}
@media(max-width:700px){.clip{flex-wrap:wrap}.clip .pc,.clip .ph{width:100%}}
.req{font-size:12px;font-weight:400;color:#111;background:#8c8;border-radius:10px;padding:1px 9px;margin-left:8px;vertical-align:middle;display:none}.req.queued{display:inline;background:#ec5}.req.working{display:inline;background:#8bf}.req.done{display:inline;background:#8c8}
@media(max-width:700px){.row{flex-wrap:wrap}.row img{width:100%}}</style>
<main><h1>Gandel Hall tour: camera storyboard</h1><div class="top">Notes save as you type into tour-storyboard.md. Play clip shows the shot on a loop in the real viewer. Generate hands the shot's notes to Claude and moves on; the chip shows where it is up to.</div>${cards}</main>
<script>
const timers={};
document.querySelectorAll('textarea').forEach(t=>{ t.addEventListener('input',()=>{ const i=t.dataset.i, st=document.getElementById('st'+i); st.textContent='…'; clearTimeout(timers[i]);
 timers[i]=setTimeout(async()=>{ const r=await fetch('/save',{method:'POST',headers:{'content-type':'application/json'},body:JSON.stringify({i:+i,text:t.value})}); st.textContent=r.ok?'saved':'NOT SAVED'; },500); }); });
// one clip at a time: the viewer is the whole 3D hall, so a second one would halve the frame rate
document.querySelectorAll('button.play').forEach(b=>{ b.addEventListener('click',()=>{ const box=document.getElementById('clip'+b.dataset.i); const open=box.querySelector('iframe');
 document.querySelectorAll('.clip').forEach(c=>{ c.innerHTML=''; }); document.querySelectorAll('button.play').forEach(x=>x.textContent='Play clip');
 if(open)return; // the same shot twice, side by side: the computer's frame and a phone's (Lloyd)
 const src='/viewer.html?embed=1&shot='+b.dataset.shot; box.innerHTML='<iframe class="pc" src="'+src+'" allow="autoplay"></iframe><iframe class="ph" src="'+src+'" allow="autoplay"></iframe>'; b.textContent='Stop clip'; }); });
document.querySelectorAll('button.gen').forEach(b=>{ b.addEventListener('click',async()=>{ b.disabled=true; b.textContent='Queued…'; const r=await fetch('/generate',{method:'POST',headers:{'content-type':'application/json'},body:JSON.stringify({i:+b.dataset.i})}); if(!r.ok){ b.disabled=false; b.textContent='Generate'; } status(); }); });
async function status(){ const list=await (await fetch('/requests')).json(); document.querySelectorAll('.req').forEach(c=>{ c.className='req'; c.textContent=''; });
 for(const r of list){ const c=document.getElementById('rq'+r.i); if(!c)continue; c.className='req '+r.status; c.textContent=r.status; const b=document.querySelector('button.gen[data-i="'+r.i+'"]'); if(b){ b.disabled=r.status!=='done'; b.textContent=r.status==='done'?'Generate again':'Queued…'; } } }
status(); setInterval(status,5000);
</script>`;
}
http.createServer((req,res)=>{
 const url=req.url.split('?')[0];
 if(req.method==='POST'&&(url==='/save'||url==='/generate')){ let b=''; req.on('data',d=>b+=d); req.on('end',()=>{ try{ const j=JSON.parse(b); res.writeHead((url==='/save'?save(j.i,j.text):generate(j.i))?200:400); }catch(e){ res.writeHead(400); } res.end(); }); return; }
 if(url==='/'){ res.writeHead(200,{'content-type':'text/html; charset=utf-8'}); res.end(page()); return; }
 if(url==='/requests'){ res.writeHead(200,{'content-type':'application/json'}); res.end(JSON.stringify(readReq())); return; }
 // the viewer as committed, never the working copy (it may carry another session's unfinished hunks)
 if(url==='/viewer.html'){ try{ const html=execSync('git show HEAD:index.html',{cwd:ROOT,maxBuffer:64e6}); res.writeHead(200,{'content-type':'text/html; charset=utf-8'}); res.end(html); }catch(e){ res.writeHead(500); res.end(String(e)); } return; }
 const f=path.join(ROOT,decodeURIComponent(url)); if(f.startsWith(ROOT)&&fs.existsSync(f)&&fs.statSync(f).isFile()){ res.writeHead(200,{'content-type':MIME[path.extname(f)]||'application/octet-stream'}); fs.createReadStream(f).pipe(res); return; }
 res.writeHead(404); res.end();
}).listen(port,'0.0.0.0',()=>{ const lan=Object.values(os.networkInterfaces()).flat().find(a=>a.family==='IPv4'&&!a.internal); console.log(`storyboard notes: http://localhost:${port}/  ${lan?'phone: http://'+lan.address+':'+port+'/':''}`); });
