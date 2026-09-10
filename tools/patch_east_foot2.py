"""East foot, second pass (2026-09-10). Audit after the tie-breaker: east plane h 2.0 read 0.861 in the
photograph against 0.685 in the render, 2.2 0.873 against 0.662, 3.2 0.356 against 0.238. Plane 2.0/2.2
lands on the face near 2.7/2.9 (the groundLit east zone) and plane 3.2 near 3.8 (groundShade east texel
[3.74,130]). Needed: x1.26 to 1.32 on the lit ground (render response out = 0.02274 * in^1.826, so in-scale
1.133 to 1.16: 0x696659 -> 0x777467), and x1.50 at 3.8 (texel ratio v ~ 255 * v^0.5476: 130 -> 162)."""
import re, sys
P = 'index.html'
s = open(P, encoding='utf-8').read()
pairs = [
  ("groundLit:{east:{top:3.35, day:0x696659}", "groundLit:{east:{top:3.35, day:0x777467}"),
  ("east:[[1.40,255],[2.63,255],[3.19,200],[3.74,130],[4.11,140],[4.48,140],[4.85,155],[5.30,110]]",
   "east:[[1.40,255],[2.63,255],[3.19,200],[3.74,162],[4.11,140],[4.48,140],[4.85,155],[5.30,110]]"),
]
for a, b in pairs:
    n = s.count(a)
    if n != 1:
        print('EXPECTED 1, FOUND %d: %s' % (n, a[:60])); sys.exit(1)
    s = s.replace(a, b)
open(P, 'w', encoding='utf-8', newline='\n').write(s)
print('patched', len(pairs))
