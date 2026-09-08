# Projects a hall point into every frame of a chain (tools/chain_pose.py JSON) and prints the frames that see it,
# with the pixel; optionally saves a crop round the pixel per frame for reading a feature's parallax.
#   python tools/chain_project.py <chain.json> u d h [crop_px] [out_dir]
import sys, json, os, cv2, numpy as np
import underside_geom as U
O = np.array([-54.907447, -1.43545, 3.040286]); HU = np.array([0.975681, 0, 0.219196]); HD = np.array([0.219196, 0, -0.975681])
chain, u, d, h = sys.argv[1], *map(float, sys.argv[2:5])
crop = int(sys.argv[5]) if len(sys.argv) > 5 else 0; out = sys.argv[6] if len(sys.argv) > 6 else ''
recs = json.load(open(chain)); cam, _ = U.load_class('day4k')[recs[0]['frame']]
X = O + u * HU + d * HD + np.array([0, h, 0])
IM = 'E:/sitecapture-captures/ngv-video/day4k/images/'
for r in recs:
    R = np.array(r['R']); C = np.array(r['C'])
    cam.R = R; cam.t = -R @ C
    x, y, z = cam.project(np.asarray([X]))
    if z[0] <= 0 or not (0 <= x[0] < cam.w and 0 <= y[0] < cam.h): continue
    q = C - O
    print('%s px %.0f,%.0f  camera u %.2f d %.2f h %.2f  range %.2f' % (r['frame'], x[0], y[0], q @ HU, q @ HD, q[1], np.linalg.norm(X - C)))
    if crop and out:
        im = cv2.imread(IM + r['frame'] + '.png'); x0, y0 = int(x[0]) - crop, int(y[0]) - crop
        c = im[max(0, y0):y0 + 2 * crop, max(0, x0):x0 + 2 * crop]
        cv2.imwrite(os.path.join(out, 'lamp-%s.jpg' % r['frame']), c)
