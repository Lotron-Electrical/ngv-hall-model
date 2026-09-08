# A posed frame beside the sim rendered from its pose (tools/pose-shot.mjs). Handles frames shot with
# the phone on its side: the roll is read off the camera's image-down axis, the sim is rendered
# upright at the frame's other field of view, and the frame is turned to match.
#   python tools/pose_pair.py <class> <frame> <hour> <house%> [out_prefix]
import sys, os, subprocess, cv2, numpy as np
sys.path.insert(0, 'tools'); import underside_geom as U
O = np.array([-54.907447, -1.43545, 3.040286]); HU = np.array([0.975681, 0, 0.219196]); HD = np.array([0.219196, 0, -0.975681])
cls, k, hour, house = sys.argv[1:5]; pref = sys.argv[5] if len(sys.argv) > 5 else k
S = 'E:/sitecapture-captures/ngv-site/agent-ref-walls/shots/pose/'; os.makedirs(S, exist_ok=True)
cam, p = U.load_class(cls)[k]
C = cam.center; q = C - O; u, d, h = q @ HU, q @ HD, q[1]
f = cam.R.T @ np.array([0, 0, 1.0]); fu, fd, fh = f @ HU, f @ HD, f[1]; hor = np.hypot(fu, fd); pitch = np.degrees(np.arcsin(fh))
x0, y0, _ = cam.project(np.asarray([C + f * 10])); x1, y1, _ = cam.project(np.asarray([C + f * 10 + (cam.R.T @ np.array([1.0, 0, 0]))]))
fx = np.hypot(x1[0] - x0[0], y1[0] - y0[0]) * 10
down = cam.R.T @ np.array([0, 1.0, 0])     # the image's down axis in the world
right = cam.R.T @ np.array([1.0, 0, 0])
if abs(down[1]) >= abs(right[1]):           # upright (or upside down)
    rot = None if down[1] < 0 else cv2.ROTATE_180; W, H = cam.w, cam.h
else:                                       # on its side: the image's right axis is the world's up or down
    rot = cv2.ROTATE_90_CLOCKWISE if right[1] < 0 else cv2.ROTATE_90_COUNTERCLOCKWISE; W, H = cam.h, cam.w
vfov = 2 * np.degrees(np.arctan(H / 2 / fx))
while W > 1080 or H > 1920: W, H = W // 2, H // 2   # the page renders 1080 wide at most: a 4K frame's sim came out half-width and clipped (2026-09-09)
sim = S + pref + '-sim.jpg'
cmd = ['node', 'tools/pose-shot.mjs', sim, str(W), str(H), '%.2f' % vfov, '%.3f' % u, '%.3f' % d, '%.3f' % h, '%.4f' % (fu / hor), '%.4f' % (fd / hor), '%.2f' % pitch, hour, house]
print(' '.join(cmd[2:]))
env = dict(os.environ, CDP_PORT=os.environ.get('CDP_PORT', '9334'))
r = subprocess.run(cmd, capture_output=True, text=True, env=env); print(r.stdout.strip()[-200:], r.stderr.strip()[-300:])
for ln in r.stdout.splitlines():
    if ln.startswith('pick'): print(ln)   # PICK=x,y;... names the mesh under a pixel of the sim
a = cv2.imread(p); a = cv2.rotate(a, rot) if rot is not None else a
b = cv2.imread(sim); a = cv2.resize(a, (b.shape[1], b.shape[0]))
for im, t in [(a, '%s %s (real)' % (cls, k)), (b, 'sim, same pose')]: cv2.putText(im, t, (12, 34), cv2.FONT_HERSHEY_SIMPLEX, 1.0, (0, 255, 255), 2)
pair = np.vstack([a, b]) if b.shape[1] > b.shape[0] else np.hstack([a, b])
out = S + pref + '-pair.jpg'; cv2.imwrite(out, pair, [cv2.IMWRITE_JPEG_QUALITY, 86]); print(out, pair.shape, 'rot', rot)
