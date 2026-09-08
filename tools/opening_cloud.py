# The certified sparse cloud inside the north wall's high openings: every point with u inside an
# opening, h in its height band and d behind the face, binned by depth. If the reveals and the
# corridor beyond were ever seen, their points are here.   python tools/opening_cloud.py [model_dir]
import sys, numpy as np
sys.path.insert(0, 'tools'); import colmap_bin as CB
O = np.array([-54.907447, -1.43545, 3.040286]); HU = np.array([0.975681, 0, 0.219196]); HD = np.array([0.219196, 0, -0.975681])
d = sys.argv[1] if len(sys.argv) > 1 else 'E:/sitecapture-captures/ngv-video/day4k-register/model'
pts = CB.read_points3d(d + '/points3D.bin')
xyz = pts['xyz']
q = xyz - O; u = q @ HU; dd = q @ HD; h = q[:, 1]
print('points', len(xyz))
OPS = [[4.076, 5.332], [7.676, 8.932], [10.764, 12.020], [15.132, 16.388], [18.628, 19.876], [22.336, 23.592], [26.044, 27.300], [29.948, 31.196], [33.588, 34.836], [37.348, 38.596], [40.884, 42.140], [44.508, 45.756]]
def band(lo, hi, x): return np.logical_and(x > lo, x < hi)
allsel = np.zeros(len(xyz), bool)
for i, (a, b) in enumerate(OPS):
    sel = np.logical_and.reduce([band(a - 0.05, b + 0.05, u), band(8.9, 11.45, h), dd < 0.3])
    allsel = np.logical_or(allsel, sel)
    if sel.sum(): print('opening %2d u %.2f-%.2f: %3d points, d quantiles' % (i, a, b, sel.sum()), np.round(np.quantile(dd[sel], [0.05, 0.25, 0.5, 0.75, 0.95]), 2))
if allsel.sum():
    hist, edges = np.histogram(dd[allsel], bins=np.arange(-4.0, 0.4, 0.2))
    for c, e in zip(hist, edges): print('d %5.1f..%5.1f %4d %s' % (e, e + 0.2, c, '#' * int(c)))
sel = np.logical_and.reduce([band(3, 47, u), band(8.5, 12.5, h), dd < -0.3])
print('behind the north face, h 8.5-12.5, anywhere:', sel.sum(), 'points')
if sel.sum():
    hist, edges = np.histogram(dd[sel], bins=np.arange(-6.0, -0.2, 0.2))
    for c, e in zip(hist, edges): print('d %5.1f..%5.1f %4d %s' % (e, e + 0.2, c, '#' * min(int(c), 80)))
