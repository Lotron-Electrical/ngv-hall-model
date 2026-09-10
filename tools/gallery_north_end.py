"""The east gallery's north end read off the b6 clip: which end the lit doorway is on, where it
stands along the wall, and how tall it is (2026-09-10).

WHAT THE FRAMES SHOW. b6 frames 1236 to 1332 walk the east upper gallery with the vitrine row on the
LEFT and the hall (coping, a round column, a tapestry beyond) on the RIGHT, toward a wall that faces
the camera square: a lit doorway with a green exit light in its head, then to its right two dark
rectangles the size of the corridor openings, then the tapestry low on the same wall past the column.
THE HANDEDNESS IS NOT A GUESS. Posed cameras settle which way that is: through b7s_000080 and b3
(east deck, looking west, -u) a point 3 m to +d lands on x 1845 and 3 m to -d on x 395, so looking -u
the +d side (the south wall) is on the right; through b1 (looking +d) the +u side is on the right.
So a camera with the hall on its RIGHT in the east gallery looks toward -d: the far wall is the NORTH
wall, the two rectangles are openings 12 and 11 in it seen through the gallery glass, the tapestry is
north-2 (u 37.8-43.3, top 8.31, tools/tapestries.json) hanging under openings 11 and 10, and the lit
doorway with the exit light is the gallery's NORTH door: the corridor mouth, the twin of the one the
b7 clip shows at the west gallery's north end. The block in index.html that put "A LIT DOORWAY AT THE
SOUTH END OF THE EAST GALLERY ... dead ahead looking south" read these same frames the other way
round, and this file corrects it.

THE INSTRUMENT. The far wall is one plane (d = -0.030), so along one line of it image x is a
projective function of u: x = (a u + b) / (c u + 1). Three known edges fix the map; a fourth is the
control. Known: opening 12's jambs on u 45.739 and 44.526, opening 11's on 42.064 and 40.851 (the
first opening spans 4.098-5.310, pitch 3.675, twelve of them), and the back-wall corner on u 51.906.
Frames are undistorted with the b6g intrinsics (the same phone, posed by COLMAP on 6 of its frames).
Edges are seeded by eye on a gridded crop and then refined to the strongest gradient of the expected
sign within 20 px, on a band of rows averaged.

THE DECISION RULE, FIXED BEFORE THE RUN.
  1. IDENTIFICATION CONTROL: fit the map on opening 12's two jambs and one jamb of opening 11, then
     predict the back-wall corner. It must land within 40 px of the corner read off the frame, on
     every frame used. If it does not, the rectangles are not the openings and nothing below is read.
  2. THE DOOR'S u: both jambs through the fitted map. Claimed only if two frames or more pass the
     control and the across-frame half-range is under 0.15 m. Otherwise a hint, and the drawn
     numbers stay.
  3. THE DOOR HEAD: from the vertical offset of the door's head against opening 12's head (11.165),
     with the pixel scale on opening 12 from its 1.212 m width, the depth ratio from the fitted map,
     and the camera height taken as 9.9 (b3 stands 9.70-10.14 on this deck); its +-0.3 m moves the
     answer by under 0.06 m because the two heads stand very nearly the same depth away. Same rule.
  4. Opening 12's visible bottom is read the same way against 8.740 and REPORTED, not used: from this
     deck the coping stands between the camera and the sill.

THE RESULT (2026-09-10, first run after two seed fixes: the 1248 corner seed had been put on the wall
and the height scale carried the wrong sign; both were fixed before any number was read as a claim).
  b6_001248: corner predicted 392, read 398, control 6 px. Door u 49.227 to 48.079, head 11.516.
  b6_001320: corner predicted 197, read 226, control 29 px. Door u 49.355 to 48.157, head 11.458.
  Jambs u0 49.291 (half-range 0.064), u1 48.118 (0.039); head 11.487 (0.029); doorH 3.15. Both LIVE.
  Opening 12's visible bottom 9.152 and 8.811 against the 8.740 sill: reported, not used.
  The hall-side jamb stands 0.06 m inside the glass line 48.056; the coping drawn 0.45 wide by eye cannot
  fit beside it. The jamb is measured, the coping is not; index.html keeps both and says so.

SECOND NOTE, THE SAME DAY: THE SOUTH DOOR IS REAL, AND THE WEST NORTH DOOR WAS NEVER THERE. This
file's docstring says no frame shows a door in the south end; that was written before the b7 clip was
placed. The posed b7 frames stand on the EAST deck's south end for 68 to 156 and on the west deck's
south end from 608; frame 424 repeats the hall view of 160 to 238 (facing west, the south tapestry
near on the right), and 240 to 372 look up at the canopy, so 300 to 424 never leave the east deck's
south end. In 376 to 408 a wall solid to the canopy stands on the camera's LEFT and the coping recedes
on the RIGHT: on that deck only a camera facing south-east sees that (the east back wall left, the
south wall ahead), and a pan to the right from there ends facing west, as 424 does. What those frames
show is the east gallery's south end: a round stone column in the SE corner, a DARK unlit doorway in
the south wall about a metre west of it, a green exit light beside the column, a glass case with a
marble bust in front of the south wall, a long dark ledge (the coping) on the right. index.html draws
the south door again from this, dark, with the sign, the bust and the column, all by eye, its height
borrowed from the measured north door; and the west gallery's north door, sign and bust case, which had
been built from these same frames read as the west end, are withdrawn, with the corridor's west end an
estimate once more. A separate check refuted the other reading: through the posed b1p frames 212 to
214 the west back wall above the west deck is plain lit ashlar with no dark doorway in it.

THIRD NOTE, AN HOUR LATER: THE SECOND NOTE PUT THOSE FRAMES ON THE WRONG DECK. b7 596 to 616 are one
continuous shot and 616 is posed on the WEST deck's south end (u 3.2, d 13.5, facing east, the south
tapestry near on the left, and the projection of tools/tapestries.json lands on it). The deck change is
somewhere in the canopy frames 248 to 300. In 404 to 432 the door wall slides out to the left while the
hall comes in from the right: a RIGHT turn of half a turn that ends facing east. So 384 to 404 face
SOUTH on the west deck, and the rule from the posed cameras (facing +d, +u is on the right) puts the
west back wall on the LEFT, the coping on the RIGHT, the SW corner column on the left and the south
wall ahead with the door east of the corner: all of it is in the frames. Facing north on the east deck
(the second note's reading, and b6's true one) would put the coping on the right too, but the far wall
would then hold openings 12 and 11 beside the door as b6 shows, and there are none; and 432 could not
face east there. The dark door, the sign, the bust case and the column are the west gallery's south end,
drawn there by eye. The east gallery keeps its measured north door and has no door at its south end.

Run:
  python tools/gallery_north_end.py
"""
import os, sys
import numpy as np, cv2
sys.path.insert(0, os.path.dirname(__file__))
import underside_geom as U

