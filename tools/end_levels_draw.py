# 2026-09-09: the model's end-wall levels drawn on a real posed frame, with the edge the measurement
# actually found beside each one. Yellow is where the model puts the level; green is the strongest
# brightness edge inside the search window, which is what tools/end_levels.py reports as the offset.
#   python tools/end_levels_draw.py <class> <frame> <west|east> <out.jpg>
import sys, cv2, numpy as np
sys.path.insert(0, 'tools'); import underside_geom as U
O = np.array([-54.907447, -1.43545, 3.040286]); HU = np.array([0.975681, 0, 0.219196]); HD = np.array([0.219196, 0, -0.975681])
FACE = {'west': 4.194, 'east': 48.056}
LEVELS = [('lower deck', 6.33), ('top parapet top', 9.02), ('head', 11.10), ('end-wall top', 13.50)]
cls, k, end, out = sys.argv[1], sys.argv[2], sys.argv[3], sys.argv[4]
uF = FACE[end]; cam, ip = U.load_class(cls)[k]
img = cv2.imread(ip); g = cv2.GaussianBlur(cv2.cvtColor(img, cv2.COLOR_BGR2GRAY), (5, 5), 0)
ds = np.linspace(2.5, 12.5, 41)
for name, hv in LEVELS:
    pts = np.array([O + uF * HU + dd * HD + np.array([0, hv, 0]) for dd in ds])
    up = np.array([O + uF * HU + dd * HD + np.array([0, hv + 0.25, 0]) for dd in ds])
    x, y, z = cam.project(pts); xu, yu, zu = cam.project(up)
    ok = (z > 0.5) * (zu > 0.5) * (x > 40) * (x < cam.w - 40) * (y > 40) * (y < cam.h - 40)
    idx = np.flatnonzero(ok)
    if idx.size < 6: continue
    cv2.polylines(img, [np.round(np.stack([x[idx], y[idx]], 1)).astype(np.int32)], False, (0, 235, 255), 2)
    cv2.putText(img, '%s %.2f' % (name, hv), (int(x[idx[0]]) + 6, int(y[idx[0]]) - 6), 0, 0.55, (0, 235, 255), 1)
    fx, fy = [], []
    for i in idx:
        vx, vy = xu[i] - x[i], yu[i] - y[i]; L = np.hypot(vx, vy)
        if L < 6: continue
        mpp = 0.25 / L; R = int(round(0.35 / mpp))
        if R < 5 or R > 90: continue
        t = np.arange(-R, R + 1)
        sx = np.clip(np.round(x[i] + vx / L * t).astype(int), 0, img.shape[1] - 1)
        sy = np.clip(np.round(y[i] + vy / L * t).astype(int), 0, img.shape[0] - 1)
        prof = g[sy, sx].astype(np.float32)
        if prof.max() - prof.min() < 12: continue
        j = int(np.argmax(np.abs(np.gradient(prof))[3:-3])) + 3
        fx.append(x[i] + vx / L * t[j]); fy.append(y[i] + vy / L * t[j])
    if len(fx) >= 6:
        cv2.polylines(img, [np.round(np.stack([fx, fy], 1)).astype(np.int32)], False, (80, 255, 80), 2)
# these clips are shot with the phone on its side; turn the drawing upright the way the camera was held
down = cam.R.T @ np.array([0, 1.0, 0]); right = cam.R.T @ np.array([1.0, 0, 0])
if abs(down[1]) >= abs(right[1]): rot = None if down[1] < 0 else cv2.ROTATE_180
else: rot = cv2.ROTATE_90_CLOCKWISE if right[1] < 0 else cv2.ROTATE_90_COUNTERCLOCKWISE
if rot is not None: img = cv2.rotate(img, rot)
cv2.imwrite(out, img); print('wrote', out, img.shape, 'rot', rot)
