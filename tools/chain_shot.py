# A chain-posed 4K frame (tools/chain_pose.py JSON) beside the sim rendered from its pose, like pose_pair.py for
# the register's frames. Handles the phone on its side or upside down the same way.
#   python tools/chain_shot.py <chain.json> <frame> <hour> <house%> <out_prefix>
import sys, os, json, subprocess, cv2, numpy as np
sys.path.insert(0, 'tools'); import underside_geom as U
O = np.array([-54.907447, -1.43545, 3.040286]); HU = np.array([0.975681, 0, 0.219196]); HD = np.array([0.219196, 0, -0.975681])
chain, k, hour, house, pref = sys.argv[1:6]
recs = json.load(open(chain)); rec = [r for r in recs if r['frame'] == k][0]
cname = recs[0].get('cname', 'day4k'); cam, _ = U.load_class(cname)[recs[0]['frame']]; R = np.array(rec['R']); C = np.array(rec['C'])
ipath = U.CLASSES[cname].get('frames', 'E:/sitecapture-captures/ngv-video/day4k/images/') + '%s.png' % k
S = 'E:/sitecapture-captures/ngv-site/agent-ref-walls/shots/pose/'
q = C - O; u, d, h = q @ HU, q @ HD, q[1]
f = R.T @ np.array([0, 0, 1.0]); fu, fd, fh = f @ HU, f @ HD, f[1]; hor = max(np.hypot(fu, fd), 1e-6); pitch = np.degrees(np.arcsin(fh))
fx = cam.params[0]
down = R.T @ np.array([0, 1.0, 0]); right = R.T @ np.array([1.0, 0, 0])
if abs(down[1]) >= abs(right[1]):
    rot = None if down[1] < 0 else cv2.ROTATE_180; W, H = cam.w, cam.h
else:
    rot = cv2.ROTATE_90_CLOCKWISE if right[1] < 0 else cv2.ROTATE_90_COUNTERCLOCKWISE; W, H = cam.h, cam.w
vfov = 2 * np.degrees(np.arctan(H / 2 / fx))
sim = S + pref + '-sim.jpg'
cmd = ['node', 'tools/pose-shot.mjs', sim, str(W), str(H), '%.2f' % vfov, '%.3f' % u, '%.3f' % d, '%.3f' % h, '%.4f' % (fu / hor), '%.4f' % (fd / hor), '%.2f' % pitch, hour, house]
print(' '.join(cmd[2:]))
env = dict(os.environ, CDP_PORT=os.environ.get('CDP_PORT', '9334'))
r = subprocess.run(cmd, capture_output=True, text=True, env=env); print(r.stdout.strip()[-200:], r.stderr.strip()[-300:])
a = cv2.imread(ipath); a = cv2.rotate(a, rot) if rot is not None else a
b = cv2.imread(sim); a = cv2.resize(a, (b.shape[1], b.shape[0]))
for im, t in [(a, 'chain %s (real)' % k), (b, 'sim, same pose')]: cv2.putText(im, t, (12, 34), cv2.FONT_HERSHEY_SIMPLEX, 1.0, (0, 255, 255), 2)
pair = np.vstack([a, b]) if b.shape[1] > b.shape[0] else np.hstack([a, b])
out = S + pref + '-pair.jpg'; cv2.imwrite(out, pair, [cv2.IMWRITE_JPEG_QUALITY, 86]); print(out, pair.shape, 'rot', rot)
