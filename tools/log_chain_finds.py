# 2026-09-09: logs the chain-posed look-down frames (tools/chain_pose.py, chain_pixel.py) in the walls plan and AGENTS.md.
PLAN = 'E:/sitecapture-captures/ngv-site/agent-ref-walls/PLAN-20260908-walls.md'
entry = """- 2026-09-09 the refused deck frames chain-posed (tools/chain_pose.py: the phone turned in place, each frame is the
  last one's pose turned by the homography rotation of undistorted SIFT matches, anchored on the accepted
  d4_000196; drift against the accepted d4_000262/263 after 70 frames about 3 degrees of pitch). The straight-down
  frame d4_000232 (pitch -58) has the parapet's dark cap right under the phone: on the rail-top plane h 9.40 the
  cap's edges meet 0.17-0.20 m under the camera (h 9.63), u 48.09-48.10, so the glass top sits 0.2 m (+-0.05)
  under a phone held over it: rail top 9.40-9.45, the built 9.40 (rails[1] 1.06) holds; the cap reads about a
  centimetre thick (a frameless glass edge). Behind it (nearer the camera) a perforated metal grating along the
  deck's front edge, unbuilt (its extent unmeasured). tools/chain_pixel.py meets a chain-posed pixel with a u or
  h plane. The 7-10 s look-along frames were not chained (no accepted anchor on that side of the swing).
"""
open(PLAN, 'a', encoding='utf-8', newline='\n').write(entry)
p = 'AGENTS.md'; s = open(p, encoding='utf-8').read()
old = """              the 4k frame d4_000198, shot leaning on it, looks down through glass"""
new = """              the 4k frame d4_000198, shot leaning on it, looks down through glass; the chain-posed
              straight-down frame d4_000232 (tools/chain_pose.py, chain_pixel.py) puts the glass's cap
              0.2 m under a phone held over it (h 9.63), so the 9.40 top holds (+-0.05); a perforated
              grating runs along the deck's front edge behind it (unbuilt, extent unmeasured)"""
assert old in s; s = s.replace(old, new, 1)
open(p, 'w', encoding='utf-8', newline='\n').write(s)
print('logged')
