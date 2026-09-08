# chain_pose.py for any class with a "frames" directory (the balcony2 clips): poses for the frames the register
# refused, chained from an ACCEPTED frame by the rotation that maps one image onto the next (H = K R K^-1 on
# undistorted matches; the centre stays put), re-anchored on every accepted frame met on the way. Saves
# shots/pose/chain-<class>-<start>-<end>.json with R and C per frame, readable by chain_pixel.py / chain_shot.py
# when given the class.
#   python tools/chain_pose2.py <class> <start_accepted> <end_index> [step] [--back]
#   e.g. python tools/chain_pose2.py b6s b6s_001126 1040 2 --back   (walks the index DOWN from 1126 to 1040)
import sys, os, json, cv2, numpy as np
import underside_geom as U
O = np.array([-54.907447, -1.43545, 3.040286]); HU = np.array([0.975681, 0, 0.219196]); HD = np.array([0.219196, 0, -0.975681])
cname, start, end = sys.argv[1], sys.argv[2], int(sys.argv[3])
step = int(sys.argv[4]) if len(sys.argv) > 4 and not sys.argv[4].startswith('--') else 2
back = '--back' in sys.argv
spec = U.CLASSES[cname]; IMG = spec.get('frames', spec['img']); pre = start.split('_')[0]
cams = U.load_class(cname); cam, _ = cams[start]
fx, fy, cx, cy, *rest = cam.params; k1, k2, p1, p2 = (list(rest) + [0, 0, 0, 0])[:4]
K = np.array([[fx, 0, cx], [0, fy, cy], [0, 0, 1]]); dist = np.array([k1, k2, p1, p2], float)
sift = cv2.SIFT_create(4000)
def fname(idx): return '%s_%06d' % (pre, idx)
def feats(idx):
    im = cv2.imread(IMG + fname(idx) + '.png', 0)
    if im is None: return None, None
    im = cv2.resize(im, None, fx=0.5, fy=0.5)
    kp, des = sift.detectAndCompute(im, None); pts = np.float32([k.pt for k in kp]) * 2
    return pts, des
def describe(R, C, idx):
    fwd = R.T @ np.array([0, 0, 1.0]); q = C - O
    u, d, h = q @ HU, q @ HD, q[1]; fu, fd = fwd @ HU, fwd @ HD; pitch = np.degrees(np.arcsin(fwd[1]))
    vfov = np.degrees(2 * np.arctan(cam.h / 2 / fy))
    return dict(frame=fname(idx), cname=cname, u=float(u), d=float(d), h=float(h), fu=float(fu), fd=float(fd), pitch=float(pitch), vfov=float(vfov), R=R.tolist(), C=C.tolist())
R, C = cam.R.copy(), cam.center.copy(); i0 = int(start.split('_')[1]); out = [describe(R, C, i0)]
pA, dA = feats(i0)
rng = range(i0 - step, end - 1, -step) if back else range(i0 + step, end + 1, step)
for i in rng:
    pB, dB = feats(i)
    if pB is None: print('frame', i, 'missing, skip'); continue
    m = cv2.BFMatcher().knnMatch(dA, dB, k=2); good = [a for a, b in m if a.distance < 0.75 * b.distance]
    if len(good) < 30: print('frame', i, 'only', len(good), 'matches, stop'); break
    a = np.float32([pA[g.queryIdx] for g in good]); b = np.float32([pB[g.trainIdx] for g in good])
    ua = cv2.undistortPoints(a.reshape(-1, 1, 2), K, dist, P=K).reshape(-1, 2); ub = cv2.undistortPoints(b.reshape(-1, 1, 2), K, dist, P=K).reshape(-1, 2)
    H, mask = cv2.findHomography(ua, ub, cv2.RANSAC, 4.0)
    if H is None: print('frame', i, 'no homography, stop'); break
    Rr = np.linalg.inv(K) @ H @ K; Uq, _, Vt = np.linalg.svd(Rr); Rrel = Uq @ Vt
    if np.linalg.det(Rrel) < 0: Rrel = -Rrel
    R = Rrel @ R; pA, dA = pB, dB; rec = describe(R, C, i); rec['inliers'] = int(mask.sum()); out.append(rec)
    print('%s u %.2f d %.2f h %.2f fwd %.2f %.2f pitch %.1f inl %d' % (rec['frame'], rec['u'], rec['d'], rec['h'], rec['fu'], rec['fd'], rec['pitch'], rec['inliers']))
    if fname(i) in cams:
        ca, _ = cams[fname(i)]; fw = ca.R.T @ np.array([0, 0, 1.0]); ang = np.degrees(np.arccos(np.clip(fw @ (R.T @ np.array([0, 0, 1.0])), -1, 1)))
        print('   accepted frame: chain forward off by %.2f deg; re-anchored' % ang); R, C = ca.R.copy(), ca.center.copy()
json.dump(out, open('E:/sitecapture-captures/ngv-site/agent-ref-walls/shots/pose/chain-%s-%s-%d.json' % (cname, start, end), 'w'), indent=1)
print('saved chain-%s-%s-%d.json (%d frames)' % (cname, start, end, len(out)))
