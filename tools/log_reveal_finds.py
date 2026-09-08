# 2026-09-09: logs the reveal cut and the pose-pair tool fixes in the PLAN.
PLAN = 'E:/sitecapture-captures/ngv-site/agent-ref-walls/PLAN-20260908-walls.md'
entry = """- 2026-09-09 night, the north openings from inside (b1_000105, the camera IN the opening u 18.63-19.88, d 0.03,
  h 9.77, 0.28 m from its east reveal): the real frame has the pale stone reveal beside the lens; the sim had a
  flat brown slab. pose-shot PICK named it: the GLB's own reveal faces inside the opening (not long-wall faces,
  d -1.0..-0.1), dark in the bake, crushed by the wall shader's recess gate to near black. The built
  'opening-reveal' quads stand in the same place, so those scan faces are discarded in the openings' band
  (h 8.89-11.45, d -1.2..0.05; tools/patch_reveal_cut.py, live 5166f74). Proof reveal-fix.jpg. Tool fixes on
  the way: the page renders 1080 wide at most, so a 4K frame's sim came out half-width and every 4K pair was
  clipped (pose_pair / chain_shot now halve W,H until they fit); PICK=x,y;... in pose-shot names the mesh under
  a pixel; tools/canvas-probe.mjs measures the canvas against the stage.
"""
s = open(PLAN, encoding='utf-8').read()
if 'the north openings from inside (b1_000105' not in s:
    open(PLAN, 'a', encoding='utf-8', newline='\n').write(entry)
print('logged')
