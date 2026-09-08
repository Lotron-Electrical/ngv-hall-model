# index.html (2026-09-08, the east end read off the posed day frame w1_000356 and the night frame
# w5_000240 with tools/end_overlay2.py): above the top tier the stone is FLUSH with the gallery face
# and lit, from about h 10 up, with a row of lights along its foot; the tiers below are dark. Until
# now the stone above the top floor sat back on the plate end, leaving the top tier open to the
# ceiling. Now: a head at h 10.0 (ENDW.head; endwalls.json put the face-plane edge on h 9.96-10.04),
# the stone from the head to the top on the face plane, a soffit over the top tier on the head and a
# back wall behind it on the plate end. The west doorway is clipped to the head.
p = 'index.html'
s = open(p, encoding='utf-8').read()
old = "scanWest:-4.65, dSouth:15.364, westTopDoor:[13.4,14.2,10.4]};"
new = "scanWest:-4.65, dSouth:15.364, head:10.0, westTopDoor:[13.4,14.2,10.0]};"
assert old in s; s = s.replace(old, new)
old = "  quad([[uB,0,fl[2]],[uB,D,fl[2]],[uB,D,top],[uB,0,top]],stone,'end-wall');\n"
new = ("  // the stone over the galleries stands on the face plane from the head up (the posed frames of both\n"
       "  // ends: a lit stone band flush with the tiers, its foot on h 10, the tiers dark under it)\n"
       "  quad([[uF,0,W.head],[uF,D,W.head],[uF,D,top],[uF,0,top]],stone,'end-wall');\n")
assert old in s; s = s.replace(old, new)
old = "  for(let i=0;i<fl.length;i++){ const y=fl[i], yc=(i+1<fl.length?fl[i+1]:top+1)-W.slab;\n"
new = "  for(let i=0;i<fl.length;i++){ const y=fl[i], yc=i+1<fl.length?fl[i+1]-W.slab:W.head;\n"
assert old in s; s = s.replace(old, new)
old = "   if(i+1<fl.length){\n    // a lit ceiling under the next floor and a back wall on the plate end\n"
new = "   {\n    // a lit ceiling under the next floor (the head's soffit over the top tier) and a back wall on the plate end\n"
assert old in s; s = s.replace(old, new)
open(p, 'w', encoding='utf-8', newline='\n').write(s)
print('patched')
