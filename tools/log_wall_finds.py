# 2026-09-09: the north wall's openings measured sideways against two captures, and clip 153148 located.
PLAN = 'E:/sitecapture-captures/ngv-site/agent-ref-walls/PLAN-20260908-walls.md'
entry = """- 2026-09-09, WHERE CLIP 153148 WAS SHOT, settled. The b6g register (frames 1000-1340, every 2nd, run under
  the hardware broker) accepted 6 of 171; the rest were refused on 7-9 inliers. Those six are enough for the
  one question that mattered. All six stand at u 49.13-49.38, d 13.40-13.70, h 9.57-9.79, looking due west
  along the hall (tools/b6g_where.py, and b6g is now a class in tools/underside_geom.py). That is the EAST
  UPPER BALCONY at its south side, about 1.25 m of eye height above the 8.34 deck, and it is east of the end
  face 48.056 and hard against the south wall's side of the room. It is NOT behind the north wall.
  Consequence: this morning's corridor.ceil 11.4 -> 13.55 was argued from the canopy sweeping overhead in
  every frame of that clip. That canopy is the hall's own, seen from the hall's own gallery. The change has
  been reverted; C.ceil is 11.4 again, which at least rests on a downlight seen THROUGH an opening in the
  posed 4K frame d4_000120, and it is still an inference from one lamp and still unmeasured. The 2.0 width
  is likewise still the 1968 plan and still unmeasured.
  What the clip DOES describe, well, is the upper gallery: glass vitrines of Greek urns on white plinths
  standing off the wall, a broad flat coping with no pier or jamb along a 700 px run, an ashlar back wall
  with dark display niches, round unfluted columns rising to the canopy, spotlights on the canopy steel.
  Those observations belong to the balcony build, not to the room behind the brick wall.
- 2026-09-09, THE NORTH WALL'S OPENINGS, measured sideways. New tools/wall_edges.py: the companion to
  end_levels.py, but each opening's two jambs are vertical lines on the wall face so the search runs across
  the hall and the offset is reported along u. Same protections: a window in metres that never reaches
  halfway to the other jamb, frames ranked by sharpness, and a joint least-squares fit that solves one
  shared wall-face-depth term against a per-jamb offset, because a face at the wrong d displaces a jamb by
  an amount proportional to the tangent of the camera's angle off the wall normal while a jamb in the wrong
  place along the hall does not care. THE FACE IS FINE: the fitted depth term is -0.026 m on the day walk
  and +0.107 m at night, and forcing it to zero moves the residual rms by 0.003 and 0.004 m. So d -0.09 stays.
  THE JAMBS ARE NOT. Openings 7, 8 and 9 read consistently west of where the model drew them, in BOTH the
  day walk and the night capture, with tight quartiles:
    opening  7   walk -0.149 / -0.186    night -0.115 / -0.150
    opening  8   walk -0.110 / -0.162    night -0.075 / -0.098
    opening  9   walk  0.000 / -0.230    night -0.169 / -0.213
  and every opening measured narrower than the drawn 1.256: median width 1.219 (walk, 11 openings) and
  1.208 (night, 9). Applied: the twelve openings keep their drawn centres but take the measured width 1.213,
  and openings 7, 8, 9 move bodily west by 0.132/0.168, 0.093/0.130 and 0.188/0.195. After the change the
  residuals on those three straddle zero and none exceeds 0.075 m; opening 9 reads exactly 0.000 on both
  jambs at night with quartiles inside 0.036 m. NOT applied: openings 0-3 and 4-6, where only one capture
  has frames or the two disagree in sign (walk sees 4-6 at +0.04 to +0.13 and night has no frames there;
  night sees 0-3 and walk has three to five frames). Those wait for a capture that covers them.
"""
s = open(PLAN, encoding='utf-8').read()
if 'WHERE CLIP 153148 WAS SHOT, settled' not in s:
    open(PLAN, 'a', encoding='utf-8', newline='\n').write(entry)
print('logged')
