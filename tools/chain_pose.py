# Poses for the 4K deck frames the register refused: the phone turned in place, so each refused frame is
# the previous frame's pose turned by the rotation that maps the one image onto the next (H = K R K^-1 on
# undistorted matches; the centre stays put). Chained from an ACCEPTED frame. Prints the pose-shot arguments
# (u d h fwdU fwdD pitch vfov) and the frame's camera in the hall frame, and saves the chain as JSON.
#   python tools/chain_pose.py <start_accepted> <end_index> [step]     e.g. d4_000196 240 4
import sys, os, json, cv2, numpy as np
import underside_geom as U
O = np.array([-54.907447, -1.43545, 3.040286]); HU = np.array([0.975681, 0, 0.219196]); HD = np.array([0.219196, 0, -0.975681])
IMG = 'E:/sitecapture-captures/ngv-video/day4k/images/'
start, end = sys.argv[1], int(sys.argv[2]); step = int(sys.argv[3]) if len(sys.argv) > 3 else 2
cams = U.load_class('day4k'); cam, _ = cams[start]
fx, fy, cx, cy, k1, k2, p1, p2 = cam.params; K = np.array([[fx, 0, cx], [0, fy, cy], [0, 0, 1]]); dist = np.array([k1, k2, p1, p2])
sift = cv2.SIFT_create(4000)
def feats(idx):
    im = cv2.imread(IMG + 'd4_%06d.png' % idx, 0); im = cv2.resize(im, None, fx=0.5, fy=0.5)
    kp, des = sift.detectAndCompute(im, None); pts = np.float32([k.pt for k in kp]) * 2
    return pts, des
def describe(R, C, idx):
    fwd = R.T @ np.array([0, 0, 1.0]); q = C - O
    u, d, h = q @ HU, q @ HD, q[1]; fu, fd = fwd @ HU, fwd @ HD; pitch = np.degrees(np.arcsin(fwd[1]))
    vfov = np.degrees(2 * np.arctan(cam.h / 2 / fy))
    return dict(frame='d4_%06d' % idx, u=float(u), d=float(d), h=float(h), fu=float(fu), fd=float(fd), pitch=float(pitch), vfov=float(vfov), R=R.tolist(), C=C.tolist())
R, C = cam.R.copy(), cam.center.copy(); i0 = int(start[3:9]); out = [describe(R, C, i0)]
pA, dA = feats(i0)
for i in range(i0 + step, end + 1, step):
    pB, dB = feats(i)
    m = cv2.BFMatcher().knnMatch(dA, dB, k=2); good = [a for a, b in m if a.distance < 0.75 * b.distance]
    if len(good) < 30: print('frame', i, 'only', len(good), 'matches, stop'); break
    a = np.float32([pA[g.queryIdx] for g in good]); b = np.float32([pB[g.trainIdx] for g in good])
    ua = cv2.undistortPoints(a.reshape(-1, 1, 2), K, dist, P=K).reshape(-1, 2); ub = cv2.undistortPoints(b.reshape(-1, 1, 2), K, dist, P=K).reshape(-1, 2)
    H, mask = cv2.findHomography(ua, ub, cv2.RANSAC, 4.0)
    Rr = np.linalg.inv(K) @ H @ K; Uq, _, Vt = np.linalg.svd(Rr); Rrel = Uq @ Vt
    if np.linalg.det(Rrel) < 0: Rrel = -Rrel
    R = Rrel @ R; pA, dA = pB, dB; rec = describe(R, C, i); rec['inliers'] = int(mask.sum()); out.append(rec)
    print('%s u %.2f d %.2f h %.2f fwd %.2f %.2f pitch %.1f inl %d' % (rec['frame'], rec['u'], rec['d'], rec['h'], rec['fu'], rec['fd'], rec['pitch'], rec['inliers']))
    if i in cams:   # an accepted frame on the way: report the drift against its registered pose, then re-anchor
        ca, _ = cams[i]; fw = ca.R.T @ np.array([0, 0, 1.0]); ang = np.degrees(np.arccos(np.clip(fw @ (R.T @ np.array([0, 0, 1.0])), -1, 1)))
        print('   accepted frame: chain forward off by %.2f deg; re-anchored' % ang); R, C = ca.R.copy(), ca.center.copy()
json.dump(out, open('E:/sitecapture-captures/ngv-site/agent-ref-walls/shots/pose/chain-%s-%d.json' % (start, end), 'w'), indent=1)
