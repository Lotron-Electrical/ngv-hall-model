# 2026-09-09: logs the ends-in-numbers audit re-run on the current build, and the new balcony/gallery clips' pipeline.
PLAN = 'E:/sitecapture-captures/ngv-site/agent-ref-walls/PLAN-20260908-walls.md'
entry = """- 2026-09-09 the ends re-audited in numbers on the build after the head 11.1 / front soffit / doorway panel /
  fittings / lower tier changes (end_residual.py on six fresh pose pairs: east w1_000356, w1_000404, w5_000240;
  west w2_000252, w1_000028, d4_000049). East: 9 sim steps matched, residual mean -0.10 m, median -0.15, |median|
  0.30, 90% within 0.45. West: 9 matched, mean 0.00, median +0.10, |median| 0.20, 90% within 0.41. The 2026-09-08
  audit read east 11 / 0.00 / 0.30 / 0.45 and west 11 / 0.00 / 0.20 / 0.35: no bias appeared, the scatter is
  unchanged; two fewer matches a side because the frames' soft steps meet fewer hard sim steps now that the
  lit soffit band is dark.
- 2026-09-09 evening: Lloyd shot SEVEN new 4K clips on 9 Aug from the balconies and the gallery behind the north
  wall and put them in a Drive folder (1kYG16GIPXStOqRqi58qabPqkCUF0PxUM). Pulled to ngv-video/balcony2/src,
  mapped by map.txt (b1 154400 19 s, b3 153332 12 s, b4 153739 23 s, b5 154129 19 s, b6 153148 178 s, b7 154940
  82 s; 153237 is the day4k clip already registered), every 2nd frame extracted as 2160x3840 PNG
  (balcony2_extract.py), the two long clips thinned for the register (balcony2_subset.py: b6s 552 frames, every
  6th plus every 2nd through the gallery stretch 1000-1320; b7s 306). What they show (balcony2_montage.py,
  balcony2_strip.py): b1, b3, b4, b5, b7 from the top decks and along the balconies, both ends and the opposite
  balconies in view; b6 walks INTO the gallery behind the north wall (frames 1040-1300): a long room with
  vitrines against its outer wall, people two abreast, the openings seen from inside with the hall through them,
  and the STAINED GLASS CANOPY OVERHEAD, continuous with the hall's, sloping down to the outer wall: the
  gallery has no ceiling of its own, its roof is the canopy. The 11.4 "corridor ceiling" measured from the
  lamp seen through the opening was a spotlight on the canopy's steel. To be measured once the frames are posed.
  Register: balcony2-register (a copy of the day4k workspace), register_day4k.py then lift_day4k.py per clip
  with the day4k camera frozen (SIFT on a 4K frame costs 7 s; a clip's matching against 486 keyframes about
  an hour), b1 first, then b3 b4 b5 b7s b6s queued. Tools made class-aware for the new clips: underside_geom
  CLASSES b1/b3/b4/b5/b6s/b7s (with a "frames" dir), chain_pose2.py (any class, forwards or --back),
  chain_pixel / chain_shot / chain_project read the chain's class.
"""
if 'the ends re-audited in numbers on the build after the head 11.1' not in open(PLAN, encoding='utf-8').read():
    open(PLAN, 'a', encoding='utf-8', newline='\n').write(entry)
print('logged')
