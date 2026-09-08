# 2026-09-09: appends the head finding (ENDW.head 10.3 -> 10.65) to the walls plan log and AGENTS.md (one-shot).
PLAN = 'E:/sitecapture-captures/ngv-site/agent-ref-walls/PLAN-20260908-walls.md'
entry = """- 2026-09-09 early: Lloyd: "in one of the videos I took I looked around the balcony". The 20260809_153237 4K clip
  (= day4k, 289 frames) swings along the balcony from 7 to 10 s and looks straight down from 14 to 17 s; the
  register refused those frames (its hall-geometry lift collapsed them to one bogus floor-height point), so only
  the west-looking 138 are posed. The posed deck frames still decide the head: d4_000031 (u 48.34, h 10.05,
  pitched 18 up) and d4_000169 (h 10.29) stand 0.3 m behind the glass and see CANOPY above the face where the sim
  showed the 10.3 soffit; the frame-top ray puts the head above 10.62. ENDW.head 10.3 -> 10.65 (the west's
  measured head; the east's 10.2 was the lit back's end). Pairs bal-d31, bal-d168 before/after. Audit rerun on
  the new build: east 90% within 0.30, west within 0.37. The balcony's own parapet: d4_000168's foot shows the
  glass top's bright cap right under the camera (glass over the upstand, as built); the rail height itself stays
  unmeasured.
"""
open(PLAN, 'a', encoding='utf-8', newline='\n').write(entry)
p = 'AGENTS.md'; s = open(p, encoding='utf-8').read()
old = """    10.3      the head (the lit band ends 10.2 east / 10.65 west, +-0.3), the lit soffit, and
              stone from there to the top, on the face plane"""
new = """    10.65     the head (the west's measured head; the east's 10.2 is where the lit back ends, not
              the head: Lloyd's own 4K deck frames d4_000031 (u 48.34, h 10.05, pitched 18 up) and
              d4_000169 (h 10.29) stand 0.3 m behind the glass and see canopy, not soffit, above
              the face, so the head clears 10.62; pose pairs bal-d31, bal-d168), the soffit with
              its downlights, and stone from there to the top, on the face plane"""
assert old in s; s = s.replace(old, new, 1)
old = """within 0.45 m: east 11 matched, mean 0.00 m, |median| 0.30, 90 %
within 0.45; west 11 matched, mean 0.00, |median| 0.20, 90 % within 0.35."""
new = """within 0.45 m (after the head went to 10.65): east 11 matched, mean +0.05 m, |median| 0.25, 90 %
within 0.30; west 9 matched, mean +0.09, |median| 0.20, 90 % within 0.37."""
assert old in s; s = s.replace(old, new, 1)
open(p, 'w', encoding='utf-8', newline='\n').write(s)
print('logged')
