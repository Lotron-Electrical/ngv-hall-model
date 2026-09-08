# 2026-09-09: logs the look-along deck frames (chain from d4_000104) in the walls plan and AGENTS.md.
PLAN = 'E:/sitecapture-captures/ngv-site/agent-ref-walls/PLAN-20260908-walls.md'
entry = """- 2026-09-09 the look-along deck frames chained from the accepted d4_000104 (chain_pose.py, the anchor check fixed:
  drift 0.6-1.4 degrees against every accepted frame met). d4_000120 (8 s) looks north-west along the east top
  gallery: the deck is a plain cool mid-grey surface (63,79,88 against the north stone's 82,83,97 in the same
  frame, 0.8x), the parapet a thin dark line seen from above; its glass top, met with the h 9.40 plane, runs
  straight (u 47.53-47.59 over d 10.4-13.0), so the glass IS the top edge and the phone stood 0.26 m behind it.
  The same edge from the d4_000232 chain (anchor d4_000196) sat under the phone; the two anchors differ by
  0.27 in u, the accepted deck cameras scatter 47.8-48.4, so the face is known to +-0.3 and the built 48.056 (3.85
  in front of the plate end) stays. Deck floor material: dnm(0x1a1c1e, 0x85898d), a cool grey 0.8x the stone (was
  a warm dark Lambert). Pair shots/pose/deck-d120-pair.jpg (the sim's camera sits 0.25 m in front of the built
  face for this anchor, so the sim shows no deck). chain_pixel.py gains the d= plane.
"""
open(PLAN, 'a', encoding='utf-8', newline='\n').write(entry)
p = 'AGENTS.md'; s = open(p, encoding='utf-8').read()
old = """              grating runs along the deck's front edge behind it (unbuilt, extent unmeasured)"""
new = """              grating runs along the deck's front edge behind it (unbuilt, extent unmeasured). The
              deck itself (d4_000120, chained from d4_000104, looking along it): a plain cool mid-grey
              0.8x the stone beside it, built as `floorMat` dnm(0x1a1c1e, 0x85898d). Its glass top met
              with the h 9.40 plane runs straight (u 47.53-47.59), the phone 0.26 m behind it; the
              d4_000232 chain put the same edge under the phone, the anchors differ 0.27 in u, so the
              face is +-0.3 and the built 48.056 stays"""
assert old in s; s = s.replace(old, new, 1)
open(p, 'w', encoding='utf-8', newline='\n').write(s)
print('logged')
