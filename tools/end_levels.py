# 2026-09-09: the balcony levels at the two ends, measured against the photographs instead of asserted.
# The loaded scan carries almost no surface at either end (tools/scan-coverage.mjs: about 100-700 vertices
# per 2 m bin out there against 18,000 in the hall's middle), so nothing at the ends can be checked against
# the reconstruction. What CAN check them is the posed floor imagery: every balcony level is a long
# horizontal edge across the end wall, and a projected line that sits on the real edge is a correct level.
# For each level this projects its line into every frame that sees it, walks a short profile across the
# line in the image, takes the strongest brightness gradient as the real edge, and reports the offset in
# metres. A positive offset means the real edge sits HIGHER than the model draws it.
#   python tools/end_levels.py <class> <west|east> [max_frames]
import sys, os, cv2, numpy as np
sys.path.insert(0, 'tools'); import underside_geom as U; import edge_refine as ER
O = np.array([-54.907447, -1.43545, 3.040286]); HU = np.array([0.975681, 0, 0.219196]); HD = np.array([0.219196, 0, -0.975681])
FACE = {'west': 4.194, 'east': 48.056}
# every horizontal line the model draws across the end face, from ENDW in index.html
LEVELS = [('ground-wall top', 5.30), ('apron top', 5.40), ('lower deck', 6.33), ('lower parapet top', 6.85),
          ('top slab soffit', 8.08), ('top deck', 8.34), ('top parapet top', 9.02), ('head', 11.10), ('end-wall top', 13.50)]
# LEVELS_SET lets a caller redraw one level without editing this file, which is how the follow bias is
# tested: measure the same physical edge with the model putting it in two different places and see whether
# the absolute height comes back the same. tools/follow_test.py does exactly that.
import os as _os
if _os.environ.get('LEVELS_SET'):
    _o = dict(kv.split('=') for kv in _os.environ['LEVELS_SET'].split(','))
    LEVELS = [(n, float(_o.get(n, h))) for n, h in LEVELS]
cls, end = sys.argv[1], sys.argv[2]
# THE TWO ENDS CAN BE DRAWN AT DIFFERENT HEIGHTS, and once they are, one shared LEVELS table silently
# measures one of them against a line the model no longer draws. That happened the moment ENDW gained a
# per-end upstand: the east parapet moved to 9.11 in index.html while this file went on searching around
# 9.02. Whatever the right value turns out to be, the tool has to search where the model draws, so the
# per-end levels are stated here and picked by the end under test. UPSTANDS mirrors ENDW.upstands.
UPSTANDS = {'west': 0.68, 'east': 0.77}
DECK = 8.34
LEVELS = [(n, (DECK + UPSTANDS[end]) if n == 'top parapet top' else h) for n, h in LEVELS]
maxf = int(sys.argv[3]) if len(sys.argv) > 3 else 40
uF = float(sys.argv[4]) if len(sys.argv) > 4 else FACE[end]   # a 4th argument overrides the face, so the
# same measurement can be swept across face positions. That sweep is the discriminator: an offset that
# is really a wrong FACE position moves as the face moves and zeroes for every level at one u, while a
# wrong HEIGHT stays put whatever the face does.
# The profile window is set in METRES, not pixels, and never reaches past halfway to the next modelled
# level. Without that the search grabs whichever edge is strongest nearby: run wide, the deck line
# (8.34), the slab soffit (8.08) and the parapet top (8.90) all reported the SAME edge near h 8.92,
# because from the floor the deck and the soffit are hidden behind the parapet and only its top is
# ever in view. A level whose window closes below 0.12 m cannot be told from its neighbour and is
# reported as not separable rather than given a number.
# THE WINDOW IS A CONSTANT, and that is the second half of the follow fix (2026-09-09). It used to be
# 0.45 x the gap to the nearest modelled level, which sounds careful and is circular: the level under test
# sets its own search width, so redrawing it changed both where the search starts AND how far it may go.
# Measured, that alone carried a large part of the follow gain. The width is now the same for every level
# and every draw. Separability is still checked against the neighbours, because a level whose neighbour is
# inside the window genuinely cannot be told apart from it, but that check only refuses a level, it never
# changes the search.
HS = sorted(h for _, h in LEVELS)
WINC = float(os.environ.get('WINDOW', 0.25))
def window(hv):
    near = min((abs(hv - o) for o in HS if abs(o - hv) > 1e-6), default=1.0)
    return WINC if near > 2.2 * WINC else 0.0     # 0.0 means: its neighbour is inside the window
frames = U.load_class(cls)
# A level 0.15 m out reads as about 10 px from the far side of the hall through these lenses, and a
# hand-held walking frame can carry that much motion blur on its own. So the frames are ranked by sharpness
# (the variance of a Laplacian, on a quarter-size read) and only the sharpest are measured: if an offset
# survives on the sharp frames it is geometry, and if it shrinks it was the blur pulling the gradient peak
# onto the bright side of an asymmetric edge.
cand = []
for fr, (cam, ip) in frames.items():
    pts = np.array([O + uF * HU + dd * HD + np.array([0, 9.02, 0]) for dd in (2.5, 7.5, 12.5)])
    x, y, z = cam.project(pts)
    if (z <= 0.5).any(): continue
    if ((x > 40) * (x < cam.w - 40) * (y > 40) * (y < cam.h - 40)).sum() < 2: continue
    small = cv2.imread(ip, cv2.IMREAD_REDUCED_GRAYSCALE_4)
    if small is None: continue
    cand.append((float(cv2.Laplacian(small, cv2.CV_32F).var()), fr))
