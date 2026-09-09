# 2026-09-10: WHICH RECONSTRUCTION, IF ANY, HAS POINTS IN THE END RECESS.
#
# tools/end_cloud.py has only ever been pointed at ONE model, the day4k registration, and the archive's
# standing note is that the ends carry almost no surface: about 100 to 700 vertices per 2 m bin against
# 18,000 in the middle of the hall. That note was written about a capture shot from the hall FLOOR, forty
# metres away, looking almost edge-on into a dark recess. It says nothing about the balcony clips, which
# were shot on the upper level at the recess's own height and a few metres from it, and every one of those
# has its own reconstruction sitting in the register work directory. Nobody has looked.
#
# WHAT IS BEING ASKED. On 2026-09-10 the lower tier's deck, front and apron were deleted from the model
# because 33 rays crossed the space they occupied. What replaced them is an open recess whose sill, head
# and depth are all unmeasured. A reconstruction point IS a measurement of a surface: if any model carries
# a run of points inside that band, it measures the thing that is actually there.
#
# WHAT IT CANNOT DO. A census counts points; it fits nothing. A dense-looking bin can be one window
# reflection triangulated a hundred times, so every count is reported beside the number of DISTINCT images
# that saw those points and the median reprojection error, and a bin backed by two images is reported as
# what it is.
#   python tools/end_cloud_census.py [west|east|both]
import glob
import sys

import numpy as np

sys.path.insert(0, 'tools')
import colmap_bin as CB

O = np.array([-54.907447, -1.43545, 3.040286])
HU = np.array([0.975681, 0, 0.219196])
HD = np.array([0.219196, 0, -0.975681])
# the recess as the model now draws it: open from the ground soffit to the top slab, back wall on the
# plate end. u runs from the hall face into the end.
BANDS = {'west': {'uF': 4.194, 'uB': 0.344, 'lo': 5.30, 'hi': 8.08},
         'east': {'uF': 48.056, 'uB': 51.906, 'lo': 5.30, 'hi': 8.08}}
FILES = sorted(set(
    glob.glob('E:/sitecapture-captures/ngv-video/day4k-register/model/points3D.bin')
    + glob.glob('E:/sitecapture-captures/ngv-video/balcony2-register/model/points3D.bin')
    + glob.glob('E:/sitecapture-captures/ngv-video/balcony2-register/work/model-*/points3D.bin')))
which = sys.argv[1] if len(sys.argv) > 1 else 'both'
ends = ('west', 'east') if which == 'both' else (which,)

print('%d reconstructions on disk carry a points file' % len(FILES))
print('')
for f in FILES:
    name = f.replace('\\', '/').split('/')[-2]
    try:
        P = CB.read_points3d(f)
    except Exception as e:
        print('%-34s  unreadable: %s' % (name, e))
        continue
    xyz = P['xyz']
    q = xyz - O
    u, dd, hv = q @ HU, q @ HD, q[:, 1]
    detail = []
    for end in ends:
        B = BANDS[end]
        ulo, uhi = min(B['uF'], B['uB']) - 0.30, max(B['uF'], B['uB']) + 0.30
        sel = np.logical_and.reduce([u > ulo, u < uhi, dd > 1.0, dd < 14.4,
                                     hv > B['lo'], hv < B['hi']])
        n = int(sel.sum())
        if n == 0:
            detail.append('%-5s none' % end)
            continue
        idx = np.nonzero(sel)[0]
        imgs = set()
        tr = P.get('image_ids')
        if tr is not None:
            for i in idx:
                if i < len(tr) and tr[i] is not None:
                    imgs.update(list(tr[i]))
        er = P.get('error')
        med = float(np.median([er[i] for i in idx])) if er is not None else float('nan')
        detail.append('%-5s %5d pts, %3d imgs, %.2f px,  u %.2f to %.2f,  h %.2f to %.2f'
                      % (end, n, len(imgs), med, u[sel].min(), u[sel].max(),
                         hv[sel].min(), hv[sel].max()))
    print('%-34s %8d points total' % (name, len(xyz)))
    for line in detail:
        print('      ' + line)
