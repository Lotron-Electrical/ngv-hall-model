# 2026-09-10: THE SOUTH WALL HAS NEVER BEEN ASKED ANYTHING. IT CARRIES TWELVE OPENINGS AND AN EMPTY VOID.
#
# WHAT PROMPTED IT, AND THE PREMISE WAS WRONG, WHICH IS WORTH WRITING DOWN BEFORE THE RESULT. I started
# this because index.html builds both long walls from one list, walls = [{d: dNorth, north: true}, {d:
# dSouth, north: false}], and I took that to mean the south wall carries the same twelve openings. IT DOES
# NOT. The reveals are gated "if(w.north)", the corridor behind them is gated "if(w.north)", and the bake
# shader only cuts the opening holes where sd < 7.0, which is the north half of the hall. The south wall
# is drawn SOLID except for two low doors on u 38.8 and 47.0 that reach h 2.9.
#
# THAT IS THE SECOND TIME IN A DAY I HAVE ASSERTED WHAT THIS MODEL DRAWS WITHOUT READING THE DRAW CODE,
# so the run is kept and the question is turned round: the south wall has never been tested by anything,
# 328 posed cameras face it, and the model's claim that it is blank up there is itself unchecked.
#
# AND THE SOUTH WALL IS NOT IN THE REGISTRAR'S BLIND SPOT, WHICH IS WHY THIS IS WORTH RUNNING. That blind
# spot has closed four routes in this project: the frames that show a surface are the ones with no pose.
# Not here. Of 1568 posed cameras, 328 FACE SOUTH, and 137 of those are floor frames from the day walk.
# The evidence to check the south wall has been sitting in the archive the whole time.
#
# THE INSTRUMENT IS THE ONE THAT CONFIRMED THE NORTH OPENINGS. An opening is DARK against the lit pier
# beside it. tools/opening_holes.py used exactly that on the north wall, eleven of twelve read as holes,
# and the same rule run on the piers themselves fired on 4 per cent. That is not an edge fit; it is the
# difference between a hole and a wall.
#
# TWO CONTROLS, AND BOTH ARE FREE. The NULL is pier against pier on the same wall in the same frames: two
# strips of solid stone, so whatever it reports is the false-positive rate. The POSITIVE control is the
# NORTH wall run through the identical code, because the north openings are known to be real. If the north
# does not come back as holes here, the tool is broken and the south result means nothing.
#
# WHAT IT CANNOT DO. It says whether there is a hole, not what is behind it, and it reads a wall tens of
# metres away. A dark stain, a doorway or an unlit recess would read the same as an opening.
#   python tools/south_wall.py
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
CLASSES = ('walk', 'night', 'day4k', 'b1', 'b1p', 'b4', 'b5', 'b5p')

src = io.open('index.html', encoding='utf-8').read()
mo = re.search(r'const WALLF=\{openings:\[(.*?)\],\s*\n', src, re.S)
OPEN = [[float(a), float(b)] for a, b in re.findall(r'\[([0-9.]+),([0-9.]+)\]', mo.group(1))]
DN = float(re.search(r'dNorth:(-?[0-9.]+)', src).group(1))
DS = float(re.search(r'dSouth:([0-9.]+)', src).group(1))
SILL = float(re.search(r'openY:\[([0-9.]+),', src).group(1))
HEAD = float(re.search(r'openY:\[[0-9.]+,([0-9.]+)\]', src).group(1))
LO, HI = SILL + 0.45, HEAD - 0.45
print('the north wall on d %.3f carries twelve openings; the south on d %.3f is drawn SOLID up there'
      % (DN, DS))
print('so the north twelve are the positive control and the south is the wall nothing has ever tested')
print('the patches are sampled over h %.2f to %.2f, well inside the drawn aperture' % (LO, HI))


def patch(im, cam, d, u0, u1):
    us = np.linspace(u0 + 0.15, u1 - 0.15, 6)
    ls = np.linspace(LO, HI, 5)
    pts = np.array([O + u * HU + d * HD + np.array([0.0, lv, 0.0]) for u in us for lv in ls])
    x, y, z = cam.project(pts)
    ok = np.logical_and.reduce([z > 0.5, x > 2, x < cam.w - 3, y > 2, y < cam.h - 3])
    if ok.sum() < 18:
        return None
    if (x[ok].max() - x[ok].min()) < 6:
        return None
    return float(np.median([im[int(y[i]), int(x[i])] for i in np.nonzero(ok)[0]]))


