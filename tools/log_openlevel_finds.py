# 2026-09-09: the openings' sill and head, measured for the first time.
PLAN = 'E:/sitecapture-captures/ngv-site/agent-ref-walls/PLAN-20260908-walls.md'
entry = """- 2026-09-09, THE SILL AND THE HEAD. Every wall measurement until now has been horizontal, where the jambs
  stand along the hall. The openings also have a top and a bottom, openY [8.99, 11.35], and no photograph
  had ever been put against them. tools/open_levels.py does it, tools/open_pool.py pools it,
  tools/open_levels_draw.py draws it.
  TWO PROTECTIONS the jamb work did not need. The search window is HALF A BLUESTONE COURSE, 0.14 m: the
  coursing on this wall is measured as 0.304 m courses with north bed joints on h = 0.080 + 0.304k, so a
  real joint sits within 0.152 m of any height on this face and a wider search finds masonry instead of the
  opening. And an obliquity gate refuses samples more than 60 degrees off the wall normal, because the two
  balcony clips see this wall end-on from 25-45 m down the hall.
  FIRST PASS, on the old single-look finder: the head read about 0.09 low from both floor walks and near
  zero (+0.04) from the balcony clips, a 0.13 m split that fell exactly along capture rather than along
  position. That was the follow bias the audit had just found. With tools/edge_refine.py in place it goes
  away: the balcony clips stop disagreeing and the pooled result is
    sill  +0.013 m       head  -0.013 m
  openY THEREFORE STANDS AS DRAWN, and this is the first time either number has had any evidence at all.
  THE COST OF THE HONESTY IS COVERAGE. Of twelve openings only two get two captures each for the sill and
  two for the head, because the fixed-point finder refuses every sample whose edge does not settle. So
  neither level is measured better than about 0.10 m, and neither is out by more than 13 mm. The drawing
  from night frame w5_000107 shows why: from the hall floor the openings are small dark rectangles seen
  end-on, and only the nearest one returns a settled edge.
  ONE LOOSE END, recorded not acted on: the head is 22 mm off bed joint 37 (11.328), inside the
  measurement, but the sill is 94 mm off the nearest joint (8.896). Either the sill is not built to the
  coursing or the measured coursing phase drifts by that much this high up the wall.
"""
s = open(PLAN, encoding='utf-8').read()
if 'THE SILL AND THE HEAD' not in s:
    open(PLAN, 'a', encoding='utf-8', newline='\n').write(entry)
print('logged')
