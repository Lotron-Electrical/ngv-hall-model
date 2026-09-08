# 2026-09-09: THE OPENINGS' SILL AND HEAD, the one wall dimension never yet tested.
# Every wall measurement so far has been horizontal: where the jambs stand along the hall. The openings
# also have a top and a bottom, openY [8.99, 11.35] in index.html, and those two numbers have never been
# checked against a photograph at all. They are long horizontal edges on the north wall's face, which is
# exactly what tools/end_levels.py was built to find, so the same instrument is turned ninety degrees:
# instead of a line at a fixed u across an end wall, a line at a fixed h running along the north wall face.
# THE SEARCH WINDOW IS HALF A COURSE, and that is the whole difficulty here. The bluestone coursing on
# this wall is measured (0.304 m courses, north joints h = 0.080 + 0.304k, from 4 mm orthophotos of 1,026
# posed frames), so a real bed joint sits within 0.152 m of ANY height on this face. Searching wider than
# that guarantees grabbing a course line instead of the opening, which is the same trap the end levels fell
# into when the deck, the soffit and the parapet all reported one edge. The window is therefore 0.14 m.
#   python tools/open_levels.py <class> [max_frames]
#   OPEN_JSON=out.json python tools/open_levels.py <class>
import sys, os, json, cv2, numpy as np
sys.path.insert(0, 'tools'); import underside_geom as U; import edge_refine as ER
O = np.array([-54.907447, -1.43545, 3.040286]); HU = np.array([0.975681, 0, 0.219196]); HD = np.array([0.219196, 0, -0.975681])
DN = -0.090                     # the north wall's inner face
OPENINGS = [[4.098,5.310],[7.697,8.911],[10.785,11.998],[15.154,16.367],[18.646,19.859],[22.357,23.570],
            [26.066,27.279],[29.816,31.028],[33.495,34.706],[37.177,38.383],[40.906,42.118],[44.526,45.739]]
LEVELS = [('sill', 8.99), ('head', 11.35)]
WIN = 0.14                      # half a course, less a margin
INSET = 0.15                    # keep the samples clear of the jambs
# THE OBLIQUITY GATE. The first pass split cleanly by capture, not by opening: the two floor walks, which
# stand 13-30 m out and look at this wall nearly square, both read the head about 0.09 low, while the two
# balcony clips, which see the same wall from 25-45 m down the hall at a grazing angle, read it near zero.
# A grazing view is the worse instrument and it is worth saying so with a number rather than a preference,
# so each sample now carries the angle between the camera ray and the wall's own normal, and samples past
# MAXANG are refused. Set MAXANG=90 to turn the gate off and see the raw disagreement again.
MAXANG = float(os.environ.get('MAXANG', 60.0))
NRM = HD                        # the north wall's inner face looks toward increasing d, into the hall
cls = sys.argv[1]
maxf = int(sys.argv[2]) if len(sys.argv) > 2 else 30

frames = U.load_class(cls)
# rank by sharpness on the same argument end_levels.py uses: 0.1 m on this wall is a few pixels from the
# far side of the hall, and a hand-held walking frame can carry that much blur by itself
cand = []
for fr, (cam, ip) in frames.items():
    seen = 0
    for u0, u1 in OPENINGS:
        p = np.array([O + ((u0+u1)/2) * HU + DN * HD + np.array([0, 10.17, 0])])
        x, y, z = cam.project(p)
        if z[0] > 0.5 and 40 < x[0] < cam.w - 40 and 40 < y[0] < cam.h - 40: seen += 1
    if not seen: continue
    small = cv2.imread(ip, cv2.IMREAD_REDUCED_GRAYSCALE_4)
    if small is None: continue
    cand.append((float(cv2.Laplacian(small, cv2.CV_32F).var()), seen, fr))
cand.sort(reverse=True)
print('%s: %d frames see at least one opening; sharpness best %.0f, p50 %.0f'
      % (cls, len(cand), cand[0][0] if cand else 0, np.median([c[0] for c in cand]) if cand else 0))

