# 2026-09-09: logs the corridor lamp's depth search (no second viewpoint) in the walls plan and AGENTS.md.
PLAN = 'E:/sitecapture-captures/ngv-site/agent-ref-walls/PLAN-20260908-walls.md'
entry = """- 2026-09-09 the corridor's depth, tried by parallax on the downlight. tools/chain_project.py projects the lamp
  (u 45.16, d -1.9 assumed, h 11.37) into every chained frame: six frames of chain 104-168 see it, all from the
  one deck spot (a look-around, no baseline); chain 196-272 never sees it. tools/lamp_seers.py sweeps every posed
  walk, night and day4k camera for one whose ray to the lamp crosses the opening: eleven day4k frames, all
  registered on the same deck spot (u 48.1, d 12.8-13.5, baseline 0.6 m over 15 m, so 0.2 m of depth per pixel
  of parallax), and their crops show the canopy, not the wall (tools/lamp_depth.py's blob fix collapsed onto the
  camera), so their register poses are not usable for this. No floor frame looks up through a north opening.
  Result: the lamp's depth and the corridor's back wall stay the 1968 plan's 2.0 m; the ceiling 11.4 (+-0.1)
  holds for any depth inside it.
"""
open(PLAN, 'a', encoding='utf-8', newline='\n').write(entry)
p = 'AGENTS.md'; s = open(p, encoding='utf-8').read()
old = """  that one lamp, its depth assumed mid-corridor); its back wall is UNMEASURED, so it is one dark"""
new = """  that one lamp, its depth assumed mid-corridor: every camera that sees it stands on the one deck
  spot, so no parallax, tools/lamp_seers.py); its back wall is UNMEASURED, so it is one dark"""
assert old in s; s = s.replace(old, new, 1)
open(p, 'w', encoding='utf-8', newline='\n').write(s)
print('logged')
