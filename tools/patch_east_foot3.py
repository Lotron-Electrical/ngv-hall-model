"""East foot, third pass (2026-09-10, after patch_east_foot2.py). The second pass fixed plane h 2.0/2.2/3.2 and
overshot three neighbours by a hair: plane 0.6 read 0.713 against 0.831 (bar 0.104), 2.6 0.344 against 0.514
(bar 0.169), 2.8 0.178 against 0.300 (bar 0.100). Planes map to the face about 0.65 m higher. So: the lit
lobby front's top comes down 3.35 to 3.2 so plane 2.6 (face 3.25 to 3.5) reads stone under shade, not the
lit front; a shallow dip in the shade at face 1.25 to 2.05 (texel 242, x0.91) for the 0.69 to 0.75 the
photograph reads at plane 0.6 to 1.4; and the shade between face 3.3 and 4.5 is reshaped band by band,
each texel scaled by (target/render)^0.5476 from its current value (3.45 to 3.75 at 146 for plane 2.8's
0.178, a rise to 180 at 4.0 to 4.15 for plane 3.2's 0.356 and 3.4's 0.322)."""
import sys
P = 'index.html'
s = open(P, encoding='utf-8').read()
pairs = [
  ("groundLit:{east:{top:3.35, day:0x777467}", "groundLit:{east:{top:3.2, day:0x777467}"),
  ("east:[[1.40,255],[2.63,255],[3.19,200],[3.74,162],[4.11,140],[4.48,140],[4.85,155],[5.30,110]]",
   "east:[[0.90,255],[1.25,242],[2.05,242],[2.63,255],[3.19,200],[3.30,196],[3.45,146],[3.75,146],[3.92,165],[4.00,180],[4.15,180],[4.30,163],[4.48,158],[4.85,155],[5.30,110]]"),
]
for a, b in pairs:
    n = s.count(a)
    if n != 1:
        print('EXPECTED 1, FOUND %d: %s' % (n, a[:60])); sys.exit(1)
    s = s.replace(a, b)
open(P, 'w', encoding='utf-8', newline='\n').write(s)
print('patched', len(pairs))
