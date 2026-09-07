"""Find the steel members of a ceiling photograph as lines, and turn their crossings into the
points tools/photo_register.py needs.

Why lines and not points: a crossing of two members is the one place a local search fails, because
the diagonals, the flange highlights and the emblem stacks all meet there too. Along a member, away
from the crossings, the dark centreline is unambiguous, so each member is sampled perpendicular to
its rough position every few pixels, the darkest position is taken (sub-pixel, parabola through the
minimum of the smoothed profile), and a straight line is fitted to those samples by a robust
(median-of-residuals, iterated) fit. A member in 3D is a straight segment (a ridge along the crest,
a cross member from the vertex up to the edge midpoint), so its image is a straight line under a
pinhole camera and the fit is exact in principle; a lens with radial distortion bends it, which
shows in the residual printed per line.

    python tools/photo_lines.py --photo lf02.jpg --lines lf02.lines.json --out points.json [--preview p.jpg]

lines json: {"note": "...", "flip": "flipUD", "lines": [
    {"name": "ridge-h", "orient": "h", "px": 493.75, "lattice": {"axis": "v", "j": 0, "dv": -0.5}, "width": 60},
    {"name": "cross-v0", "orient": "v", "px": 169, "lattice": {"axis": "u", "i": 0, "du": 0.0}, "width": 30}, ...]}
  orient h = a member running left-right in the photo at row px; v = running up-down at column px.
  lattice says which lattice line it is on the OLD lattice (trackA_geom): axis u = a line of constant
  hu (hu = HU0 + (i + du) PU), axis v = constant hv. width = rough dark width in px (sets the search band).
  Every h line is crossed with every v line to make the points; a crossing outside the photo is dropped.
  "range": [a0, a1] limits a line to that span of its along-coordinate (px). A CROSS MEMBER is not one
  straight line in the photo: it runs from a funnel vertex (low) up to the edge midpoint on the ridge
  (high) and down again to the next vertex, so a camera under the ridge sees a shallow V bent at the
  ridge. Give each half its own entry with a range ending at the ridge, or the fit averages the V and
  the reprojection carries the relief as a 15 px error (lf02, 2026-09-08).
  "flip" records how the photo was oriented against the plate (from ceiling_locate) and is copied through.
"""
import argparse
import json

import cv2
import numpy as np
from PIL import Image

Image.MAX_IMAGE_PIXELS = None


def dark_profile(V, orient, pos, along, band):
    """darkness minimum across the member at coordinate `along`, within +-band of pos."""
    if orient == 'v':
        seg = V[int(along), max(0, int(pos - band)):int(pos + band)]
        base = max(0, int(pos - band))
    else:
        seg = V[max(0, int(pos - band)):int(pos + band), int(along)]
        base = max(0, int(pos - band))
    if len(seg) < 5:
        return None, 0.0
    s = cv2.GaussianBlur(seg.astype(np.float32).reshape(1, -1), (0, 0), 2.0).ravel()
    k = int(np.argmin(s))
    if 0 < k < len(s) - 1:
        a, b, c = s[k - 1], s[k], s[k + 1]
        den = a - 2 * b + c
        k = k + (0.5 * (a - c) / den if abs(den) > 1e-6 else 0.0)
    contrast = float(np.median(s) - s.min())
    return base + k, contrast