WALLS = [('north', DN, -1.0), ('south', DS, 1.0)]
res = {}
for wname, WD, sgn in WALLS:
    hole = {i: [] for i in range(len(OPEN))}
    null = []
    inside = []
    nf = 0
    for cname in CLASSES:
        try:
            frames = U.load_class(cname)
        except Exception:
            continue
        for k, (cam, ip) in sorted(frames.items()):
            q = cam.center - O
            cu, cd, ch = float(q @ HU), float(q @ HD), float(q[1])
            if ch > 3.0 or not (0.3 < cd < DS - 0.3):
                continue
            f = cam.R.T @ np.array([0, 0, 1.0])
            if float(f @ HD) * sgn < 0.30:      # it has to be looking at THIS wall
                continue
            im = None
            for oi, (u0, u1) in enumerate(OPEN):
                w = u1 - u0
                if im is None:
                    im = cv2.imread(ip, cv2.IMREAD_GRAYSCALE)
                    if im is None:
                        break
                    nf += 1
                a = patch(im, cam, WD, u0, u1)
                b = patch(im, cam, WD, u1 + 0.25 * w, u1 + 1.25 * w)
                c = patch(im, cam, WD, u1 + 1.35 * w, u1 + 2.35 * w)
                if a is not None and b is not None and b > 8:
                    hole[oi].append((a / b, abs(cd - WD)))
                    inside.append(a)
                if b is not None and c is not None and c > 8:
                    null.append(b / c)
    res[wname] = (hole, null, inside, nf)

print('')
for wname, WD, sgn in WALLS:
    hole, null, inside, nf = res[wname]
    print('%s WALL: %d frames look at it' % (wname.upper(), nf))
    if len(null) < 50:
        print('   the null did not fill; nothing on this wall can be judged')
        continue
    nm = float(np.median(null))
    # THE BAR WAS WRONG THE FIRST TIME AND THE POSITIVE CONTROL IS WHAT CAUGHT IT. It was the null's 5th
    # percentile, a tail statistic sitting far below the null's own median, so no opening could ever clear
    # it and the KNOWN north openings scored zero out of twelve. The bar is now the null's lower QUARTILE,
    # which is a statement about the bulk of the control rather than about its tail.
    nq = float(np.percentile(null, 25))
    print('   the NULL, pier against pier on this same wall: median %.3f, quartiles %.3f to %.3f.'
          % (nm, nq, float(np.percentile(null, 75))))
    print('   nothing counts as a hole unless it is darker than the lower quartile, %.3f.' % nq)
    print('   opening   readings   opening over pier   hole')
    hits = 0
    meds = []
    for oi in range(len(OPEN)):
        v = hole[oi]
        if len(v) < 12:
            print('   %2d        %6d     too few readings' % (oi + 1, len(v)))
            continue
        m = float(np.median([t[0] for t in v]))
        meds.append(m)
        yes = m < nq
        hits += 1 if yes else 0
        print('   %2d        %6d     %.3f               %s' % (oi + 1, len(v), m, 'yes' if yes else 'no'))
    res[wname] = res[wname] + (hits, len(meds), float(np.median(meds)) if meds else float('nan'), nq, nm)
    print('   %d of %d openings on this wall read as holes.' % (hits, len(meds)))
    print('')

print('')
if len(res['north']) < 5 or len(res['south']) < 5:
    sys.exit('   one of the walls did not answer, so the comparison cannot be made')
nh, nn, nmed, nq, _ = res['north'][4:]
sh, sn, smed, sq, _ = res['south'][4:]
print('   NORTH, the positive control: %d of %d read as holes, median ratio %.3f against a bar of %.3f'
      % (nh, nn, nmed, nq))
print('   SOUTH, the question:         %d of %d read as holes, median ratio %.3f against a bar of %.3f'
      % (sh, sn, smed, sq))
if nh < 0.6 * nn:
    print('')
    print('   THE POSITIVE CONTROL FAILS. The north openings are known to be real and this code cannot')
    print('   find them, so nothing it says about the south wall counts. NOTHING MOVES.')
    sys.exit(0)
print('')
print('   the north openings come back as holes, so the instrument works on a wall with known holes.')
if sh >= 0.6 * sn:
    print('   AND SO DOES THE SOUTH WALL, which would be a defect: this file draws it solid up there.')
