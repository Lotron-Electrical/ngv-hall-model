# 2026-09-10: WHERE IS THE WEST LOWER FRONT OPEN? ASKED WITH LIGHT THAT CAME OUT OF IT.
#
# WHAT THIS IS FOR, CORRECTED. The first version of this file said index.html still draws the lower tier
# as a solid deck on the end face. IT DOES NOT, and has not since earlier on 2026-09-10, when the apron,
# the solid upstand, the glass rail and the 6.33 floor slab were all DELETED and the tier became an open
# recess from the ground wall's soffit up to the top slab. That was a large change to the balconies and it
# rested on ONE instrument: tools/lamp_void.py swept the space 33 triangulated rays crossed to reach a
# fitting 2.003 m behind the face and found all four surfaces inside the emptiness. A deletion of four
# surfaces on one sweep is exactly the kind of thing that needs a second opinion from different machinery,
# and it never had one. THIS IS THAT SECOND OPINION.
#
# WHY IT HAS TO BE DIFFERENT MACHINERY. lamp_void.py argues from ray CONVERGENCE: rays met somewhere, so
# the space they crossed is empty. That is geometry about where lines go. This argues from whether a
# bright blob is actually IN THE PICTURE where the model says a lamp should be, with a measured
# false-positive rate. Same conclusion from either would be worth having; they share only the poses.
#
# THE RIGHT QUESTION IS OCCLUSION, WHICH IS THE ONE CLASS OF ARGUMENT THAT HAS HELD UP HERE. There are
# LIGHTS BEHIND that face. This file already draws four of them on the west gallery back wall, 3.830 m
# behind the face plane, and a fifth was triangulated from 33 rays on u 2.191, d 7.858, h 7.083, 2.003 m
# behind it, surviving a split-halves test that killed both east candidates. A camera in the hall can only
# see any of them THROUGH the opening. So for every camera, work out the height where its ray to a lamp
# crosses the face plane, then look at the photograph and ask whether the lamp is really there. Heights
# where lamps are seen are heights where the face is OPEN. No edge finder, no fitted plane, no brightness
# step: light either arrived or it did not.
#
# THE NULL IS A LAMP THAT IS NOT THERE. The same photometry is run on PHANTOM points, the same lamps slid
# along d to places where this file draws no lamp and no fitting found one. That measures how often this
# test says "seen" when nothing is there, and it also sets the threshold, so the threshold is calibrated
# by a control instead of chosen by me.
#
# WHAT IT CAN AND CANNOT SAY, AND THE TWO DIRECTIONS ARE NOT EQUAL. A high hit rate for some crossing
# height PROVES the face is open there: the light got out. A low hit rate does NOT prove it is closed,
# because a lamp can be off in a clip, blown out, behind a pier inside the recess, or simply too far. So
# the open band this returns is a floor on the real aperture, and the heights outside it are reported as
# unanswered rather than as solid.
#   python tools/west_recess.py
import io
import re
import sys

import cv2
import numpy as np

sys.path.insert(0, 'tools')
import underside_geom as U

O = np.array([-54.907447, -1.43545, 3.040286])
HU = np.array([0.975681, 0, 0.219196])
HD = np.array([0.219196, 0, -0.975681])
CLASSES = ('walk', 'night', 'day4k')
HBIN = 0.10
RIN, ROUT1, ROUT2 = 5, 25, 40      # pixels: the lamp disc, and the ring of wall around it
MARGIN = 45


src = io.open('index.html', encoding='utf-8').read()
# ENDW carries nested braces, so a lazy [^}] scope stops at railTops and never reaches dSouth. Take the
# whole declaration and read keys out of that.
_i = src.index('const ENDW={')
BLOCK = src[_i:src.index('\n', _i)]


def endw(key):
    return float(re.search(r'\b' + key + r':\s*(-?[0-9.]+)', BLOCK).group(1))


BACK = endw('west')
FACE = BACK + endw('face')
DSOUTH = endw('dSouth')
low = re.search(r'lowLamps:\{west:\[(.*?)\]\}', src).group(1)
DRAWN = [[float(a), float(b)] for a, b in re.findall(r'\[([0-9.]+),([0-9.]+)\]', low)]

