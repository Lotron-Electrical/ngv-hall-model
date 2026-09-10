"""THE LEDGE'S TONE AGAINST THE HALL FLOOR'S, FROM THE DECK FRAMES THAT SEE BOTH (2026-09-10).

The ledge tops on both decks were drawn in upstandMat (day 0x4a4540, "about the stone"), which renders as
light as the sim's own floor; in every posed deck frame the ledge looks dark against a bright floor. This
reads ratios, which need no exposure, along the edge each sweep found (tools/ledge_edge.py on the east,
tools/ledge_edge_west.py on the west): the median grey of strips below the edge in the image (the ledge
side) over the median grey of a strip 40 to 130 px above it (the hall floor seen over the edge).

THE FIRST RUN, AND WHAT IT MEASURED. One strip, 30 to 120 px below the edge, read 0.136 of the floor on the
east (ten frames, 0.087 to 0.226) and 0.118 on the west (nine frames; two more, 876 and 920, hold the phone
case and a hand there and are not used), and the coping top was drawn near black from it, copingMat day
0x0c0b0a. THAT STRIP IS NOT THE LEDGE TOP. A profile across the edge (rows -480 to +480, every 60 px) in
b7s_000896, 000888 and 000080 shows the floor above the edge, a dark strip 60 to 150 px wide right under it
(14 to 45 grey), and then the ledge top proper: 98 to 118 on the west against a floor of 141 to 164, and 55
to 58 on the east against 166 to 189. The dark strip is a NOSING along the ledge's outer edge, about 0.08 m
wide by its width in the frame at the ledge's distance (by eye), and it is what the first run measured.

THE RULE, AMENDED AFTER THAT PROFILE AND SAID SO. Two strips per frame: the nosing, 30 to 120 px below the
edge, and the top, 180 to 420 px below it (frames whose edge sits too low for the top strip are skipped for
it). The nosing keeps the first run's numbers and gets its own material and a 0.08 m width by eye. The top:
if the two decks agree within the larger spread, one colour from the pooled median; if they do not, the
midpoint of the two medians is drawn as a hint with both medians and the disagreement recorded, because a
single material has to carry both decks and the frames are two exposures of the same stone. The colour
follows the sim's floor (52 in the b7s_000080 render) through the 0.80 factor these unlit materials render
at, and the record carries the range. The parapet faces the hall sees keep upstandMat: nothing here looked
at them.

THE SECOND RUN. Nosing: 0.136 east (ten frames, 0.087 to 0.226), 0.117 west (nine, 0.097 to 0.162). Top: 0.398 east
(six frames, 0.344 to 0.544; four have it out of frame), 0.789 west (eight, 0.647 to 0.877). The decks disagree on
the top by more than the larger spread (0.115): the midpoint 0.593 is drawn as a hint, copingMat day 0x272523 (39,
range 26 to 51); the nosing nosingMat day 0x080807 (8), 0.08 m wide by eye. Why the tops differ is not known; the
east sees its top from a grazing 41 to 48 degrees and the west from between 50 and 66, a guess and labelled one.

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
OUTLIERS = (876, 920)   # the phone case and a hand lie in the strips below the edge in these two
NOSE = range(30, 120, 10); TOP = range(180, 421, 20); FLOOR = range(40, 130, 10)
FLOOR_SIM, FACTOR = 52.0, 0.80


def W(u, d, h): return O + u * HU + d * HD + np.array([0, h, 0])


def main():
    cams = {}
    for cls in ('b7s', 'b7sp'):
        for k, v in U.load_class(cls).items(): cams.setdefault(k, v)
    nose = {}; top = {}
    for side, table, htop in (('east', EAST, 9.095), ('west', WEST, 9.097)):
        nose[side] = []; top[side] = []
        for fno, ue in sorted(table.items()):
            cam, ip = cams['b7s_%06d' % fno]; q = cam.center - O
            g = cv2.cvtColor(cv2.imread(ip), cv2.COLOR_BGR2GRAY).astype(np.float32)
            dc = q @ HD; ds = np.arange(dc - 2.5, dc + 1.0, 0.05)
            x, y, z = cam.project(np.array([W(ue, d, htop) for d in ds]))
            ok = np.logical_and.reduce([z > 0.2, x > 2, x < cam.w - 3, y > 130, y < cam.h - 130])
            xi = x[ok].astype(int); yi = y[ok].astype(int)
            floor = np.median(np.concatenate([g[yi - o, xi] for o in FLOOR]))
            n = np.median(np.concatenate([g[yi + o, xi] for o in NOSE]))
            okt = yi + max(TOP) < cam.h
            t = np.median(np.concatenate([g[yi[okt] + o, xi[okt]] for o in TOP])) if okt.sum() >= 5 else None
            used = fno not in OUTLIERS
            print('%s b7s_%06d: floor %.0f, nosing %.0f (%.3f), top %s%s' % (side, fno, floor, n, n / floor,
                  ('%.0f (%.3f)' % (t, t / floor)) if t is not None else 'out of frame', '' if used else '  (not used)'))
            if used:
                nose[side].append(n / floor)
                if t is not None: top[side].append(t / floor)
    for name, d in (('nosing', nose), ('top', top)):
        for side in ('east', 'west'):
            r = np.array(d[side])
            print('%s %s: median %.3f over %d frames, range %.3f to %.3f, half-range %.3f' % (side, name, np.median(r), len(r), r.min(), r.max(), (r.max() - r.min()) / 2))
    te, tw = np.median(top['east']), np.median(top['west'])
    hr = max((max(top['east']) - min(top['east'])) / 2, (max(top['west']) - min(top['west'])) / 2)
    if abs(te - tw) <= hr:
        val = np.median(top['east'] + top['west']); print('the decks AGREE on the top: pooled median %.3f' % val)
    else:
        val = (te + tw) / 2; print('the decks DISAGREE on the top (%.3f east, %.3f west, larger spread %.3f): the midpoint %.3f is drawn as a hint' % (te, tw, hr, val))
    ne = np.median(nose['east'] + nose['west'])
    print('top day colour %.0f (range %.0f to %.0f from the two medians); nosing day colour %.0f'
          % (val * FLOOR_SIM / FACTOR, min(te, tw) * FLOOR_SIM / FACTOR, max(te, tw) * FLOOR_SIM / FACTOR, ne * FLOOR_SIM / FACTOR))


if __name__ == '__main__':
    main()
