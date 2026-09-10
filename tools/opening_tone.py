"""THE CORRIDOR'S TONE THROUGH THE OPENINGS, PHOTO AGAINST SIM (2026-09-10).

Nothing posed looks into the corridor, but the hall-floor cameras see its interior through the north openings as
a patch of tone framed by the wall. This compares that patch with the sim's, through the same two cameras, the
widest whole-opening views the dataset has (tools/find_openseers.py): night w6_000085 on opening 9 (index 9,
u 37.18 to 38.38) and walk w1_000104 on opening 5 (u 22.57 to 23.78).

THE NIGHT FRAME REPLACED BEFORE ANY TONE WAS READ. The picks step projects the corners and prints their angle off
the camera axis: w6_000085's opening 9 sits 64 to 65 degrees off axis, outside a frame whose half diagonal is 40,
and its in-frame polygon was the OpenCV radial polynomial folding those points back (radial factor 0.02 to
-0.02; the plain pinhole puts them at (-418,-1878)). tools/find_openseers.py now rejects folds; re-run over every
class and opening it gives night w6_000146 on opening 7 (u 29.96 to 31.18, 132 px) as the widest real night view,
and that is the second frame. The rule itself is unchanged.

THE RULE, FIXED BEFORE THE RUN. For each frame: the median grey inside the aperture polygon (the opening's four
corners at d -0.03, sill 8.740, head 11.165, projected through the pose) over the median grey of a ring around
it (the polygon scaled 1.6x about its centre, the polygon itself cut out), in the photo and in the sim rendered
through the same pose. The ratio is what the wall does to the light and is insensitive to exposure. The sim's
corridor materials change only if the sim's ratio differs from the photo's IN THE SAME DIRECTION IN BOTH FRAMES
by more than a factor 1.5; one frame alone, or the two disagreeing, records only. Controls: the photo's ring must
be the wall (median between 40 and 200 grey, not sky or black), and the sim's polygon must land inside the render
(all four corners inside the square) or the frame is void.

THE POSES. The pose is read off the COLMAP camera itself (forward = R[2], right = R[0]; a first draft of this
paragraph blamed a transcription error for opening 9 sitting sixty degrees off w6_000085's axis, but the forward
was right and the fold above was the whole story). The render camera has no roll, so the square render covers
the rolled frame and the render polygon is computed through an unrolled pinhole with the same forward and
pitch: f_r = S / 2 / tan(sqvfov / 2), right = forward x up, up = right x forward.

Run:
  python tools/opening_tone.py picks       # writes render-shots/render-match.json from the poses
  python tools/opening_tone.py compare     # after tools/render_match.mjs: the medians, the ratios, the verdict
"""
import os, sys, math, json
import numpy as np
import cv2
sys.path.insert(0, os.path.dirname(__file__))
from underside_geom import load_class

O = np.array([-54.907447, -1.43545, 3.040286]); HU = np.array([0.975681, 0, 0.219196]); HD = np.array([0.219196, 0, -0.975681]); UP = np.array([0, 1.0, 0])
OPEN = {9: (37.177, 38.383), 5: (22.565, 23.778), 7: (29.963, 31.175)}
FRAMES = (('night', 'w6_000146', 7), ('walk', 'w1_000104', 5))   # w6_000085/9 was a fold, see above
SILL, HEAD, DFACE = 8.740, 11.165, -0.03
RING = 1.6
FACTOR = 1.5
WALL_OK = (40, 200)
SCRATCH = 'C:/Users/LLOYDG~1/AppData/Local/Temp/claude/C--Users-Lloyd-Gibbs-Claude-Projects-ngv-hall-model/7ac78459-3aa5-43ef-aae7-7d6745ece11b/scratchpad'


def W(u, d, h):
    return O + u * HU + d * HD + np.array([0, h, 0])


def corners(k):
    u0, u1 = OPEN[k]
    return np.array([W(u0, DFACE, SILL), W(u1, DFACE, SILL), W(u1, DFACE, HEAD), W(u0, DFACE, HEAD)])


def pose(cam):
    R = cam.R; f = R[2]; right = R[0]
    q = cam.center - O
    hr = np.cross(f, UP); hr /= np.linalg.norm(hr); hu = np.cross(hr, f)
    return dict(u=float(q @ HU), d=float(q @ HD), h=float(q[1]), fu=float(f @ HU), fd=float(f @ HD), fy=float(f[1]),
                pitch=math.degrees(math.asin(float(f[1]))), roll=math.degrees(math.atan2(float(right @ hu), float(right @ hr))),
                vfov=2 * math.degrees(math.atan(cam.h / 2 / cam.params[1])), w=cam.w, h_px=cam.h)


