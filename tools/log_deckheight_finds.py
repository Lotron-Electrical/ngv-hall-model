# 2026-09-09: logs what the registered balcony cameras' own positions say about the decks and the corridor floor,
# and the west-end reading from b3 that stays inconclusive.
PLAN = 'E:/sitecapture-captures/ngv-site/agent-ref-walls/PLAN-20260908-walls.md'
entry = """- 2026-09-09 late, the decks from the cameras themselves (the register's accepted poses are measurements of
  where Lloyd stood): b3 (clip 153332) stands on the EAST top gallery's edge, u 48.12-48.40, d 4.1-7.2, h
  9.70-10.14: 0.06-0.35 m east of the end face (48.056), 1.36-1.80 m above the top floor 8.34, above the glass
  top 9.40, a phone held over the balustrade. b1 (clip 154400) stands IN north opening 5 (u 19.1-19.6, d -0.36
  to +0.09) at h 9.17-9.80: 0.83-1.46 m above 8.34, a phone at chest height and dipped, so the floor of the
  gallery behind the wall IS the second floor 8.34 at that opening (the corridor floor in WALLF), and the
  opening's sill 8.99 is 0.65 above it (a low sill one leans over, as the b7 frames show). Both agree with ENDW
  and WALLF as built; nothing to change.
- 2026-09-09 late, the west end read from b3 across 44 m (b3_000100 and b3_000034, the end face plane
  u 4.194): the lit top-gallery band's TOP sits on h 12.9-13.0 in both (the sim's back wall runs to 13.5
  behind the canopy's edge; the canopy's dark edge covers the rest, so no disagreement); its BOTTOM reads
  h 9.4 in b3_000100 (the glass 8.9-9.4 dark from there) and h 8.4 in b3_000034 (the glass showing the lit
  interior). Half a metre apart between two frames of one clip 44 m away, so the two poses disagree by about
  0.6 deg or the glass reflects differently from d 5.4 and d 4.1: inconclusive, the balustrade stays as the
  2026-09-09 morning reading (0.56 upstand, glass to 9.40). The lower tier's four fittings read h 8.0 in both
  (the sim's 7.8-8.0 west fittings). Grids b3_034-west-grid.jpg, b3_100-west-grid.jpg.
"""
s = open(PLAN, encoding='utf-8').read()
if 'the decks from the cameras themselves' not in s:
    open(PLAN, 'a', encoding='utf-8', newline='\n').write(entry)
print('logged')