def fit_line(xs, ys, iters=4):
    """y = m x + c by least squares, then re-weighted by the median absolute residual (a crossing
    or a flange that pulled a sample off the centreline drops out)."""
    w = np.ones(len(xs))
    for _ in range(iters):
        A = np.stack([xs, np.ones_like(xs)], 1) * w[:, None]
        m, c = np.linalg.lstsq(A, ys * w, rcond=None)[0]
        r = np.abs(ys - (m * xs + c))
        mad = np.median(r) + 1e-6
        w = 1.0 / (1.0 + (r / (3 * mad)) ** 2)
    keep = r < 4 * mad
    return m, c, float(np.sqrt(np.mean(r[keep] ** 2))), int(keep.sum())


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('--photo', required=True)
    ap.add_argument('--lines', required=True)
    ap.add_argument('--out', required=True)
    ap.add_argument('--preview', default='')
    ap.add_argument('--step', type=int, default=6)
    ap.add_argument('--avoid', type=int, default=90, help='px kept clear of every other member crossing')
    args = ap.parse_args()
    im = np.array(Image.open(args.photo).convert('RGB'))
    V = cv2.cvtColor(im, cv2.COLOR_RGB2HSV)[..., 2]
    h, w = V.shape
    spec = json.load(open(args.lines))
    lines = spec['lines']
    hs = [l for l in lines if l['orient'] == 'h']
    vs = [l for l in lines if l['orient'] == 'v']
    fitted = {}
    for l in lines:
        others = vs if l['orient'] == 'h' else hs
        length = w if l['orient'] == 'h' else h
        band = max(20, int(l.get('width', 30)))
        xs, ys, cs = [], [], []
        a0, a1 = l.get('range', [0, length])
        for a in range(max(4, int(a0)), min(length - 4, int(a1)), args.step):
            if any(abs(a - o['px']) < args.avoid for o in others):
                continue
            p, contrast = dark_profile(V, l['orient'], l['px'], a, band)
            if p is None or contrast < 15:
                continue
            xs.append(a); ys.append(p); cs.append(contrast)
        xs = np.array(xs, float); ys = np.array(ys, float)
        if len(xs) < 8:
            print(f"{l['name']}: only {len(xs)} samples, skipped"); continue
        m, c, rms, n = fit_line(xs, ys)
        fitted[l['name']] = dict(l, m=m, c=c, rms=rms, n=n)
        print(f"{l['name']:10s} {l['orient']}  {n:4d} samples  slope {m:+.4f}  offset {c:8.2f}  rms {rms:.2f} px")
    pts = []
    for lh in hs:
        for lv in vs:
            if lh['name'] not in fitted or lv['name'] not in fitted:
                continue
            fh, fv = fitted[lh['name']], fitted[lv['name']]
            # h: y = mh x + ch ; v: x = mv y + cv  (v lines are parametrised by y)
            # x = mv (mh x + ch) + cv  ->  x (1 - mv mh) = mv ch + cv
            x = (fv['m'] * fh['c'] + fv['c']) / (1 - fv['m'] * fh['m'])
            y = fh['m'] * x + fh['c']
            if not (0 <= x < w and 0 <= y < h):
                continue
            # a half-member only owns the crossings inside (or at the end of) its own span
            ok = True
            for l, along in ((lh, x), (lv, y)):
                if 'range' in l and not (l['range'][0] - 60 <= along <= l['range'][1] + 60):
                    ok = False
            if not ok:
                continue
            lu = lv['lattice'] if lv['lattice']['axis'] == 'u' else lh['lattice']
            lvv = lh['lattice'] if lh['lattice']['axis'] == 'v' else lv['lattice']
            pts.append(dict(px=round(float(x), 2), py=round(float(y), 2), i=lu['i'], du=lu['du'], j=lvv['j'], dv=lvv['dv'],
                            lines=[lh['name'], lv['name']]))
    json.dump(dict(note=spec.get('note', ''), flip=spec.get('flip', ''), lines=fitted, points=pts), open(args.out, 'w'), indent=1)
    print(f'{len(pts)} points -> {args.out}')
    if args.preview:
        prev = im.copy()
        for f in fitted.values():
            if f['orient'] == 'h':
                p0 = (0, int(f['c'])); p1 = (w, int(f['m'] * w + f['c']))
            else:
                p0 = (int(f['c']), 0); p1 = (int(f['m'] * h + f['c']), h)
            cv2.line(prev, p0, p1, (0, 255, 0), 1)
        for p in pts:
            cv2.circle(prev, (int(p['px']), int(p['py'])), 7, (255, 0, 255), 2)
        cv2.imwrite(args.preview, prev[..., ::-1], [cv2.IMWRITE_JPEG_QUALITY, 88])


if __name__ == '__main__':
    main()
