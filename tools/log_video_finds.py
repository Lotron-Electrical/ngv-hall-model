# 2026-09-08: appends the balcony-video findings to the walls plan log and AGENTS.md (one-shot).
PLAN = 'E:/sitecapture-captures/ngv-site/agent-ref-walls/PLAN-20260908-walls.md'
entry = """- 2026-09-08 22:50 the balcony video (online/video/qXnaPNrQAsI.webm, "[4K] NGV Tour", uploaded 2022-10-12, 1080p):
  frames 258-275 s are shot FROM the east top gallery looking west (full frames _sheet/q4k-266.jpg, q4k-271.jpg;
  pose pairs shots/pose/q4k-266-pair.jpg, q4k-271-pair.jpg against pose-shot from u 47.4 d 10.5 h 9.9, fwd -u,
  pitch -8 / -32, vfov 60, noon). Read against the sim: the north wall's six top openings as deep dark recesses
  with a lit east reveal (as built); the lit ground doorway under the rig by column N4 (as built, 23.1-29.4); the
  west end's double door with two round windows on the SOUTH side of the end (as built, d 13.25/13.95); the pale
  full-height "pier" on the south side is the south glazing's fin + daylit bay (flat-glazing-south-fin-0..4 in
  the GLB, u 17.6-34.6, already in the sim); the west lower tier reads as a black drape and the top tier dark
  with a green exit sign in 2022 (temporal: the 2026 day frames read the top tier lit, keep the measured tones).
  Sim from the same spot matches in layout; no new numbers (unposed phone, wide lens). Other downloads swept
  (one frame per 8 s, _sheet/*-tiles.jpg): 2SGa2bph-2I is AI-generated stock (discard); ieWs7b_Z39o, fQt1O8jTHbc,
  nZn4PYzbhnA no hall; 3nhQrQGSln4 149-165 s canopy from the floor + one end wall from below (_sheet/3nh-163.jpg:
  the gallery head as a dark slot under the stone, as built); pTYuYCtWjsA one canopy glimpse. No corridor footage.
"""
open(PLAN, 'a', encoding='utf-8', newline='\n').write(entry)
p = 'AGENTS.md'; s = open(p, encoding='utf-8').read()
key = "**Every other source, weighed.**"
add = """**Online video and photographs (2026-09-08, agent-ref-walls/online/).** Two research agents harvested YouTube
and Wikimedia Commons for the hall's interior. Useful: `video/qXnaPNrQAsI.webm` ("[4K] NGV Tour", 2022, 1080p),
258-275 s shot FROM the east top gallery looking west: it confirms the north wall's six top openings as deep dark
recesses, the lit ground doorway (u 23.1-29.4), the west double door with two round windows on the south side of
the end, and the south glazing's fins (the pale full-height "pier" in that footage is fin 0 and its daylit bay).
The 2022 footage shows the west lower tier as a black drape and the top tier dark: temporal, the 2026 day frames rule.
`video/bigcujP2hQg.mp4` (2022 walkthrough) 84-114 s: the east end by day, qualitative. `commons-great-hall-ngv-2014.jpg`
and the 1968 Leonard French photograph: the hall from the floor. Nothing online shows the corridor behind the north
wall; its width, floor and ceiling stay on the 1968 plan. Pose pairs in shots/pose/q4k-*-pair.jpg, log in
PLAN-20260908-walls.md 22:50.

"""
assert key in s and add not in s
s = s.replace(key, add + key, 1)
open(p, 'w', encoding='utf-8', newline='\n').write(s)
print('logged')
