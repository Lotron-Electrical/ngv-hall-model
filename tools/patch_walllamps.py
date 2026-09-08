# index.html (2026-09-09): a white light fitting on each top gallery's back wall (ENDW.wallLamps), seen as a saturated
# white blob from the floor: east in w1_000404 and w1_000356 (their rays meet the back wall on d 7.82/7.97,
# h 10.72/10.24, a wall lamp there projecting within 10 px of both while a soffit downlight misses by 40),
# west in w2_000252 (d 7.03, h 11.44). Built as lit 0.15 m discs a hair off the back wall.
p = 'index.html'; s = open(p, encoding='utf-8').read()
old = "eastVent:[48.21,48.55,12.64,13.34],"
new = "eastVent:[48.21,48.55,12.64,13.34], wallLamps:{east:[[7.9,10.5]], west:[[7.0,11.4]]},"
assert old in s; s = s.replace(old, new, 1)
old = "  // the downlights in the top gallery's soffit (the day frames show a row of them, about 3 m apart)\n"
new = ("  // a white light fitting on the back wall (floor frames w1_000404, w1_000356 east; w2_000252 west: a saturated\n"
       "  // blob whose ray meets the back wall there, not the soffit), a lit 0.15 disc a hair off the wall\n"
       "  for(const [ld,lh] of ((W.wallLamps||{})[s<0?'west':'east']||[])){ const uL=uB-s*0.02, r=0.075;\n"
       "   quad([[uL,ld-r,lh-r],[uL,ld+r,lh-r],[uL,ld+r,lh+r],[uL,ld-r,lh+r]],lampMat,'gallery-wall-lamp'); }\n" + old)
assert old in s; s = s.replace(old, new, 1)
open(p, 'w', encoding='utf-8', newline='\n').write(s); print('patched')
