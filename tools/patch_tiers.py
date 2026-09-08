# index.html (2026-09-08, the balconies pass): the tiers re-read from brightness profiles up both end
# faces (tools/end_profile.py, tools/end_lines.py zoom crops) in six posed frames (w2_000252, w2_000257,
# w1_000028 west; w6_000184, w5_000240, w1_000356 east):
#  - the ground stone reads as stone up to h 5.4 (values 26-29, the stone's own 23-28), then a dark
#    band 5.4-6.7 (11-19) under the 6.33 floor: groundTop 4.2 -> 5.3, apron 4.4 -> 5.4.
#  - the top tier's lit interior shows from h 8.85-8.95 up (both ends), not from 9.41: the parapet is a
#    0.56 m upstand with glass over it (the 4k frame d4_000198, shot leaning on it, looks down THROUGH
#    glass), so ENDW.upstand 0.56, the glass rail to rails[1] 1.06.
#  - the head: the lit band ends 10.2 (east, w1_000356) / 10.65 (west, w2_000252); head 10.0 -> 10.3 (+-0.3).
p = 'index.html'
s = open(p, encoding='utf-8').read()
old = "floors:[6.33,8.34], slab:0.26, rails:[0.89,1.07], apron:4.4, groundTop:4.2, head:10.0,"
new = "floors:[6.33,8.34], slab:0.26, rails:[0.89,1.06], upstand:0.56, apron:5.4, groundTop:5.3, head:10.3,"
assert old in s; s = s.replace(old, new)
old = "  quad([[uF,0,fl[1]],[uF,D,fl[1]],[uF,D,fl[1]+W.rails[1]],[uF,0,fl[1]+W.rails[1]]],meshMat,'gallery-parapet');\n"
new = ("  // a 0.56 m solid upstand with glass over it: the lit interior shows from h 8.9 in every frame of both\n"
       "  // ends (end_profile.py) and the 4k frame d4_000198 looks down through the glass\n"
       "  quad([[uF,0,fl[1]],[uF,D,fl[1]],[uF,D,fl[1]+W.upstand],[uF,0,fl[1]+W.upstand]],meshMat,'gallery-parapet');\n"
       "  quad([[uF,0,fl[1]+W.upstand],[uF,D,fl[1]+W.upstand],[uF,D,fl[1]+W.rails[1]],[uF,0,fl[1]+W.rails[1]]],railMat,'gallery-rail');\n")
assert old in s; s = s.replace(old, new)
open(p, 'w', encoding='utf-8', newline='\n').write(s)
print('patched')