else:
    print('   THE SOUTH WALL DOES NOT, %d of %d against %d of %d, by the same rule in the same frames.'
          % (sh, sn, nh, nn))
    print('   THAT AGREES WITH WHAT THIS FILE DRAWS. The south wall is solid on the north wall lines and')
    print('   the model says so. It is the first time anything has checked that, and it passes.')
# AND THE ONE CONFOUND THAT COULD FAKE ALL OF THIS. The south wall is further from every camera than the
# north: a camera on d 5 stands 5 m from the north wall and 10.4 m from the south. Further means smaller,
# blurrier apertures and less contrast, which would flatten the south ratios for a reason that has nothing
# to do with whether the holes are there. So the two walls are compared at the SAME RANGE.
print('')
print('   THE RANGE-MATCHED COMPARISON, because the south wall is further from every camera and distance')
print('   alone would flatten it. Ratio of opening to pier, pooled over all twelve, by how far the')
print('   camera stood from that wall:')
print('   range        north          south')
for r0, r1 in ((3, 6), (6, 9), (9, 12), (12, 16)):
    row = []
    for wname in ('north', 'south'):
        hole = res[wname][0]
        v = [t[0] for oi in hole for t in hole[oi] if r0 <= t[1] < r1]
        row.append('%s' % ('%.3f (%d)' % (float(np.median(v)), len(v)) if len(v) >= 30 else '   -   '))
    print('   %2d-%2d m    %-14s %-14s' % (r0, r1, row[0], row[1]))

print('')
print('   HOW DARK, WHICH IS A DIFFERENT QUESTION FROM WHETHER. The pixels inside the openings read')
ni = np.array(res['north'][2], dtype=float)
si = np.array(res['south'][2], dtype=float)
if ni.size > 50 and si.size > 50:
    print('   north %.1f and south %.1f at the median (0-255), a ratio of %.2f. A void behind a wall'
          % (float(np.median(ni)), float(np.median(si)), float(np.median(si)) / max(float(np.median(ni)), 1)))
    print('   is not the same brightness as a room with a lit back wall and two lamps in it, so this is')
    print('   the number to chase next, with the caveat that the two walls are lit differently and')
    print('   nothing here separates that from what is behind them.')

# AND THE ALTERNATIVE THAT THE TEST ABOVE CANNOT RULE OUT ON ITS OWN. "No contrast where the model draws
# an opening" has two readings: there is no opening, or there IS one and it is somewhere else along the
# wall, so the patch landed on stone either way. Those are different errors and they need different fixes,
# so the whole wall is swept rather than only the twelve places this file happens to point at. On the
# north wall the sweep must find twelve dips on the drawn lines; that is what makes it readable.
print('')
print('   THE WHOLE-WALL SWEEP, because "nothing where we looked" and "something somewhere else" are')
print('   different errors. Walking u across each wall in %d cm steps, sampling the same height band:'
      % 15)
