# index.html (2026-09-08, the balconies pass, second step): the tiers' tones from the brightness
# profiles up the end faces, real against sim on the same pose (tools/end_profile.py class:frame:PAIR):
#  - the top gallery reads THREE times the stone by day at both ends (w2_000252 150-180 against 50;
#    w1_000356 119 against 25), with downlights in its soffit; the sim had it black (unlit Lambert
#    interior behind a dark upstand). Its back wall, soffit and floor become unlit warm materials and
#    five downlights sit in the soffit.
#  - the recess under the 6.33 floor reads 0.55 of the stone (11-19 against 27): an unlit near-black apron.
#  - the lower tier's interior reads about the stone (22-37 against 27): an unlit mid grey back.
p = 'index.html'
s = open(p, encoding='utf-8').read()
old = " const backMat=new THREE.MeshLambertMaterial({color:0x7d776e, side:THREE.DoubleSide, name:'gallery-back'});\n"
new = (old +
       " // the tiers' tones (end_profile.py, real against sim on the same pose, 2026-09-08): the top gallery is lit by\n"
       " // day, three times the stone, with downlights; the recess under the lower floor is near black; the lower\n"
       " // tier's interior about the stone. Unlit materials, so the day frames' ratios hold whatever the house does.\n"
       " const topBackMat=new THREE.MeshBasicMaterial({color:0x8a7660, side:THREE.DoubleSide, name:'gallery-back-lit'});\n"
       " const topSoffitMat=new THREE.MeshBasicMaterial({color:0x9c8a70, side:THREE.DoubleSide, name:'gallery-soffit'});\n"
       " const lowBackMat=new THREE.MeshBasicMaterial({color:0x4e4841, side:THREE.DoubleSide, name:'gallery-back-low'});\n"
       " const apronMat=new THREE.MeshBasicMaterial({color:0x221f1c, side:THREE.DoubleSide, name:'gallery-apron'});\n"
       " const lampMat=new THREE.MeshBasicMaterial({color:0xfff4e0, side:THREE.DoubleSide, name:'gallery-downlight'});\n")
assert old in s; s = s.replace(old, new)
old = "  quad([[uF,0,W.apron],[uF,D,W.apron],[uF,D,fl[0]],[uF,0,fl[0]]],meshMat,'gallery-apron');\n"
new = "  quad([[uF,0,W.apron],[uF,D,W.apron],[uF,D,fl[0]],[uF,0,fl[0]]],apronMat,'gallery-apron');\n"
assert old in s; s = s.replace(old, new)
old = "  quad([[uB,0,fl[0]],[uB,D,fl[0]],[uB,D,fl[1]-W.slab],[uB,0,fl[1]-W.slab]],backMat,'gallery-back');\n"
new = "  quad([[uB,0,fl[0]],[uB,D,fl[0]],[uB,D,fl[1]-W.slab],[uB,0,fl[1]-W.slab]],lowBackMat,'gallery-back');\n"
assert old in s; s = s.replace(old, new)
old = ("  quad([[uF,0,W.head],[uB,0,W.head],[uB,D,W.head],[uF,D,W.head]],soffitMat,'gallery-soffit');\n"
       "  quad([[uB,0,fl[1]],[uB,D,fl[1]],[uB,D,W.head],[uB,0,W.head]],backMat,'gallery-back');\n")
new = ("  quad([[uF,0,W.head],[uB,0,W.head],[uB,D,W.head],[uF,D,W.head]],topSoffitMat,'gallery-soffit');\n"
       "  quad([[uB,0,fl[1]],[uB,D,fl[1]],[uB,D,W.head],[uB,0,W.head]],topBackMat,'gallery-back');\n"
       "  // the downlights in the top gallery's soffit (the day frames show a row of them, about 3 m apart)\n"
       "  for(let dl=1.9; dl<D-0.5; dl+=2.8){ const uL=uF+s*0.7, hL=W.head-0.02, r=0.14;\n"
       "   quad([[uL-s*r,dl-r,hL],[uL+s*r,dl-r,hL],[uL+s*r,dl+r,hL],[uL-s*r,dl+r,hL]],lampMat,'gallery-downlight'); }\n")
assert old in s; s = s.replace(old, new)
open(p, 'w', encoding='utf-8', newline='\n').write(s)
print('patched')
