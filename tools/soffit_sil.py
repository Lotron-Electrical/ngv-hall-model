# 2026-09-09: THE CEILING OVER THE END BALCONY READ AS A SILHOUETTE, which is the only thing it can be.
#
# The two previous instruments both sampled brightness along the parapet face plane, and both failed for
# the same reason, which is worth writing down because it is a general trap. THAT PLANE IS OPEN AIR. Above
# the deck there is nothing at u 48.056 to reflect light, so a pixel on that path shows whatever stands
# behind it, thirty metres away across the hall. The step those runs found was real and it was in the far
# west end of the building; drawn back on b7s_000152 it circles the lit west wall over the dark gallery.
# A level on an open plane cannot be read by looking at the plane.
#
# The soffit is not a surface in the picture, it is an OCCLUSION: a near dark ceiling cutting off the far
# bright hall. So the boundary is found in image space, walking each column of the picture from the top
# down to the first strong dark-to-bright transition, with no world geometry entering the search at all.
# Only afterwards is that pixel turned into a height, by intersecting its ray with the parapet face plane,
# and THAT step does assume the soffit's edge stands over the face, which is the model's own claim and is
# stated rather than hidden. The height never enters the search, so the follow gain of this instrument is
# structurally zero.
#   python tools/soffit_sil.py [east|west] [draw]
import os
import sys

import cv2
import numpy as np

sys.path.insert(0, 'tools')
import underside_geom as U  # noqa: E402

O = np.array([-54.907447, -1.43545, 3.040286])
HU = np.array([0.975681, 0, 0.219196])
HD = np.array([0.219196, 0, -0.975681])
DECK, FACE = 8.34, 3.85
ENDS = {'west': (0.344, -1.0), 'east': (51.906, 1.0)}
CLASSES = ('b1p', 'b3p', 'b5p', 'b7sp', 'b6gp', 'b1', 'b3', 'b4', 'b5', 'b6s', 'b7s', 'b6g')
OUT = 'E:/sitecapture-captures/ngv-site/agent-ref-walls/shots/balcony'
CONTRAST = 28.0                 # a dark-to-bright jump smaller than this is not an occluding edge
BAND = 24                       # rows averaged either side of a candidate row


def top_boundary(grey, x):
    """the first strong dark-to-bright transition walking DOWN column x, or None"""
    col = grey[:, x].astype(np.float32)
    n = len(col)
    for r in range(BAND, n - BAND, 4):
        above = col[r - BAND:r].mean()
        below = col[r + 1:r + 1 + BAND].mean()
        if below - above > CONTRAST and above < 90.0:
            return r
    return None


def run(end, draw=False):
    uB, s = ENDS[end]
    uF = uB - s * FACE
    cams = {}
    for cls in CLASSES:
        try:
            frames = U.load_class(cls)
        except Exception:
            continue
        for fr, v in frames.items():
            cams.setdefault(fr, v)
    deck = []
    for fr, (cam, ip) in cams.items():
        q = cam.center - O
        cu, ch = float(q @ HU), float(cam.center[1] - O[1])
        if ch > DECK + 0.35 and abs(cu - uB) < 6.0:
            deck.append((fr, cam, ip, cu, ch))
    deck.sort()
    print(end.upper(), 'end:', len(deck), 'deck frames, face plane u %.3f' % uF)
    rows = []
    for fr, cam, ip, cu, ch in deck:
        # the face plane's image line at a ladder of heights and depths: used ONLY to know which columns
        # of this picture look at the face plane at all, never to place the boundary
        hs = np.arange(9.0, 13.4, 0.02)
        ds = np.linspace(0.2, 15.2, 76)
        pts = np.array([O + uF * HU + dd * HD + np.array([0, float(v), 0]) for dd in ds for v in hs])
        x, y, z = cam.project(pts)
        ok = (z > 0.3) * (x > 20) * (x < cam.w - 20) * (y > 20) * (y < cam.h - 20)
        if ok.sum() < 40:
            continue
        cols = sorted(set(int(v) for v in np.round(x[ok] / 60.0) * 60))
        cols = [c for c in cols if 30 < c < cam.w - 30]
        if len(cols) < 3:
            continue
        grey = cv2.GaussianBlur(cv2.imread(ip, cv2.IMREAD_GRAYSCALE), (7, 7), 0)
        # ONE grid of the face plane per frame, projected once, then every boundary pixel is matched to
        # its nearest grid point in image space. The grid is only a lookup from pixel to height; it does
        # not vote, weight, or attract, so a boundary found in a column stays where the picture put it.
        gx, gy = x[ok], y[ok]
        gh = np.array([float(v) for dd in ds for v in hs])[ok]
        got = []
        for c in cols[:24]:
            r = top_boundary(grey, c)
            if r is None:
                continue
            dist = np.hypot(gx - c, gy - r)
            k = int(np.argmin(dist))
            if float(dist[k]) > 14.0:
                continue
            got.append((c, r, float(gh[k]), float(dist[k])))
        if len(got) >= 3:
            med = float(np.median([g[2] for g in got]))
            spread = float(max(g[2] for g in got) - min(g[2] for g in got))
            rows.append((fr, cu, ch, len(got), med, spread))
            if draw:
                im = cv2.imread(ip)
                for c, r, bh, _e in got:
                    cv2.circle(im, (c, r), 16, (0, 255, 255), 4)
                    cv2.putText(im, '%.2f' % bh, (c + 22, r), cv2.FONT_HERSHEY_SIMPLEX, 1.1,
                                (0, 255, 255), 3, cv2.LINE_AA)
                k = 1500.0 / im.shape[0]
                cv2.imwrite(os.path.join(OUT, fr + '-sil.jpg'),
                            cv2.resize(im, (int(im.shape[1] * k), 1500)), [cv2.IMWRITE_JPEG_QUALITY, 84])
                draw = False
    if not rows:
        print('   no frame produced three columns with an occluding edge over the face plane')
        return
    med = np.array([r[4] for r in rows])
    print('   %d frames read it, median h %.3f, frame to frame spread %.3f, drawn 11.100'
          % (len(rows), float(np.median(med)), float(med.max() - med.min())))
    for r in sorted(rows, key=lambda t: t[4])[:6]:
        print('        %-12s cu %6.2f ch %5.2f  %2d columns  h %6.3f  within-frame spread %.3f'
              % (r[0], r[1], r[2], r[3], r[4], r[5]))


if __name__ == '__main__':
    e = sys.argv[1] if len(sys.argv) > 1 else 'east'
    run(e, draw=('draw' in sys.argv))
