# Posed frames that see a whole north opening (all four corners in frame, in front, margin from the edges), ranked
# by how much of the corridor behind it the sightline reaches. For measuring what is behind the wall.
#   python tools/find_openseers.py <class> <opening index 0-11> [margin_px]
import sys, numpy as np
sys.path.insert(0, 'tools'); import underside_geom as U
O = np.array([-54.907447, -1.43545, 3.040286]); HU = np.array([0.975681, 0, 0.219196]); HD = np.array([0.219196, 0, -0.975681])
OPEN = [[4.076,5.332],[7.676,8.932],[10.764,12.020],[15.132,16.388],[18.628,19.876],[22.336,23.592],[26.044,27.300],[29.948,31.196],[33.588,34.836],[37.348,38.596],[40.884,42.140],[44.508,45.756]]
cname = sys.argv[1]; k = int(sys.argv[2]); m = float(sys.argv[3]) if len(sys.argv) > 3 else 40
u0, u1 = OPEN[k]; H0, H1 = 8.99, 11.35
pts = np.array([O + u * HU + (-0.09) * HD + np.array([0, h, 0]) for u in (u0, u1) for h in (H0, H1)])
rows = []
for fr, (cam, ip) in U.load_class(cname).items():
    x, y, z = cam.project(pts)
    if (z <= 0.3).any() or (x < m).any() or (x > cam.w - m).any() or (y < m).any() or (y > cam.h - m).any(): continue
    C = cam.center; q = C - O
    # how high up the corridor back wall (d = -2.99) the ray through the OUTER head edge reaches
    slope = (H1 - q[1]) / (q @ HD + 0.99)
    reach = H1 + slope * 2.0
    span = float(np.hypot(x[0] - x[2], y[0] - y[2]))   # the opening's width in pixels
    rows.append((-span, fr, q @ HU, q @ HD, q[1], reach, span, ip))
rows.sort()
for r in rows[:12]: print('%-14s camera u %6.2f d %6.2f h %5.2f  head ray reaches h %5.2f at the back wall  opening %4.0f px wide' % (r[1], r[2], r[3], r[4], r[5], r[6]))
print(len(rows), 'frames see the whole opening')
if rows: print('best image:', rows[0][7])
