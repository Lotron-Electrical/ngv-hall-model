# 2026-09-09: the re-gated models were built on unrefined poses. Diagnosis right, export wrong.
PLAN = 'E:/sitecapture-captures/ngv-site/agent-ref-walls/PLAN-20260908-walls.md'
entry = """- 2026-09-09, THE RE-GATED MODELS WERE VOID, and the pose census is what caught it. The diagnosis behind
  them stands: the acceptance gate in register_day4k.py was written for floor walks and threw away two
  thirds of Lloyd's balcony footage for reasons unrelated to pose quality. The EXPORT was wrong.
  tools/regate_export.py built the wider sets by subsetting work/reg-<prefix>. That directory is the
  register's RAW output, written a minute before the accepted model, and it is not what the per-frame
  reports describe. Measured three ways:
    the 25 strict b3 frames, read from model-b3-accepted, match their own report to 45 mm
    the same 25 frames, read from reg-b3, disagree with the report by a median of 0.295 m, max 10.90 m
    the frames the re-gate added disagree by a median of 0.216 m, max 15.21 m
  So the disagreement is not a property of the added frames; reg-b3 simply is not the refined model. The
  re-gated model built from it carried camera heights from -5.62 m to +12.68 m, below the floor and above
  the roof, and tools/corridor_poses.py reported a camera 11.08 m NORTH of the wall, which is what made it
  visible. Reading it through the measurement path (underside_geom) gave the same wild values, so it was
  the poses and not the reader.
  EVERYTHING MEASURED THROUGH THOSE MODELS IS VOID, including the two results that came out of them:
    the head 11.10 appearing to settle across six captures within 10 mm
    the east parapet appearing NOT to be measured, which looked like it overturned upstands.east 0.77
  Neither may be quoted, and the east upstand is NOT altered on that basis. The strict results are
  untouched by this; they never went near reg-*.
  THE RIGHT WAY, now implemented in register_day4k.py itself so the extra frames get the same refinement
  the accepted ones did: two opt-in flags, both defaulting to the old behaviour.
    --standing-floors  the floors a person may be standing on, a camera accepted 1.10 to 1.90 m above one.
                       The default keeps the old two bands. The lower balcony, floor 6.33, had none, so a
                       phone held there near h 7.5-8.1 fell between the bands and was refused by
                       construction: every lower-balcony frame in the archive was discarded unseen.
    --pan-tolerant     replaces the max-walking-speed continuity chain with an outlier test against the
                       robust local median of the frames within two seconds. The chain suits a continuous
                       walk; on a balcony the operator stands still and pans, and once frames are refused
                       it jumps between survivors so standing motion reads as impossible speed. It refused
                       83 of b1's 142 otherwise-good frames.
  Re-running the four clips with --skip-match costs about a minute each, because the features and matches
  are already in the database. The re-gated artefacts have been removed so nothing can measure with them.
"""
s = open(PLAN, encoding='utf-8').read()
if 'THE RE-GATED MODELS WERE VOID' not in s:
    open(PLAN, 'a', encoding='utf-8', newline='\n').write(entry)
print('logged')
