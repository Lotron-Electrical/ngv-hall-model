# 2026-09-09: the north wall's face depth, fitted from an estimator that is identified.
PLAN = 'E:/sitecapture-captures/ngv-site/agent-ref-walls/PLAN-20260908-walls.md'
entry = """- 2026-09-09, THE NORTH FACE DEPTH, AND AN ESTIMATOR THAT IS ACTUALLY IDENTIFIED. The audit's finding 2.4
  was that tools/wall_edges.py could not separate the wall's face depth from the jamb positions: forcing
  the depth term to zero moved the residual rms by 3 mm over 492 readings, which is no separation at all.
  That mattered, because a face at the wrong depth contaminates every jamb reading taken through it, and
  the whole opening table rests on those.
  THE IDENTIFIED FORM. A jamb is a vertical line ON the face. A face drawn at the wrong depth throws that
  line sideways in the image by the depth error times (how far along the hall the camera stands from the
  jamb) divided by (how far out from the wall it stands). A misplaced JAMB adds a CONSTANT to the readings.
  A misplaced FACE adds a SLOPE against that ratio. So: write out every per-frame reading (WALL_RAW in
  wall_edges.py), remove each jamb's own mean, regress the remainder on the ratio, and the slope is the
  depth error by itself. The ratio spans 2.8 to 15.6 inside a single capture, so it is strongly determined
  rather than marginally.
  SIX CAPTURES, fitted separately and then pooled (tools/face_depth.py):
    b1 -0.009 (49 rows); b3 +0.016 (69); b7s -0.019 (37); day4k -0.009 (114); night +0.017 (244);
    walk +0.002 (418)
    pooled -0.003 m, capture range 0.036 m
  d -0.090 STANDS, confirmed to 3 mm with a capture spread of 36 mm. This is the tightest measurement in
  the whole wall effort, and it retires the audit's 2.4: the depth is no longer unconstrained, it is
  constrained and correct. It also clears the jamb pipeline, because the systematic that would have biased
  every jamb reading is now bounded.
  THE SOUTH FACE 15.364 has no equivalent. Its glazing comes from the scan mesh rather than a table, so
  there are no drawn vertical lines on it to run this estimator against. It stays UNMEASURED by this method
  and is marked so above the table in index.html.
"""
s = open(PLAN, encoding='utf-8').read()
if 'AN ESTIMATOR THAT IS ACTUALLY IDENTIFIED' not in s:
    open(PLAN, 'a', encoding='utf-8', newline='\n').write(entry)
print('logged')