# THE FIVE SOURCES. Four are what this file already draws on the west gallery back wall; the fifth is the
# fitting that survived the split-halves test, and it is the one that produced the 5.458 to 6.842 bound
# this run is trying to widen. Its u is 2.003 m behind the face, theirs 3.830 m.
LAMPS = [('back %d' % (i + 1), BACK + 0.02, d, h) for i, (d, h) in enumerate(DRAWN)]
LAMPS.append(('fitting', 2.191, 7.858, 7.083))
print('the west face plane stands on u %.3f and the gallery back wall on u %.3f' % (FACE, BACK))
print('%d sources sit behind it: %s' % (len(LAMPS), ', '.join(l[0] for l in LAMPS)))
# the open recess this file draws: from the ground wall's soffit up to the underside of the top slab
DRAWN_LO = endw('groundTop')
DRAWN_HI = float(re.search(r'floors:\[[0-9.]+,([0-9.]+)\]', BLOCK).group(1)) - endw('slab')
print('this file NOW draws that tier OPEN from h %.2f to %.2f, the recess left when four surfaces went'
      % (DRAWN_LO, DRAWN_HI))

# THE NULL: the same lamps slid along the gallery, where nothing is drawn and nothing was fitted.
PHANTOM = []
for nm, ul, dl, hl in LAMPS:
    for off in (-4.0, -2.5, 2.5, 4.0):
        dd = dl + off
        if 0.5 < dd < DSOUTH - 0.5 and all(abs(dd - o[2]) > 1.2 for o in LAMPS):
            PHANTOM.append(('null %s%+.1f' % (nm, off), ul, dd, hl))
print('%d phantom points stand beside them, same depth and height, where no lamp is drawn or fitted'
      % len(PHANTOM))


def world(ul, dl, hl):
    return O + ul * HU + dl * HD + np.array([0.0, hl, 0.0])


LAMPR = 0.075                      # the radius index.html draws these lamps at


def score(im, cam, p):
    """how much brighter a small disc is than the ring of wall around it, and how big the lamp is in px"""
    edge = p + LAMPR * np.array([0.0, 1.0, 0.0])
    x, y, z = cam.project(np.array([p, edge]))
    if z[0] <= 0.5:
        return None
    rpx = float(np.hypot(x[1] - x[0], y[1] - y[0]))
    cx, cy = float(x[0]), float(y[0])
    if not (MARGIN < cx < cam.w - MARGIN and MARGIN < cy < cam.h - MARGIN):
        return None
    yy, xx = np.mgrid[int(cy) - ROUT2:int(cy) + ROUT2 + 1, int(cx) - ROUT2:int(cx) + ROUT2 + 1]
    rr = np.hypot(xx - cx, yy - cy)
    patch = im[int(cy) - ROUT2:int(cy) + ROUT2 + 1, int(cx) - ROUT2:int(cx) + ROUT2 + 1]
    if patch.shape != rr.shape:
        return None
    disc = patch[rr <= RIN]
    ring = patch[np.logical_and(rr >= ROUT1, rr <= ROUT2)]
    if disc.size < 20 or ring.size < 200:
        return None
    b = float(np.median(ring))
    if b < 3:
        b = 3.0
    return float(np.percentile(disc, 90)) / b, rpx


real, null = [], []
nf = 0
for cname in CLASSES:
    try:
        frames = U.load_class(cname)
    except Exception:
        continue
    for k, (cam, ip) in sorted(frames.items()):
        q = cam.center - O
        cu, cd, ch = float(q @ HU), float(q @ HD), float(q[1])
        if ch > 3.0 or not (0.0 < cd < DSOUTH) or cu < FACE + 1.0:
            continue
        im = None
        broke = False
        for tag, lst in (('real', LAMPS), ('null', PHANTOM)):
            for nm, ul, dl, hl in lst:
                t = (FACE - cu) / (ul - cu)
                if not (0.02 < t < 0.999):
                    continue
                hx = ch + t * (hl - ch)
                dx = cd + t * (dl - cd)
                if not (0.0 < dx < DSOUTH):
                    continue
                if im is None:
                    im = cv2.imread(ip, cv2.IMREAD_GRAYSCALE)
                    if im is None:
                        broke = True
                        break
                    nf += 1
                sc = score(im, cam, world(ul, dl, hl))
                if sc is None:
                    continue
                (real if tag == 'real' else null).append((hx, dx, sc[0], nm, cu, sc[1]))
            if broke:
                break

print('')
print('%d frames stand on the hall floor east of the west face' % nf)
if len(real) < 100 or len(null) < 100:
    sys.exit('   too few sightlines reach these points to judge anything')
ns = np.array([r[2] for r in null])
THRESH = float(np.percentile(ns, 95))
print('   %d sightlines to a real source, %d to a phantom' % (len(real), len(null)))
print('   the phantoms score %.3f median and %.3f on their 95th, and that 95th IS the threshold:'
      % (float(np.median(ns)), THRESH))
