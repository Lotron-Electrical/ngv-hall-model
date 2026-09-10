"""THE b7 TAIL (920 to 1224), SOLVED BUT REFUSED: WHERE THOSE POSES LAND AND WHAT THEY ARE GOOD FOR (2026-09-10).

tools/log_clip_sweep.py flagged b7 920 to 1224 as the closest view of any north opening in the dataset and the
registration target for the reveal depth. It turns out the 2026-09-09 b7s register already tried them: the
register took every 4th frame 0 to 1220 (306 frames), SOLVED 237, and the gate accepted 12 (inliers, rms,
standing band, walking-speed continuity); the pan chain (b7sp) later extended the accepted ones. The solved
but refused poses sit in balcony2-register/work/reg-b7s. This reads them for the tail.

THE CENSUS (74 tail frames solved, none accepted).
  On the WEST deck's north end, facing east, at a person's height: 1136, 1140, 1144, 1148, 1168, 1184,
    u 2.40 to 3.41, d 1.29 to 3.92, h 8.92 to 9.59. The northernmost, 1184, stands 1.3 m from the north
    wall plane.
  Impossible, 68 of them: 932 to 1120 mostly on u 18.9 to 19.3, d 4 to 11, h 9.5, FACING WEST, which is
    mid-air over the hall floor; the frames show the west deck's view east (south-1 near on the left, the
    east gallery far ahead), so the solver has matched the far east gallery to the near west one, the two
    ends being alike; others on u 49 (the east deck), on h 13 to 24, or off the building. The gate refused
    every one of them on inliers (3 to 29) or continuity, and it was right to.
  Not solved: 1188 to 1224 except 1200 (which solved off the building). These are the frames in which the
    first north openings are a metre or two away, obliquely, with a LIT REVEAL FACE beside each dark slot.

THE CONTROL ON THE SIX. The north-1 tapestry's outline (tools/tapestries.json) and openings 1 to 3 (WALLF,
sill 8.740, head 11.165) projected through 1184 and 1144 land on the tapestry and on the openings to within
a few per cent of the frame, offset by roughly a tenth of the tapestry's width: the poses are right to about
a quarter of a metre and a few degrees, and wrong by more than any reveal measurement can bear. So nothing
is measured from them; they are the PRIOR for the next step, a relocalisation of 1188 to 1224 seeded from
1184 with openings 1 to 3 as the control, which is the first thing in the archive that could measure the
reveal depth from close by.

CORRECTED BY THE FIRST RUN OF THIS FILE. The census above was written from a listing cut off after frame 1200. The
print says: 74 of the 75 tail frames solved (1128 did not); TEN stand on the west deck at a person's height (924,
928, 948, 1136, 1140, 1144, 1148, 1168, 1184, 1212); 39 sit on u 17 to 21 facing west in mid-air; 25 elsewhere
impossible, among them 1188 to 1220 bar 1212 on u 17 to 19 near the floor looking up (the floor taken for the
deck). 1212 stands on u 2.96, d 0.61, h 9.05 facing east and a little south, 0.6 m from the north wall plane, and
openings 1 and 2 with their reveal faces project through it onto the frame's right side, close to the real slots
and offset by about their own width: it, not 1184, is the seed.

Run:
  python tools/b7_tail_census.py
"""
import os, sys
import numpy as np
sys.path.insert(0, os.path.dirname(__file__))
from colmap_bin import read_model

REG = 'E:/sitecapture-captures/ngv-video/balcony2-register/work/reg-b7s'
O = np.array([-54.907447, -1.43545, 3.040286]); HU = np.array([0.975681, 0, 0.219196]); HD = np.array([0.219196, 0, -0.975681])
WEST_DECK = dict(u=(0.344, 4.194), d=(-0.5, 15.5), h=(8.6, 10.5))


def main():
    cams, imgs, _ = read_model(REG, with_points2d=False)
    rows = []
    for im in imgs.values():
        if not im.name.startswith('b7s_'): continue
        n = int(im.name.split('_')[1].split('.')[0])
        if n < 924: continue
        R = im.R(); t = np.asarray(im.t).reshape(3); c = -(R.T @ t); q = c - O; f = R[2]
        rows.append((n, float(q @ HU), float(q @ HD), float(q[1]), float(f @ HU), float(f @ HD), float(f[1])))
    rows.sort()
    on_deck = [r for r in rows if WEST_DECK['u'][0] <= r[1] <= WEST_DECK['u'][1] and WEST_DECK['d'][0] <= r[2] <= WEST_DECK['d'][1] and WEST_DECK['h'][0] <= r[3] <= WEST_DECK['h'][1]]
    midair = [r for r in rows if 17 < r[1] < 21 and r[4] < -0.9]
    print('%d tail frames solved (of %d taken every 4th from 924 to 1220); accepted by the gate: 0' % (len(rows), len(range(924, 1224, 4))))
    print('%d on the west deck at a person\'s height:' % len(on_deck))
    for r in on_deck: print('   b7s_%06d u %.2f d %.2f h %.2f fwd (%.2f %.2f %.2f)' % r)
    print('%d on u 17 to 21 facing west, mid-air over the hall (the two ends confused)' % len(midair))
    print('%d elsewhere impossible' % (len(rows) - len(on_deck) - len(midair)))
    solved = {r[0] for r in rows}
    print('not solved:', ' '.join('%d' % n for n in range(924, 1224, 4) if n not in solved))


if __name__ == '__main__':
    main()
