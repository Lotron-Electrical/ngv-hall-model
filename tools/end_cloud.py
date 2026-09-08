# The certified cloud at an end of the hall: a (u, h) occupancy map, d 2-13, so the tiers' depths
# show as runs of points.   python tools/end_cloud.py <east|west> [model_dir]
import sys, numpy as np
sys.path.insert(0, 'tools'); import colmap_bin as CB
O = np.array([-54.907447, -1.43545, 3.040286]); HU = np.array([0.975681, 0, 0.219196]); HD = np.array([0.219196, 0, -0.975681])
side = sys.argv[1]; d = sys.argv[2] if len(sys.argv) > 2 else 'E:/sitecapture-captures/ngv-video/day4k-register/model'
xyz = CB.read_points3d(d + '/points3D.bin')['xyz']; q = xyz - O; u = q @ HU; dd = q @ HD; h = q[:, 1]
ulo, uhi = (42.0, 52.0) if side == 'east' else (0.0, 10.0)
sel = np.logical_and.reduce([u > ulo, u < uhi, dd > 2, dd < 13, h > 3, h < 12.5])
print(side, sel.sum(), 'points')
ub = np.arange(ulo, uhi + 0.01, 0.25); hb = np.arange(3, 12.51, 0.25)
H, _, _ = np.histogram2d(u[sel], h[sel], bins=[ub, hb])
print('u \ h ' + ' '.join('%4.1f' % a for a in hb[:-1]))
for i in range(len(ub) - 1):
    row = H[i]
    print('%5.2f ' % ub[i] + ' '.join(('%4d' % c if c else '   .') for c in row))
