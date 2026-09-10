"""THE EAST DECK'S NORTH CORNER: THE PARAPET AS DRAWN RUNS INTO THE NORTH DOOR (2026-09-10).

As drawn, the east gallery's parapet (face 48.056, setback solid from 48.460, coping to 48.910, all from d 0 to the
south end) meets the north wall where the gallery's north door stands (ENDW.topNorthDoor.east: u 48.158 to 49.371,
3.17 high from the deck). So the solid and coping cross the door's lower west half. A person could not walk through
the west half of that door. Either the parapet stops short of the wall (a return), or the door is narrower or
further east than measured, and only a frame that sees the corner can say which.

THIS TOOL finds every posed frame that sees the corner (the door's west jamb foot and head, the solid's north end,
all in frame and in front), ranks them by how large the corner is on the frame, and writes crops of the best with
the sim's lines drawn through the pose: the door outline (yellow), the parapet's inner top edge along d (cyan), the
coping's outer edge (magenta) and the face's top (green). The reading is then by eye against those lines, and any
number taken from it is labelled so.

THE RESULT. 85 posed frames see the corner: b5 and b5p from a north opening 24 m away, edge-on (the door's jamb
is the wall's own edge there); b1, b1p likewise from opening 5; b6s from the hall floor 30 m off; b7s and b7sp from
the west deck, 44 m across the hall, where the whole corner is 50 px. None of the 321 cameras that stand on the
east deck (b3, b3p, b6g, b6gp, day4k) looks north along it: b3 faces west from d 4 to 7.5, b6g faces west from
d 13.5, day4k faces west from d 13. The corner is not measurable from a pose. The raw b6 frames 1280 to 1328 face
the door from inside the gallery: b6_001320 shows two people walking through it abreast, so the door is clear a
metre or more, and the ledge, which as drawn would leave it 0.46 m, must stop short of the wall. Its end is read
off that frame by eye, within about a metre of the wall: ledgeStart.east 1.0 in index.html, carrying half a metre.

Run:
  python tools/deck_door_corner.py [n_crops]                         # the seers, one crop per class
  python tools/deck_door_corner.py frames day4k:d4_000079 ...        # crops of named frames
"""
import os, sys
import numpy as np
import cv2
sys.path.insert(0, os.path.dirname(__file__))
from underside_geom import load_class

O = np.array([-54.907447, -1.43545, 3.040286]); HU = np.array([0.975681, 0, 0.219196]); HD = np.array([0.219196, 0, -0.975681])
UF, US, UI = 48.056, 48.460, 48.910
FL, UPS, RAIL = 8.34, 0.755, 1.525
DOOR = (48.158, 49.371, 3.17); DN = -0.02
CLASSES = ('b3', 'b3p', 'b6g', 'b6gp', 'day4k', 'b6s', 'b1', 'b1p', 'b5', 'b5p')
SCRATCH = 'C:/Users/LLOYDG~1/AppData/Local/Temp/claude/C--Users-Lloyd-Gibbs-Claude-Projects-ngv-hall-model/7ac78459-3aa5-43ef-aae7-7d6745ece11b/scratchpad'


def W(u, d, h):
    return O + u * HU + d * HD + np.array([0, h, 0])


def poly(cam, pts, color, img, closed=False):
    x, y, z = cam.project(np.array(pts))
    if (z <= 0.3).any(): return
    p = np.stack([x, y], 1).astype(np.int32).reshape(-1, 1, 2)
    cv2.polylines(img, [p], closed, color, 2)


def crops(frames, out_name):
    """Crops of named frames (cls:stem) with the sim's lines, 2 per row, written to the scratchpad."""
    tiles = []
    for spec in frames:
        cls, stem = spec.split(':')
        cam, imgpath = load_class(cls)[stem]
        img = cv2.imread(imgpath)
        poly(cam, [W(DOOR[0], DN, FL), W(DOOR[1], DN, FL), W(DOOR[1], DN, FL + DOOR[2]), W(DOOR[0], DN, FL + DOOR[2])], (0, 255, 255), img, True)
        poly(cam, [W(US, d, FL + UPS) for d in (0, 0.5, 1, 2, 3, 4, 6, 8)], (255, 255, 0), img)
        poly(cam, [W(UI, d, FL + UPS) for d in (0, 0.5, 1, 2, 3, 4, 6, 8)], (255, 0, 255), img)
        poly(cam, [W(UF, d, FL + RAIL) for d in (0, 0.5, 1, 2, 3, 4, 6, 8)], (0, 255, 0), img)
        poly(cam, [W(US, 0, FL), W(US, 0, FL + UPS), W(UI, 0, FL + UPS), W(UI, 0, FL)], (255, 255, 0), img, True)
        pts = np.array([W(DOOR[0], DN, FL), W(DOOR[0], DN, FL + 1.0), W(US, 0.0, FL + UPS), W(UI, 0.0, FL + UPS), W(US, 1.5, FL + UPS)])
        x, y, z = cam.project(pts)
        cx, cy = float(np.mean(x)), float(np.mean(y)); r = int(max(np.ptp(x), np.ptp(y)) * 1.2) + 80
        x0, y0 = int(max(cx - r, 0)), int(max(cy - r, 0))
        crop = np.ascontiguousarray(img[y0:y0 + 2 * r, x0:x0 + 2 * r])
        crop = cv2.resize(crop, (640, 640))
        cv2.putText(crop, '%s %s' % (cls, stem), (8, 24), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 255), 2)
        tiles.append(crop)
    rows_img = [np.hstack(tiles[i:i + 2]) if i + 1 < len(tiles) else np.hstack([tiles[i], np.zeros_like(tiles[i])]) for i in range(0, len(tiles), 2)]
    out = SCRATCH + '/' + out_name
    cv2.imwrite(out, np.vstack(rows_img), [cv2.IMWRITE_JPEG_QUALITY, 88]); print('wrote', out)


