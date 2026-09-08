# 2026-09-09: the pose census, which closes the corridor question for the whole archive.
PLAN = 'E:/sitecapture-captures/ngv-site/agent-ref-walls/PLAN-20260908-walls.md'
entry = """- 2026-09-09, THE POSE CENSUS. Every photometric route into the room behind the north wall has now failed
  for a reason that is itself measured: from the floor an opening is 100-150 px wide with under 20 grey
  levels inside it, no capture sees a whole opening except the walk pass, and the head soffit stands over
  the reveal so an upward sightline ends on its underside. So the last instrument was applied: a registered
  camera IS a measurement of the point it stood at, the same argument that placed clip 153148 on the east
  balcony. tools/corridor_poses.py walks EVERY accepted model in the archive and puts every camera centre
  in the hall frame; tools/corridor_poses_draw.py plots it.
  RESULT, 1,116 registered cameras across six classes:
    in the hall (d > -0.09)          1,094
    inside an opening (-0.99..-0.09)    22, all b1, all in opening 5 (u 19.36-19.71)
    in the corridor (d < -0.99)          0
  The deepest camera in the entire archive is b1_000057 at d -0.45: 0.36 m past the wall's inner face and
  still 0.54 m short of the back of the reveal, with its lens pointed back out at the hall (look d +0.79).
  Nobody ever carried a camera into that room. C.width 2.0 and C.ceil 11.4 therefore cannot be measured
  from this archive by ANY method, photometric or geometric, and they stay marked unmeasured against the
  1968 plan and the single downlight. This is written into index.html so no further pass is spent on it:
  the frames do not exist.
  THE ONE NUMBER IT DOES SETTLE is the corridor floor. Those 22 cameras sit h 9.58-9.86 while leaning
  through the opening; a phone is carried 1.35-1.65 m above the feet, so the surface the operator stood on
  is h 7.93-8.51. C.floor 8.34 sits inside that and is the building's own second floor, so it moves from
  assumed to corroborated. It also puts the opening sill (8.99) a low 0.65 m above that floor, which is
  exactly why a person leaning on it puts a lens near h 9.7.
  Census CSV: agent-ref-walls/corridor-poses.csv (class, frame, u, d, h, look vector).
"""
s = open(PLAN, encoding='utf-8').read()
if 'THE POSE CENSUS' not in s:
    open(PLAN, 'a', encoding='utf-8', newline='\n').write(entry)
print('logged')
