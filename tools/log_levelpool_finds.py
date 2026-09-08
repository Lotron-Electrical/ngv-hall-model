# 2026-09-09: the balcony levels pooled across six captures, and what that confirms and refuses.
PLAN = 'E:/sitecapture-captures/ngv-site/agent-ref-walls/PLAN-20260908-walls.md'
entry = """- 2026-09-09, THE BALCONIES POOLED. tools/end_levels.py now writes its per-capture medians (LEVEL_JSON)
  and new tools/level_pool.py pools them, the same test tools/wall_pool.py applies to the wall's jambs and
  for the same reason: today's upstand change was made on three readings that each looked tight inside
  their own capture, and the jambs had just shown that inner tightness is not accuracy.
  COVERAGE, which is itself new. The west end is seen by five captures (day walk 25 frames, night 4, day4k
  25, b3 25, b6g 6) and the east by three (day walk 25, night 25, b1 25). b3 sees the west end well and is
  the FIRST capture in the archive to resolve the west lower tier at all.
  POOLED RESIDUALS against the model as it now stands:
    top parapet top 9.02   west +0.000 (3 captures, range 0.181)   east +0.073 (3, range 0.129)
    head 11.10             west -0.059 (4, range 0.163)            east -0.024 (3, range 0.188)
    end-wall top 13.50     west -0.009 (5, range 0.134)            east -0.017 (3, range 0.360)
  SO THE UPSTAND CHANGE IS CONFIRMED at the west end: the pooled residual is exactly zero where it was
  +0.12 before the change. At the east it still reads +0.073, and there the two floor captures agree
  closely (+0.070 night, +0.073 walk) while b1 is the outlier at +0.199, looking at that end obliquely
  from inside a north opening. 0.073 is inside the method's own capture-to-capture spread, so it is not
  acted on; a per-end upstand would be fitting one capture.
  THE LOWER TIER STAYS AS DRAWN, and now for a stated reason rather than for want of data. It is resolved
  by exactly two readings in the whole archive and they contradict each other: b3 puts the west lower
  parapet +0.024 against its drawn 6.85, and the night capture put the east one -0.139. The single-capture
  -0.139 recorded earlier today is therefore NOT generalisable and lowUpstand 0.52 is left alone.
  Both ends are now at the resolution limit of the imagery, the same place the north wall's openings
  reached. The comment above ENDW in index.html carries all of it.
"""
s = open(PLAN, encoding='utf-8').read()
if 'THE BALCONIES POOLED' not in s:
    open(PLAN, 'a', encoding='utf-8', newline='\n').write(entry)
print('logged')
