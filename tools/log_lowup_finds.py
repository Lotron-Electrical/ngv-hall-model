# 2026-09-09: logs the lower tier's solid upstand (ENDW.lowUpstand 0.52) in the walls plan and AGENTS.md.
PLAN = 'E:/sitecapture-captures/ngv-site/agent-ref-walls/PLAN-20260908-walls.md'
entry = """- 2026-09-09 the lower tier's front. The 2009 Commons frame commons-len-french-ceiling-ngv.jpg (3264 px, from the
  east top gallery, the west end square on) reads, scaled 106 px/m on the top parapet's 8.08-9.40 (140 px): the
  lower tier's dark panel from 5.44 (the apron's foot, built 5.4) up to 6.8, and bar stools seen THROUGH the run
  above it, so the lower front is a solid upstand with glass over it, like the top's. The 2026 profiles agree:
  end_profile.py on w2_000252, w1_000028, d4_000049 (west) and w1_000404, w1_000356 (east) step up out of the
  dark 6.8-7.3 on both ends (mean 7.05, the glass's dark reflection included). Built: ENDW.lowUpstand 0.52
  (solid 6.33-6.85, glass 6.85-7.22), the 2009 6.8 and the 2026 7.05 straddling it. Pairs lowup-w252, lowup-w404.
  The 2009 frame also shows the central lit ground doorway (about d 7.7) and the top parapet reading dark to its
  top: both 2009 fit-out, not 2026 (the 2026 frames show no central doorway and the lit interior through the top
  glass), so not built. Its stack otherwise fits: apron foot 5.44, top slab underside 8.08 (anchor), head above.
"""
open(PLAN, 'a', encoding='utf-8', newline='\n').write(entry)
p = 'AGENTS.md'; s = open(p, encoding='utf-8').read()
old = """    8.08-8.34 the top balcony's fascia; 8.34-8.90 a 0.56 solid upstand, GLASS over it to 9.40:"""
new = """    6.33-6.85 the lower tier's solid upstand (0.52), glass over it to 7.22: the 2009 Commons frame
              from the east gallery shows bar stools through the run above a dark panel ending 6.8,
              and the 2026 profiles step up out of the dark 6.8-7.3 on both ends (2026-09-09)
    8.08-8.34 the top balcony's fascia; 8.34-8.90 a 0.56 solid upstand, GLASS over it to 9.40:"""
assert old in s; s = s.replace(old, new, 1)
open(p, 'w', encoding='utf-8', newline='\n').write(s)
print('logged')