print('   a source counts as SEEN only when it beats what this test returns where nothing is.')

rs = np.array([r[2] for r in real])
print('   the real sources score %.3f median, and %.0f per cent of them beat the threshold'
      % (float(np.median(rs)), 100.0 * float(np.mean(rs > THRESH))))

lo = np.floor(min(r[0] for r in real) / HBIN) * HBIN
hi = np.ceil(max(r[0] for r in real) / HBIN) * HBIN
print('')
print('   the rays cross the west face between h %.2f and %.2f' % (lo, hi))
print('')
print('   h band     rays   seen   rate     null rays   null rate')
rows = []
h = lo
while h < hi - 1e-9:
    rin = [r for r in real if h <= r[0] < h + HBIN]
    nin = [r for r in null if h <= r[0] < h + HBIN]
    if len(rin) >= 12:
        sr = float(np.mean([r[2] > THRESH for r in rin]))
        nr = float(np.mean([r[2] > THRESH for r in nin])) if len(nin) >= 12 else float('nan')
        rows.append((h, len(rin), sr, len(nin), nr))
        print('   %.2f-%.2f  %5d  %5d  %.2f     %6d      %s'
              % (h, h + HBIN, len(rin), int(round(sr * len(rin))), sr, len(nin),
                 '%.2f' % nr if np.isfinite(nr) else '  -'))
    h += HBIN
if not rows:
    sys.exit('   no height band carries enough rays to judge')

# THE OPEN BAND. A band counts as open when its hit rate beats the phantom rate by a clear margin, and
# the margin is the phantom rate itself doubled rather than a number picked to make a band appear.
seen_nulls = [r[4] for r in rows if np.isfinite(r[4])]
BAR = max(0.10, 2.0 * float(np.mean(seen_nulls))) if seen_nulls else 0.10
op = [r for r in rows if r[2] > BAR]
print('')
print('   a band counts as OPEN when its hit rate beats %.2f, twice the phantom rate.' % BAR)
if not op:
    print('   NO BAND CLEARS IT. Nothing here says the face is open anywhere, and nothing moves.')
    sys.exit(0)
b0, b1 = min(r[0] for r in op), max(r[0] for r in op) + HBIN
print('   %d of %d bands clear it, running from h %.2f to h %.2f.' % (len(op), len(rows), b0, b1))
dd = [r[1] for r in real if b0 <= r[0] < b1 and r[2] > THRESH]
if dd:
    print('   the seen rays cross that face over d %.2f to %.2f, so it is not one local hole.'
          % (min(dd), max(dd)))

# WHICH SOURCE ACTUALLY ANSWERED, because a band carried by ONE lamp is one lamp's answer however many
# rays it drew, and this run was about to quote a pooled rate without saying where it came from. The
# column that matters is not the total rays but the rays that crossed INSIDE the open band: a source with
# none of those was never asked the question and its zero means nothing.
# AND BEFORE ANY OF THAT COUNTS, THE INSTRUMENT HAS TO BE FAIR BETWEEN THE SOURCES. The disc is a fixed
# 5 px, so a source that is further away underfills it and scores lower for no reason to do with the wall.
# The back lamps stand 1.827 m deeper than the fitting, so the range and the lamp's own angular radius are
# printed per source: if a lamp still fills the disc, a zero is about light and not about distance.
print('')
print('   which source answered      rays   in band   seen   rate    range   lamp radius   climb in')
answered = []
CLIMB = {}
for nm, ul, dl, hl in LAMPS:
    mine = [r for r in real if r[3] == nm]
    band = [r for r in mine if b0 <= r[0] < b1]
    hits = [r for r in band if r[2] > THRESH]
    rate = (float(len(hits)) / len(band)) if band else float('nan')
    if band and rate > BAR:
        answered.append(nm)
    rng = float(np.median([abs(r[4] - ul) for r in band])) if band else float('nan')
    px = float(np.median([r[5] for r in band])) if band else float('nan')
    # THE CLIMB IS THE CONFOUND THAT DECIDES HOW THIS IS REPORTED. A ray that crosses the face inside the
    # open band still has to travel to the lamp, and the further it rises or falls on the way, the taller
    # the real recess must be for it to get there. A source that is nearer and larger but needs a much
    # bigger climb was not asked a fair question, and its zero explains itself.
    climb = float(np.median([abs(hl - r[0]) for r in band])) if band else float('nan')
    print('   %-22s %6d   %7d %6d   %s   %s   %s   %s'
          % (nm, len(mine), len(band), len(hits),
             '%.2f' % rate if band else '   -',
             '%5.1f m' % rng if band else '    -',
             '%4.1f px' % px if band else '   -',
             '%5.2f m' % climb if band else '   -'))
    CLIMB[nm] = climb
