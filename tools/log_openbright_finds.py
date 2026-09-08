# 2026-09-09: what the floor imagery CAN say about the room behind the north wall (how bright it reads
# through the openings), and a warning about what the interior clip cannot yet be said to show.
PLAN = 'E:/sitecapture-captures/ngv-site/agent-ref-walls/PLAN-20260908-walls.md'
entry = """- 2026-09-09, the openings' own brightness, measured. New tools: tools/opening_bright.py (every posed
  frame that sees a whole opening: the mean grey inside the opening rectangle over the mean grey of the
  stone control band right under its sill, h 7.55-8.85, same frame so the same exposure; a pair is
  dropped when either band clips or the control sits in the dark), tools/opening_stats.py (the same test
  on one frame beside a sim render taken from that frame's pose), tools/sim_openings.py (the sim side
  done through the SIM's own camera, because projecting the photograph's camera onto the render
  mis-places the quad by tens of pixels wherever the pitch is steep and the yaw goes unstable),
  tools/openmatch.sh and openmatch2.sh (the batch), tools/names-dump.mjs (the built scene's mesh names,
  so a shot can hide a whole subsystem), tools/db_clear_prefix.py (drop one frame prefix out of the
  COLMAP database so a killed register can run again instead of dying on "constraint failed").
  THE REAL HALL, 190 usable frame/opening pairs over 137 walk frames:
    opening / wall brightness ratio  median 0.75  (p25 0.67, p75 0.92)
    contrast inside the opening      median 31 levels p95-p5, against the stone control's 35: ratio 0.99
  So through a real opening the room reads about a quarter darker than the stone beside it and carries as
  much tonal variation as that stone does. It is not a black hole and it is not featureless.
  THE SIM over nine of those same poses, the install's rig and tapestries hidden, measured through its own
  camera: ratios 0.50, 0.67, 0.71, 0.83, 1.25, 1.47, 1.48, 1.54, 1.70 (median 1.25). That scatter is the
  measurement failing, not the model: the sim's own control band reads a median 3 of 255 in two of those
  views, so the denominator is meaningless there. NOTHING IS CHANGED ON IT. The one firm number is the
  real hall's 0.75 with contrast 0.99, recorded here as the target any future corridor tone has to hit.
  Seen from the hall the built room still reads as a flat brown panel: with the plan's 2.0 m the back wall
  fills every opening edge to edge, so there is no depth in it to see. That is a consequence of the width.
- 2026-09-09, A WARNING ABOUT CLIP 153148 AND THE 13.55 CEILING. Five independent attempts to measure the
  room's width from the interior frames (the opening rectangle as a ruler, the 0.306 m stone courses, human
  scale, the canopy module, the vitrines) EVERY ONE returned no number. Worse, they disagree about where
  the camera is standing: four read it as inside the room behind the north wall, one reads it as standing
  on the hall side of that wall, and both readings fit the pixels. Every frame shows the canopy sweeping
  directly overhead with no flat ceiling, which cannot happen from inside the room if the north wall runs
  solid from the opening heads (11.35) up to the canopy (13.55). So one of three things is true: the clip
  is not in that room, or the canopy also roofs that room, or the wall does not reach 13.55 along there.
  The corridor.ceil 13.55 committed earlier today rests on the second reading and is therefore NOT settled.
  What the frames do give, solid: the canopy lands straight on coursed ashlar with no beam, frieze or
  cornice between glass and stone; one round unfluted shaft rises to that junction standing in front of a
  single continuous wall plane, not in a corner (the course angle is the same either side of it); the
  hall-side edge of the walked space is a broad flat coping with no pier, jamb or 0.9 m reveal anywhere
  along a 700 px unbroken run, which is the strongest argument that the edge is not the punched north wall
  seen from inside; the vitrines are free-standing frameless cases on white plinths standing off the wall;
  clear walking floor beside a plinth measures 0.95 m in g1320, at that one depth only. Ratios that will
  become metres once the poses land: plinth height = 0.42 x camera eye height; coping band width = 0.50 x
  (eye height minus coping height).
  The b6g register (b6 frames 1000-1340) is re-running under the new hardware broker after a peer's
  governor test reaped the first attempt and left half-written matches behind. It settles WHERE the clip
  was shot before it settles anything the clip appears to show.
"""
s = open(PLAN, encoding='utf-8').read()
if "the openings' own brightness, measured" not in s:
    open(PLAN, 'a', encoding='utf-8', newline='\n').write(entry)
print('logged')
