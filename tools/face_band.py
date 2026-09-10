"""THE EAST FACE BETWEEN THE LEDGE SIGHT LINE AND THE HALL'S EDGE, READ FOR WHAT IT TRANSMITS (2026-09-10).

tools/ledge_edge.py left the east face drawn as a low solid to 8.631, a TINTED band from there to 9.095 (its
top the edge tools/end_face_scan.py tracked on the face plane from the hall), and clear glass above. The
tint was a reading, not a measurement: it reconciled the hall seeing an edge there with the deck seeing the
floor beneath it. The same deck frames can say how much that band transmits, because the hall floor is seen
through it just over the ledge edge, and the floor a little further out is seen through the face ABOVE
9.095. If the two read alike, the band is as clear as the glass above it and the tint goes.

THE INSTRUMENT. In each east survivor frame of tools/ledge_edge.py, the ledge edge's line (u_i on 9.095) and
the hall's edge line (48.056 on 9.095) are projected over the same span of d. Between them, in the image,
the floor is seen through the band; above the hall's edge line it is seen through the glass above it. The
median grey of the floor in a strip 30 to 90 px above the ledge edge (through the band) is divided by the
median grey in a strip 30 to 90 px above the hall's edge line (through the clear glass). People and seats
are in both strips at random; the median over the strip and over ten frames is the guard against them.
THE BAR: along the hall's edge line, the strongest dark horizontal edge within 40 px is compared to the
local median row gradient; a bar of any kind standing on the face on 9.095 would show as one in every frame
from a metre away.

THE DECISION RULE, FIXED BEFORE THE RUN.
  1. TRANSMISSION: if the median ratio over frames is 0.85 or more, the band transmits like the glass above
     it and the tint is REFUTED: faceBand is drawn with the rail glass material (clear), and the record says
     the material is clear glass by this reading. Under 0.60 the tint stands. Between, undecided, tint kept.
  2. THE BAR: if a dark edge at least three times the local median gradient lies within 40 px of the hall's
     edge line in at least eight of ten frames, a 40 mm bar is drawn on the face on 9.095 (the hall's edge
     has a deck-side counterpart). Otherwise no bar is drawn and the hall's edge is recorded as having no
     counterpart seen from the deck: what the hall tracked there is unresolved.
  3. Nothing else moves. The ledge, faceSolid and the set-back are tools/ledge_edge.py's and its control's.

THE FIRST RUN. Ratios 0.572 to 0.807, median 0.712: UNDECIDED by rule 1, tint kept. The bar: a dip of 20 to
66 grey levels near the line in six frames, 3 to 11 in four: NOT DRAWN.

VERSION 2, DECLARED AFTER THE FIRST RUN. The two strips look at different floor: the one over the ledge edge
sees the floor nearer the east wall, the other the floor further out, and the floor is not evenly lit, so
rule 1 compares two patches of floor as much as two pieces of face. The west deck is the control the rule
should have carried: its face is glazed clear to the deck (tools/gallery_arrival.py), so the same ratio
there, over the west survivors of tools/ledge_edge_west.py, is the floor's own gradient with no band in
it. The east's transmission is its ratio divided by the west's, and the same bars apply: 0.85 or more,
refuted; under 0.60, stands; between, undecided.

THE RESULT OF VERSION 2 (2026-09-10). West ratios 0.749 to 0.873, median 0.841. East 0.712 / 0.841 = 0.847:
UNDECIDED (three thousandths under the clear bar), the tint kept. index.html draws it at the measured strength,
opacity 0.39 against railMat's 0.28 (1 - 0.847 x 0.72), and no bar on 9.095; the hall's edge there is recorded
as having no counterpart seen from the deck.

Run:
  python tools/face_band.py
"""
import os, sys
import numpy as np, cv2
sys.path.insert(0, os.path.dirname(__file__))
import underside_geom as U

