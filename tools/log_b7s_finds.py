# 2026-09-09: where clip 154940 was shot, and the east parapet it decided.
PLAN = 'E:/sitecapture-captures/ngv-site/agent-ref-walls/PLAN-20260908-walls.md'
entry = """- 2026-09-09, CLIP 154940 PLACED, AND THE EAST PARAPET WITH IT. The b7s register finished its 148,716-pair
  matching in 4,166 s and then exited 127 before the mapper without writing to stderr; queue7b.sh resumed it
  with --skip-match and it solved in 59 s. Twelve frames accepted, and they answer Lloyd's question about
  the second video outright (tools/b6g_where.py on model-b7s-accepted):
    five frames  u 48.94-49.21  d 13.04-14.33  h 9.50-9.75  looking WEST
    seven frames u  3.19-3.33   d 12.82-14.03  h 9.56-9.74  looking EAST
  The clip walks the SOUTH UPPER GALLERY from the east end to the west end. Zero frames behind the north
  wall, so the pose census stands: 1,128 registered cameras now, 1,106 in the hall, 22 in an opening, none
  in the corridor.
  WHAT IT UNLOCKED. b7s sees both end walls from a place nothing else in the archive stands, so it is the
  fourth east capture. Every capture was then re-read with the fixed-point finder, because the b7s numbers
  came from the new code and the rest of the leveljson was written by the old one, and pooling two
  instruments together is not a measurement. With one instrument across all seven:
    west parapet top 9.02   3 captures  median -0.021  range 0.048   SETTLED within 21 mm
    east parapet top 9.02   4 captures  median +0.090  range 0.061   MOVES +0.090 m
      b1 +0.107; b7s +0.119; night +0.057; walk +0.073
  This is the first level in the whole effort to pass the pooled test WITH a move. The same four captures
  could not agree at all (range 0.129) while the following instrument was reading them; with the follow
  removed they agree within 61 mm and all four say the east parapet stands high. So ENDW gains a per-end
  upstand: west 0.68, east 0.77.
  THE SIZE IS A LOWER BOUND. tools/follow_test.py measures a residual gain of 0.45 here, and a following
  instrument understates the offset, so the true east parapet is 9.11 or higher; extrapolating the
  draw-to-answer line to where it crosses itself puts it near 9.15. The model takes the measured value.
  For the same reason a small residual on the next re-measure is NOT confirmation: part of it is the echo.
  ALSO: the wall's own follow test after the fix (tools/wall_follow.py). Drawn 1.256 now measures 1.217,
  drawn 1.213 measures 1.202, gain down from 0.70 to 0.37, and the two answers BRACKET the shipped 1.213.
  Today's opening-width correction is therefore validated by the repaired instrument rather than by the
  instrument that was echoing it.
"""
s = open(PLAN, encoding='utf-8').read()
if 'CLIP 154940 PLACED' not in s:
    open(PLAN, 'a', encoding='utf-8', newline='\n').write(entry)
print('logged')
