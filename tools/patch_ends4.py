# index.html (2026-09-08, the east day frame w1_000356 beside the sim): the space under the tiers reads
# dark in both ends' frames by day (the galleries are unlit), only the head's foot carries a row of
# lights; the lower ceilings go from the pale 0x9a948a to a dim 0x5a554e and the head soffit keeps the
# pale, lit tone.
p = 'index.html'
s = open(p, encoding='utf-8').read()
old = " const ceilMat=new THREE.MeshLambertMaterial({color:0x9a948a, side:THREE.DoubleSide, name:'gallery-ceiling'});\n"
new = (" const ceilMat=new THREE.MeshLambertMaterial({color:0x5a554e, side:THREE.DoubleSide, name:'gallery-ceiling'});   /* unlit by day in the frames of both ends */\n"
       " const soffitMat=new THREE.MeshLambertMaterial({color:0x9a948a, side:THREE.DoubleSide, name:'gallery-soffit'});   /* the head's soffit, its foot lit */\n")
assert old in s; s = s.replace(old, new)
old = "    quad([[uF,0,yc],[uB,0,yc],[uB,D,yc],[uF,D,yc]],ceilMat,'gallery-ceiling');\n"
new = "    quad([[uF,0,yc],[uB,0,yc],[uB,D,yc],[uF,D,yc]],i+1<fl.length?ceilMat:soffitMat,i+1<fl.length?'gallery-ceiling':'gallery-soffit');\n"
assert old in s; s = s.replace(old, new)
open(p, 'w', encoding='utf-8', newline='\n').write(s)
print('patched')
