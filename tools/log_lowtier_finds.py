# 2026-09-09: logs the lower tier's interior tone, fittings and exit sign (ENDW.lowLamps, lowExit) in the walls plan and AGENTS.md.
PLAN = 'E:/sitecapture-captures/ngv-site/agent-ref-walls/PLAN-20260908-walls.md'
entry = """- 2026-09-09 the west lower tier by day, from the 4K frame d4_000049 (east deck, 45 m): its interior is near
  black (RGB 16-23 against 157/137/98 for the stone, 0.1-0.15 of it; the sim's lowBackMat day 0x4e4841 was 0.5,
  now 0x16120f), with four saturated white fittings whose rays meet the back wall (u 0.4) on d 1.64 h 7.81,
  d 11.97 h 8.20, d 13.17 h 8.02, d 13.29 h 7.87 (the two above the 8.08 ceiling clamped to 8.0: the register's
  +-0.3 at this range; a ceiling lamp would meet the plane too high only if it sat in front of the face, so
  they are on the wall or its top edge), and a GREEN exit sign (188/252/212) on d 13.52, h 7.32. Built as
  ENDW.lowLamps.west, lowExit.west (patch_lowtier.py). The east lower tier is seen from a height by no posed
  frame (the day4k clip looks west), so it keeps the tone and gets no fittings. Pair low-d49-pair.jpg.
"""
if 'the west lower tier by day' not in open(PLAN, encoding='utf-8').read():
    open(PLAN, 'a', encoding='utf-8', newline='\n').write(entry)
p = 'AGENTS.md'; s = open(p, encoding='utf-8').read()
old = "    6.33-6.85 the lower tier's solid upstand (0.52), glass over it to 7.22:"
new = ("    6.33-8.08 the lower tier's interior: near black by day (0.1-0.15x the stone in d4_000049,\n"
       "              `lowBackMat`), four white fittings on the west back wall (d 1.64, 11.97, 13.17,\n"
       "              13.29, h 7.8-8.0) and a green exit sign (d 13.52, h 7.32), `ENDW.lowLamps/lowExit`;\n"
       "              the east lower tier is unseen from a height (2026-09-09)\n" + old)
assert old in s, 'anchor'; s = s.replace(old, new, 1)
open(p, 'w', encoding='utf-8', newline='\n').write(s)
print('logged')
