# 2026-09-09: the adversarial audit of today's three measurements, and what survived it.
PLAN = 'E:/sitecapture-captures/ngv-site/agent-ref-walls/PLAN-20260908-walls.md'
entry = """- 2026-09-09, THE AUDIT AND THE FACE ON TRIAL. A six-lens adversarial audit was run over the three
  measurements written into the live model today (the balcony upstand, the opening widths, the corridor
  ceiling revert). Nothing had to be reverted, but it found one real defect and one large claim, and both
  were tested rather than accepted.
  THE DEFECT, confirmed: both level instruments partly ECHO the model. Same frames, same face, same code,
  only the drawn level changed. Old code: drawn 8.90 returned the east parapet as h 9.057, drawn 9.02
  returned the same physical edge as h 9.093, a follow gain of 0.30; on the wall's jambs the gain reached
  0.70 (drawn width 1.256 measured 1.219, drawn 1.213 measured 1.189). That is worse than a bias, because
  it makes "the residual is near zero after the change" useless as a check.
  THE FIX, tools/edge_refine.py: a fixed point instead of a single look. Search, re-centre the window on
  what was found, search again, stop when it moves less than a pixel. Plus the interior test the old code
  lacked (a peak on the slice boundary means the edge is outside the window: refuse the sample rather than
  report the boundary as a small offset) and a two-window travel limit. tools/end_levels.py also loses its
  circular window: it was 0.45 x the gap to the nearest modelled level, so the level under test set its own
  search width; it is now a constant 0.25 m for every level and every draw.
  WHAT IS LEFT, and this is the honest part: the gain did NOT go to zero. tools/follow_test.py reports 0.45
  on the east parapet (drawn 8.90 settles on h 9.039 over 11 frames, drawn 9.02 on h 9.093 over 25). The
  two starts land in different basins and resolve different subsets, so the east parapet is known to about
  50 mm whichever way it is drawn. That agrees with the pooled figure (+0.073 inside a 0.129 spread) and is
  now measured rather than asserted. The claim in index.html that the offset was flat with distance and so
  could not be a face error came from the same unfixed run and has been withdrawn.
  THE LARGE CLAIM, refuted: the audit put the east end face 0.26-0.36 m west of the drawn u 48.056, which
  would move the whole east-end build further than anything else today. Its evidence was a face sweep on
  ONE capture and two levels. tools/face_sweep.py runs the same sweep over five faces (47.70 through 48.20)
  and pools the day walk, the night walk and b1. The levels do not agree on any face: the parapet is
  smallest on 47.70, the head on 47.90, the end-wall top on 48.20, and every pooled residual stays under
  0.13 m across the whole 0.5 m sweep. A real face error zeroes every level together on one u, which is
  exactly what does not happen. The face stays 48.056 and the test cannot place it better than about
  +-0.3 m. The east end is NOT moved.
"""
s = open(PLAN, encoding='utf-8').read()
if 'THE AUDIT AND THE FACE ON TRIAL' not in s:
    open(PLAN, 'a', encoding='utf-8', newline='\n').write(entry)
print('logged')
