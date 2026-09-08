# 2026-09-09: corrects the deck notes after the chain re-anchored on the accepted d4_000200 (u 48.17, h 9.81).
PLAN = 'E:/sitecapture-captures/ngv-site/agent-ref-walls/PLAN-20260908-walls.md'
entry = """- 2026-09-09 the deck notes corrected. With chain_pose.py's anchor check fixed the d4_000232 chain re-anchors on the
  accepted d4_000200 (u 48.17, h 9.81; the neighbour d4_000198 registers 0.18 lower, the deck cameras' own scatter),
  and the glass cap's edge meets the h 9.40 plane 0.31-0.36 m from the phone, u 48.19-48.22, straight over d
  13.17-13.56: on either anchor the cap lies on the built 9.40 within +-0.15 and beside the built face within the
  cameras' +-0.3. The "grating along the deck's front edge" was over-read: on the deck plane (h 8.34) the
  perforated patch spans u 48.38-48.69 (0.3 m wide, starting 0.2-0.3 m behind the glass) and d 12.65 to past
  13.36 (its south end off frame), a floor vent strip beside the parapet; too little of it is seen to build.
"""
open(PLAN, 'a', encoding='utf-8', newline='\n').write(entry)
p = 'AGENTS.md'; s = open(p, encoding='utf-8').read()
old = """              straight-down frame d4_000232 (tools/chain_pose.py, chain_pixel.py) puts the glass's cap
              0.2 m under a phone held over it (h 9.63), so the 9.40 top holds (+-0.05); a perforated
              grating runs along the deck's front edge behind it (unbuilt, extent unmeasured). The"""
new = """              straight-down frame d4_000232 (tools/chain_pose.py, chain_pixel.py) has the glass's cap
              0.2-0.4 m under the phone on either of its two anchors (h 9.63 / 9.81), the cap on the
              built 9.40 within +-0.15; a perforated floor vent strip 0.3 m wide lies 0.2-0.3 m behind
              the glass on the deck (u 48.38-48.69, d 12.65 to past 13.36; unbuilt, its south end
              unseen). The"""
assert old in s; s = s.replace(old, new, 1)
open(p, 'w', encoding='utf-8', newline='\n').write(s)
print('logged')