RAW = 'E:/sitecapture-captures/ngv-video/balcony2/b6/images/b6_%06d.png'
OUT = os.path.join(os.path.dirname(__file__), '..', 'render-shots-north-end')
U12 = (45.739, 44.526); U11 = (42.064, 40.851); UCORNER = 51.906
HEAD = 11.165; SILL = 8.740; WIDTH = 1.212; HCAM = 9.9; FLOOR = 8.34
CTRL_PX = 40; SPREAD = 0.15

# seeds (undistorted pixel coordinates, read by eye on gridded crops); sign -1: light to dark going right or down
SEEDS = {
    1248: dict(corner=(415, (700, 800), 0), doorL=(686, (880, 950), -1), doorR=(800, (880, 950), +1),
               r1L=(1014, (920, 1000), -1), r1R=(1143, (920, 1000), +1), r2R=(1457, (960, 1040), +1),
               doorTop=(821, (700, 790), -1), r1Top=(868, (1030, 1130), -1), r1Bot=(1086, (1030, 1130), +1)),
    1320: dict(corner=(245, (800, 900), 0), doorL=(571, (1000, 1080), -1), doorR=(729, (1000, 1080), +1),
               r1L=(1014, (1050, 1150), -1), r1R=(1171, (1050, 1150), +1), r2L=(1414, (1100, 1200), -1),
               doorTop=(950, (600, 700), -1), r1Top=(993, (1040, 1150), -1), r1Bot=(1261, (1040, 1150), +1)),
}
HORIZ = ('doorTop', 'r1Top', 'r1Bot')


def refine(gray, seed, band, sign, vertical):
    """strongest gradient of the expected sign within 20 px of the seed, the band's rows (or columns) averaged"""
    a, b = band
    prof = gray[a:b, :].mean(axis=0) if vertical else gray[:, a:b].mean(axis=1)
    prof = cv2.GaussianBlur(prof.reshape(-1, 1).astype(np.float32), (1, 7), 0).ravel()
    g = np.gradient(prof)
    i0, i1 = max(1, seed - 20), min(len(g) - 2, seed + 20)
    seg = g[i0:i1]
    if sign < 0: seg = -seg
    elif sign == 0: seg = np.abs(seg)
    return i0 + int(np.argmax(seg))


def fit_map(us, xs):
    """x = (a u + b) / (c u + 1) through three (u, x) pairs"""
    A = [[u, 1.0, -x * u] for u, x in zip(us, xs)]
    a, b, c = np.linalg.solve(np.array(A), np.array(xs, float))
    return a, b, c


def to_u(x, m):
    a, b, c = m
    return (b - x) / (c * x - a)


