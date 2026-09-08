p = 'index.html'; s = open(p, encoding='utf-8').read(); n = 0
def rep(a, b):
    global s, n
    if b in s: return
    assert s.count(a) == 1, a[:60]; s = s.replace(a, b); n += 1
rep("const ROAM_EYE={u:48.3,d:7.6,h:2.0};",
    "const ROAM_EYE={u:47.0,d:7.6,h:2.0};")
rep("  {north:false, u0:37.962, u1:39.662, h:2.906, lit:true, depth:1.0},",
    "  {north:false, u0:37.962, u1:39.662, h:2.906, closed:true, depth:1.0},")
rep("  {north:true, u0:23.10, u1:29.40, h:2.3, lit:true, depth:1.0, photoOnly:true, back:0xc4cbd2, bright:[28.4,29.4]}],",
    "  {north:true, u0:23.10, u1:29.40, h:2.3, closed:true, depth:1.0}],")
rep(" const darkBack=new THREE.MeshLambertMaterial({color:0x171512, side:THREE.DoubleSide, name:'door-back'});",
    " const darkBack=new THREE.MeshLambertMaterial({color:0x171512, side:THREE.DoubleSide, name:'door-back'});\n const leafMat=new THREE.MeshLambertMaterial({color:0x2e2a25, side:THREE.DoubleSide, name:'door-leaf'});")
rep("   const side=D.lit?lit:stoneMat, floor=D.lit?litFloor:darkBack, top=D.lit?lit:stoneMat;",
    "   if(D.closed){ const dL=d0+w.s*0.12; quad([[u0,dL,0],[u1,dL,0],[u1,dL,h],[u0,dL,h]],leafMat,'door-leaf');\n"
    "    quad([[u0,d0,0],[u0,dL,0],[u0,dL,h],[u0,d0,h]],stoneMat,'door-reveal'); quad([[u1,d0,0],[u1,dL,0],[u1,dL,h],[u1,d0,h]],stoneMat,'door-reveal'); quad([[u0,d0,h],[u1,d0,h],[u1,dL,h],[u0,dL,h]],stoneMat,'door-head'); continue; }\n"
    "   const side=D.lit?lit:stoneMat, floor=D.lit?litFloor:darkBack, top=D.lit?lit:stoneMat;")
open(p, 'w', encoding='utf-8', newline='\n').write(s); print('patched', n)
