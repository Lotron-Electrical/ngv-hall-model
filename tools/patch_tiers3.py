# index.html (2026-09-08, the balconies pass, third step): the band between the lower tier's glass and the
# top tier's glass (the lower ceiling's underside, the top slab's fascia, the 0.56 upstand) reads about the
# stone in the day frames (22-37 against the stone's 27, w2_000252 d5) and rendered black (unlit Lambert):
# unlit mid-dark materials instead. Verified by tools/pose-pick.mjs hall:u,d,h picks on the w2_000252 pose.
p = 'index.html'
s = open(p, encoding='utf-8').read()
old = " const ceilMat=new THREE.MeshLambertMaterial({color:0x5a554e, side:THREE.DoubleSide, name:'gallery-ceiling'});   /* unlit by day in the frames of both ends */\n"
new = (" const ceilMat=new THREE.MeshBasicMaterial({color:0x3a3632, side:THREE.DoubleSide, name:'gallery-ceiling'});   /* the lower tier's ceiling underside: dim, about half the stone */\n"
       " const upstandMat=new THREE.MeshBasicMaterial({color:0x4a4540, side:THREE.DoubleSide, name:'gallery-parapet'});   /* the top slab's fascia and the 0.56 upstand: about the stone (end_profile.py) */\n")
assert old in s; s = s.replace(old, new)
old = "  quad([[uF,0,fl[1]-W.slab],[uF,D,fl[1]-W.slab],[uF,D,fl[1]],[uF,0,fl[1]]],darkMat,'gallery-fascia');\n"
new = "  quad([[uF,0,fl[1]-W.slab],[uF,D,fl[1]-W.slab],[uF,D,fl[1]],[uF,0,fl[1]]],upstandMat,'gallery-fascia');\n"
assert old in s; s = s.replace(old, new)
old = "  quad([[uF,0,fl[1]],[uF,D,fl[1]],[uF,D,fl[1]+W.upstand],[uF,0,fl[1]+W.upstand]],meshMat,'gallery-parapet');\n"
new = "  quad([[uF,0,fl[1]],[uF,D,fl[1]],[uF,D,fl[1]+W.upstand],[uF,0,fl[1]+W.upstand]],upstandMat,'gallery-parapet');\n"
assert old in s; s = s.replace(old, new)
open(p, 'w', encoding='utf-8', newline='\n').write(s)
print('patched')