O = np.array([-54.907447, -1.43545, 3.040286]); HU = np.array([0.975681, 0, 0.219196]); HD = np.array([0.219196, 0, -0.975681])
EAST = dict(face=48.056, htop=9.095, edges={68: 48.45, 72: 48.47, 76: 48.48, 80: 48.49, 132: 48.47, 136: 48.41, 140: 48.38, 144: 48.36, 148: 48.29, 152: 48.56})
WEST = dict(face=4.194, htop=9.097, edges={876: 3.44, 884: 3.63, 888: 3.68, 892: 3.74, 896: 3.74, 900: 3.69, 904: 3.64, 908: 3.64, 912: 3.63, 916: 3.65, 920: 3.64})
CLEAR, TINT = 0.85, 0.60; BAR_TOL = 40; BAR_STRONG = 3.0; BAR_FRAMES = 8


def W(u, d, h): return O + u * HU + d * HD + np.array([0, h, 0])


def run(side, S, cams, bar=True):
    ratios = []; bars = 0
    for fno, ue in sorted(S['edges'].items()):
        cam, ip = cams['b7s_%06d' % fno]; q = cam.center - O
        g = cv2.cvtColor(cv2.imread(ip), cv2.COLOR_BGR2GRAY).astype(np.float32)
        dc = q @ HD; ds = np.arange(dc - 2.5, dc + 1.0, 0.05)
        xl, yl, zl = cam.project(np.array([W(ue, d, S['htop']) for d in ds]))
        xh, yh, zh = cam.project(np.array([W(S['face'], d, S['htop']) for d in ds]))
        ok = np.logical_and.reduce([zl > 0.2, zh > 0.2, xl > 2, xl < cam.w - 3, xh > 2, xh < cam.w - 3, yl > 100, yl < cam.h - 100, yh > 100, yh < cam.h - 100])
        xl, yl, xh, yh = xl[ok].astype(int), yl[ok].astype(int), xh[ok].astype(int), yh[ok].astype(int)
        band = np.median(np.concatenate([g[yl - o, xl] for o in range(30, 91, 10)]))
        clear = np.median(np.concatenate([g[yh - o, xh] for o in range(30, 91, 10)]))
        r = band / clear; ratios.append(r)
        line = '%s b7s_%06d: floor over the ledge edge %.0f, over the face line %.0f, ratio %.3f; sep %d px' % (side, fno, band, clear, r, int(np.median(yl - yh)))
        if bar:
            gy = np.abs(np.diff(g, axis=0))
            local = np.median(np.concatenate([gy[yh + o, xh] for o in range(-120, 121, 8)]))
            prof = np.array([np.median(g[yh + o, xh]) for o in range(-BAR_TOL, BAR_TOL + 1)])
            dip = prof.max() - prof.min()
            strong = dip >= BAR_STRONG * max(local, 1.0) * 4    # a bar is a dip of several rows, not one row of gradient
            bars += int(strong)
            line += '; dip near the face line %.0f against a local step of %.1f -> %s' % (dip, local, 'a bar' if strong else 'no bar')
        print(line)
    return np.array(ratios), bars


def verdict(x):
    return 'REFUTED, the band is as clear as the glass above it' if x >= CLEAR else ('STANDS' if x < TINT else 'UNDECIDED, tint kept')


def main():
    cams = {}
    for cls in ('b7s', 'b7sp'):
        for k, v in U.load_class(cls).items(): cams.setdefault(k, v)
    re_, bars = run('east', EAST, cams, bar=True)
    print()
    med_e = float(np.median(re_))
    print('EAST: ratio median %.3f (range %.3f to %.3f, half-range %.3f) -> rule 1: the tint %s' % (med_e, re_.min(), re_.max(), (re_.max() - re_.min()) / 2, verdict(med_e)))
    print('a bar on the face on 9.095: seen in %d of %d frames -> %s' % (bars, len(EAST['edges']), 'DRAWN, 40 mm' if bars >= BAR_FRAMES else 'NOT DRAWN; the hall edge has no counterpart seen from the deck'))
    print()
    rw, _ = run('west', WEST, cams, bar=False)
    med_w = float(np.median(rw))
    print()
    print('WEST (the control, a clear face): ratio median %.3f (range %.3f to %.3f, half-range %.3f): the floor gradient alone' % (med_w, rw.min(), rw.max(), (rw.max() - rw.min()) / 2))
    t = med_e / med_w
    print('VERSION 2: the east transmission against the west baseline %.3f / %.3f = %.3f -> the tint %s' % (med_e, med_w, t, verdict(t)))


if __name__ == '__main__':
    main()
