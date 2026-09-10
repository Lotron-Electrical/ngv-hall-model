"""THE LEDGE'S TONE AGAINST THE HALL FLOOR'S, FROM THE DECK FRAMES THAT SEE BOTH (2026-09-10).

The ledge tops on both decks are drawn in upstandMat (day 0x4a4540, "about the stone"), which renders as light
as the sim's own floor; in every posed deck frame the ledge is near black against a bright floor. This reads
the ratio, which needs no exposure: along the edge each sweep found (tools/ledge_edge.py on the east,
tools/ledge_edge_west.py on the west), the median grey of a strip 30 to 120 px below the edge (the ledge top)
over the median grey of a strip 40 to 130 px above it (the hall floor seen over the edge).

THE RULE, DECLARED WITH THE RUN (this is a material, not a dimension; it was measured first and the rule
written with the numbers in view, and says so). The two decks must agree within their spreads or nothing is
drawn from it. If they do, the coping top gets its own material whose day colour is the sim's rendered floor
tone times the pooled ratio, divided by the sim's own rendering factor for these unlit materials (upstandMat
day 0x4a, 74, renders 59 in the b7s_000080 pose: 0.80), and the record carries the spread as a range of
colours the drawn one must sit inside. The parapet faces the hall sees keep upstandMat: nothing here looked
at them.

THE RESULT. East, ten frames: ratio 0.087 to 0.226, median 0.136, half-range 0.069. West, eleven frames: median
0.118; nine of them 0.097 to 0.162, and two (876, 920) read 0.60 and 0.76 because the strip below the edge in
those two holds the phone case and a hand, not the ledge; they are printed and not used. The decks agree
(0.136 against 0.118, inside the east spread). The sim's floor in the same pose renders 52 (the median of the
floor patch in the b7s_000080 render), so the ledge top should render 0.136 x 52 = 7, a day colour of 9 with
the factor, in a range of 4 to 13 from the spread; the file draws copingMat day 0x0c0b0a (12), inside it, night
0x050504. What the number cannot say: whether the sim's floor is the right tone in the first place; the ratio
is what the frames give and the coping follows the sim's floor wherever that goes.

Run:
  python tools/ledge_tone.py
"""
import os, sys
import numpy as np, cv2
sys.path.insert(0, os.path.dirname(__file__))
import underside_geom as U

O = np.array([-54.907447, -1.43545, 3.040286]); HU = np.array([0.975681, 0, 0.219196]); HD = np.array([0.219196, 0, -0.975681])
EAST = {68: 48.45, 72: 48.47, 76: 48.48, 80: 48.49, 132: 48.47, 136: 48.41, 140: 48.38, 144: 48.36, 148: 48.29, 152: 48.56}
WEST = {876: 3.44, 884: 3.63, 888: 3.68, 892: 3.74, 896: 3.74, 900: 3.69, 904: 3.64, 908: 3.64, 912: 3.63, 916: 3.65, 920: 3.64}
OUTLIERS = (876, 920)   # the phone case and a hand lie in the strip below the edge in these two


def W(u, d, h): return O + u * HU + d * HD + np.array([0, h, 0])


def main():
    cams = {}
    for cls in ('b7s', 'b7sp'):
        for k, v in U.load_class(cls).items(): cams.setdefault(k, v)
    pooled = {}
    for side, table, htop in (('east', EAST, 9.095), ('west', WEST, 9.097)):
        rs = []
        for fno, ue in sorted(table.items()):
            cam, ip = cams['b7s_%06d' % fno]; q = cam.center - O
            g = cv2.cvtColor(cv2.imread(ip), cv2.COLOR_BGR2GRAY).astype(np.float32)
            dc = q @ HD; ds = np.arange(dc - 2.5, dc + 1.0, 0.05)
            x, y, z = cam.project(np.array([W(ue, d, htop) for d in ds]))
            ok = np.logical_and.reduce([z > 0.2, x > 2, x < cam.w - 3, y > 130, y < cam.h - 130])
            xi = x[ok].astype(int); yi = y[ok].astype(int)
            ledge = np.median(np.concatenate([g[yi + o, xi] for o in range(30, 120, 10)]))
            floor = np.median(np.concatenate([g[yi - o, xi] for o in range(40, 130, 10)]))
            r = ledge / floor
            print('%s b7s_%06d: ledge %.0f floor %.0f ratio %.3f%s' % (side, fno, ledge, floor, r, '  (not used)' if fno in OUTLIERS else ''))
            if fno not in OUTLIERS: rs.append(r)
        rs = np.array(rs); pooled[side] = rs
        print('%s: ratio median %.3f, range %.3f to %.3f, half-range %.3f' % (side, np.median(rs), rs.min(), rs.max(), (rs.max() - rs.min()) / 2))
    e, w = np.median(pooled['east']), np.median(pooled['west'])
    hr = (pooled['east'].max() - pooled['east'].min()) / 2
    agree = abs(e - w) <= hr
    print('the decks %s: %.3f east against %.3f west, the east spread %.3f' % ('AGREE' if agree else 'DISAGREE, nothing drawn', e, w, hr))
    floor_sim, factor = 52.0, 0.80
    print('the ledge top should render %.1f against the sim floor %.0f: day colour %.0f, range %.0f to %.0f' % (e * floor_sim, floor_sim, e * floor_sim / factor, (e - hr) * floor_sim / factor, (e + hr) * floor_sim / factor))


if __name__ == '__main__':
    main()
