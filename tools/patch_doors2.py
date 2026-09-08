# 2026-09-09 (Lloyd): the GANDEL HALL sign over the north door goes ("that should never have been there"), and the
# flat closed-door leaves become panelled doors: a canvas per doorway, one leaf per metre, stiles, rails, two recessed
# panels and a push plate, tinted by the clock like the rest of the wall tones. Idempotent string patches.
p = 'index.html'; s = open(p, encoding='utf-8').read(); n = 0
def rep(a, b):
    global s, n
    if b in s: return
    assert s.count(a) == 1, a[:70]; s = s.replace(a, b); n += 1
rep(" sign:{text:'GANDEL HALL', u0:24.5, u1:27.1, h0:2.65, h1:3.0},\n", "")
i0 = s.find("  // the hall's name over the north doorway (F.sign"); i1 = s.find("  // (the Felton inscription")
if i0 > 0 and i1 > i0:
    s = s[:i0] + "  // (the GANDEL HALL sign drawn over the north door from 2026-09-08 is gone: Lloyd, 2026-09-09, \"that should never have been there\")\n" + s[i1:]; n += 1
rep(" const leafMat=cnm(0x1c1916,0x4a4038,'door-leaf');",
    " const doorTex=(k)=>{ const cv=document.createElement('canvas'); cv.width=256*k; cv.height=640; const g=cv.getContext('2d');\n"
    "  g.fillStyle='#8d8d8d'; g.fillRect(0,0,cv.width,cv.height);   /* grey: the material colour tints it */\n"
    "  for(let i=0;i<k;i++){ const x=i*256; g.fillStyle='#9a9a9a'; g.fillRect(x+6,6,244,628);\n"
    "   g.fillStyle='#6a6a6a'; g.fillRect(x,0,6,640); g.fillRect(x+250,0,6,640); g.fillRect(x,0,256,6); g.fillRect(x,634,256,6);   /* the frame and the meeting stiles */\n"
    "   const panel=(y,h)=>{ g.fillStyle='#5e5e5e'; g.fillRect(x+34,y,188,h); g.fillStyle='#b4b4b4'; g.fillRect(x+34,y,188,4); g.fillRect(x+34,y,4,h); g.fillStyle='#464646'; g.fillRect(x+34,y+h-4,188,4); g.fillRect(x+218,y,4,h); g.fillStyle='#8c8c8c'; g.fillRect(x+44,y+10,168,h-20); };\n"
    "   panel(40,300); panel(380,220); g.fillStyle='#c4c4c4'; g.fillRect(i%2?x+14:x+226,300,16,60); }   /* two recessed panels a leaf, a push plate by the meeting stile */\n"
    "  const tx=new THREE.CanvasTexture(cv); tx.colorSpace=THREE.SRGBColorSpace; tx.anisotropy=8; return tx; };\n"
    " const leafMat=(k)=>{ const m=cnm(0x4a423b,0x7c6c5e,'door-leaf'); m.map=doorTex(k); return m; };   /* closed door leaves (2026-09-09): dark painted timber, tones unmeasured (the walks saw these doors open); the grey canvas times the clock tint */")
rep("   if(D.closed){ const dL=d0+w.s*0.12; quad([[u0,dL,0],[u1,dL,0],[u1,dL,h],[u0,dL,h]],leafMat,'door-leaf');",
    "   if(D.closed){ const dL=d0+w.s*0.12, k=Math.max(1,Math.round((u1-u0)/1.0)); quad([[u0,dL,0],[u1,dL,0],[u1,dL,h],[u0,dL,h]],leafMat(k),'door-leaf',w.north);   /* a leaf a metre: north 6, south 2 */")
open(p, 'w', encoding='utf-8', newline='\n').write(s); print('patched', n)
