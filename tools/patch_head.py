# index.html (2026-09-09): the top gallery's head 11.1 with a 2.1 m deep front soffit, the back wall running on to
# the top behind it. Evidence: the west floor frame w2_000252 (28 m) has a lit fascia edge on h 11.1 (front plane),
# a dark underside for 2.1 m of depth (the h 11.1 plane meets its far end on u 2.07) and the lit back wall beyond;
# the 4K deck frame d4_000049 has the exit light on the back wall on h 11.07 with stone continuous above it to the
# canopy, which a full-depth 10.65 soffit would hide; the east floor frame w1_000404 reads the lit back wall to
# h 12.9 on the back plane, which only an open void behind a front soffit allows.
p = 'index.html'; s = open(p, encoding='utf-8').read()
old = "head:10.65, cut:4.0,"
new = "head:11.1, soffitDepth:2.1, cut:4.0,"
assert old in s; s = s.replace(old, new, 1)
old = "  quad([[uF,0,W.head],[uB,0,W.head],[uB,D,W.head],[uF,D,W.head]],topSoffitMat,'gallery-soffit');\n"
new = ("  // the soffit is a 2.1 m deep front canopy (w2_000252: its lit edge on 11.1, its underside for 2.1 m, then the lit\n"
       "  // back wall rising past it; d4_000049: the exit light on the back wall on 11.07 with stone above it to the canopy)\n"
       "  { const uS=uF+s*W.soffitDepth; quad([[uF,0,W.head],[uS,0,W.head],[uS,D,W.head],[uF,D,W.head]],topSoffitMat,'gallery-soffit'); }\n")
assert old in s; s = s.replace(old, new, 1)
old = "  quad([[uB,0,fl[1]],[uB,D,fl[1]],[uB,D,W.head],[uB,0,W.head]],topBackMat,'gallery-back');\n"
new = "  quad([[uB,0,fl[1]],[uB,D,fl[1]],[uB,D,top],[uB,0,top]],topBackMat,'gallery-back');   /* to the top: the void behind the front soffit is open to the canopy */\n"
assert old in s; s = s.replace(old, new, 1)
# the west panel keeps its own measured top (10.65), no longer the head
old = "   quad([[du,p0,fl[1]],[du,p1,fl[1]],[du,p1,W.head],[du,p0,W.head]],panelMat,'gallery-panel');\n"
new = "   quad([[du,p0,fl[1]],[du,p1,fl[1]],[du,p1,10.65],[du,p0,10.65]],panelMat,'gallery-panel');   /* its top on 10.65 (d4_000049), under the 11.1 head */\n"
assert old in s; s = s.replace(old, new, 1)
old = "[du-s*0.02,e0,W.head-0.32],[du-s*0.02,e1,W.head-0.32],[du-s*0.02,e1,W.head-0.12],[du-s*0.02,e0,W.head-0.12]"
new = "[du-s*0.02,e0,10.97],[du-s*0.02,e1,10.97],[du-s*0.02,e1,11.17],[du-s*0.02,e0,11.17]"
assert old in s; s = s.replace(old, new, 1)
open(p, 'w', encoding='utf-8', newline='\n').write(s); print('patched')
