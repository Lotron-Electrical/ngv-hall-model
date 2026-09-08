# index.html (2026-09-09): the lower tier's interior as the 4K frame d4_000049 (east deck, 45 m off) reads the west
# one by day: near black (RGB 16-23 against 157 for the stone, 0.1-0.15 of it; lowBackMat day 0x4e4841 was 0.5),
# with four white fittings on its back wall (their rays meet u 0.4 on d 1.64/11.97/13.17/13.29, h 7.8-8.2; the
# two above the 8.08 ceiling are clamped to 8.0, the register's spread) and a green exit sign (d 13.52, h 7.32).
p = 'index.html'; s = open(p, encoding='utf-8').read()
old = "const lowBackMat=dnm(0x0a0908,0x4e4841,'gallery-back-low');"
new = "const lowBackMat=dnm(0x0a0908,0x16120f,'gallery-back-low');   /* 0.1-0.15x the stone by day: the lower tier is unlit in d4_000049 (2026-09-09) */"
assert old in s; s = s.replace(old, new, 1)
old = "wallLamps:{east:[[7.9,10.5]], west:[[7.0,11.4]]},"
new = old + " lowLamps:{west:[[1.64,7.81],[11.97,8.0],[13.17,8.0],[13.29,7.87]]}, lowExit:{west:[13.52,7.32]},"
assert old in s; s = s.replace(old, new, 1)
old = "  // a white light fitting on the back wall (floor frames w1_000404, w1_000356 east; w2_000252 west: a saturated\n"
new = ("  // the lower tier's back wall: white fittings and a green exit sign where d4_000049 has them (west; the east's\n"
       "  // lower tier is unseen by any posed frame from a height)\n"
       "  for(const [ld,lh] of ((W.lowLamps||{})[s<0?'west':'east']||[])){ const uL=uB-s*0.02, r=0.075;\n"
       "   quad([[uL,ld-r,lh-r],[uL,ld+r,lh-r],[uL,ld+r,lh+r],[uL,ld-r,lh+r]],lampMat,'gallery-wall-lamp'); }\n"
       "  { const E=(W.lowExit||{})[s<0?'west':'east']; if(E){ const uL=uB-s*0.02, [ed,eh]=E;\n"
       "   quad([[uL,ed-0.175,eh-0.1],[uL,ed+0.175,eh-0.1],[uL,ed+0.175,eh+0.1],[uL,ed-0.175,eh+0.1]],exitLitMat,'exit-sign'); } }\n" + old)
assert old in s; s = s.replace(old, new, 1)
open(p, 'w', encoding='utf-8', newline='\n').write(s); print('patched')
