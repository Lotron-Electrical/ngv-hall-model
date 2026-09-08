# 2026-09-09: logs the wall overlay audit on the first posed balcony frames and the b6 camera finding.
PLAN = 'E:/sitecapture-captures/ngv-site/agent-ref-walls/PLAN-20260908-walls.md'
entry = """- 2026-09-09 night, the walls drawn over the posed balcony frames (tools/overlay_walls.py: the north openings,
  the glazing fins, the end levels 5.3 / 6.33 / 8.34 / 11.1 / 13.5, the four doors, projected through each frame's
  own camera; overlay-*.jpg in shots/pose). b3 (clip 153332) turns out to be shot from the EAST top gallery's
  edge (u 48.1-48.4, d 4.1-7.2, h 9.7-10.1) looking west down the whole hall; b1 from inside north opening 5.
  b3_000100 and b3_000034: the twelve openings' rectangles sit on the real openings all the way down the north
  wall (the near ones within a few pixels, the far ones inside the dark of the real reveals); the five fins sit
  on the real fins; at the west end the 13.5 line meets the canopy's foot, the lit top-gallery band sits between
  the 8.34 and 11.1 lines and the dark lower tier between 6.33 and 8.34, the ground wall below 5.3. b1_000105:
  the north door 45.97-47.79 lands on the real dark doorway on the left wall, the south door 45.70-48.22 on the
  dark door on the right, the east end's lit top gallery between its 8.34 and 11.1 lines. No disagreement
  visible in these frames; the walls hold against the balcony footage.
- 2026-09-09 night: the b6 clip (153148) is NOT 4K: 1520x2032 (a 120 fps mode, ffprobe). The frozen 4K camera
  (1850 px, principal point 1080,1920) cannot fit it; the queue2 run had begun b6s with it (and outlived its
  stop: its extraction and matching are good, features do not depend on the camera). queue3.sh waits for that
  run to end, then re-registers b6s with --skip-match, a scaled prior (1302 px, 760,1016) and the register's own
  sweep 900-2200 px + joint adjustment, lifts it, then b4 b5 b7s with the frozen 4K camera.
"""
s = open(PLAN, encoding='utf-8').read()
if 'the walls drawn over the posed balcony frames' not in s:
    open(PLAN, 'a', encoding='utf-8', newline='\n').write(entry)
print('logged')