def main():
    fr = U.load_class('b6g'); cam, _ = fr[sorted(fr)[0]]
    fx, fy, cx, cy, k1, k2, p1, p2 = cam.params
    K = np.array([[fx, 0, cx], [0, fy, cy], [0, 0, 1]]); dist = np.array([k1, k2, p1, p2])
    os.makedirs(OUT, exist_ok=True)
    rows = []
    for f, sd in SEEDS.items():
        im = cv2.undistort(cv2.imread(RAW % f), K, dist)
        gray = cv2.cvtColor(im, cv2.COLOR_BGR2GRAY).astype(np.float32)
        e = {}
        for k, (seed, band, sign) in sd.items():
            e[k] = refine(gray, seed, band, sign, vertical=(k not in HORIZ))
        # 1. identification control: the openings fix the map, the corner is predicted
        r2key = 'r2R' if 'r2R' in e else 'r2L'; r2u = U11[1] if r2key == 'r2R' else U11[0]
        m = fit_map([U12[0], U12[1], r2u], [e['r1L'], e['r1R'], e[r2key]])
        a, b, c = m
        xc = (a * UCORNER + b) / (c * UCORNER + 1)
        ctrl = abs(xc - e['corner'])
        ok = ctrl <= CTRL_PX
        # 2. the door's u
        u0, u1 = to_u(e['doorL'], m), to_u(e['doorR'], m)
        # 3. the door head
        s_r = (e['r1R'] - e['r1L']) / WIDTH                      # px per metre on opening 12 (x grows to the right)
        zr_over_zd = (c * U12[0] + 1) / (c * (u0 + u1) / 2 + 1)   # depth ratio Z_r / Z_d
        s_d = s_r * zr_over_zd
        head_for = lambda hc: hc - (s_r * (hc - HEAD) - (e['r1Top'] - e['doorTop'])) / s_d
        h_door, h_lo, h_hi = head_for(HCAM), head_for(HCAM - 0.3), head_for(HCAM + 0.3)
        # 4. opening 12's visible bottom
        h_bot = HEAD - (e['r1Bot'] - e['r1Top']) / s_r
        rows.append(dict(f=f, ctrl=ctrl, ok=ok, u0=u0, u1=u1, h=h_door, bot=h_bot, e=e))
        print('b6_%06d: corner predicted %.0f, read %d, control %.0f px %s' % (f, xc, e['corner'], ctrl, 'PASS' if ok else 'FAIL'))
        print('   door u %.3f to %.3f (width %.2f), head h %.3f (camera height +-0.3: %.3f to %.3f), doorH %.2f'
              % (max(u0, u1), min(u0, u1), abs(u1 - u0), h_door, min(h_lo, h_hi), max(h_lo, h_hi), h_door - FLOOR))
        print('   opening 12 visible bottom h %.3f (sill drawn %.3f)' % (h_bot, SILL))
        print('   edges', {k: int(v) for k, v in e.items()})
        vis = im.copy()
        for k, v in e.items():
            if k in HORIZ:
                x0, x1 = sd[k][1]; cv2.line(vis, (x0, v), (x1, v), (0, 255, 255), 2)
            else:
                y0, y1 = sd[k][1]; cv2.line(vis, (v, y0 - 40), (v, y1 + 40), (0, 255, 0) if k != 'corner' else (255, 0, 255), 2)
        cv2.line(vis, (int(xc), 650), (int(xc), 1300), (0, 0, 255), 2)
        cv2.putText(vis, 'red: corner predicted from openings 12+11; magenta: corner read', (20, 640), cv2.FONT_HERSHEY_SIMPLEX, 0.8, (255, 255, 255), 2)
        cv2.imwrite(os.path.join(OUT, 'north-end-%d.jpg' % f), vis[550:1400], [cv2.IMWRITE_JPEG_QUALITY, 88])
    good = [r for r in rows if r['ok']]
    print()
    if len(good) < 2:
        print('FEWER THAN TWO FRAMES PASS THE CONTROL (%d): the rectangles are not shown to be the openings, nothing claimed' % len(good))
        return
    u0s = [max(r['u0'], r['u1']) for r in good]; u1s = [min(r['u0'], r['u1']) for r in good]; hs = [r['h'] for r in good]
    hr = lambda v: (max(v) - min(v)) / 2
    print('door jambs: u0 %.3f (half-range %.3f), u1 %.3f (half-range %.3f)' % (np.mean(u0s), hr(u0s), np.mean(u1s), hr(u1s)))
    print('door head: h %.3f (half-range %.3f), doorH %.2f' % (np.mean(hs), hr(hs), np.mean(hs) - FLOOR))
    print('u claim: %s' % ('LIVE' if max(hr(u0s), hr(u1s)) < SPREAD else 'NOT LIVE, spread too wide'))
    print('head claim: %s' % ('LIVE' if hr(hs) < SPREAD else 'NOT LIVE, spread too wide'))
    print('opening 12 visible bottom, per frame:', ['%.3f' % r['bot'] for r in good], '(reported, not used)')


if __name__ == '__main__':
    main()
