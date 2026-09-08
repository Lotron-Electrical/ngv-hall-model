# AGENTS.md: the galleries' head, read off the posed frames of both ends (string patch, 2026-09-08).
p = 'AGENTS.md'
s = open(p, encoding='utf-8').read()
anchor = '- POSE-MATCHED PROOF (2026-09-08):'
new = '''- THE GALLERIES' HEAD (2026-09-08, tools/pose_frames_for.py found the sharpest posed frames that hold
  each end: night w5_000240 and day w1_000356 look at the EAST end from 36-38 m, the first frames of
  it from inside; tools/end_overlay2.py draws ENDW into any of them, upright). Both ends read the
  same: from about h 10 up the stone is lit and FLUSH with the gallery face, a row of lights along
  its foot, the three tiers dark under it. So ENDW.head 10.0 (endwalls.json had the face-plane edge
  on h 9.96-10.04): the stone over the galleries stands on the face plane from the head up, a lit
  soffit (gallery-soffit) closes the top tier on the head, a back wall sits behind it on the plate
  end, the west doorway is clipped to the head, and the lower tiers' ceilings are dim (0x5a554e):
  the frames show them unlit by day. The east is no longer a copy of the west by assumption: its
  tiers and head match the west's in its own frames (shots/pose/east-day-pair.jpg).
'''
assert anchor in s and "GALLERIES' HEAD" not in s
s = s.replace(anchor, new + anchor)
open(p, 'w', encoding='utf-8', newline='\n').write(s)
q = 'E:/sitecapture-captures/ngv-site/agent-ref-walls/PLAN-20260908-walls.md'
t = open(q, encoding='utf-8').read()
t += ('- 2026-09-08 16:40 east end seen from inside (w5_000240 night, w1_000356 day; pose_frames_for.py, end_overlay2.py,\n'
      '  pose_pair.py): stone flush on the face from h 10 up, tiers dark below. ENDW.head 10.0, soffit over the\n'
      '  top tier, lower ceilings dim, west doorway clipped. Tapestry frames (w2_000190, w2_000257, w1_000362)\n'
      '  rendered beside the sim: the four hang where the frames show them.\n')
open(q, 'w', encoding='utf-8', newline='\n').write(t)
print('ok')
