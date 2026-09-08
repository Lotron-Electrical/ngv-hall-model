# 2026-09-09: logs the south wall's exit light (WALLF.exitSigns) in the walls plan and AGENTS.md.
PLAN = 'E:/sitecapture-captures/ngv-site/agent-ref-walls/PLAN-20260908-walls.md'
entry = """- 2026-09-09 the "lit sign about u 39.5-40.4" beside the south door resolved: in the night frame w5_000082 (u 22.4,
  d 12.3, looking east along the south wall, 18 m off, grazing) it is a green exit light beside the door's east
  jamb plus a red indicator below it; wall_pixel.py meets the green glow with the south face on u 40.66, h 2.78
  and the red on u 40.20, h 1.60 (+-0.3 along the wall from the range and blur). Built as WALLF.exitSigns, a
  0.35 x 0.2 green box (0x2ee88a) 30 mm proud on u 40.5-40.85, h 2.68-2.88, lit day and night; the red is too
  small to build. Pair shots/pose/exit-w82-pair.jpg: the sim's green dot sits on the real one.
"""
open(PLAN, 'a', encoding='utf-8', newline='\n').write(entry)
p = 'AGENTS.md'; s = open(p, encoding='utf-8').read()
old = """  the 2014 photograph's lit doorway), a dark aperture at u 45.70-48.22 head 2.52 (+- 0.3)."""
new = """  the 2014 photograph's lit doorway), a dark aperture at u 45.70-48.22 head 2.52 (+- 0.3). A green
  exit light sits beside the lit door's east jamb, u 40.5-40.85, h 2.68-2.88 (night w5_000082 met
  with the south face, +-0.3; `WALLF.exitSigns`), with a small red indicator below it, unbuilt."""
assert old in s; s = s.replace(old, new, 1)
open(p, 'w', encoding='utf-8', newline='\n').write(s)
print('logged')