acc = {}                        # (level, opening index) -> [(offset, distance)]
used = 0
for _, _, fr in cand[:maxf]:
    cam, ip = frames[fr]
    img = None
    for name, hv in LEVELS:
        for oi, (u0, u1) in enumerate(OPENINGS):
            us = np.linspace(u0 + INSET, u1 - INSET, 9)
            pts = np.array([O + uu * HU + DN * HD + np.array([0, hv, 0]) for uu in us])
            up = np.array([O + uu * HU + DN * HD + np.array([0, hv + 0.25, 0]) for uu in us])
            x, y, z = cam.project(pts); xu, yu, zu = cam.project(up)
            ok = (z > 0.5) * (zu > 0.5) * (x > 30) * (x < cam.w - 30) * (y > 30) * (y < cam.h - 30)
            if ok.sum() < 5: continue
            if img is None:
                img = cv2.imread(ip, cv2.IMREAD_GRAYSCALE)
                if img is None: break
                img = cv2.GaussianBlur(img, (5, 5), 0); used += 1
            offs, angs = [], []
            for i in np.flatnonzero(ok):
                ray = cam.center - pts[i]; rl = np.linalg.norm(ray)
                ang = np.degrees(np.arccos(np.clip(float(ray @ NRM) / max(rl, 1e-6), -1, 1)))
                if ang > MAXANG: continue
                vx, vy = xu[i] - x[i], yu[i] - y[i]; L = np.hypot(vx, vy)
                if L < 4: continue                      # 0.25 m is under 4 px here: nothing to resolve
                mpp = 0.25 / L; ux, uy = vx / L, vy / L
                # the fixed-point finder (tools/edge_refine.py). A single look follows the drawn line.
                e = ER.find_edge(img, x[i], y[i], ux, uy, mpp, WIN, min_contrast=10.0)
                if e is None: continue
                offs.append(e); angs.append(ang)
            if len(offs) >= 4:
                q = cam.center - O
                du = float(np.hypot(float(q @ HU) - (u0+u1)/2, float(q @ HD) - DN))
                acc.setdefault((name, oi), []).append((float(np.median(offs)), du, float(np.median(angs))))
        if img is None: break

print('%s, %d frames used' % (cls, used))
rec = {}
for name, hv in LEVELS:
    per = []
    print('  %s, drawn h %.2f' % (name.upper(), hv))
    for oi, (u0, u1) in enumerate(OPENINGS):
        a = acc.get((name, oi))
        if not a or len(a) < 3:
            print('    opening %2d  u %6.2f   %s' % (oi + 1, (u0+u1)/2, 'not resolved' if not a else 'only %d frames' % len(a)))
            continue
        v = np.array([p[0] for p in a]); d = np.array([p[1] for p in a]); g = np.array([p[2] for p in a])
        per.append(float(np.median(v)))
        rec['%s-%d' % (name, oi + 1)] = {'h': hv, 'u': (u0+u1)/2, 'n': len(v), 'median': float(np.median(v)),
                                         'p25': float(np.percentile(v, 25)), 'p75': float(np.percentile(v, 75)),
                                         'dist': float(np.median(d)), 'ang': float(np.median(g))}
        print('    opening %2d  u %6.2f   n %3d   %+0.3f m   p25 %+0.3f p75 %+0.3f   seen from %.0f m, %.0f deg off square'
              % (oi + 1, (u0+u1)/2, len(v), np.median(v), np.percentile(v, 25), np.percentile(v, 75), np.median(d), np.median(g)))
    if per:
        print('    %s across %d openings: median %+0.3f m, spread %.3f' % (name, len(per), float(np.median(per)), float(max(per) - min(per))))
if os.environ.get('OPEN_JSON'):
    json.dump({'class': cls, 'frames': used, 'maxang': MAXANG, 'levels': rec}, open(os.environ['OPEN_JSON'], 'w'), indent=1)
    print('wrote', os.environ['OPEN_JSON'])
