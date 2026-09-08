# 2026-09-09: logs the top gallery's head 11.1 with a 2.1 m front soffit (ENDW.head, soffitDepth) in the walls plan and AGENTS.md.
PLAN = 'E:/sitecapture-captures/ngv-site/agent-ref-walls/PLAN-20260908-walls.md'
entry = """- 2026-09-09 the top gallery's head resolved: 11.1 with a 2.1 m deep FRONT soffit, the back wall running on to
  the canopy behind it (ENDW.head 10.65 -> 11.1, soffitDepth 2.1, patch_head.py). Evidence, all by frame_pixel.py:
  (a) the west floor frame w2_000252 (u 30.7, h 1.87, 28 m off) across the gallery at d 7.8: a lit fascia edge
  whose ray meets the front plane on h 11.1, a dark underside for the next 31 px that the h 11.1 plane spans from
  u 4.20 to u 2.07 (2.1 m deep), then the lit back wall (brightness 39 -> 107-140) which a full-depth soffit would
  hide; (b) the 4K deck frame d4_000049 has the exit light on the back wall on h 11.07 and stone continuous above
  the doorway up to the canopy (brightness profile down the wall: no dark band between 10.65 and 13.4), which the
  old full-depth 10.65 soffit hid in the sim; (c) the east floor frame w1_000404 reads the lit back wall fading
  upward to h 12.9 on the back plane before the canopy's dark edge, again open above a front soffit. The deck
  frames d4_000031/169 that set 10.65 only bound the head from below (their frame-top ray), so 11.1 keeps them.
  The west doorway's pale panel keeps its own measured top 10.65 and the exit light sits on 10.97-11.17. Pairs
  head-d49-pair.jpg (the deck view now shows the wall to the canopy like the frame), head-w252-pair.jpg. The
  2026-09-09 ends-in-numbers audit was run on the 10.65 build; its step matches are unaffected (the head is not
  among the audited edges) but its note names 10.65.
"""
if 'the top gallery\'s head resolved' not in open(PLAN, encoding='utf-8').read():
    open(PLAN, 'a', encoding='utf-8', newline='\n').write(entry)
p = 'AGENTS.md'; s = open(p, encoding='utf-8').read()
old = """    10.65     the head (the west's measured head; the east's 10.2 is where the lit back ends, not
              the head: Lloyd's own 4K deck frames d4_000031 (u 48.34, h 10.05, pitched 18 up) and
              d4_000169 (h 10.29) stand 0.3 m behind the glass and see canopy, not soffit, above
              the face, so the head clears 10.62; pose pairs bal-d31, bal-d168), the soffit with
              its downlights, and stone from there to the top, on the face plane"""
new = """    11.1      the head: a 2.1 m deep FRONT soffit with its downlights, the back wall running on
              to the canopy behind it (`ENDW.head`, `soffitDepth`, 2026-09-09). The west floor
              frame w2_000252 has a lit fascia edge on 11.1, a dark underside spanning u 4.2-2.07
              on that plane, then the lit back wall beyond; the 4K deck frame d4_000049 has the
              exit light on the back wall on 11.07 and stone continuous above the doorway to the
              canopy; the east floor frame w1_000404 reads the lit back wall to 12.9 on the back
              plane. The deck frames d4_000031/169 (h 10.05/10.29, 0.3 m behind the glass, canopy
              above the face) only bound the head from below (10.62). Stone from the head to the
              top on the face plane"""
assert old in s, 'anchor'; s = s.replace(old, new, 1)
old = """  wall on h 11.07, above the 10.65 head, so the gallery ceiling may be higher behind a lower front
  fascia (or the register's tilt is 0.4 degrees off), unresolved. OPEN:"""
new = """  wall on h 11.07, under the 11.1 head (resolved the same day: a 2.1 m front soffit, the wall
  open to the canopy behind it). OPEN:"""
assert old in s, 'anchor2'; s = s.replace(old, new, 1)
open(p, 'w', encoding='utf-8', newline='\n').write(s)
print('logged')
