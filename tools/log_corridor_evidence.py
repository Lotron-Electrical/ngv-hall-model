# 2026-09-09: what the EXISTING posed imagery can and cannot say about the corridor behind the north wall.
PLAN = 'E:/sitecapture-captures/ngv-site/agent-ref-walls/PLAN-20260908-walls.md'
entry = """- 2026-09-09 late, an honest audit of the evidence behind the north wall, before any rebuild. New tools:
  tools/find_seers.py (which posed frames see a hall point, and how square-on), tools/find_openseers.py (which
  frames see a WHOLE opening, all four corners in frame, with the height its head-ray reaches on the corridor's
  back wall), tools/opening_probe.py (the opening drawn with a labelled height ladder on the back wall),
  tools/opening_look.py (the raw pixels inside one opening, rotated upright, levels stretched).
  What they found, per opening, over every posed class:
    walk (789 day floor frames): 85-150 frames see a whole opening, but the best is 100-150 px wide and the
      pixels inside are nearly flat: opening 5 in w1_000379 stretches from levels 23-86, in w1_000447 from
      12-31, under 20 grey levels of signal across the whole opening. Nothing behind the wall is legible.
      The widest spans belong to cameras standing 2 m off the wall looking 7 m sideways, so they are oblique,
      not informative.
    night: not one frame sees a whole opening.
    day4k (138 balcony frames): every one of them is at the EAST end (u 48.1, d 13.3), so an opening at u 19
      is 30 m away and 38 px wide.
    b1 / b3 (the new balcony clips): 0 frames see a whole opening (b1 stands IN one, b3 is at the far end).
  CONCLUSION: nothing posed today measures the corridor behind the brick wall, so it is not being changed on a
  guess. It rests on the b6 gallery frames 1056-1330, the only imagery taken INSIDE that room.
"""
s = open(PLAN, encoding='utf-8').read()
if 'an honest audit of the evidence behind the north wall' not in s:
    open(PLAN, 'a', encoding='utf-8', newline='\n').write(entry)
print('logged')
