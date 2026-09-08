# 2026-09-09: THE SOUTH WALL, which has never been measured at all.
# Everything done on the north wall (twelve openings, their sill and head, and the face depth fitted to
# 3 mm) has no counterpart here, and the reason given was that the south glazing comes from the scan mesh
# rather than a table, so there are no drawn vertical lines to search for. That is only true of the
# GLAZING. The south face also carries three grilles and two doors, and those ARE tables in index.html,
# which gives ten vertical edges on this wall to work with:
#   grilles  [4.682,5.610] [9.346,10.242] [42.714,43.670]   at h 2.82 to 3.27
#   doors    [37.962,39.662] head 2.906   [45.698,48.218] head 2.522
# Same instrument as the north wall: project each edge as a vertical line, walk a profile ACROSS it,
# take the fixed point of tools/edge_refine.py, and report the offset along u. A positive offset means the
# real edge stands further east than the model draws it. Every per-frame reading is written out as well,
# because the same rows feed tools/face_depth.py, which fits the SOUTH face depth the identified way.
#   SOUTH_JSON=x.json SOUTH_RAW=x.csv python tools/south_edges.py <class> [max_frames]
import sys, os, json, cv2, numpy as np
sys.path.insert(0, 'tools'); import underside_geom as U; import edge_refine as ER
O = np.array([-54.907447, -1.43545, 3.040286]); HU = np.array([0.975681, 0, 0.219196]); HD = np.array([0.219196, 0, -0.975681])
DFACE = 15.364                     # the south wall's inner face
# name, u, the height band the edge actually exists over
TARGETS = [
    ('grille 1 west', 4.682, 2.954, 3.262), ('grille 1 east', 5.610, 2.954, 3.262),
    ('grille 2 west', 9.346, 2.994, 3.266), ('grille 2 east', 10.242, 2.994, 3.266),
    ('grille 3 west', 42.714, 2.822, 3.114), ('grille 3 east', 43.670, 2.822, 3.114),
    ('door 1 west', 37.962, 0.35, 2.906), ('door 1 east', 39.662, 0.35, 2.906),
    ('door 2 west', 45.698, 0.35, 2.522), ('door 2 east', 48.218, 0.35, 2.522),
]
WINC = float(os.environ.get('WINDOW', 0.25))
cls = sys.argv[1]
maxf = int(sys.argv[2]) if len(sys.argv) > 2 else 25
frames = U.load_class(cls)
sharp, sees = {}, {}
for fr, (cam, ip) in frames.items():
    vis = []
    for name, uu, h0, h1 in TARGETS:
        hs = (h0 + 0.05, (h0 + h1) / 2, h1 - 0.05)
        pts = np.array([O + uu * HU + DFACE * HD + np.array([0, hv, 0]) for hv in hs])
        side = np.array([O + (uu + 0.25) * HU + DFACE * HD + np.array([0, hv, 0]) for hv in hs])
        x, y, z = cam.project(pts); xs, ys, zs = cam.project(side)
        ok = (z > 0.5) * (zs > 0.5) * (x > 30) * (x < cam.w - 30) * (y > 30) * (y < cam.h - 30)
        if ok.sum() >= 2 and np.hypot(xs[1] - x[1], ys[1] - y[1]) >= 5: vis.append(name)
    if not vis: continue
    small = cv2.imread(ip, cv2.IMREAD_REDUCED_GRAYSCALE_4)
    if small is None: continue
    sharp[fr] = float(cv2.Laplacian(small, cv2.CV_32F).var()); sees[fr] = vis
want = {}
for name, uu, h0, h1 in TARGETS:
    order = sorted((f for f in sharp if name in sees[f]), key=lambda f: -sharp[f])[:maxf]
    for f in order: want.setdefault(f, []).append(name)
acc = {n: [] for n, _, _, _ in TARGETS}
used = 0
for fr in sorted(want, key=lambda f: -sharp[f]):
    cam, ip = frames[fr]
    img = None
    for name in want[fr]:
        uu, h0, h1 = next((u, a, b) for n, u, a, b in TARGETS if n == name)
        hs = np.linspace(h0 + 0.04, h1 - 0.04, 13)
        pts = np.array([O + uu * HU + DFACE * HD + np.array([0, hv, 0]) for hv in hs])
        side = np.array([O + (uu + 0.25) * HU + DFACE * HD + np.array([0, hv, 0]) for hv in hs])
        x, y, z = cam.project(pts); xs, ys, zs = cam.project(side)
        ok = (z > 0.5) * (zs > 0.5) * (x > 30) * (x < cam.w - 30) * (y > 30) * (y < cam.h - 30)
        if ok.sum() < 5: continue
        if img is None:
            img = cv2.imread(ip, cv2.IMREAD_GRAYSCALE)
            if img is None: break
            img = cv2.GaussianBlur(img, (5, 5), 0); used += 1
        offs = []
        for i in np.flatnonzero(ok):
            vx, vy = xs[i] - x[i], ys[i] - y[i]; L = np.hypot(vx, vy)
            if L < 5: continue
            e = ER.find_edge(img, x[i], y[i], vx / L, vy / L, 0.25 / L, WINC, min_contrast=10.0)
            if e is None: continue
            offs.append(e)
        if len(offs) >= 5:
            q = cam.center - O
            along = float(q @ HU) - uu
            out = DFACE - float(q @ HD)          # how far the camera stands out from THIS wall
            acc[name].append((float(np.median(offs)), float(np.hypot(along, out)), along, along / max(out, 0.5)))
print('%s, %d frames used' % (cls, used))
rec = {}
for name, uu, h0, h1 in TARGETS:
    a = acc[name]
    if len(a) < 3:
        print('  %-15s u %6.3f   only %d frames' % (name, uu, len(a))); continue
    v = np.array([p[0] for p in a]); d = np.array([p[1] for p in a])
    rec[name] = {'u': uu, 'n': len(v), 'median': float(np.median(v)),
                 'p25': float(np.percentile(v, 25)), 'p75': float(np.percentile(v, 75))}
    print('  %-15s u %6.3f   n %3d   %+0.3f m   p25 %+0.3f p75 %+0.3f   seen from %.0f m'
          % (name, uu, len(v), np.median(v), np.percentile(v, 25), np.percentile(v, 75), np.median(d)))
if os.environ.get('SOUTH_JSON'):
    json.dump({'class': cls, 'frames': used, 'jambs': rec}, open(os.environ['SOUTH_JSON'], 'w'), indent=1)
    print('wrote', os.environ['SOUTH_JSON'])
if os.environ.get('SOUTH_RAW'):
    with open(os.environ['SOUTH_RAW'], 'w') as fh:
        print('class,jamb,u,offset,dist,along,ratio', file=fh)
        for nm, rows in acc.items():
            uu = next(u for n, u, _, _ in TARGETS if n == nm)
            for r in rows:
                print('%s,%s,%.3f,%.4f,%.3f,%.3f,%.4f' % (cls, nm, uu, r[0], r[1], r[2], r[3]), file=fh)
    print('wrote', os.environ['SOUTH_RAW'])
