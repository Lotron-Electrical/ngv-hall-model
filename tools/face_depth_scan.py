# 2026-09-09: how well do the rays constrain the DEPTH of the north wall at all? Scan it and see.
#
# Three numbers now claim to be the depth of that wall. The model draws d -0.090. The head, put through
# three averaging windows, averages -0.123. The nine jamb lines average -0.207. The head and the jambs are
# different orientations of the same fit reading the same masonry and they disagree by 84 mm.
#
# ONE OF THE TWO FITS IS KNOWN TO BE WELL CONDITIONED AND THE OTHER IS NOT. The jambs survived the window
# audit (12 to 36 mm of movement) and survived the anchoring test positively: forcing their depth onto the
# drawn face FRAGMENTED each jamb into two or three lines spread over 0.33 m, which is what happens when
# rays that really meet an edge elsewhere are made to agree on the wrong plane. The horizontal fits are
# the ones with the disease: the sill slid 285 mm in depth across three windows along a perfectly straight
# line, and the head slid 26 mm along one too, just less far.
#
# SO STOP FITTING THE DEPTH AND SCAN IT. Fix d, and the ray equation vh*(d - cd) - vd*(h - ch) = 0 gives
# the height directly, one unknown per ray, with nothing left to slide. Sweep d across the whole plausible
# range and plot how many rays agree and how closely. If the wall's depth is really in this data the curve
# has a minimum at it. If the curve is flat, the depth was never measured by these edges and the 84 mm
# argument is an argument about noise.
#   EDGE=head python tools/face_depth_scan.py      EDGE=sill python tools/face_depth_scan.py
import os

import numpy as np

OUT = 'E:/sitecapture-captures/ngv-site/agent-ref-walls/shots/walls'
EDGE = os.environ.get('EDGE', 'head')
DRAWN = {'sill': 8.778, 'head': 11.222}[EDGE]
DS = np.arange(-0.40, 0.081, 0.005)
THRESH = 0.06


def solve_h(R, dfix):
    """for a fixed depth, each ray gives the height of the line it met, directly"""
    vd = np.where(np.abs(R[:, 2]) < 1e-9, 1e-9, R[:, 2])
    return R[:, 1] + R[:, 3] * (dfix - R[:, 0]) / vd


def perp(R, dv, hv):
    num = R[:, 3] * (dv - R[:, 0]) - R[:, 2] * (hv - R[:, 1])
    return np.abs(num) / np.sqrt(R[:, 2] ** 2 + R[:, 3] ** 2)


src = os.path.join(OUT, 'wall-%s-rays.npy' % EDGE)
A = np.load(src)
R = A[:, :4]
print('%s: %d rays from cameras standing d %.2f to %.2f'
      % (EDGE.upper(), len(R), R[:, 0].min(), R[:, 0].max()))
print('')
print('   depth      height   rays within 60 mm   median miss')
best = None
rows = []
for dv in DS:
    h = solve_h(R, float(dv))
    sel = np.abs(h - DRAWN) < 1.0                 # stay on this edge, not a course half a metre away
    if sel.sum() < 50:
        continue
    hv = float(np.median(h[sel]))
    res = perp(R, float(dv), hv)
    inl = res < THRESH
    if int(inl.sum()) < 50:
        continue
    med = float(np.median(res[inl]))
    rows.append((float(dv), hv, int(inl.sum()), med))
    if best is None or inl.sum() > best[2]:
        best = (float(dv), hv, int(inl.sum()), med)
for dv, hv, n, med in rows[::4]:
    bar = '#' * int(round(60.0 * n / max(r[2] for r in rows)))
    print('   %+.3f    %7.3f   %5d  %-40s %3.0f mm' % (dv, hv, n, bar, 1000 * med))

print('')
if not rows:
    raise SystemExit('nothing to scan')
ns = np.array([r[2] for r in rows], float)
dsv = np.array([r[0] for r in rows])
peak = ns.max()
wide = dsv[ns >= 0.98 * peak]
print('   most rays agree at d %+.3f, giving h %.3f on %d rays with a %.0f mm median'
      % (best[0], best[1], best[2], 1000 * best[3]))
print('   the count stays within 2 per cent of its peak from d %+.3f to %+.3f, a band %.0f mm wide'
      % (wide.min(), wide.max(), 1000 * (wide.max() - wide.min())))
print('   over the whole sweep the height runs %.3f to %.3f, so a %.0f mm error in depth is a %.0f mm'
      % (min(r[1] for r in rows), max(r[1] for r in rows),
         1000 * (dsv.max() - dsv.min()), 1000 * (max(r[1] for r in rows) - min(r[1] for r in rows))))
print('   error in height: that ratio IS the degeneracy, written out')
if (wide.max() - wide.min()) > 0.15:
    print('')
    print('   THE CURVE IS FLAT. These rays do not measure the depth of this wall; they measure one')
    print('   combination of depth and height, and any depth inside that band fits them about equally')
    print('   well. The 84 mm argument between the head and the jambs is not a disagreement about a')
    print('   measured quantity, because one side of it was never measuring it.')
else:
    print('')
    print('   the curve has a real minimum, so this edge does carry a depth of its own')