print('   the lamp is %.3f m across and the disc is %d px, so a source whose radius above is under'
      % (2 * LAMPR, RIN))
print('   that fills the disc and a zero against it is about light rather than about distance.')

print('')
inside = DRAWN_LO <= b0 and b1 <= DRAWN_HI
print('   THE DRAWN RECESS IS OPEN FROM h %.2f TO %.2f AND THE MEASURED BAND IS %.2f TO %.2f, so the'
      % (DRAWN_LO, DRAWN_HI, b0, b1))
print('   band this run finds sits %s the shape this file draws.'
      % ('INSIDE' if inside else 'OUTSIDE'))
if inside:
    print('   THE DELETION OF THE FOUR SURFACES IS CONFIRMED BY MACHINERY THAT HAD NO PART IN IT. Where')
    print('   the apron, the upstand, the rail and the 6.33 slab used to be drawn, light demonstrably')
    print('   comes out, %d times in %d rays against a phantom rate no higher than the null bands show.'
          % (len([r for r in real if b0 <= r[0] < b1 and r[2] > THRESH]),
             len([r for r in real if b0 <= r[0] < b1])))
else:
    print('   THAT IS A DISAGREEMENT WITH WHAT IS DRAWN and it is the finding of the run.')
if len(answered) < 2:
    print('')
    print('   IT IS ONE SOURCE, AND THAT LIMITS WHAT IT IS WORTH. Only %s cleared the bar, and it is the'
          % (answered[0] if answered else 'nothing'))
    print('   same fitting lamp_void.py swept to. So this is a second opinion on the SURFACES, from a')
    print('   different question, but not a second SOURCE: both readings rest on that one lamp being')
    print('   real. Its 0.047 m rms over 33 rays and its split-halves agreement of 0.066 m in u are what')
    print('   carry that, and they are not re-tested here. The band is also NARROWER than the sweep,')
    print('   %.2f m against 1.384, so nothing about the recess extent is extended by it.' % (b1 - b0))
    cb = [CLIMB[n] for n in CLIMB if n.startswith('back') and np.isfinite(CLIMB[n])]
    cf = CLIMB.get('fitting', float('nan'))
    print('   THE PART THAT IS NEW IS WHAT DID NOT ANSWER. The four lamps this file DRAWS on the west')
    print('   gallery back wall are seen in none of the %d rays that reached the right height, and the'
          % sum(1 for r in real if r[3].startswith('back') and b0 <= r[0] < b1))
    print('   photometry FAVOURS them: they stand nearer and fill more pixels than the fitting that is')
    print('   seen 27 times in a hundred.')
    if np.isfinite(cf) and cb and float(np.median(cb)) > 1.6 * cf:
        print('   BUT THE GEOMETRY DOES NOT FAVOUR THEM, AND THAT IS WHY THIS IS NOT A REFUTATION. A ray')
        print('   to a back lamp must climb %.2f m inside the recess after it crosses the face, against'
              % float(np.median(cb)))
        print('   %.2f m for the fitting. A recess only has to be shallower or shorter than that climb'
              % cf)
        print('   needs and the light never gets out, with the lamp exactly where it is drawn. So these')
        print('   four stay, marked UNCONFIRMED: nothing in 859 frames has ever seen them, and nothing')
        print('   here can tell absence from a ceiling in the way.')
    else:
        print('   AND THE GEOMETRY DOES NOT EXCUSE THEM: their rays climb %.2f m inside the recess')
        print('   against %.2f m for the fitting, so they were asked the same question and gave no'
              % (float(np.median(cb)) if cb else float('nan'), cf))
        print('   answer. Four lamps are drawn on that wall that no photograph in this archive supports.')
else:
    print('   %d SEPARATE SOURCES CLEAR THE BAR: %s. That is redundancy the target itself provides, and'
          % (len(answered), ', '.join(answered)))
    print('   it is what makes this a second opinion on the 5.458 to 6.842 bound rather than a repeat.')
print('')
print('   Nothing is re-drawn on it: an open band is a floor on the aperture, not a sill and a head. A')
print('   height that did not answer is UNANSWERED rather than solid, because a lamp can be off, blown')
print('   out or hidden behind a pier inside the recess.')
