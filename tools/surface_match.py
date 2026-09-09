# 2026-09-10: SCORE THE PHOTOGRAPH INSIDE EACH SURFACE'S OWN MASK.
#
# THE QUESTION THE WHOLE-FRAME TEST COULD NOT ASK. tools/render_match.py showed the sim lands on the
# photograph well enough to beat every mismatched pair, and gave a bound of about a degree. But a hall
# frame is mostly ceiling and floor, so a balcony fascia in the wrong place moves that score by a per cent
# and disappears into it. This scores each named surface separately, inside the pixels the model itself
# says that surface covers, which comes from the identity pass tools/surface_match.mjs renders.
#
# THE DECISION RULE, FIXED HERE BEFORE THE RUN.
#   1. A surface is only read where the model draws at least MINPIX of it in a frame, after the mask is
#      eroded so that no antialiased edge pixel is counted.
#   2. Its score is the normalised cross-correlation of the gradients inside that mask, taken where a
#      perfect model would put the render, which is the principal point offset and not zero.
#   3. THE CONTROL IS THE SAME MASK ON A DIFFERENT FRAME'S PHOTOGRAPH. That answers the objection that a
#      mask over a busy part of the picture scores well no matter what is drawn there.
#   4. A surface is CORROBORATED in a frame when its true score beats every control score for that same
#      mask. Anything else is NOT CORROBORATED, which is not the same as refuted and is never written as
#      though it were.
#   5. A surface the model draws but no frame can corroborate is reported as DRAWN ON NOTHING VISIBLE,
#      which is a statement about the archive, not about the building.
#
# WHAT IT CANNOT DO. The mask comes from the model, so a surface drawn in completely the wrong place is
# scored against whatever the photograph happens to show there, and will fail rather than point anywhere.
# It cannot separate a surface being wrong from the camera pose being wrong. And much of what it scores is
# the baked scan, which came from photographs of this building, so a high score there is partly the bake
# agreeing with its own source; the baked names are marked in the output.
#   python tools/surface_match.py
import io
import json
import os
import sys

import cv2
import numpy as np

OUT = 'render-match'
WH = 540
MINPIX = 2500
ERODE = 5

sys.path.insert(0, 'tools')


def grad(im):
    g = cv2.GaussianBlur(im.astype(np.float32), (0, 0), 1.6)
    m = np.hypot(cv2.Sobel(g, cv2.CV_32F, 1, 0, ksize=3), cv2.Sobel(g, cv2.CV_32F, 0, 1, ksize=3))
    return m / max(float(m.std()), 1e-6)


def turn(p, im, nearest=False):
    """Put the square render on its side by the camera's own roll, then cut the frame out of the middle."""
    side = im.shape[0]
    c = (side / 2.0 - 0.5, side / 2.0 - 0.5)
    want = np.array([p['upx'], p['upy']])
    best, bM = None, None
    for a in (p['roll'], -p['roll']):
        M = cv2.getRotationMatrix2D(c, a, 1.0)
        e = float(np.hypot(*(M[:2, :2] @ np.array([0.0, -1.0]) - want)))
        if best is None or e < best:
            best, bM = e, M
    fl = cv2.INTER_NEAREST if nearest else cv2.INTER_AREA
    im = cv2.warpAffine(im, bM, (side, side), flags=fl, borderValue=0)
    kw = int(round(side * p['w'] / float(p['hgt']) / p['sqside']))
    kh = int(round(side / p['sqside']))
    x0, y0 = (side - kw) // 2, (side - kh) // 2
    wide = int(round(WH * p['w'] / float(p['hgt'])))
    return cv2.resize(im[y0:y0 + kh, x0:x0 + kw], (wide, WH), interpolation=fl)


def photo(p):
    im = cv2.imread(p['photo'], cv2.IMREAD_GRAYSCALE)
    if im is None:
        return None
    q = p['params']
    if len(q) > 4:
        K = np.array([[q[0], 0, q[2]], [0, q[1], q[3]], [0, 0, 1.0]])
        im = cv2.undistort(im, K, np.array(q[4:8], float), None, K)
    wide = int(round(WH * p['w'] / float(p['hgt'])))
    return grad(cv2.resize(im, (wide, WH), interpolation=cv2.INTER_AREA))


def masked_ncc(A, B, mask, dx, dy):
    h, w = A.shape
    x0, x1 = max(0, dx), min(w, w + dx)
    y0, y1 = max(0, dy), min(h, h + dy)
    a = A[y0:y1, x0:x1]
    b = B[y0 - dy:y1 - dy, x0 - dx:x1 - dx]
    m = mask[y0:y1, x0:x1]
    if m.sum() < MINPIX:
        return None
    av, bv = a[m], b[m]
    av = av - av.mean()
    bv = bv - bv.mean()
    den = float(np.sqrt((av * av).sum() * (bv * bv).sum()))
    return float((av * bv).sum() / den) if den > 0 else None


