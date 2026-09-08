# 2026-09-09: logs the west top gallery's doorway panel and exit light (ENDW.westTopPanel/westTopExit) in the walls plan and AGENTS.md.
PLAN = 'E:/sitecapture-captures/ngv-site/agent-ref-walls/PLAN-20260908-walls.md'
entry = """- 2026-09-09 the west top gallery's south doorway, re-read in the 4K frame d4_000049 (east deck, 45 m off, 44 px/m;
  tools/frame_pixel.py, new: a register frame's pixel met with a u, d or h plane, PINHOLE or OPENCV). On the back
  wall (u 0.4): a PALE panel d 12.4-15.3 (2.9 m) from the parapet line up to the head, 1.25x the back wall's tone
  (RGB 205/190/153 against 157/137/98 for the stone), with a DARKER door opening in it d 13.35-14.15 (155/117/79,
  people standing in it), and a green exit light over the door (215/221/217, d 13.3-13.85). The old build had a
  single bright 0.8 m slot: the tones were the wrong way round. Built: ENDW.westTopPanel [12.4, 15.3] (panelMat
  day 0xac9478), westTopDoor [13.35, 14.15] (topDoorMat, 0.95x the stone), westTopExit [13.3, 13.85] under the head
  (patch_westdoor.py). Open: the sign meets the u 0.4 plane on h 11.07 and the panel's top on 10.62-10.71, and the
  frame sees stone on the back wall up to h 11.7 over the sign, which a 10.65 front head should hide from a camera
  on h 9.79 and 45 m off (its ray passes the front on 10.97); either the top gallery's ceiling is higher behind a
  lower front fascia, or the register's tilt is off by the 0.4 degrees that would move a 45 m point 0.3 m. Kept.
  Pair wdoor-d49-pair.jpg.
"""
if 're-read in the 4K frame d4_000049' not in open(PLAN, encoding='utf-8').read():
    open(PLAN, 'a', encoding='utf-8', newline='\n').write(entry)
p = 'AGENTS.md'; s = open(p, encoding='utf-8').read()
old = "it; its tier heights are unmeasured). OPEN: the install sim's corridor door (buildDoor, the"
new = ("it; its tier heights are unmeasured). The west top gallery's south doorway (4K d4_000049, 45 m off):\n"
       "  a pale panel d 12.4-15.3 from the parapet to the head round a darker door d 13.35-14.15 with a green\n"
       "  exit light over it (`ENDW.westTopPanel/westTopDoor/westTopExit`, 2026-09-09); the sign meets the back\n"
       "  wall on h 11.07, above the 10.65 head, so the gallery ceiling may be higher behind a lower front\n"
       "  fascia (or the register's tilt is 0.4 degrees off), unresolved. OPEN: the install sim's corridor door (buildDoor, the")
assert old in s, 'anchor'; s = s.replace(old, new, 1)
open(p, 'w', encoding='utf-8', newline='\n').write(s)
print('logged')
