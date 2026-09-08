# AGENTS.md: the pose-matched check of the ends and the glazing (string patch, 2026-09-08).
p = 'AGENTS.md'
s = open(p, encoding='utf-8').read()
anchor = '- TAPESTRIES (2026-09-08): all four identified by NCC'
new = '''- POSE-MATCHED PROOF (2026-09-08): tools/pose_of.py reads a posed frame's hall-frame pose (u, d, h,
  forward, pitch, vertical fov) and tools/pose-shot.mjs puts the sim's camera on it (install mode,
  the stage immersive, collision off, the eye on the frame's height through player.eye, the fov
  through fx.baseFov), so the render and the photograph sit side by side with the same framing
  (shots/pose-d4_000049-pair*.jpg). Read against the 4K west-end frame d4_000049: the three tiers,
  the top doorway and the north wall's three far openings line up; the balustrades had read as
  solid dark bands where the frame shows people through glass under a thin rail, so gallery-rail
  went from 0.62 to 0.28 opaque with a solid 60 mm handrail on top; the built stone quads (the end
  walls, the wall extensions past the scan) carried a white bake so the recess mask read them a
  third brighter than the scan's wall (117 against 90 in the same shot), now a 13/255 bake, the
  scan's own level. The pale vertical band right of the far end in that view is the glazing's fin
  sides seen through the panes six degrees off the wall (tools/pose-find.mjs bisects the scene per
  mesh to name what paints a pixel); Lloyd's daylight photo lloyd-02 shows the fins pale from
  inside, so they stay, and the panes got a Fresnel term (Schlick, F0 0.04) so glass seen edge-on
  mirrors the hall instead of showing the court. tools/pose-pick.mjs raycasts a pixel and lists the
  meshes near a hall-frame box.
'''
assert anchor in s and 'POSE-MATCHED PROOF' not in s
s = s.replace(anchor, new + anchor)
open(p, 'w', encoding='utf-8', newline='\n').write(s)
q = 'E:/sitecapture-captures/ngv-site/agent-ref-walls/PLAN-20260908-walls.md'
t = open(q, encoding='utf-8').read()
t += ('- 2026-09-08 15:30 pose-matched check (tools/pose_of.py, pose-shot.mjs, pose-pick.mjs, pose-find.mjs): sim on\n'
      '  the d4_000049 pose beside the frame. Tiers/doorway/openings line up. Fixed: balustrade 0.28 opaque + 60 mm\n'
      '  handrail; built stone quads carry a 13/255 bake (were white, a third too bright); glass Fresnel (F0 0.04).\n'
      '  The pale band by the far end is the fin sides through the panes (pose-find), as lloyd-02 shows them.\n')
open(q, 'w', encoding='utf-8', newline='\n').write(t)
print('ok')
