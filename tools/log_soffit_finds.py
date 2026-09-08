# 2026-09-09: logs the soffit downlights' removal and the underside's tone in the walls plan and AGENTS.md.
PLAN = 'E:/sitecapture-captures/ngv-site/agent-ref-walls/PLAN-20260908-walls.md'
entry = """- 2026-09-09 the soffit's row of downlights tested and removed. The five built positions (uF+0.7, d 1.9-13.1 by
  2.8, h 11.08) projected into four floor frames (w2_000252, w1_000028 west; w1_000404, w1_000356 east) and the
  brightness sampled in a 13 px window at each: max 156 of 255 and mostly under 100, no saturated dot anywhere,
  while the back-wall fittings in the same frames read 255. A lit downlight facing the floor would read like the
  fittings. The row came from an estimate ("about 3 m apart"), not a measurement, so it is gone; the two wall
  fittings stay. The underside itself reads 53/44/39 in w2_000252 against 142/120/98 for the lit back wall, so
  topSoffitMat's day colour goes from a lit 0x9c8a70 to 0x332c26 (0.37 of topBackMat). patch_soffit.py; pair
  soffit-w252-pair.jpg.
"""
if "the soffit's row of downlights tested and removed" not in open(PLAN, encoding='utf-8').read():
    open(PLAN, 'a', encoding='utf-8', newline='\n').write(entry)
p = 'AGENTS.md'; s = open(p, encoding='utf-8').read()
old = "    11.1      the head: a 2.1 m deep FRONT soffit with its downlights, the back wall running on"
new = "    11.1      the head: a 2.1 m deep FRONT soffit (its underside dark, 0.37x the lit back wall; the\n              row of downlights once built in it showed in no floor frame and is gone), the back wall running on"
assert old in s, 'anchor'; s = s.replace(old, new, 1)
open(p, 'w', encoding='utf-8', newline='\n').write(s)
print('logged')
