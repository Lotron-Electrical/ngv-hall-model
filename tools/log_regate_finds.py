# 2026-09-09: Lloyd asked whether the balconies were got properly from the clips he supplied. They were not.
PLAN = 'E:/sitecapture-captures/ngv-site/agent-ref-walls/PLAN-20260908-walls.md'
entry = """- 2026-09-09, THE BALCONY FOOTAGE WAS NEVER PROPERLY USED. Lloyd: "I gave some specific video references
  for you yesterday that has clips from standing on each of the balconies and looking around." He is right.
  Six clips were supplied (balcony2/map.txt): b6 153148, b3 153332, b4 153739, b5 154129, b1 154400,
  b7 154940, 5,246 extracted frames between them. Before today they had produced 102 usable frames.
  WHERE THEY WENT. It is not the footage. Of 940 frames offered across the four clips that were attempted,
  803 SOLVED A POSE and only 102 survived the acceptance gate in register_day4k.py. Three faults:
    1. INLIERS >= 30. These clips look across 15-40 m of hall to a wall where the site reconstruction is
       sparse, so a good balcony pose carries 12-25 inliers where a floor walk carries hundreds. Median
       registered inliers: b3 21, b6g 14, b7s 12. The cut refuses the MEDIAN FRAME of three of four clips.
    2. NO STANDING BAND FOR THE LOWER BALCONY. A frame is refused unless the camera sits 0.8-2.3 m (hall
       floor) or 8.73-10.23 m (upper deck). The lower balcony floor is 6.33, so a phone there sits near
       7.5-8.1 m, between the bands, refused by construction. Every lower-balcony frame was discarded
       before it was ever looked at.
    3. THE CONTINUITY RULE, the biggest single loss and wrong in principle here. It refuses a frame whose
       implied speed from its neighbour exceeds a walking speed. That suits a person walking the floor with
       every frame tracked; on a balcony the operator stands still and pans, and once frames are refused
       the chain jumps between survivors so ordinary standing motion reads as impossible speed. It killed
       83 of b1's 142 otherwise-good frames.
  THE FIX, tools/regate.py: re-gate from the stored per-frame reports, which already carry every registered
  frame's inliers, rms, camera height and camera centre. Nothing is re-registered and no COLMAP time is
  spent. Inliers >= 15, standing bands for all three floors (hall 0, lower 6.33, upper 8.34) covering
  floor+1.10 to floor+1.90, and the continuity chain replaced by a robust local-median outlier test that
  tolerates a stationary operator. Result 296 frames against 102. tools/regate_export.py writes them as
  model-<t>-regated and they are exposed as classes b1r/b3r/b6gr/b7sr in tools/underside_geom.py, kept
  ALONGSIDE the strict ones so the two can be compared rather than swapped blindly.
  THE STRICT SETS WERE BIASED, not merely small. b1's 59 strict frames span clip positions 53-206 of 250
  solved; the 69 the re-gate adds span 6-286, and their median inlier count is 163 against the strict set's
  120. The excluded frames were BETTER conditioned. They were dropped by the continuity chain and the
  bands, not by weak geometry.
  WHAT IT CHANGES. Measured against the same drawn value with the same instrument (end_levels.py hardcoded
  9.02 for both ends at the time, and LEVELS_SET was not set in either run, so the comparison is clean):
    head 11.10        strict: captures disagree by 128 mm, NOT MEASURED
                      re-gated: 6 captures, median -0.010, range 0.074, SETTLED WITHIN 10 mm
    east parapet 9.02 strict: b1 +0.107(25), b7s +0.119(6), night +0.057(25), walk +0.073(25)
                              median +0.090, range 0.061  -> the basis for upstands.east 0.77 (55af327)
                      re-gated: b1r +0.021(44), b6gr -0.061(8), b7sr +0.126(27), night +0.057, walk +0.073
                              median +0.057, range 0.186  -> CAPTURES DISAGREE, NOT MEASURED
  The two floor walks are identical in both runs; only the balcony clips moved, and b1 moved most: +0.107
  from a 25-frame middle slice became +0.021 from 44 frames spanning the whole clip. The east upstand
  change therefore rests on a biased subset and is under challenge. Verdict pending an adversarial check.
  ALSO FOUND. b4 (343 frames) and b5 (287) had never registered at all: b4 died on "database is locked" on
  2026-09-08 and again today on "3 cameras for the bundle", because the failed attempts left its images
  split across camera 33 (15 images), 35 (109) and 40 (219). tools/db_clear_prefix.py is the repair.
  b5 is clean (one camera, 287 images) and is matching. b6s, the 552-frame WHOLE-CLIP sample of the longest
  clip (153148, 177 s), has never registered either: colmap's matcher exited 0xC0000142 on 2026-09-08.
  b6g, the only part of that clip ever registered, is a 340-frame WINDOW (frames 1000-1340), which is why
  it only ever found the east balcony. queue10.sh retries b6s with the frozen day4k camera.
  AND A DEFECT THIS INTRODUCED. Once ENDW gained a per-end upstand, end_levels.py went on searching around
  9.02 for BOTH ends while the model drew the east parapet as 9.11. It now takes its parapet height from
  the end under test. Any measurement taken after that change is not directly comparable with one taken
  before it, which is the follow-bias trap again and is stated here so the next pass does not fall in.
"""
s = open(PLAN, encoding='utf-8').read()
if 'THE BALCONY FOOTAGE WAS NEVER PROPERLY USED' not in s:
    open(PLAN, 'a', encoding='utf-8', newline='\n').write(entry)
print('logged')
