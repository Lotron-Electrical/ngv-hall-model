# AGENTS.md: the pleat depth check from the posed frames (string patch, 2026-09-08).
p = 'AGENTS.md'
s = open(p, encoding='utf-8').read()
old = '''  head's dark facets peak at the bay centres, the near point when looking up. Its depth and angle
  stay unmeasured (tools/glazing_hyp.py draws both hypotheses into the one posed frame that holds
  the middle fins, w1_000131, and it is too blurred to read).
'''
new = '''  head's dark facets peak at the bay centres, the near point when looking up. Its depth: the posed
  frames give at most 12 px of leverage between an apex on the face and one 2.1 m out (they all
  stand within 28 deg of the wall normal; past 55 deg the fins hide the bay; tools/glazing_depth.py
  ranks every frame/bay pair and draws the apex at candidate depths). In the sharpest, w6_000082
  bay 3, the apex mullion sits between the 1.5 and the 2.09 candidates: the declared 2.09 m / 41.5
  deg is CONSISTENT with the frames and cannot be pinned tighter than about +-0.5 m from this
  material. The courtyard balcony photo (lloyd-01) was also tried (tools/court_lines.py: vanishing
  points give a 95 deg lens of unknown distortion, six pale bands where five fins were expected)
  and judged unfit for a depth solve.
'''
assert old in s
s = s.replace(old, new)
open(p, 'w', encoding='utf-8', newline='\n').write(s)
q = 'E:/sitecapture-captures/ngv-site/agent-ref-walls/PLAN-20260908-walls.md'
t = open(q, encoding='utf-8').read()
t += ('- 2026-09-08 14:10 pleat depth: tools/glazing_depth.py (posed frames, apex at candidate depths, leverage\n'
      '  10-12 px, 20 frame/bay pairs) puts the w6_000082 bay-3 mullion between the 1.5 and 2.09 candidates:\n'
      '  the declared 2.09 m apex is consistent, not refinable (+-0.5 m). Courtyard photo solve (court_lines.py)\n'
      '  abandoned: 95 deg lens, unknown distortion. Glazing geometry unchanged. Shots: shots/glaz/depth-*.jpg.\n')
open(q, 'w', encoding='utf-8', newline='\n').write(t)
print('ok')