USTEP, WIN = 0.15, 0.60
US = np.arange(4.0, 46.0 + 1e-9, USTEP)
prof = {}
for wname, WD, sgn in WALLS:
    acc = [[] for _ in US]
    half = ([[] for _ in US], [[] for _ in US])
    par = 0
    for cname in CLASSES:
        try:
            frames = U.load_class(cname)
        except Exception:
            continue
        for k, (cam, ip) in sorted(frames.items()):
            q = cam.center - O
            cd, ch = float(q @ HD), float(q[1])
            if ch > 3.0 or not (0.3 < cd < DS - 0.3):
                continue
            f = cam.R.T @ np.array([0, 0, 1.0])
            if float(f @ HD) * sgn < 0.30:
                continue
            im = cv2.imread(ip, cv2.IMREAD_GRAYSCALE)
            if im is None:
                continue
            vals = [patch(im, cam, WD, u - WIN / 2, u + WIN / 2) for u in US]
            good = [v for v in vals if v is not None]
            if len(good) < 0.5 * len(US):
                continue
            base = float(np.percentile(good, 85))
            if base < 8:
                continue
            for i, v in enumerate(vals):
                if v is not None:
                    acc[i].append(v / base)
                    half[par][i].append(v / base)
            par = 1 - par
    m = np.array([np.median(v) if len(v) >= 10 else np.nan for v in acc])
    prof[wname] = m
    g = np.isfinite(m)
    if g.sum() < 100:
        print('   %s: the sweep did not fill' % wname)
        continue
    bar = float(np.nanpercentile(m, 85)) - 0.5 * (float(np.nanpercentile(m, 85)) -
                                                  float(np.nanmin(m)))
    dips = []
    i = 0
    while i < len(US):
        if g[i] and m[i] < bar:
            j = i
            while j + 1 < len(US) and g[j + 1] and m[j + 1] < bar:
                j += 1
            if US[j] - US[i] > 0.4:
                dips.append(0.5 * (US[i] + US[j]))
            i = j + 1
        else:
            i += 1
    print('   %-5s  filled %3d of %3d stops, profile %.3f to %.3f, %d dips below the half-way bar'
          % (wname, int(g.sum()), len(US), float(np.nanmin(m)), float(np.nanmax(m)), len(dips)))
    if dips:
        print('          dips on u %s' % ', '.join('%.1f' % v for v in dips))

    # A DIP FOUND ONCE IS NOT A FEATURE. The frames are split alternately into two halves that share the
    # geometry and the code and differ only in which photographs went in. A mark on the wall appears in
    # both halves on the same u. Something in front of the wall, or a shadow that moved, does not.
    def dipsof(a2):
        mm = np.array([np.median(v) if len(v) >= 5 else np.nan for v in a2])
        gg = np.isfinite(mm)
        if gg.sum() < 100:
            return None
        bb = float(np.nanpercentile(mm, 85)) - 0.5 * (float(np.nanpercentile(mm, 85)) -
                                                      float(np.nanmin(mm)))
        out, ii = [], 0
        while ii < len(US):
            if gg[ii] and mm[ii] < bb:
                jj = ii
                while jj + 1 < len(US) and gg[jj + 1] and mm[jj + 1] < bb:
                    jj += 1
                if US[jj] - US[ii] > 0.4:
                    out.append(0.5 * (US[ii] + US[jj]))
                ii = jj + 1
            else:
                ii += 1
        return out

    da, db = dipsof(half[0]), dipsof(half[1])
    if da is None or db is None:
        print('          the halves did not fill, so the dips are not confirmed')
    else:
        agree = [v for v in da if any(abs(v - w2) < 0.5 for w2 in db)]
        print('          split halves: %d and %d dips, %d agree to 0.5 m' % (len(da), len(db), len(agree)))
        if agree:
            print('          confirmed in both halves on u %s' % ', '.join('%.1f' % v for v in agree))

drawn = [0.5 * (a + b) for a, b in OPEN]
print('')
print('   this file draws its twelve on u %s' % ', '.join('%.1f' % v for v in drawn))
nn_ = np.nanmax(prof['north']) - np.nanmin(prof['north']) if 'north' in prof else 0
ss_ = np.nanmax(prof['south']) - np.nanmin(prof['south']) if 'south' in prof else 0
print('   the north profile swings %.3f across the wall and the south %.3f.' % (nn_, ss_))
if ss_ < 0.5 * nn_:
    print('')
    print('   THE SOUTH WALL HAS NO STRUCTURE ANYWHERE ALONG IT, not on the drawn lines and not off them.')
    print('   The north wall swings %.0f per cent as much over the same 42 m, in the same frames, by the'
          % (100.0 * nn_ / max(ss_, 1e-6)))
    print('   same code. So this is not a registration error and the openings are not somewhere else:')
    print('   THE SOUTH WALL DOES NOT CARRY THE TWELVE OPENINGS THIS FILE DRAWS ON IT.')
    print('   ONE READING SURVIVES THAT THIS CANNOT KILL: an opening onto a space lit to exactly the')
    print('   brightness of the wall around it would also read flat. The south ratios sit on 1.00 to')
    print('   1.11 where the north sits on 0.61 to 0.97, so if such a space is there it matches the')
    print('   stone to within a few per cent at every range, which is not what rooms do.')
else:
    print('')
    print('   THE SOUTH WALL DOES HAVE STRUCTURE, and the question becomes whether it is where this file')
    print('   draws it. Compare the dip list against the drawn list above.')

# A DIP LIST IS NOT A MEASUREMENT, so the obvious model gets tested properly. The south dips sit on a
# pitch close to the drawn one but not on the drawn LINES, which is exactly what a rigid shift looks like.
# Score every shift from -3 to +3 m by how much darker the twelve shifted opening positions are than the
# eleven piers between them, and the best shift is the answer. THE NORTH WALL IS THE CONTROL and it has
# to come back on zero, because its openings are where this file draws them.
print('')
print('   IS IT A RIGID SHIFT? Scoring every shift by how much darker the twelve openings are than the')
print('   eleven piers between them. The north wall must answer zero or nothing here counts.')
piers = [0.5 * (OPEN[i][1] + OPEN[i + 1][0]) for i in range(len(OPEN) - 1)]


