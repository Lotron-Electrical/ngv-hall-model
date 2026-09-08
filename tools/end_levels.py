# 2026-09-09: the balcony levels at the two ends, measured against the photographs instead of asserted.
# The loaded scan carries almost no surface at either end (tools/scan-coverage.mjs: about 100-700 vertices
# per 2 m bin out there against 18,000 in the hall's middle), so nothing at the ends can be checked against
# the reconstruction. What CAN check them is the posed floor imagery: every balcony level is a long
# horizontal edge across the end wall, and a projected line that sits on the real edge is a correct level.
# For each level this projects its line into every frame that sees it, walks a short profile across the
# line in the image, takes the strongest brightness gradient as the real edge, and reports the offset in
# metres. A positive offset means the real edge sits HIGHER than the model draws it.
#   python tools/end_levels.py <class> <west|east> [max_frames]
import sys, cv2, numpy as np
sys.path.insert(0, 'tools'); import underside_geom as U
O = np.array([-54.907447, -1.43545, 3.040286]); HU = np.array([0.975681, 0, 0.219196]); HD = np.array([0.219196, 0, -0.975681])
FACE = {'west': 4.194, 'east': 48.056}
# every horizontal line the model draws across the end face, from ENDW in index.html
LEVELS = [('ground-wall top', 5.30), ('apron top', 5.40), ('lower deck', 6.33), ('lower parapet top', 6.85),
          ('top slab soffit', 8.08), ('top deck', 8.34), ('top parapet top', 9.02), ('head', 11.10), ('end-wall top', 13.50)]
cls, end = sys.argv[1], sys.argv[2]
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
HS = sorted(h for _, h in LEVELS)
def window(hv):
    near = min((abs(hv - o) for o in HS if abs(o - hv) > 1e-6), default=1.0)
    return min(0.35, 0.45 * near)
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
        if win < 0.12:
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
            R = int(round(win / mpp))
            if R < 5 or R > 90: continue                   # unresolvable, or so close the window is huge
            t = np.arange(-R, R + 1)
            sx = np.clip(np.round(x[i] + ux * t).astype(int), 0, img.shape[1] - 1)
            sy = np.clip(np.round(y[i] + uy * t).astype(int), 0, img.shape[0] - 1)
            prof = img[sy, sx].astype(np.float32)
            if prof.max() - prof.min() < 12: continue     # no edge here, only noise
            g = np.abs(np.gradient(prof))
            j = int(np.argmax(g[3:-3])) + 3
            offs.append(float(t[j]) * mpp)
        if len(offs) >= 6:
            q = cam.center - O; du = abs(float(q @ HU) - uF)      # how far down the hall this camera stands
            acc[name].append((float(np.median(offs)), du))
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
