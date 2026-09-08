# 2026-09-09, part 3: the ceiling pixel map as a real patch. Two exports, both in the shapes this page
# already uses: a plain CSV of one row per pane, and ELM 2026's 3D-stage import CSV so the canopy can be
# driven from the same console as the columns.
p = 'index.html'; s = open(p, encoding='utf-8').read(); n = 0
def rep(a, b):
    global s, n
    if b in s: return
    assert s.count(a) == 1, (a[:70], s.count(a))
    s = s.replace(a, b); n += 1

# ---- the controls, in the pixel mapping panel, under the strips' own exports
rep("""  <button type="button" id="pm_elm" class="sw">Download ELM CSV (one row per pixel)</button>
  </div>""",
"""  <button type="button" id="pm_elm" class="sw">Download ELM CSV (one row per pixel)</button>
  </div>
  <p class="note">The ceiling is its own fixture set: one RGBW pixel behind every pane of glass, addressed
   in the order the panes are traced. The two files below patch it the same way the columns are patched.</p>
  <div class="pmgrid">
   <label>Canopy first universe <input type="number" id="cx_u0" value="200" min="0"></label>
   <label>Panes per universe <input type="number" id="cx_ppu" value="128" min="1" max="128"></label>
   <label>&nbsp;<span class="note" id="cx_tot">counting panes</span></label>
   <button type="button" id="cx_csv" class="sw">Download canopy patch CSV (one row per pane)</button>
   <button type="button" id="cx_elm" class="sw">Download canopy ELM CSV (3D stage)</button>
  </div>""")

# ---- the exports themselves, beside the strips'
rep("""document.getElementById('pm_csv').onclick=()=>{const rows=pixelMap.rows||[];""",
"""// ---- THE CANOPY'S OWN PATCH (2026-09-09). One RGBW pixel per pane, addressed in trace order, which is
// the same order the shader's pane ids run in, so what a console drives and what this page draws cannot
// drift apart. 128 panes fill a universe exactly (4 channels each, 512 slots), which is why that is the
// default; a controller that wants 170 RGB pixels per universe is the wrong shape for RGBW and the field
// is there to say so. Positions are the pane centroids lifted onto the coffer surface, in millimetres,
// the same convention the strips' ELM file uses.
function cxPatch(){
 const ppu=Math.max(1,Math.min(128,+document.getElementById('cx_ppu').value||128));
 const u0=Math.max(0,+document.getElementById('cx_u0').value||0);
 PIX.ppu=ppu; PIX.uStart=u0;
 const nU=Math.ceil(PIX.n/ppu);
 const el=document.getElementById('cx_tot');
 if(el)el.textContent=PIX.n?`${PIX.n.toLocaleString()} panes -> ${(PIX.n*4).toLocaleString()} channels -> ${nU} universes (${u0} to ${u0+nU-1})`:'the canopy has not loaded yet';
 return {ppu,u0,nU};
}
function cxCsv(){
 const {ppu,u0}=cxPatch();
 const out=['pane,hall_u_m,hall_v_m,x_mm,y_mm,z_mm,area_m2,trace_r,trace_g,trace_b,universe,address_r,address_g,address_b,address_w'];
 for(let i=0;i<PIX.n;i++){ const q=PIX.panes[i], uni=u0+Math.floor(i/ppu), ch=1+(i%ppu)*4;
  out.push([i,q.u.toFixed(3),q.v.toFixed(3),(q.X*1000).toFixed(0),(q.Y*1000).toFixed(0),(q.Z*1000).toFixed(0),
            q.area.toFixed(4),q.r,q.g,q.b,uni,ch,ch+1,ch+2,ch+3].join(',')); }
 const a=document.createElement('a'); a.href=URL.createObjectURL(new Blob([out.join('\\n')],{type:'text/csv'}));
 a.download='ngv-canopy-pane-patch.csv'; a.click();
}
function cxElm(){
 const {ppu,u0}=cxPatch();
 const zup=document.getElementById('pm_up').value==='z', proto=document.getElementById('pm_proto').value;
 const out=['x,y,z,protocol,universe,address,type,bits,strip,order,name'];
 for(let i=0;i<PIX.n;i++){ const q=PIX.panes[i], uni=u0+Math.floor(i/ppu), ch=1+(i%ppu)*4;
  const X=(q.X*1000).toFixed(0), Y=(q.Y*1000).toFixed(0), Z=(q.Z*1000).toFixed(0);
  out.push([zup?X:X, zup?Z:Y, zup?Y:Z, proto, uni, ch, 'RGBW', 8, 'canopy', i, 'pane'+i].join(',')); }
 const a=document.createElement('a'); a.href=URL.createObjectURL(new Blob([out.join('\\n')],{type:'text/csv'}));
 a.download='ngv-canopy-elm.csv'; a.click();
}
for(const id of ['cx_u0','cx_ppu'])document.getElementById(id).addEventListener('input',cxPatch);
document.getElementById('cx_csv').onclick=cxCsv;
document.getElementById('cx_elm').onclick=cxElm;
document.getElementById('pm_csv').onclick=()=>{const rows=pixelMap.rows||[];""")

# ---- and the counter refreshes once the panes are in
rep("  const pv=document.getElementById('pixval'); if(pv)pv.textContent=PIX.n.toLocaleString()+' panes';",
    "  const pv=document.getElementById('pixval'); if(pv)pv.textContent=PIX.n.toLocaleString()+' panes';\n  if(typeof cxPatch==='function')cxPatch();")

open(p, 'w', encoding='utf-8', newline='\n').write(s); print('part 3 patched', n)
