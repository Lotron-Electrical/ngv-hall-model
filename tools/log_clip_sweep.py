"""EVERY UNEXAMINED STRETCH OF THE BALCONY CLIPS, LOOKED THROUGH FOR THE CORRIDOR (2026-09-10).

Lloyd: "You need to look through them thoroughly." The goal names the corridor behind the brick wall, and no
posed frame faces it. This is the record of looking through the parts of the five balcony clips that no
tool had used, by contact sheet (every 4th to 40th frame) and then at full resolution where a sheet
suggested something. The clips (balcony2/map.txt): b1 287 frames, b3 176, b4 343, b5 287, b6 2666, b7 1224.

WHAT WAS FOUND, CLIP BY CLIP.
  b1 0 to 28: the phone rests on the SILL of north opening 5 (the posed frames 53 to 206 stand in that
     opening); the sill top is dark rough stone with a light hall-side arris, the phone case sits on it, a
     dark vertical bar on the left is the reveal's jamb, and the hall floor and the lighting truss are seen
     over the arris. 28 to 52: the camera lifts off the sill and looks east along the hall. 207 to 286:
     across the hall at the south wall and up at the ceiling. The camera never turns into the corridor.
  b5 (unposed, 287 frames): shot from a north-wall opening near the WEST end (the foyer's glass wall and
     yellow objects near in frames 0 to 24 and 108 to 132); pans over the ceiling, the east gallery and the
     floor. Never into the corridor.
  b6 0 to 1000 and 1340 to 2666: the east deck looking west with a SECOND PHONE held in the frame running a
     room-scan app; 1040 and 1340 are inside the east gallery facing north toward its door. Nothing new.
  b7 300 to 370: the WEST gallery's back wall, light ashlar (not bluestone): two dark rectangular vents
     high on the wall, a dark rectangular niche or doorway at mid height below them, two glass vitrines
     against the wall, and the round stone column rising to the canopy where the wall turns a corner. None
     of it is drawn; all of it is unposed, so it waits for poses or goes in by eye, labelled.
  b7 920 to 1224 (unposed): a walk NORTH along the west deck facing east; by 1140 the north-1 tapestry is
     close on the right and by 1200 the first north openings are seen from a metre or two, obliquely, their
     reveals as lit strips beside dark slots. THIS IS THE CLOSEST VIEW OF ANY OPENING IN THE DATASET and the
     registration target for the reveal depth (openDepth 0.90, with soffit hints 0.92 and 1.26); the frames
     chain from the posed 920. Not run today: the token window stood on 95% at the moment of choosing.
  b6 1248 and 1320, the door at full resolution: people stand across the door's lower half in both, so
     whether the east ledge stops short of the door or runs into it (as the file draws it, listed open)
     cannot be read from them.

WHAT THIS MEANS FOR THE CORRIDOR. No frame in the six clips enters it or looks along it. What the file
draws there rests, as before, on the openings, the east gallery's north door, the lamps seen through the
openings, and the b1 and b3 camera heights. The next measurement that can touch it is the b7 tail, posed.

Run:
  python tools/log_clip_sweep.py
"""
import re, sys, os

FOUND = {
    'b1 0-28': 'the sill of north opening 5 from the corridor side, the phone case on it; never into the corridor',
    'b5': 'from a north opening near the west end; ceiling, east gallery, floor; never into the corridor',
    'b6 0-1000, 1340-2666': 'the east deck looking west with a second phone in the frame; nothing new',
    'b7 300-370': 'the west back wall: light ashlar, two vents, a mid-height niche, two vitrines, the column; unposed, undrawn',
    'b7 920-1224': 'a walk north along the west deck; the first north openings from a metre or two; the registration target',
    'b6 1248/1320 door': 'people across the lower half; the ledge-into-door question stays open',
}

if __name__ == '__main__':
    for k, v in FOUND.items(): print('%-24s %s' % (k, v))
    src = open(os.path.join(os.path.dirname(__file__), '..', 'index.html'), encoding='utf-8').read()
    print('index.html carries the sweep:', 'EVERY UNEXAMINED STRETCH OF THE BALCONY CLIPS' in src)
