# 2026-09-09: the north wall's jambs pooled across five captures, and the limit that pooling exposes.
PLAN = 'E:/sitecapture-captures/ngv-site/agent-ref-walls/PLAN-20260908-walls.md'
entry = """- 2026-09-09, THE LIMIT OF THE WALL MEASUREMENT, found by pooling. New tools/wall_pool.py, fed by
  tools/wall_edges.py writing its per-capture medians (WALL_JSON). Every jamb measured from five separate
  captures: day walk (114 frames), night (65), b1 (22), b3 (25), day4k (106).
  THE POINT: a single capture's quartiles are not an uncertainty. Consecutive frames of one walking pass
  share that pass's exposure, motion, pose solution and side of the hall, so they agree with each other
  far better than two passes agree with one another. Measured: the capture-to-capture median spread on a
  jamb is 0.162 m against an inner spread of 0.122 m, and the worst jamb spans 394 mm across captures
  while one of its captures reported quartiles 30 mm wide. ABOUT 0.15 m is what this method actually
  knows a jamb to.
  WHAT THAT SAYS ABOUT TODAY'S CORRECTION: it stands. Against the current table the pooled residual on
  all six moved jambs (openings 7, 8, 9) is within 21 mm of zero (-0.001, -0.015, -0.007, -0.021, +0.000,
  -0.019). Against the table as it was this morning the same pooled medians were -0.133, -0.183, -0.100,
  -0.151, -0.188, -0.214: negative on all six, over four captures. The move removed a real bias, and two
  captures that were not used to make it (b3 and day4k) are among the four that confirm it.
  WHAT IT SAYS ABOUT GOING FURTHER: stop. Twenty-one of the twenty-four jambs cannot be agreed across
  captures, and not one jamb is both agreed and out by more than 50 mm. Two west jambs (openings 4 and 5)
  clear the agreement test on two captures each, but their east jambs disagree by 394 mm and 170 mm, so
  moving them would change the opening's WIDTH, which is the one number several captures do agree on
  (1.219 by day, 1.208 at night, drawn 1.213). Nothing further is applied. The comment in index.html above
  WALLF now carries this so the next pass does not re-fit the noise.
"""
s = open(PLAN, encoding='utf-8').read()
if 'THE LIMIT OF THE WALL MEASUREMENT' not in s:
    open(PLAN, 'a', encoding='utf-8', newline='\n').write(entry)
print('logged')
