# 2026-09-09: logs the east top gallery's fittings and exit sign (ENDW.wallLamps.east, topExit.east) in the walls plan and AGENTS.md.
PLAN = 'E:/sitecapture-captures/ngv-site/agent-ref-walls/PLAN-20260908-walls.md'
entry = """- 2026-09-09 the east top gallery's back wall, from the two floor frames w1_000404 (34 m) and w1_000356 (39 m),
  saturated and green pixels clustered and met with u 51.85: white fittings on d 7.79 / 7.90 (the one built
  already), d 12.27 / 12.29 (h 10.86 / 10.34) and d 13.26 / 13.24 (h 10.62 / 10.39), and a GREEN exit sign on
  d 13.57 / 13.43, h 10.68 / 10.70: the two frames agree on every d within 0.15 and on h within the register's
  0.5 spread. A fourth white blob near the north end reads d 0.64 in one frame and 4.49 in the other (grazing,
  36-43 m): not built. Built: wallLamps.east + [12.28, 10.6], [13.25, 10.5]; topExit.east [13.5, 10.69]
  (patch_eastlamps.py). The east lower tier band in w1_000404 holds no bright or green pixel (its interior
  28/26/28 against 62/52/47 for the stone in that frame): no fittings there. Pair eastlamps-w404-pair.jpg.
"""
if "the east top gallery's back wall, from the two floor frames" not in open(PLAN, encoding='utf-8').read():
    open(PLAN, 'a', encoding='utf-8', newline='\n').write(entry)
p = 'AGENTS.md'; s = open(p, encoding='utf-8').read()
old = "              east d 7.9, h 10.5 from w1_000404 and w1_000356, +-0.25; west d 7.0, h 11.4 from\n              w2_000252 alone; 2026-09-09)"
new = ("              east d 7.9, 12.28 and 13.25, h 10.5-10.6, plus a green exit sign on d 13.5, h 10.69,\n"
       "              from w1_000404 and w1_000356, +-0.25 (`topExit.east`); west d 7.0, h 11.4 from\n              w2_000252 alone; 2026-09-09)")
assert old in s, 'anchor'; s = s.replace(old, new, 1)
open(p, 'w', encoding='utf-8', newline='\n').write(s)
print('logged')
