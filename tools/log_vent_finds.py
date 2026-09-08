# 2026-09-09: logs the east deck's floor vent strip (ENDW.eastVent) in the walls plan and AGENTS.md.
# The plan entry was appended on the first run (whose AGENTS.md replace missed on whitespace); it is skipped if present.
PLAN = 'E:/sitecapture-captures/ngv-site/agent-ref-walls/PLAN-20260908-walls.md'
entry = """- 2026-09-09 the east deck's floor vent strip, built. The chained straight-down frame d4_000232 (camera u 48.17,
  d 13.39, h 9.81) met with the deck (h 8.34, chain_pixel.py): the perforated plate's far edge u 48.35 (0.3 behind
  the glass line), its south end d 13.34 (seen, the plain deck beyond it), its north end past the frame's edge on
  d 12.64 and its near edge past the frame's bottom on u 48.69, so ENDW.eastVent [48.35, 48.69, 12.64, 13.34]
  (the earlier note had its ends the wrong way round: the SOUTH end is the seen one). The plate reads no darker
  than the deck with a grid of dark holes on a 22 mm pitch (36 px in the frame, 0.6 mm per px), so it is built
  as a canvas of holes over the deck's own day/night tone (patch_vent.py). Pair vent-d232-pair.jpg (chain_shot.py,
  new: a chain-posed frame beside the sim, like pose_pair.py). tools/with_server.py serves the repo for one
  command when tools/serve.js is down (it died mid-session; nothing outlives the call).
"""
if "the east deck's floor vent strip, built" not in open(PLAN, encoding='utf-8').read():
    open(PLAN, 'a', encoding='utf-8', newline='\n').write(entry)
p = 'AGENTS.md'; s = open(p, encoding='utf-8').read()
pairs = [("a perforated floor vent strip 0.3 m wide lies 0.2-0.3 m behind",
          "a perforated floor vent strip 0.3 m wide lies 0.3 m behind"),
         ("the glass on the deck (u 48.38-48.69, d 12.65 to past 13.36; unbuilt, its south end",
          "the glass on the deck (`ENDW.eastVent` u 48.35-48.69, d 12.64-13.34: its south end seen, its"),
         ("              unseen). The\n",
          "              north end and near edge past the frame; holes on a 22 mm pitch in the deck's tone, 2026-09-09). The\n")]
for old, new in pairs:
    assert old in s, old; s = s.replace(old, new, 1)
open(p, 'w', encoding='utf-8', newline='\n').write(s)
print('logged')
