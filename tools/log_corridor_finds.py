# 2026-09-09: logs the corridor showing through the north wall's openings (install mode) in the plan and AGENTS.md.
PLAN = 'E:/sitecapture-captures/ngv-site/agent-ref-walls/PLAN-20260908-walls.md'
entry = """- 2026-09-09 the corridor behind the openings, install mode. The chained deck frame d4_000120 (east top
  gallery, looking west along the north wall) sees a lit back wall and a ceiling lamp through the nearest
  opening and dark stone reveals in the others; the sim showed every opening black. Cause, by pose-pick from
  that pose: the scan mesh closes each opening with a black cap about 1.2 m behind the face (never seen into),
  and the install "seal" box's north face sat between the cap and the built corridor-back. Fix: the viewer's
  photoMaterial and game/hallmat.js discard fragments 0.3-3.5 m behind the north face inside an opening's
  u and h span (tools/patch_open_caps.py), and the seal box moved north to d -4.3 so the corridor-back
  (d -2.9, day 0x4b4844, night 0x0c0b0a, lerped in applyDay) is in front of it. Pair shots/pose/corr-d120-pair.jpg:
  the sim's openings now show the corridor's reveal and back wall where the frame shows them; the corridor's
  ceiling and back-wall depth stay plan-only (unmeasured).
"""
open(PLAN, 'a', encoding='utf-8', newline='\n').write(entry)
p = 'AGENTS.md'; s = open(p, encoding='utf-8').read()
old = """  volume u 3-47, open only at the twelve openings ('corridor-back/floor/ceiling/near'). 6 grilles"""
new = """  volume u 3-47, open only at the twelve openings ('corridor-back/floor/ceiling/near'); the scan
  closes each opening with a black cap about 1.2 m in, so photoMaterial and game/hallmat.js
  discard scan fragments 0.3-3.5 m behind the face inside an opening (tools/patch_open_caps.py)
  and the install seal box sits behind the corridor-back (d -4.3), so the corridor shows through
  in both modes (checked on the chained deck frame d4_000120, 2026-09-09). 6 grilles"""
assert old in s; s = s.replace(old, new, 1)
open(p, 'w', encoding='utf-8', newline='\n').write(s)
print('logged')
