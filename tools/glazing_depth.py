# Fold depth of the south glazing from the posed frames (walk, night, day4k) that see a bay obliquely.
# For each bay between two fins the apex mullion is drawn at candidate depths A behind the face
# (d = FACE + A) so its real image position reads off against the candidates. Frames are ranked by
# leverage (obliqueness x sharpness); only bays not occluded by the fins (view angle < 55 deg) count.
#   python tools/glazing_depth.py [A ...]     writes shots/glaz/depth-<frame>-bay<i>.jpg
import sys, os, cv2, numpy as np
sys.path.insert(0, 'tools'); import underside_geom as U
O = np.array([-54.907447, -1.43545, 3.040286]); HU = np.array([0.975681, 0, 0.219196]); HD = np.array([0.219196, 0, -0.975681])
def world(u, d, h): return O + u * HU + d * HD + np.array([0, h, 0])
OUT = 'E:/sitecapture-captures/ngv-site/agent-ref-walls/shots/glaz/'; os.makedirs(OUT, exist_ok=True)
FACE = 15.364; FINS = [18.48, 22.34, 26.20, 30.06, 33.93]; FINW = 0.40; FIND = 2.10
As = [float(a) for a in sys.argv[1:]] or [0.5, 1.0, 1.5, 2.09]
COLS = [(255, 0, 255), (0, 200, 0), (255, 128, 0), (0, 255, 255), (0, 0, 255), (255, 255, 0)]
def pr(cam, pts):
    x, y, z = cam.project(np.asarray(pts)); return x, y, z
cands = []
for cls in ('day4k', 'night', 'walk'):
    for k, (cam, p) in U.load_class(cls).items():
        C = cam.center; q = C - O; cu = q @ HU; cd = q @ HD
        if cd > FACE - 0.5: continue
        fwd = cam.R.T @ np.array([0, 0, 1.0])
        for i in range(4):
            um = (FINS[i] + FINS[i + 1]) / 2
            v = world(um, FACE, 4.0) - C; dist = np.linalg.norm(v); v /= dist
            if v @ fwd < np.cos(np.radians(48)): continue
            ang = np.degrees(np.arctan2(abs(um - cu), FACE - cd))      # from the wall normal
            if ang > 55 or ang < 15: continue
            x, y, z = pr(cam, [world(FINS[i], FACE, 1.0), world(FINS[i + 1], FACE, 1.0), world(um, FACE, 9.0), world(um, FACE + 2.1, 1.0)])
            if not (np.all(z > 0) and np.all(x > 20) and np.all(x < cam.w - 20) and np.all(y > 20) and np.all(y < cam.h - 20)): continue
            # leverage: image shift (px) of the apex between A=0 and A=2.1 at h 1
            x0, _, _ = pr(cam, [world(um, FACE, 1.0)]); x1, _, _ = pr(cam, [world(um, FACE + 2.1, 1.0)])
            lev = abs(float(x1[0] - x0[0]))
            cands.append((lev, cls, k, i, cu, cd, q[1], ang, p, cam))
cands.sort(key=lambda r: -r[0])
print(len(cands), 'frame/bay pairs; best leverage per bay:')
done = {}
for r in cands:
    lev, cls, k, i, cu, cd, ch, ang, p, cam = r
    if done.get(i, 0) >= 3: continue
    im = cv2.imread(p)
    sharp = cv2.Laplacian(cv2.resize(cv2.cvtColor(im, cv2.COLOR_BGR2GRAY), None, fx=0.3, fy=0.3), cv2.CV_32F).var()
    if sharp < 8: continue
    done[i] = done.get(i, 0) + 1
    um = (FINS[i] + FINS[i + 1]) / 2
    def vline(pu, pd, col, w):
        x, y, z = pr(cam, [world(pu, pd, 0.3), world(pu, pd, 10.5)])
        if np.all(z > 0): cv2.line(im, (int(x[0]), int(y[0])), (int(x[1]), int(y[1])), col, w, cv2.LINE_AA)
    for f in (FINS[i], FINS[i + 1]):
        vline(f - FINW / 2, FACE, (255, 255, 255), 1); vline(f + FINW / 2, FACE, (255, 255, 255), 1)
        vline(f - FINW / 2, FACE + FIND, (200, 200, 200), 1); vline(f + FINW / 2, FACE + FIND, (200, 200, 200), 1)
    for j, A in enumerate(As): vline(um, FACE + A, COLS[j % 6], 1)
    x, y, z = pr(cam, [world(FINS[i] - 1, FACE, 0.0), world(FINS[i + 1] + 1, FACE, 0.0), world(FINS[i] - 1, FACE, 11.0), world(FINS[i + 1] + 1, FACE, 11.0), world(um, FACE + 2.1, 0.0), world(um, FACE + 2.1, 11.0)])
    x0, x1 = int(max(0, x.min() - 40)), int(min(cam.w, x.max() + 40)); y0, y1 = int(max(0, y.min() - 40)), int(min(cam.h, y.max() + 40))
    c = im[y0:y1, x0:x1]
    sc = 900 / max(c.shape[0], 1) if c.shape[0] < 600 else 1.0
    if sc != 1.0: c = cv2.resize(c, None, fx=sc, fy=sc, interpolation=cv2.INTER_CUBIC)
    cv2.putText(c, '%s bay%d lev %.0fpx ang %.0f  A=%s' % (k, i, lev, ang, As), (8, 24), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 255), 2)
    for j, A in enumerate(As): cv2.putText(c, '%.2f' % A, (8, 50 + 20 * j), cv2.FONT_HERSHEY_SIMPLEX, 0.6, COLS[j % 6], 2)
    out = OUT + 'depth-%s-bay%d.jpg' % (k, i)
    cv2.imwrite(out, c, [cv2.IMWRITE_JPEG_QUALITY, 90])
    print('  bay%d %s %s lev %.0f px ang %.0f sharp %.0f cam u %.1f d %.1f h %.1f -> %s' % (i, cls, k, lev, ang, sharp, cu, cd, ch, out))
