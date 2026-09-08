# 2026-09-09: the balconies measured, and the upper parapet corrected on that measurement.
PLAN = 'E:/sitecapture-captures/ngv-site/agent-ref-walls/PLAN-20260908-walls.md'
entry = """- 2026-09-09, THE BALCONIES. First, why they were never checkable against the reconstruction: new
  tools/scan-coverage.mjs maps where the loaded scan actually has surface, and the answer is that it has
  almost none at the ends. Along the hall in 2 m bins the scan carries 18,156 / 18,290 / 16,208 / 13,869 /
  17,762 / 17,493 vertices in the middle bands and 115-669 in every bin past u 46 or below u 5. The
  balconies were built from photographs, the 1968 plans and the posed frames, and only posed frames can
  test them. tools/balcony-probe.mjs and tools/scan-extent.mjs were the attempts that established it.
- New instrument: tools/end_levels.py. Every balcony level is a long horizontal edge across the end face,
  so it projects the level's line into every posed frame that sees it, walks a profile across the line in
  the image, and takes the strongest brightness gradient as the real edge. Three things make it honest:
  the search window is in METRES and never reaches halfway to the next modelled level (run wide, the deck
  8.34, the slab soffit 8.08 and the parapet top all report the SAME edge, because from the floor the deck
  and soffit are hidden behind the parapet and only its top is ever in view); the frames are ranked by
  sharpness so motion blur cannot manufacture an offset; and the per-frame offsets are split by camera
  distance, because a wrong FACE position produces an offset that halves as the camera doubles its
  distance while a wrong HEIGHT does not care where the camera stands. tools/end_levels_draw.py draws the
  model's lines and the found edges on the frame. tools/parapet-check.mjs reads the built result back.
  WHAT IT FOUND, on the upper balcony's parapet top, which the model drew as 8.34 + 0.56 = 8.90:
    walk, east end    +0.157 m   22 sharpest frames, p25 +0.147 p75 +0.173, flat 22 m to 43 m
    night, east end   +0.114 m   17 frames, p25 +0.069 p75 +0.138, flat 20 m to 26 m
    walk, west end    +0.078 m   25 sharpest frames, p25 +0.055 p75 +0.098, flat 17 m to 31 m
  Two captures on different nights with different cameras agree in sign and size at the east end, and the
  offset is flat with distance, which rules out the end face standing somewhere else (that would have read
  +0.31 near and +0.16 far). So ENDW.upstand goes 0.56 -> 0.68. After the change the three residuals are
  +0.073, +0.070, -0.046: halved, and no longer sharing a sign, which is what removing a systematic looks
  like. A per-end split (west 0.64, east 0.70) sits inside the spread between the two east numbers and was
  not adopted. The deck stays 8.34: b1 and b3 stand on it with the eye 9.17-10.14, a person's height above
  8.34 and no other.
  NOT CHANGED, recorded: the night frames alone put the LOWER parapet top 0.139 m below its drawn 6.85
  (14 frames, p25 -0.154 p75 -0.120), so lowUpstand may be nearer 0.38 than 0.52. The walk class cannot
  see that edge at all from the floor at either end, so there is no second capture to confirm it and it
  stays as drawn. The end-wall top 13.50 reads within 0.05 m of its drawn line at both ends but is
  insensitive to everything and arbitrates nothing. The head 11.10 varies with camera distance and is the
  one level that still looks like a face-position question rather than a height.
"""
s = open(PLAN, encoding='utf-8').read()
if 'THE BALCONIES. First, why they were never checkable' not in s:
    open(PLAN, 'a', encoding='utf-8', newline='\n').write(entry)
print('logged')
