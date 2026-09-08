# 2026-09-09: logs the top galleries' back-wall light fittings (ENDW.wallLamps) in the walls plan and AGENTS.md.
PLAN = 'E:/sitecapture-captures/ngv-site/agent-ref-walls/PLAN-20260908-walls.md'
entry = """- 2026-09-09 a white light fitting on each top gallery's back wall. East: the floor frames w1_000404 (34 m) and
  w1_000356 (39 m) each hold one saturated white blob (255/255/255) inside the lit gallery; their rays meet the
  back wall (u 51.85) on d 7.82 / 7.97, h 10.72 / 10.24 (frame_pixel.py), and a fitting on the wall on d 7.9,
  h 10.5 projects within 10 px of both blobs while a soffit downlight (u 48.76, h 11.08) misses both by 40 px,
  so it is on the wall, not in the soffit. West: w2_000252 (28 m) holds one white blob whose ray meets the back
  wall on d 7.03, h 11.44 (one frame; w1_000028 is too dim to confirm). Built as ENDW.wallLamps, lit 0.15 m
  discs a hair off each back wall (patch_walllamps.py). Pair wlamp-w404-pair.jpg. The heights carry the
  register's +-0.25 spread between the two east frames.
"""
if 'a white light fitting on each top gallery' not in open(PLAN, encoding='utf-8').read():
    open(PLAN, 'a', encoding='utf-8', newline='\n').write(entry)
p = 'AGENTS.md'; s = open(p, encoding='utf-8').read()
old = "above the face) only bound the head from below (10.62). Stone from the head to the\n              top on the face plane"
new = ("above the face) only bound the head from below (10.62). Stone from the head to the\n              top on the face plane. A white light fitting on each back wall (`ENDW.wallLamps`:\n"
       "              east d 7.9, h 10.5 from w1_000404 and w1_000356, +-0.25; west d 7.0, h 11.4 from\n              w2_000252 alone; 2026-09-09)")
assert old in s, 'anchor'; s = s.replace(old, new, 1)
open(p, 'w', encoding='utf-8', newline='\n').write(s)
print('logged')
