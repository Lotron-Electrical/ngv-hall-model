# Two pleat hypotheses for the south glazing drawn into the sharpest posed frames that face it:
#   A (declared, model.glb): fins 0.4 x 2.1 m projecting OUT from the face, glass legs from the fins'
#     inner edge outward to an apex 2.09 m behind the face (the V points into the court);
#   B: the same fins, glass legs from the fin going INWARD to an apex A metres in front of the fin
#     line (the V points into the hall), for A in the list.
# Every vertical edge of each hypothesis is drawn from h 0.3 to 11 m.   python tools/glazing_hyp.py [A ...]
import sys, os, cv2, numpy as np
sys.path.insert(0, 'tools'); import underside_geom as U
O = np.array([-54.907447, -1.43545, 3.040286]); HU = np.array([0.975681, 0, 0.219196]); HD = np.array([0.219196, 0, -0.975681])
def world(u, d, h): return O + u * HU + d * HD + np.array([0, h, 0])
OUT = 'E:/sitecapture-captures/ngv-site/agent-ref-walls/shots/glaz/'; os.makedirs(OUT, exist_ok=True)
FACE = 15.364
FINS = [18.48, 22.34, 26.20, 30.06, 33.93]   # measured centres (glazing.json), +-0.25
FINW = 0.40; FIND = 2.10
As = [float(a) for a in sys.argv[1:]] or [1.0, 1.6]
def edgesA():
    e = []
    for f in FINS: e += [(f - FINW / 2, FACE), (f + FINW / 2, FACE), (f - FINW / 2, FACE + FIND), (f + FINW / 2, FACE + FIND)]
    for i in range(4): e.append(((FINS[i] + FINS[i + 1]) / 2, FACE + 2.09))          # the apex mullion
    return e
def edgesB(A):
    e = []
    for f in FINS: e += [(f - FINW / 2, FACE), (f + FINW / 2, FACE), (f - FINW / 2, FACE + FIND), (f + FINW / 2, FACE + FIND)]
    for i in range(4): e.append(((FINS[i] + FINS[i + 1]) / 2, FACE - A))            # the apex mullion, inside
    return e
rows = []
for cls in ('night', 'walk'):
    for k, (cam, p) in U.load_class(cls).items():
        C = cam.center; q = C - O; u = q @ HU; d = q @ HD
        if d > 11 or u < 14 or u > 38: continue
        f = cam.R.T @ np.array([0, 0, 1.0]); v = world(26.2, FACE, 5.0) - C; v /= np.linalg.norm(v)
        if v @ f < np.cos(np.radians(50)): continue
        uu, vv, zz = cam.project(np.asarray([world(22.0, FACE, 1.5), world(30.5, FACE, 1.5), world(26.2, FACE, 8.0)]))
        if not (np.all(zz > 0) and np.all(uu > 0) and np.all(uu < cam.w) and np.all(vv > 0) and np.all(vv < cam.h)): continue
        sharp = cv2.Laplacian(cv2.resize(cv2.imread(p, 0), None, fx=0.3, fy=0.3), cv2.CV_32F).var()
        rows.append((sharp, cls, k, u, d, q[1], p, cam))
rows.sort(reverse=True)
print(len(rows), 'frames hold the middle three fins; sharpest:')
for r in rows[:6]: print('  %s %s sharp %.0f u %.1f d %.1f h %.1f' % (r[1], r[2], r[0], r[3], r[4], r[5]))
def draw(im, cam, edges, col, w):
    for (pu, pd) in edges:
        x, y, z = cam.project(np.asarray([world(pu, pd, 0.3), world(pu, pd, 11.0)]))
        if np.all(z > 0): cv2.line(im, (int(x[0]), int(y[0])), (int(x[1]), int(y[1])), col, w, cv2.LINE_AA)
for r in rows[:4]:
    sharp, cls, k, u, d, h, p, cam = r
    im = cv2.imread(p)
    draw(im, cam, edgesA(), (0, 255, 255), 2)
    for j, A in enumerate(As): draw(im, cam, edgesB(A), [(255, 0, 255), (0, 200, 0), (255, 128, 0)][j % 3], 1)
    uu, vv, zz = cam.project(np.asarray([world(17.5, FACE, 0.0), world(35.0, FACE, 0.0), world(17.5, FACE, 12.0), world(35.0, FACE, 12.0)]))
    x0, x1 = int(max(0, uu.min() - 60)), int(min(cam.w, uu.max() + 60)); y0, y1 = int(max(0, vv.min() - 60)), int(min(cam.h, vv.max() + 60))
    c = im[y0:y1, x0:x1]
    cv2.putText(c, '%s  yellow=A declared  magenta/green=B apex in %s' % (k, As), (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.8, (255, 255, 255), 2)
    cv2.imwrite(OUT + 'hyp-%s.jpg' % k, c, [cv2.IMWRITE_JPEG_QUALITY, 90])
print('wrote', OUT)