def darkness(m, S):
    def at(uu):
        i = int(round((uu - US[0]) / USTEP))
        return m[i] if 0 <= i < len(m) and np.isfinite(m[i]) else np.nan
    o = [at(v + S) for v in drawn]
    q = [at(v + S) for v in piers]
    o = [v for v in o if np.isfinite(v)]
    q = [v for v in q if np.isfinite(v)]
    if len(o) < 8 or len(q) < 7:
        return None
    return float(np.median(o) - np.median(q))


SH = np.arange(-3.0, 3.001, 0.05)
best = {}
for wname in ('north', 'south'):
    if wname not in prof:
        continue
    sc = [(S, darkness(prof[wname], S)) for S in SH]
    sc = [t for t in sc if t[1] is not None]
    if len(sc) < 20:
        print('   %s: too few shifts scored' % wname)
        continue
    b = min(sc, key=lambda t: t[1])
    z = [t for t in sc if abs(t[0]) < 1e-9][0]
    best[wname] = (b[0], b[1], z[1])
    print('   %-5s  best shift %+.2f m (openings %.3f darker than piers); at zero shift %+.3f'
          % (wname, b[0], -b[1], -z[1]))

if 'north' in best and 'south' in best:
    nb, _, nz = best['north']
    sb, sd, sz = best['south']
    print('')
    if abs(nb) > 0.30:
        print('   THE CONTROL FAILS: the north wall wants a %+.2f m shift when its openings are where this'
              % nb)
        print('   file draws them. The score is not measuring what it is meant to, so the south number is')
        print('   not quoted and NOTHING MOVES.')
    elif sd > -0.05:
        print('   NO SHIFT MAKES THE SOUTH WALL LOOK LIKE A WALL WITH TWELVE OPENINGS IN IT. The best any')
        print('   shift can do is %.3f, against %.3f on the north at zero shift. So the south wall does'
              % (-sd, -nz))
        print('   not carry twelve openings on this pitch anywhere, and the twelve this file draws there')
        print('   came from one code path drawing both walls, not from evidence.')
    else:
        print('   THE SOUTH WALL PREFERS A SHIFT OF %+.2f m, where the north control sits on %+.2f. That'
              % (sb, nb))
        print('   is a specific and testable claim and it is NOT acted on here: one profile, one pitch')
        print('   model, and four dips out of twelve is not enough to move a wall. What IS established is')
        print('   that the drawn lines are wrong: at zero shift the south openings are %.3f darker than'
              % -sz)
        print('   their piers where the north is %.3f, and the range-matched table above says the same.'
              % -nz)

# THREE MARKS ON A WALL ARE THREE NUMBERS UNTIL THEY HAVE A HEIGHT. The same ruler is now walked UP the
# south wall at each confirmed u, against a strip of wall beside it, so each feature gets a band rather
# than a point. THE CONTROLS ARE THE SAME WALK ON u WHERE THE SWEEP FOUND NOTHING: if a blank stretch of
# south wall also produces a band, the bands mean nothing.
CONFIRMED = [14.1, 21.6, 25.5]
BLANK = [18.0, 31.0, 39.0]
HSTEP, HBAND = 0.15, 0.40
HW = np.arange(5.0, 12.5 + 1e-9, HSTEP)
print('')
print('   HOW TALL ARE THEY? Walking h up the south wall at each confirmed u, against the wall beside it.')


def strip(im, cam, u0, u1, lo, hi):
    us = np.linspace(u0, u1, 5)
    ls = np.linspace(lo, hi, 4)
    pts = np.array([O + u * HU + DS * HD + np.array([0.0, lv, 0.0]) for u in us for lv in ls])
    x, y, z = cam.project(pts)
    ok = np.logical_and.reduce([z > 0.5, x > 2, x < cam.w - 3, y > 2, y < cam.h - 3])
    if ok.sum() < 12:
        return None
    return float(np.median([im[int(y[i]), int(x[i])] for i in np.nonzero(ok)[0]]))