def main():
    if len(sys.argv) > 2 and sys.argv[1] == 'frames':
        crops(sys.argv[2:], 'deck-door-frames.jpg'); return
    n_crops = int(sys.argv[1]) if len(sys.argv) > 1 else 6
    # the corner as the points that must be in frame: the jamb's foot and the solid's north end (the door head only
    # when it fits; a camera on the deck near the door cannot hold the head and still see the parapet's end)
    corner = np.array([W(DOOR[0], DN, FL), W(DOOR[0], DN, FL + 1.0), W(US, 0.0, FL + UPS), W(UI, 0.0, FL + UPS), W(US, 1.5, FL + UPS)])
    rows = []
    for cls in CLASSES:
        try: cams = load_class(cls)
        except Exception as e: print('%s: %s' % (cls, e)); continue
        for stem, (cam, imgpath) in cams.items():
            x, y, z = cam.project(corner)
            if (z <= 0.5).any() or (x < 20).any() or (x > cam.w - 20).any() or (y < 20).any() or (y > cam.h - 20).any(): continue
            q = cam.center - O
            size = float(np.hypot(x[1] - x[0], y[1] - y[0]))    # the jamb's height in px
            rows.append((size, cls, stem, imgpath, float(q @ HU), float(q @ HD), float(q[1])))
    rows.sort(reverse=True)
    print('%d frames see the corner' % len(rows))
    best = []
    for cls in CLASSES:
        sub = [r for r in rows if r[1] == cls]
        if not sub: continue
        print('  %-5s %3d frames; best %-12s jamb metre %4.0f px  camera u %6.2f d %6.2f h %5.2f' % (cls, len(sub), sub[0][2], sub[0][0], sub[0][4], sub[0][5], sub[0][6]))
        best.append(sub[0])
    tiles = []
    for size, cls, stem, imgpath, cu, cd, ch in best[:n_crops]:
        cam = load_class(cls)[stem][0]
        img = cv2.imread(imgpath)
        poly(cam, [W(DOOR[0], DN, FL), W(DOOR[1], DN, FL), W(DOOR[1], DN, FL + DOOR[2]), W(DOOR[0], DN, FL + DOOR[2])], (0, 255, 255), img, True)
        poly(cam, [W(US, d, FL + UPS) for d in (0, 0.5, 1, 2, 3, 4)], (255, 255, 0), img)
        poly(cam, [W(UI, d, FL + UPS) for d in (0, 0.5, 1, 2, 3, 4)], (255, 0, 255), img)
        poly(cam, [W(UF, d, FL + RAIL) for d in (0, 0.5, 1, 2, 3, 4)], (0, 255, 0), img)
        poly(cam, [W(US, 0, FL), W(US, 0, FL + UPS), W(UI, 0, FL + UPS), W(UI, 0, FL)], (255, 255, 0), img, True)
        x, y, z = cam.project(corner)
        cx, cy = float(np.mean(x)), float(np.mean(y)); r = int(max(np.ptp(x), np.ptp(y)) * 0.9) + 60
        x0, y0 = int(max(cx - r, 0)), int(max(cy - r, 0))
        crop = np.ascontiguousarray(img[y0:y0 + 2 * r, x0:x0 + 2 * r])
        crop = cv2.resize(crop, (540, 540))
        cv2.putText(crop, '%s %s' % (cls, stem), (8, 24), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 255), 2)
        tiles.append(crop)
    if tiles:
        rows_img = [np.hstack(tiles[i:i + 2]) if i + 1 < len(tiles) else np.hstack([tiles[i], np.zeros_like(tiles[i])]) for i in range(0, len(tiles), 2)]
        out = SCRATCH + '/deck-door-corner.jpg'
        cv2.imwrite(out, np.vstack(rows_img), [cv2.IMWRITE_JPEG_QUALITY, 85]); print('wrote', out)


if __name__ == '__main__':
    main()