def picks():
    out = []
    for cls, stem, k in FRAMES:
        cam, imgpath = load_class(cls)[stem]
        p = pose(cam)
        pts = corners(k)
        x, y, z = cam.project(pts)
        ang = [math.degrees(math.acos(float(((q - cam.center) / np.linalg.norm(q - cam.center)) @ cam.R[2]))) for q in pts]
        sqv = min(120.0, 2 * max(ang) + 6)
        print('%s %s: u %.3f d %.3f h %.3f  fwd (%.4f %.4f %.4f) pitch %.2f roll %.2f vfov %.2f' % (cls, stem, p['u'], p['d'], p['h'], p['fu'], p['fd'], p['fy'], p['pitch'], p['roll'], p['vfov']))
        print('   opening %d in the photo: %s  off axis %s deg  -> square vfov %.1f' % (k, [(int(a), int(b)) for a, b in zip(x, y)], ' '.join('%.1f' % a for a in ang), sqv))
        out.append(dict(u=round(p['u'], 3), d=round(p['d'], 3), h=round(p['h'], 3), fu=round(p['fu'], 4), fd=round(p['fd'], 4), pitch=round(p['pitch'], 2), w=p['w'], hgt=p['h_px'], vfov=round(p['vfov'], 2),
                        sqvfov=round(sqv, 1), sqside=round(math.tan(math.radians(sqv / 2)) / math.tan(math.radians(p['vfov'] / 2)), 3), roll=round(p['roll'], 2), cls=cls, frame=int(stem.split('_')[1])))
    os.makedirs('render-shots/render-match', exist_ok=True)
    json.dump(out, open('render-shots/render-match.json', 'w'))
    print('wrote render-shots/render-match.json (%d picks)' % len(out))


def stats(img, poly):
    g = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    m = np.zeros(g.shape, np.uint8); cv2.fillPoly(m, [poly.astype(np.int32)], 1)
    c = poly.mean(0); big = ((poly - c) * RING + c).astype(np.int32)
    mb = np.zeros(g.shape, np.uint8); cv2.fillPoly(mb, [big], 1)
    ring = np.logical_and(mb == 1, m == 0)
    if m.sum() == 0 or ring.sum() == 0: return None
    return float(np.median(g[m == 1])), float(np.median(g[ring])), int(m.sum())


def crop(img, poly, size=360):
    c = poly.mean(0); r = int(max(np.ptp(poly[:, 0]), np.ptp(poly[:, 1])) * 1.2) + 4
    x0, y0 = int(max(c[0] - r, 0)), int(max(c[1] - r, 0))
    t = np.ascontiguousarray(img[y0:y0 + 2 * r, x0:x0 + 2 * r])
    cv2.polylines(t, [(poly - [x0, y0]).astype(np.int32)], True, (0, 255, 255), 2)
    return cv2.resize(t, (size, size))


def compare():
    pk = json.load(open('render-shots/render-match.json'))
    rows = []; tiles = []
    for i, (cls, stem, k) in enumerate(FRAMES):
        p = pk[i]; cam, imgpath = load_class(cls)[stem]
        ph = cv2.imread(imgpath); rd = cv2.imread('render-shots/render-match/r%02d.jpg' % i)
        pts = corners(k)
        x, y, z = cam.project(pts); pp = np.stack([x, y], 1)
        S = rd.shape[0]; fr = S / 2 / math.tan(math.radians(p['sqvfov'] / 2))
        C = W(p['u'], p['d'], p['h']); fh = p['fu'] * HU + p['fd'] * HD; fh /= np.linalg.norm(fh)
        pr = math.radians(p['pitch']); f = fh * math.cos(pr) + UP * math.sin(pr)
        right = np.cross(f, UP); right /= np.linalg.norm(right); up = np.cross(right, f)
        rp = np.array([(S / 2 + fr * ((X - C) @ right) / ((X - C) @ f), S / 2 - fr * ((X - C) @ up) / ((X - C) @ f)) for X in pts])
        inside = bool(np.all(np.logical_and(rp >= 0, rp < S)))
        a = stats(ph, pp); b = stats(rd, rp)
        ok_wall = a is not None and WALL_OK[0] <= a[1] <= WALL_OK[1]
        void = not (inside and ok_wall and b is not None)
        print('%s %s opening %d: photo poly %s; render poly %s (inside %s)' % (cls, stem, k, [(int(q), int(r)) for q, r in pp], [(int(q), int(r)) for q, r in rp], inside))
        if a: print('   PHOTO inside %.0f  ring %.0f  ratio %.2f  (%d px)%s' % (a[0], a[1], a[0] / a[1], a[2], '' if ok_wall else '  RING NOT WALL, void'))
        if b: print('   SIM   inside %.0f  ring %.0f  ratio %.2f  (%d px)' % (b[0], b[1], b[0] / b[1], b[2]))
        rows.append(None if void else (a[0] / a[1], b[0] / b[1]))
        tiles.append(np.hstack([crop(ph, pp), crop(rd, rp)]))
    cv2.imwrite(SCRATCH + '/opening-tone.jpg', np.vstack(tiles), [cv2.IMWRITE_JPEG_QUALITY, 85])
    live = [r for r in rows if r]
    if len(live) < 2:
        print('VERDICT: %d of 2 frames valid; the rule needs both; record only' % len(live)); return
    dirs = [np.sign(math.log(s / q)) for q, s in live]
    big = [abs(math.log(s / q)) > math.log(FACTOR) for q, s in live]
    if all(big) and dirs[0] == dirs[1]:
        print('VERDICT: the sim is %s than the photo through both openings by more than %.1fx: change the corridor materials' % ('brighter' if dirs[0] > 0 else 'darker', FACTOR))
    else:
        print('VERDICT: no change (factors %s, directions %s); record only' % (' '.join('%.2f' % (s / q) for q, s in live), dirs))


if __name__ == '__main__':
    {'picks': picks, 'compare': compare}[sys.argv[1]]()
