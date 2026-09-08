# 2026-09-09: logs the corridor back wall's daytime tone (corridorBackMat day 0x423a2c) in the walls plan and AGENTS.md.
PLAN = 'E:/sitecapture-captures/ngv-site/agent-ref-walls/PLAN-20260908-walls.md'
entry = """- 2026-09-09 the corridor's daytime tone. In d4_000120 (15:32, the hall lit by the canopy) the back wall seen
  through the nearest opening reads RGB 51/38/26 against 75/63/58 for the stone beside it: warm, 0.68/0.60/0.45 of
  the stone. The sim's stone in the same crop renders 78/75/69, so the wall should render 53/45/31; corridorBackMat
  day went 0x4b4844 (rendered 66/63/58, neutral, too bright) to 0x423a2c, which renders 52/43/29 (two renders to
  land it through the tone map). Night 0x0c0b0a kept (the night frames read the openings black). Pair
  corr3-d120-pair.jpg. The reveal's shadowed jamb reads 32/27/22 (0.43 of the stone): the stone reveals are left
  to the lighting.
"""
open(PLAN, 'a', encoding='utf-8', newline='\n').write(entry)
p = 'AGENTS.md'; s = open(p, encoding='utf-8').read()
old = """  spot, so no parallax, tools/lamp_seers.py); its back wall is UNMEASURED, so it is one dark"""
new = """  spot, so no parallax, tools/lamp_seers.py); its back wall's depth is UNMEASURED, its daytime
  tone measured (warm, 0.68/0.60/0.45 of the stone beside the opening in d4_000120, corridorBackMat
  day 0x423a2c renders it 52/43/29 against the frame's 51/38/26); so it is one dark"""
assert old in s; s = s.replace(old, new, 1)
open(p, 'w', encoding='utf-8', newline='\n').write(s)
print('logged')
