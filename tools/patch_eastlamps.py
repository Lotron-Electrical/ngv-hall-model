# index.html (2026-09-09): the east top gallery's back wall as the two floor frames w1_000404 and w1_000356 agree on
# it: white fittings on d 12.28 (h 10.86 / 10.34) and d 13.25 (10.62 / 10.39) beside the one already built on 7.9,
# and a green exit sign on d 13.43-13.57, h 10.68-10.70 (the south end, like the west's). A fourth blob near the
# north end (d 0.64 in one frame, 4.49 in the other) does not agree between the frames and is not built.
p = 'index.html'; s = open(p, encoding='utf-8').read()
old = "wallLamps:{east:[[7.9,10.5]], west:[[7.0,11.4]]},"
new = "wallLamps:{east:[[7.9,10.5],[12.28,10.6],[13.25,10.5]], west:[[7.0,11.4]]}, topExit:{east:[13.5,10.69]},"
assert old in s; s = s.replace(old, new, 1)
old = "  { const E=(W.lowExit||{})[s<0?'west':'east']; if(E){ const uL=uB-s*0.02, [ed,eh]=E;\n"
new = ("  // the top gallery's exit sign on the back wall (east: w1_000404 and w1_000356 agree on d 13.5, h 10.69; the\n"
       "  // west's sits over its doorway, built with it)\n"
       "  { const E=(W.topExit||{})[s<0?'west':'east']; if(E){ const uL=uB-s*0.02, [ed,eh]=E;\n"
       "   quad([[uL,ed-0.175,eh-0.1],[uL,ed+0.175,eh-0.1],[uL,ed+0.175,eh+0.1],[uL,ed-0.175,eh+0.1]],exitLitMat,'exit-sign'); } }\n" + old)
assert old in s; s = s.replace(old, new, 1)
open(p, 'w', encoding='utf-8', newline='\n').write(s); print('patched')
