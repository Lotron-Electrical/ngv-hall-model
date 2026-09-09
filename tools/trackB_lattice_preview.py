"""Track B: the measured lattice (every steel joint of the 7x2 bays) drawn over the bottom ortho
preview, plus an NGVP validity check of the traced pane files.

  python tools/trackB_lattice_preview.py            -> scratch/trackB/bottom-lattice-preview.jpg (2000 px)
                                                       and E:/.../trackB/bottom-lattice-preview.jpg
  python tools/trackB_lattice_preview.py --check f.bin ...  -> per file: vertex range, winding, convexity,
                                                       simple-polygon test, k range, board bbox
"""
import argparse
import os
import struct
import sys

import cv2
import numpy as np
from PIL import Image

Image.MAX_IMAGE_PIXELS = None
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import ceiling_ortho as co


def lattice_preview(out_dir=co.OUT_DEFAULT, scratch=co.SCRATCH_DEFAULT, tag=''):
    import json
    meta = json.load(open(os.path.join(out_dir, 'bottom-meta%s.json' % tag)))
    img = np.asarray(Image.open(os.path.join(out_dir, 'bottom-ortho%s.png' % tag)).convert('RGB'))
    H, W = img.shape[:2]
    s = 2000.0 / W
    pv = cv2.resize(img, (2000, int(round(H * s))), interpolation=cv2.INTER_AREA)
    mpp = meta['mm_per_px'] / 1000.0
    hu0, hv0 = meta['hu0'], meta['hv0']
    for i in range(co.NB_U):
        for j in range(co.NB_V):
            for (a, b, w) in co.joint_lines(i, j):
                p0 = (int(round((a[0] - hu0) / mpp * s)), int(round((a[1] - hv0) / mpp * s)))
                p1 = (int(round((b[0] - hu0) / mpp * s)), int(round((b[1] - hv0) / mpp * s)))
                cv2.line(pv, p0, p1, (0, 255, 255) if w > 0.15 else (0, 200, 255), 1, cv2.LINE_AA)
            cu, cv_ = co.bay_vertex(i, j)
            c = (int(round((cu - hu0) / mpp * s)), int(round((cv_ - hv0) / mpp * s)))
            cv2.circle(pv, c, 6, (255, 0, 255), 1, cv2.LINE_AA)
            cv2.putText(pv, '%d,%d' % (i, j), (c[0] + 8, c[1] - 8), cv2.FONT_HERSHEY_SIMPLEX, 0.45, (255, 0, 255), 1, cv2.LINE_AA)
    cv2.putText(pv, 'lattice joints (yellow ridge 0.20 m, orange 0.12 m) and funnel vertices (magenta) on the corrected ortho; row 0 = south, col 0 = west',
                (6, pv.shape[0] - 8), cv2.FONT_HERSHEY_SIMPLEX, 0.45, (255, 255, 255), 1, cv2.LINE_AA)
    for d in (scratch, out_dir):
        Image.fromarray(pv).save(os.path.join(d, 'bottom-lattice-preview%s.jpg' % tag), quality=88)
    print('wrote bottom-lattice-preview%s.jpg to' % tag, scratch, 'and', out_dir)


def is_simple(poly):
    """No two non-adjacent edges intersect."""
    n = len(poly)

    def seg_x(p, q, r, s_):
        def orient(a, b, c):
            return (b[0] - a[0]) * (c[1] - a[1]) - (b[1] - a[1]) * (c[0] - a[0])
        o1, o2, o3, o4 = orient(p, q, r), orient(p, q, s_), orient(r, s_, p), orient(r, s_, q)
        return (o1 * o2 < 0) and (o3 * o4 < 0)
    for i in range(n):
        for j in range(i + 1, n):
            if abs(i - j) in (1, n - 1):
                continue
            if seg_x(poly[i], poly[(i + 1) % n], poly[j], poly[(j + 1) % n]):
                return False
    return True


def check(path):
    buf = open(path, 'rb').read()
    assert buf[:4] == b'NGVP', 'bad magic'
    n, u0, v0, mm = struct.unpack_from('<IffH', buf, 4)
    o = 18
    ks, areas, nonconvex, nonsimple, cw, ccw = [], [], 0, 0, 0, 0
    us, vs = [], []
    for _ in range(n):
        r, g, b, k = struct.unpack_from('<4B', buf, o); o += 4
        pts = np.array(struct.unpack_from('<%dH' % (2 * k), buf, o), np.float64).reshape(k, 2) / mm; o += 4 * k
        ks.append(k)
        us.extend((pts[:, 0] + u0).tolist()); vs.extend((pts[:, 1] + v0).tolist())
        x, y = pts[:, 0], pts[:, 1]
        A = 0.5 * (np.dot(x, np.roll(y, -1)) - np.dot(y, np.roll(x, -1)))
        areas.append(A)
        if A > 0:
            ccw += 1
        else:
            cw += 1
        # convexity: all cross products same sign
        cr = []
        for i in range(k):
            a, b2, c = pts[i], pts[(i + 1) % k], pts[(i + 2) % k]
            cr.append((b2[0] - a[0]) * (c[1] - b2[1]) - (b2[1] - a[1]) * (c[0] - b2[0]))
        cr = np.array(cr)
        if (cr > 1e-9).any() and (cr < -1e-9).any():
            nonconvex += 1
        if not is_simple(pts.tolist()):
            nonsimple += 1
    assert o == len(buf), 'trailing bytes'
    ks = np.array(ks); areas = np.array(areas)
    print('%s: %d pieces, %d bytes fully consumed, origin (%.4f, %.4f), scale %d' % (os.path.basename(path), n, len(buf), u0, v0, mm))
    print('  k range %d..%d, CCW (A>0 in u,v) %d, CW %d, non-convex %d, non-simple %d, |area| min %.5f m2, zero-area %d' % (
        ks.min(), ks.max(), ccw, cw, nonconvex, nonsimple, np.abs(areas).min(), int((np.abs(areas) < 1e-6).sum())))
    print('  board bbox u %.3f..%.3f  v %.3f..%.3f  (plate huv -> board: u 1.670..53.670, v 0.614..15.389)' % (min(us), max(us), min(vs), max(vs)))


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('--check', nargs='*')
    ap.add_argument('--tag', default='')
    args = ap.parse_args()
    if args.check:
        for p in args.check:
            check(p)
        return
    lattice_preview(tag=args.tag)


if __name__ == '__main__':
    main()
