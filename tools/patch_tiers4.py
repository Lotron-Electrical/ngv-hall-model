# index.html (2026-09-08, the balconies pass, fourth step): the galleries' unlit materials follow the
# daylight. By day the top gallery reads three times the stone (w2_000252, w1_000356); by night it reads
# dark, a shade over the stone (w6_000184: 50 against 30), and the east-w6 pose pair (22:00) showed the
# sim's gallery glowing. Night and day colours per material, lerped by lit.day beside the court's.
p = 'index.html'
s = open(p, encoding='utf-8').read()
old = "const photoMats=[], columnMats=[], glazingMats=[];\n"
new = "const photoMats=[], columnMats=[], glazingMats=[], endLitMats=[];   /* endLitMats: the galleries' unlit tones, night -> day by lit.day */\n"
assert old in s; s = s.replace(old, new)
old = " sceneDirty=true;\n"
i = s.index("for(const grp of [typeof court!=='undefined'?court:null, typeof eventGroup!=='undefined'?eventGroup:null])")
j = s.index(old, i)
s = s[:j] + " for(const m of endLitMats){ m.color.copy(m.userData.night).lerp(m.userData.day,lit.day); }\n" + s[j:]
old = (" const ceilMat=new THREE.MeshBasicMaterial({color:0x3a3632, side:THREE.DoubleSide, name:'gallery-ceiling'});   /* the lower tier's ceiling underside: dim, about half the stone */\n"
       " const upstandMat=new THREE.MeshBasicMaterial({color:0x4a4540, side:THREE.DoubleSide, name:'gallery-parapet'});   /* the top slab's fascia and the 0.56 upstand: about the stone (end_profile.py) */\n")
new = (" // the galleries' unlit tones, a night and a day colour each (end_profile.py, real against sim on the same pose)\n"
       " const dnm=(night,day,name)=>{ const m=new THREE.MeshBasicMaterial({color:day, side:THREE.DoubleSide, name}); m.userData.night=new THREE.Color(night); m.userData.day=new THREE.Color(day); endLitMats.push(m); return m; };\n"
       " const ceilMat=dnm(0x161412,0x3a3632,'gallery-ceiling');   /* the lower tier's ceiling underside: dim, about half the stone */\n"
       " const upstandMat=dnm(0x1e1c1a,0x4a4540,'gallery-parapet');   /* the top slab's fascia and the 0.56 upstand: about the stone */\n")
assert old in s; s = s.replace(old, new)
old = (" const topBackMat=new THREE.MeshBasicMaterial({color:0x8a7660, side:THREE.DoubleSide, name:'gallery-back-lit'});\n"
       " const topSoffitMat=new THREE.MeshBasicMaterial({color:0x9c8a70, side:THREE.DoubleSide, name:'gallery-soffit'});\n"
       " const lowBackMat=new THREE.MeshBasicMaterial({color:0x4e4841, side:THREE.DoubleSide, name:'gallery-back-low'});\n"
       " const apronMat=new THREE.MeshBasicMaterial({color:0x221f1c, side:THREE.DoubleSide, name:'gallery-apron'});\n"
       " const lampMat=new THREE.MeshBasicMaterial({color:0xfff4e0, side:THREE.DoubleSide, name:'gallery-downlight'});\n")
new = (" const topBackMat=dnm(0x2e2a26,0x8a7660,'gallery-back-lit');\n"
       " const topSoffitMat=dnm(0x332e29,0x9c8a70,'gallery-soffit');\n"
       " const lowBackMat=dnm(0x221f1c,0x4e4841,'gallery-back-low');\n"
       " const apronMat=dnm(0x0e0d0c,0x221f1c,'gallery-apron');\n"
       " const lampMat=dnm(0x6a6050,0xfff4e0,'gallery-downlight');\n")
assert old in s; s = s.replace(old, new)
open(p, 'w', encoding='utf-8', newline='\n').write(s)
print('patched')