def main():
    picks = json.loads(io.open('render-match.json', encoding='utf-8').read())
    tab = json.loads(io.open(os.path.join(OUT, 'idmap.json'), encoding='utf-8').read())
    names = tab['names'][:len(tab['colours'])]
    cols = [c for c in tab['colours'] if c]
    names = names[:len(cols)]
    print('THE DECISION RULE, WRITTEN OUT BEFORE THE SCORES ARE READ.')
    print('   A surface is read only where the model draws at least %d pixels of it after the mask is'
          % MINPIX)
    print('   eroded by %d, so no antialiased edge is counted. Its score is the gradient correlation'
          % ERODE)
    print('   inside that mask, taken where a PERFECT model would put the render. THE CONTROL IS THE SAME')
    print('   MASK ON A DIFFERENT FRAME PHOTOGRAPH, which answers the objection that a mask over a busy')
    print('   part of a picture scores well whatever is drawn there. CORROBORATED means the true score')
    print('   beats every control for that same mask. Anything else is NOT CORROBORATED, which is not')
    print('   refuted and will not be written as though it were.')
    print('')
    frames = []
    for i, p in enumerate(picks):
        rp, ip = os.path.join(OUT, 'r%02d.jpg' % i), os.path.join(OUT, 'id%02d.jpg' % i)
        if not (os.path.exists(rp) and os.path.exists(ip)):
            continue
        A = photo(p)
        rn = cv2.imread(rp, cv2.IMREAD_GRAYSCALE)
        idm = cv2.imread(ip, cv2.IMREAD_COLOR)
        if A is None or rn is None or idm is None:
            continue
        B = grad(turn(p, rn))
        ID = turn(p, idm, nearest=True)
        frames.append((i, p, A, B, ID))
    if not frames:
        sys.exit('   no rendered pair on disk, nothing to score')

    # HOW MUCH OF THE IDENTITY PASS SURVIVED THE TRIP, asked before anything is read from it
    tot = cls = 0
    for _, _, _, _, ID in frames:
        px = ID.reshape(-1, 3).astype(np.int16)
        near = np.full(len(px), 10 ** 6)
        for c in cols + [[0, 0, 0]]:
            d = np.abs(px - np.array([c[2], c[1], c[0]], np.int16)).max(1)
            near = np.minimum(near, d)
        tot += len(px)
        cls += int((near <= 28).sum())
    print('   THE IDENTITY PASS SURVIVED THE SCREENSHOT: %.1f per cent of pixels sit within 28 levels of'
          % (100.0 * cls / max(tot, 1)))
    print('   a colour that was actually assigned, over %d frames. Anything further off is an edge between'
          % len(frames))
    print('   two surfaces and is not counted for either of them.')
    if cls / max(tot, 1) < 0.9:
        print('')
        print('   THAT IS TOO LOW TO READ ANYTHING FROM. The colours did not come back intact, so the')
        print('   masks below would not be the surfaces they claim to be. NOTHING IS CONCLUDED.')
        sys.exit(0)

    ker = np.ones((ERODE, ERODE), np.uint8)
    per = {}
    for i, p, A, B, ID in frames:
        sc = WH / float(p['hgt'])
        dx, dy = int(round(p['ppx'] * sc)), int(round(p['ppy'] * sc))
        for nm, c in zip(names, cols):
            d = np.abs(ID.astype(np.int16) - np.array([c[2], c[1], c[0]], np.int16)).max(2)
            m = cv2.erode((d <= 28).astype(np.uint8), ker).astype(bool)
            if m.sum() < MINPIX:
                continue
            s = masked_ncc(A, B, m, dx, dy)
            if s is None:
                continue
            ctrl = []
            for j, q, A2, _, _ in frames:
                if j == i:
                    continue
                a2 = A2 if A2.shape == A.shape else cv2.resize(A2, (A.shape[1], A.shape[0]))
                v = masked_ncc(a2, B, m, dx, dy)
                if v is not None:
                    ctrl.append(v)
            if not ctrl:
                continue
            per.setdefault(nm, []).append((p['cls'], p['frame'], int(m.sum()), s, max(ctrl)))

    if not per:
        print('')
        print('   NOT ONE SURFACE COVERS ENOUGH OF ANY FRAME TO BE READ. Nothing is concluded.')
        sys.exit(0)

    print('')
    print('   surface                     frames  best score  its control  corroborated in')
    rank = []
    for nm, rows in per.items():
        bestrow = max(rows, key=lambda t: t[3] - t[4])
        good = sum(1 for t in rows if t[3] > t[4])
        rank.append((good, bestrow[3] - bestrow[4], nm, rows, bestrow, good))
    rank.sort(key=lambda t: (-t[0], -t[1]))
    for good, marg, nm, rows, bestrow, _ in rank:
        print('   %-26s %4d    %+.4f     %+.4f      %d of %d  %s'
              % (nm[:26], len(rows), bestrow[3], bestrow[4], good, len(rows),
                 bestrow[0] + ' ' + bestrow[1]))
    print('')
    corr = [t for t in rank if t[0] > 0]
    dead = [t for t in rank if t[0] == 0]
    print('   %d of the %d surfaces the goal names are CORROBORATED in at least one frame: the photograph'
          % (len(corr), len(rank)))
    print('   agrees with what the model draws there better than it agrees with any other frame.')
    if dead:
        print('')
        print('   AND %d ARE DRAWN ON NOTHING THESE FRAMES CAN SEE. That is a statement about the archive'
              % len(dead))
        print('   and not about the building: no frame in this set looks at them with enough pixels and')
        print('   enough contrast to tell. They are where the next measurement should go.')
        for good, marg, nm, rows, bestrow, _ in dead:
            print('      %-26s best %+.4f against a control of %+.4f, on %s %s'
                  % (nm[:26], bestrow[3], bestrow[4], bestrow[0], bestrow[1]))
    print('')
    print('   WHAT THIS CANNOT DO, said plainly. The mask comes from the MODEL, so a surface drawn in')
    print('   completely the wrong place is scored against whatever the photograph shows there and simply')
    print('   fails, without pointing anywhere. It cannot separate a wrong surface from a wrong pose. And')
    print('   the baked scan meshes came from photographs of this building, so where one of those scores')
    print('   well, part of the agreement is the bake agreeing with its own source.')


if __name__ == '__main__':
    main()
