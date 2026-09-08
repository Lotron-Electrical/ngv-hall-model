# 2026-09-09: the openings re-read by the repaired instrument, and moved as openings.
PLAN = 'E:/sitecapture-captures/ngv-site/agent-ref-walls/PLAN-20260908-walls.md'
entry = """- 2026-09-09, THE OPENINGS MOVE AS OPENINGS. tools/wall_edges.py has now had the same two repairs as the
  level instrument (the fixed-point finder from tools/edge_refine.py, and a constant search window instead
  of one derived from the very table under test), plus an OPEN_WIDTH hook so it can be pointed at a table
  it did not draw. tools/wall_follow.py then measures what is left: drawn 1.256 reads 1.217, drawn 1.213
  reads 1.202, the follow gain is down from 0.70 to 0.37, and the two answers BRACKET the shipped 1.213.
  The width is confirmed by an instrument that is no longer echoing it, and is not touched again.
  All six captures were then re-read with that instrument, b7s included, and pooled. Five individual jambs
  come out more than 50 mm out with the captures agreeing. Applying those five one at a time would give
  four openings widths of 1.269, 1.112, 1.094 and 1.240, which is not what a wall of twelve identical
  windows does. Read as openings instead, they mostly move the same way by the same amount.
  THE ESTIMATOR, tools/opening_shift.py: each capture states its OWN shift for an opening, the mean of its
  two jamb offsets, both read in the same frames where most of the error is common to them; then those
  per-capture shifts are pooled. The width never enters it and the pooling measures disagreement about a
  shift, which is the number that matters.
    opening  3   -0.078   night -0.121, walk -0.036   range 0.085   MOVES
    opening  4   +0.073   night +0.099, walk +0.047   range 0.052   MOVES
    opening  5   +0.124   b7s +0.120, walk +0.127     range 0.007   MOVES
    opening  6   +0.061   b1 +0.019, walk +0.103      range 0.084   MOVES
    openings 7, 8, 9, 12  agreed and within 50 mm, stay
    openings 1, 10, 11    captures disagree by 108, 178, 192 mm, no move
    opening  2            one capture only, no move
  Opening 5 is the strongest reading in the whole wall effort: a day floor walk and a 4K balcony clip shot
  from the south upper gallery, two completely different viewpoints and cameras, agree within 7 mm.
  That openings 7, 8 and 9 now pool agreed and within 50 mm is independent confirmation of this morning's
  shifts of those three, made with the instrument that was still echoing.
  Every shift is a LOWER bound: the 0.37 follow gain remains and a following instrument understates. A
  small residual on the next re-measure is NOT confirmation; part of it will be this change echoing.
"""
s = open(PLAN, encoding='utf-8').read()
if 'THE OPENINGS MOVE AS OPENINGS' not in s:
    open(PLAN, 'a', encoding='utf-8', newline='\n').write(entry)
print('logged')
