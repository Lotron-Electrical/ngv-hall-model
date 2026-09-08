# index.html (2026-09-08): the corridor behind the north wall's high openings, and the lit north
# doorway moved to where the day walk measured it.
#  - the lit doorway: w1_000028 (day walk, 2026-08-09) shows one lit doorway on the north wall; its
#    corners cast onto the wall plane through the posed camera land on u 26.1-28.3, h 0.55-2.3 (the
#    sill line is the carpet, the head 2.3-2.4). The 2014 photograph (great-hall-ngv-2014.jpg) shows
#    the same single lit door under the 4th-5th high openings. The page had it on u 18.85-21.15 from
#    a photograph that does not show it (7aad8857: the stage covers that stretch). Moved.
#  - the reveals: the certified cloud holds points 0.2-0.6 m behind the face inside the openings
#    with a tail to 1.8 m (tools/opening_cloud.py), and the 2014 photograph shows a deep stone-lined
#    reveal; openDepth 0.6 -> 0.9 (+-0.3).
#  - the corridor: the 1968 second-floor plan (BUIL005494) draws the CIRCULATION GALLERY along this
#    wall, a strip about 2 m wide (schematic, +-0.5); its floor is the second floor, h 8.34 (the
#    balconies); no frame or cloud point resolves its ceiling or its back wall (REPORT.md: unlit in
#    every capture), so it is built dark: back wall 2.0 m behind the reveals, floor 8.34, ceiling
#    11.8 (unmeasured), one continuous volume from u 3 to 47.
p = 'index.html'
s = open(p, encoding='utf-8').read()
old = " openY:[8.99,11.35], openDepth:0.6,\n"
new = " openY:[8.99,11.35], openDepth:0.9, corridor:{width:2.0, floor:8.34, ceil:11.8},   /* reveal 0.9 +-0.3 (cloud, 2014 photo); the corridor from the 1968 plan, unlit in every capture */\n"
assert old in s; s = s.replace(old, new)
old = "  {north:true, u0:18.85, u1:21.15, h:2.5, lit:true, depth:1.0, photoOnly:true}],\n"
new = "  {north:true, u0:26.10, u1:28.30, h:2.4, lit:true, depth:1.0, photoOnly:true}],   /* w1_000028 cast on the wall; the 2014 photograph's lit door */\n"
assert old in s; s = s.replace(old, new)
old = "   quad([[u0,d1,y0],[u1,d1,y0],[u1,d1,y1],[u0,d1,y1]],corridorMat,'opening-back'); }\n"
new = ("  }\n"
       "  // the circulation gallery behind the openings (the 1968 second-floor plan): a dark corridor W wide\n"
       "  // past the reveals, its floor the second floor, seen only through the openings\n"
       "  if(w.north){ const C=F.corridor, dR=w.d+w.s*F.openDepth, dB=dR+w.s*C.width, ua=3.0, ub=47.0;\n"
       "   quad([[ua,dB,C.floor],[ub,dB,C.floor],[ub,dB,C.ceil],[ua,dB,C.ceil]],corridorMat,'corridor-back');\n"
       "   quad([[ua,dR,C.floor],[ub,dR,C.floor],[ub,dB,C.floor],[ua,dB,C.floor]],corridorMat,'corridor-floor');\n"
       "   quad([[ua,dR,C.ceil],[ub,dR,C.ceil],[ub,dB,C.ceil],[ua,dB,C.ceil]],corridorMat,'corridor-ceiling');\n"
       "   // the wall's own back face BETWEEN the openings (each opening stays open into the corridor)\n"
       "   let up=ua; for(const [u0,u1] of F.openings){ if(u0>up)quad([[up,dR,C.floor],[u0,dR,C.floor],[u0,dR,C.ceil],[up,dR,C.ceil]],corridorMat,'corridor-near'); up=u1; }\n"
       "   if(ub>up)quad([[up,dR,C.floor],[ub,dR,C.floor],[ub,dR,C.ceil],[up,dR,C.ceil]],corridorMat,'corridor-near'); }\n")
assert old in s; s = s.replace(old, new)
# the near face must not block the openings themselves: cut it at each opening in the loop instead
old = "   quad([[u0,d0,y1],[u1,d0,y1],[u1,d1,y1],[u0,d1,y1]],stoneMat,'opening-head');\n  }\n"
new = "   quad([[u0,d0,y1],[u1,d0,y1],[u1,d1,y1],[u0,d1,y1]],stoneMat,'opening-head'); }\n"
assert old in s; s = s.replace(old, new)
open(p, 'w', encoding='utf-8', newline='\n').write(s)
print('patched')