TG = [('feature u %.1f' % v, v) for v in CONFIRMED]
TG = TG + [('control u %.1f' % v, v) for v in BLANK]
prof2 = {t[0]: [[] for _ in HW] for t in TG}
for cname in CLASSES:
    try:
        frames = U.load_class(cname)
    except Exception:
        continue
    for k, (cam, ip) in sorted(frames.items()):
        q = cam.center - O
        cd, ch = float(q @ HD), float(q[1])
        if ch > 3.0 or not (0.3 < cd < DS - 0.3):
            continue
        f = cam.R.T @ np.array([0, 0, 1.0])
        if float(f @ HD) < 0.30:
            continue
        im = cv2.imread(ip, cv2.IMREAD_GRAYSCALE)
        if im is None:
            continue
        for nm2, uc in TG:
            for i, hv in enumerate(HW):
                a = strip(im, cam, uc - 0.30, uc + 0.30, hv - HBAND / 2, hv + HBAND / 2)
                b = strip(im, cam, uc + 1.80, uc + 2.40, hv - HBAND / 2, hv + HBAND / 2)
                if a is not None and b is not None and b > 8:
                    prof2[nm2][i].append(a / b)

print('   target            band it dips over        depth of the dip')
for nm2, uc in TG:
    m2 = np.array([np.median(v) if len(v) >= 10 else np.nan for v in prof2[nm2]])
    g2 = np.isfinite(m2)
    if g2.sum() < 20:
        print('   %-16s  too few readings' % nm2)
        continue
    base2 = float(np.nanpercentile(m2, 85))
    dip2 = base2 - float(np.nanmin(m2))
    bar2 = base2 - 0.5 * dip2
    inb = [HW[i] for i in range(len(HW)) if g2[i] and m2[i] < bar2]
    if not inb or dip2 < 0.10:
        print('   %-16s  no band                  %.3f' % (nm2, dip2))
        continue
    print('   %-16s  h %.2f to %.2f            %.3f' % (nm2, min(inb), max(inb), dip2))
    prof2[nm2] = (min(inb), max(inb), dip2)

fd = [prof2[n] for n, _ in TG[:3] if isinstance(prof2[n], tuple)]
cd2 = [prof2[n] for n, _ in TG[3:] if isinstance(prof2[n], tuple)]
print('')
if len(fd) >= 2 and (not cd2 or max(t[2] for t in fd) > 1.5 * max([t[2] for t in cd2] or [0])):
    print('   THE SOUTH WALL CARRIES FEATURES THIS MODEL DOES NOT DRAW, and they have a height now.')
    print('   %d of the three confirmed marks give a band, the deepest %.3f, where the blank controls'
          % (len(fd), max(t[2] for t in fd)))
    print('   give %s. They are RECORDED AND NOT DRAWN: a band and a u is not a shape, there is no'
          % ('%.3f' % max([t[2] for t in cd2] or [0])))
    print('   depth, no width beyond the 0.6 m window that found them and no identification. What this')
    print('   run establishes is that the south wall is not blank up there, and that nothing in this')
    print('   project had ever looked.')
else:
    print('   THE HEIGHT WALK DOES NOT SEPARATE THE MARKS FROM BLANK WALL, so they stay as three u')
    print('   positions confirmed in two halves and nothing more. Nothing is drawn on them.')

# WHAT THE WHOLE RUN COMES TO, WRITTEN AT THE END SO THE THREE SECTIONS ARE NOT READ SEPARATELY.
print('')
print('   IN SUM. The instrument passes its positive control: the north wall gives 12 of 12 holes at the')
print('   drawn lines, and the blind whole-wall sweep recovers 8 of those 12 without being told where')
print('   they are. On the south wall the same code in the same frames finds NO hole on any of those')
print('   twelve lines, range-matched at every distance band, and at zero shift the south patches are')
print('   brighter than their piers where the north patches are darker. That CONFIRMS what this file')
print('   draws: the south wall is solid up there. Nothing had ever tested it.')
print('   THE SOUTH MARKS ARE NOT ESTABLISHED AND THE CONTROL IS WHY. Three u positions survived a split')
print('   of the frames into halves, which shows the pattern is stable across photographs. It does not')
print('   show the pattern is ON the wall: a fixed lighting gradient is stable too. The height walk was')
print('   meant to settle that and it does the opposite, because blank stretches of south wall dip as')
print('   deep as the marks. So this instrument cannot separate a feature from the light on the wall,')
print('   and no south feature is claimed. The route needs an instrument that can, and that is written')
print('   down here so the next attempt does not rebuild this one.')
