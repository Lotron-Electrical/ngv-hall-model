# 2026-09-09: logs the vent strip's move onto the cap line (ENDW.eastVent u 48.21-48.55) in the walls plan and AGENTS.md.
PLAN = 'E:/sitecapture-captures/ngv-site/agent-ref-walls/PLAN-20260908-walls.md'
entry = """- 2026-09-09 the vent strip against the glass. chain_pixel.py on d4_000232 with the cap's own height (h 9.40) puts
  the dark cap band under the phone on u 48.18-48.21 (range 0.35 m: the phone was leaning on the glass), and the
  plate's far edge 0.13-0.17 behind it; the sim's cap stands on the end face u 48.056, so the chain's absolute u
  runs 0.15 east of the sim's here. The plate is set by its offset from the cap, not the chain's absolute u:
  ENDW.eastVent u 48.21-48.55 (was 48.35-48.69), d unchanged. The balcony front itself agrees with the scan's end
  face within the register's +-0.27 anchor spread, so it stays. Pair vent2-d232-pair.jpg.
"""
if 'the vent strip against the glass' not in open(PLAN, encoding='utf-8').read():
    open(PLAN, 'a', encoding='utf-8', newline='\n').write(entry)
p = 'AGENTS.md'; s = open(p, encoding='utf-8').read()
old = "the glass on the deck (`ENDW.eastVent` u 48.35-48.69, d 12.64-13.34: its south end seen, its"
new = "the glass on the deck (`ENDW.eastVent` u 48.21-48.55, 0.15 behind the built cap as the frame has it behind the real one, d 12.64-13.34: its south end seen, its"
assert old in s; s = s.replace(old, new, 1)
old = "a perforated floor vent strip 0.3 m wide lies 0.3 m behind"
new = "a perforated floor vent strip 0.34 m wide lies 0.15 m behind"
assert old in s; s = s.replace(old, new, 1)
open(p, 'w', encoding='utf-8', newline='\n').write(s)
print('logged')
