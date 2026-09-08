# 2026-09-09: logs the review of the two long balcony clips (Lloyd: "those videos need to be reviewed more", "those
# videos are up on the balcony") and the new register order.
PLAN = 'E:/sitecapture-captures/ngv-site/agent-ref-walls/PLAN-20260908-walls.md'
entry = """- 2026-09-09 night, the two long clips reviewed frame by frame (tools/balcony2_sheet.py, contact sheets
  b7-sheet-*.jpg and b6-sheet-*.jpg in shots/pose; Lloyd: "those videos need to be reviewed more, 154940, 153148;
  those videos are up on the balcony"):
  b7 = 20260809_154940 (82 s, 1224 frames extracted): shot from the NORTH balcony's top deck, walking along it.
    Frames 0-60 open on a glasses case on the balustrade cap (the cap and its glass top, usable for the rail
    height), then the hall looking down and along it both ways (the whole south wall with the painting, the south
    glazing, the columns, the truss, the east and west ends with their galleries), the canopy straight up from
    under it (256-416, 736-832: ribs and panes in 4K, the closest canopy frames we have), the north balcony
    itself (the openings' reveals passing by, the stone piers between them, the balustrade in the foreground).
    The best balcony source so far: every frame sees the hall from the deck, few people in the way.
  b6 = 20260809_153148 (178 s, 2666 frames): the same north balcony, darker exposure. Frames 88-1012 and
    1331-2651 have Lloyd's own phone in the frame (the ARCore room-scan app, its screen showing the hall) held
    up in front of the lens: the phone hides the middle of the view and its screen is a moving picture in the
    picture, bad for SIFT matching, so those stretches will register weakly and any pose accepted there needs
    a look. Frames 1056-1330 are the ones that matter: the GALLERY behind the north wall from inside (vitrines
    against its outer wall, urns, people, the openings seen from behind, the stained-glass canopy overhead
    running to the outer wall, the stone of the piers), plus the canopy close up (1100-1188). The thinned b6s
    set keeps every 2nd frame through 1000-1320 and every 6th elsewhere.
  Register order changed: the first queue (b3 b4 b5 b7s b6s) ended after b3's report (25 accepted of 176,
  heights 9.51-10.19) and queue2.sh runs b6s FIRST, then b4 b5 b7s. The b4 extraction the old queue had begun
  went with it (its log ends 21:47).
"""
s = open(PLAN, encoding='utf-8').read()
if 'the two long clips reviewed frame by frame' not in s:
    open(PLAN, 'a', encoding='utf-8', newline='\n').write(entry)
print('logged')
