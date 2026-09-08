# index.html (2026-09-08): the hall's name over the north doorway. The walk frame w1_000446 (u 22.0, d 12.7,
# h 2.0, looking north and up) reads "GANDEL HALL" in dark letters on the stone above the lit doorway; its
# pixels met with the north face (tools/wall_pixel.py) give u 24.5-27.1, h 2.65-3.0 (the letters 0.35 tall,
# the doorway head under them 2.1 in this frame against the 2.3 built). Drawn on a canvas, 20 mm proud.
p = 'index.html'
s = open(p, encoding='utf-8').read()
old = "  {north:true, u0:23.10, u1:29.40, h:2.3, lit:true, depth:1.0, photoOnly:true, back:0xc4cbd2, bright:[28.4,29.4]}],"
new = old + "\n sign:{text:'GANDEL HALL', u0:24.5, u1:27.1, h0:2.65, h1:3.0},   /* the name over the north doorway: walk w1_000446 met with the face, wall_pixel.py */"
assert old in s; s = s.replace(old, new, 1)
old = "  if(!w.north)continue;\n  // (the Felton inscription"
new = ("  if(!w.north)continue;\n"
       "  // the hall's name over the north doorway (F.sign, measured in w1_000446): dark letters on a clear canvas, 20 mm proud of the stone\n"
       "  if(F.sign){ const S=F.sign, cv=document.createElement('canvas'); cv.width=1024; cv.height=Math.round(1024*(S.h1-S.h0)/(S.u1-S.u0));\n"
       "   const g=cv.getContext('2d'); g.clearRect(0,0,cv.width,cv.height); g.fillStyle='#2b2723'; g.textBaseline='middle'; g.textAlign='center';\n"
       "   g.font='bold '+Math.round(cv.height*0.8)+'px Arial'; try{ g.letterSpacing='12px'; }catch(e){} g.fillText(S.text,cv.width/2,cv.height*0.54);\n"
       "   const tx=new THREE.CanvasTexture(cv); tx.colorSpace=THREE.SRGBColorSpace; tx.anisotropy=8;\n"
       "   const m=new THREE.MeshBasicMaterial({map:tx, transparent:true, side:THREE.DoubleSide, name:'hall-sign'});\n"
       "   const d=w.d-w.s*0.02; quad([[S.u0,d,S.h0],[S.u1,d,S.h0],[S.u1,d,S.h1],[S.u0,d,S.h1]],m,'hall-sign',true); }\n"
       "  // (the Felton inscription")
assert old in s; s = s.replace(old, new, 1)
open(p, 'w', encoding='utf-8', newline='\n').write(s)
print('patched')
