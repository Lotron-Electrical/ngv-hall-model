# 2026-09-09: logs the corridor ceiling (WALLF.corridor.ceil 11.4) and its downlight in the walls plan and AGENTS.md.
PLAN = 'E:/sitecapture-captures/ngv-site/agent-ref-walls/PLAN-20260908-walls.md'
entry = """- 2026-09-09 the corridor's ceiling, measured. The chained deck frame d4_000120 (camera u 47.81, d 13.43, h 9.99,
  13 m from the wall) looks up through the nearest opening (u 44.9-46.2) and sees a downlight in the corridor's
  ceiling just under the head. chain_pixel.py on the lamp (frame px 205,1558): h 11.29 for d -1.0, 11.37 for
  d -1.9, 11.46 for d -2.9, so the ceiling is 11.3-11.5 wherever the lamp sits across the 2.0 m corridor; the head
  reveal's top in the same frame reads 11.37 (built 11.35) and the lit sill line 8.98-9.02 (built 8.99). A ceiling
  on 11.8 would be out of sight from this camera (the ray through the head rises 0.09 per metre and the corridor
  is 2.9 deep), so 11.8 was wrong. Built: WALLF.corridor.ceil 11.4 (+-0.1), one downlight (corridor.lamps, u 45.16
  measured, depth assumed mid-corridor, a lit 0.15 disc). Pair corr2-d120-pair.jpg: the sim's lamp sits on the real
  one at the top of the opening. The corridor's back wall depth stays the plan's 2.0.
"""
open(PLAN, 'a', encoding='utf-8', newline='\n').write(entry)
p = 'AGENTS.md'; s = open(p, encoding='utf-8').read()
old = """  side and its ceiling is not another floor; its floor the second floor h 8.34; its ceiling
  (11.8) and back wall are UNMEASURED (no frame or cloud point sees them), so it is one dark Lambert"""
new = """  side and its ceiling is not another floor; its floor the second floor h 8.34; its ceiling
  11.4 (+-0.1: the deck frame d4_000120 sees a downlight in it through the nearest opening,
  h 11.29-11.46 across the corridor's depth, chain_pixel.py 2026-09-09; `corridor.lamps` builds
  that one lamp, its depth assumed mid-corridor); its back wall is UNMEASURED, so it is one dark"""
assert old in s; s = s.replace(old, new, 1)
open(p, 'w', encoding='utf-8', newline='\n').write(s)
print('logged')
