// A local notes tool for the tour storyboard (Lloyd, 2026-09-01): one page, every camera path
// with its three frames and a text box. Whatever is typed is saved straight into the Notes line
// of that path in tour-storyboard.md, so the markdown stays the single copy.
//   node tools/storyboard-notes.js [--port 8890]
const http=require('http'), fs=require('fs'), path=require('path'), os=require('os');
const ROOT=path.join(__dirname,'..'), MD=path.join(ROOT,'tour-storyboard.md');
const port=+(process.argv[process.argv.indexOf('--port')+1])||8890;

// the sections: everything from a "## " heading to the next one; the Notes text is what follows
// "**Notes:**" up to the "---" rule (or the end of the section)
function parse(){
 const md=fs.readFileSync(MD,'utf8'); const parts=md.split(/\n(?=## )/); const head=parts.shift();
 const secs=parts.map((s,i)=>{ const title=s.match(/^## (.*)/)[1]; const m=s.match(/\*\*Notes:\*\*([\s\S]*?)(?=\n---|$)/);
  const notes=m?m[1].trim():''; const imgs=[...s.matchAll(/!\[\]\(([^)]+)\)/g)].map(x=>x[1]);
  const body=s.replace(/^## .*\n/,'').split('| start |')[0].trim();
  return {i,title,notes,imgs,body}; });
 return {head,parts,secs};
}
function save(i,text){
 const {head,parts}=parse(); const s=parts[i]; const t=text.replace(/\r/g,'').trim();
 const re=/\*\*Notes:\*\*([\s\S]*?)(?=\n---|$)/; if(!re.test(s))return false;
 parts[i]=s.replace(re,'**Notes:**'+(t?' '+t:'')+'\n');
 fs.writeFileSync(MD,[head,...parts].join('\n')); return true;
}
function page(){
 const {secs}=parse();
 const esc=s=>s.replace(/[&<>]/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;'}[c]));
 const cards=secs.map(s=>`<section id="s${s.i}"><h2>${esc(s.title)}</h2><p>${esc(s.body).replace(/`([^`]+)`/g,'<code>$1</code>').replace(/\n+/g,'<br>')}</p>
  ${s.imgs.length?`<div class="row">${s.imgs.map(u=>`<img src="/${u}" loading="lazy">`).join('')}</div>`:''}
  <label>Notes <span class="st" id="st${s.i}"></span></label><textarea data-i="${s.i}" placeholder="Type your notes for this shot">${esc(s.notes)}</textarea></section>`).join('');
 return `<!doctype html><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>Tour storyboard notes</title>
<style>body{margin:0;background:#111;color:#eee;font:15px/1.5 system-ui,sans-serif}main{max-width:1100px;margin:0 auto;padding:16px}
h1{font-size:20px;margin:8px 0 4px}h2{font-size:17px;margin:0 0 6px}section{background:#1b1b1b;border:1px solid #333;border-radius:8px;padding:14px;margin:14px 0}
p{margin:0 0 10px;color:#bbb}code{color:#9cf}.row{display:flex;gap:6px;margin-bottom:10px}.row img{width:calc((100% - 12px)/3);border-radius:4px;background:#000}
label{display:block;font-weight:600;margin-bottom:4px}textarea{width:100%;min-height:90px;box-sizing:border-box;background:#0d0d0d;color:#fff;border:1px solid #444;border-radius:6px;padding:10px;font:inherit;resize:vertical}
textarea:focus{outline:none;border-color:#7af}.st{font-weight:400;color:#8c8;font-size:13px}.top{color:#999;font-size:13px}
@media(max-width:700px){.row{flex-wrap:wrap}.row img{width:100%}}</style>
<main><h1>Gandel Hall tour: camera storyboard</h1><div class="top">Saves as you type into tour-storyboard.md. Tell Claude when you are done.</div>${cards}</main>
<script>
const timers={};
document.querySelectorAll('textarea').forEach(t=>{ t.addEventListener('input',()=>{ const i=t.dataset.i, st=document.getElementById('st'+i); st.textContent='…'; clearTimeout(timers[i]);
 timers[i]=setTimeout(async()=>{ const r=await fetch('/save',{method:'POST',headers:{'content-type':'application/json'},body:JSON.stringify({i:+i,text:t.value})}); st.textContent=r.ok?'saved':'NOT SAVED'; },500); }); });
</script>`;
}
http.createServer((req,res)=>{
 if(req.method==='POST'&&req.url==='/save'){ let b=''; req.on('data',d=>b+=d); req.on('end',()=>{ try{ const {i,text}=JSON.parse(b); res.writeHead(save(i,text)?200:400); }catch(e){ res.writeHead(400); } res.end(); }); return; }
 if(req.url==='/'){ res.writeHead(200,{'content-type':'text/html; charset=utf-8'}); res.end(page()); return; }
 const f=path.join(ROOT,decodeURIComponent(req.url.split('?')[0])); if(f.startsWith(ROOT)&&fs.existsSync(f)&&fs.statSync(f).isFile()){ res.writeHead(200,{'content-type':f.endsWith('.jpg')?'image/jpeg':'application/octet-stream'}); fs.createReadStream(f).pipe(res); return; }
 res.writeHead(404); res.end();
}).listen(port,'0.0.0.0',()=>{ const lan=Object.values(os.networkInterfaces()).flat().find(a=>a.family==='IPv4'&&!a.internal); console.log(`storyboard notes: http://localhost:${port}/  ${lan?'phone: http://'+lan.address+':'+port+'/':''}`); });