cand.sort(reverse=True)
print('%d frames see the %s end; sharpness p50 %.0f, best %.0f, worst %.0f'
      % (len(cand), end, np.median([c[0] for c in cand]) if cand else 0,
         cand[0][0] if cand else 0, cand[-1][0] if cand else 0))
order = [c[1] for c in cand[:maxf]]
acc = {n: [] for n, _ in LEVELS}
used = 0
for fr in order:
    cam, ip = frames[fr]
    if used >= maxf: break
    img = None
    for name, hv in LEVELS:
        ds = np.linspace(2.5, 12.5, 21)
        pts = np.array([O + uF * HU + dd * HD + np.array([0, hv, 0]) for dd in ds])
        up = np.array([O + uF * HU + dd * HD + np.array([0, hv + 0.25, 0]) for dd in ds])
        x, y, z = cam.project(pts); xu, yu, zu = cam.project(up)
        win = window(hv)
        if win <= 0.0:
            acc[name] = None; continue                    # its neighbour is too close to separate
        ok = (z > 0.5) * (zu > 0.5) * (x > 40) * (x < cam.w - 40) * (y > 40) * (y < cam.h - 40)
        if ok.sum() < 8: continue
        if img is None:
            img = cv2.imread(ip, cv2.IMREAD_GRAYSCALE)
            if img is None: break
            img = cv2.GaussianBlur(img, (5, 5), 0)
            used += 1
        offs = []
        for i in np.flatnonzero(ok):
            vx, vy = xu[i] - x[i], yu[i] - y[i]          # the image direction of 0.25 m upward, here
            L = np.hypot(vx, vy)
            if L < 6: continue                            # too foreshortened to resolve a level
            mpp = 0.25 / L                                # metres per pixel along that direction
            ux, uy = vx / L, vy / L
            # tools/edge_refine.py, not a single look: search, re-centre on what was found, search again
            # until it stops moving. An audit showed the single look FOLLOWED the drawn line, returning a
            # different height for the same physical edge depending on where the model put it (drawn 8.90
            # gave h 9.057, drawn 9.02 gave h 9.093 from the same 25 frames). The fixed point does not.
            e = ER.find_edge(img, x[i], y[i], ux, uy, mpp, win, min_contrast=12.0)
            if e is None: continue
            offs.append(e)
        if len(offs) >= 6:
            q = cam.center - O; du = abs(float(q @ HU) - uF)      # how far down the hall this camera stands
            acc[name].append((float(np.median(offs)), du))
# The same lesson the wall jambs taught (tools/wall_pool.py): one capture's quartiles say how well its own
# consecutive frames agree, not how well the level is known. So each capture writes its medians out and
# tools/level_pool.py pools them across captures, where the spread that matters lives.
import json, os
if os.environ.get('LEVEL_JSON'):
    rec = {}
    for nm, hv in LEVELS:
        a = acc[nm]
        if a is None or len(a) < 3: continue
        v = [x[0] for x in a]
        rec[nm] = {'h': hv, 'n': len(v), 'median': float(np.median(v)),
                   'p25': float(np.percentile(v, 25)), 'p75': float(np.percentile(v, 75))}
    json.dump({'class': cls, 'end': end, 'face': uF, 'frames': used, 'levels': rec},
              open(os.environ['LEVEL_JSON'], 'w'), indent=1)
    print('wrote', os.environ['LEVEL_JSON'])
print('%s, %s end, %d frames used' % (cls, end, used))
for name, hv in LEVELS:
    if acc[name] is None:
        print('  %-18s h %5.2f   not separable from its neighbour (window under 0.12 m)' % (name, hv)); continue
    a = np.array(acc[name])
    if a.shape[0] < 3: print('  %-18s h %5.2f   only %d frames could resolve it' % (name, hv, a.shape[0])); continue
    v, du = a[:, 0], a[:, 1]
    o = np.argsort(du); k = max(3, len(o) // 3)
    near, far = v[o[:k]], v[o[-k:]]
    # A wrong FACE position looks bigger from close up and smaller from far away; a wrong HEIGHT does not
    # care where the camera stands. The near/far split is what tells those two apart.
    print('  %-18s h %5.2f   n %3d   offset median %+.3f m  p25 %+.3f  p75 %+.3f   near %.0f m %+.3f | far %.0f m %+.3f'
          % (name, hv, len(v), np.median(v), np.percentile(v, 25), np.percentile(v, 75),
             np.median(du[o[:k]]), np.median(near), np.median(du[o[-k:]]), np.median(far)))
