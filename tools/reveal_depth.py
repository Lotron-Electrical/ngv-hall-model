# 2026-09-10: THE WALL THICKNESS AT THE OPENINGS, READ FROM INSIDE THEM.
#
# WHAT THIS NUMBER IS. The twelve openings in the north wall are drawn with stone reveals openDepth
# deep, 0.90 m, from the hall face on d -0.030 back to the corridor arris on -0.930. That is the
# thickness of the brick wall the goal names, and it is the biggest single shape in every balcony
# picture Lloyd sent. It is not a measurement: the provenance carries a LOWER bound of 0.422 m from a
# lens that leaned through an opening (a camera cannot be inside stone), and the 0.90 above that bound
# was read by eye. Nothing has measured the arris where the reveal meets the corridor.
#
# WHO CAN SEE IT. 315 posed frames stand inside the openings, and the pan sets (b1p, b5p) turn the phone
# around inside them, which is the one place the pan poses are good: their own quality file puts the
# position error on 0.056 and 0.051 m median with the reveal half a metre away. From inside an opening
# the reveal is a stone face beside the camera running from the hall arris back to the corridor arris,
# and beyond the corridor arris the ray runs on into the unlit corridor. Stone against dark. The soffit
# ruler died on dark against dark; this is the opposite case, and it is the reason to try a picture
# boundary once more.
#
# HOW. For every frame standing inside an opening, sample the photograph along sweeps in d ON each reveal
# plane (u = jamb) at seven heights between sill and head, from 0.30 m in front of the hall face to
# 0.70 m behind the drawn corridor arris. Each frame is read ON ITS OWN, because stacking frames whose
# poses differ by 50 mm on a target 500 mm away would blur the edge away; and it is read as a SEPARATION,
# hall arris to corridor arris on the same sweep, so a pose shift common to both cancels.
#
# THE DECISION RULE, FIXED BEFORE THE NUMBERS ARE OPENED.
#   1. Hall arris = strongest gradient within 0.15 m of the drawn -0.030. Corridor arris = strongest
#      gradient within 0.35 m of the drawn -0.930. Both declared here. A frame that does not show both
#      inside the picture is not read.
#   2. THE NULL, per frame: the same sweep on an invented plane in the open air of the aperture, 0.60 m
#      from the jamb (or 0.95 m when the camera stands within 0.20 m of the first), judged in the same
#      corridor band. A frame whose real plane does not beat its invented plane is a miss.
#   3. A jamb is LIVE when eight or more frames read it and the real plane beats the invented one in
#      seventy percent of them or more.
#   4. THE SECOND CONTROL is agreement: two live jambs or more from two different openings, medians
#      within 0.10 m of each other. And A CLAIM MUST NOT BE SMALLER THAN ITS OWN SPREAD: a jamb whose
#      10th-to-90th percentile half-width exceeds 0.15 m is reported but not used.
#   5. The number claimed is the median over the live jambs, to no better than 0.05 m.
#
# WHAT IT CANNOT DO. It reads the openings people stood in (4, 5 and 10) and no other; it assumes the
# jamb u values, which body_in_wall.py holds to the same 0.100 m; and if the corridor behind the arris
# is as bright as the stone, the band holds noise and the null says so.
#
# THE RESULT, AND WHY IT IS A COUNT AND NOT A SHRUG (2026-09-10, first run). NO FRAME READS ANY REVEAL:
# 317 frames offered, none with the sweep in view. The census behind that, run the same hour: 132 frames
# have the HALL arris of a reveal at least half in view, and the CORRIDOR arris band is in view in none of
# them, the best of the 317 showing 8% of it. Every camera standing in an opening stands 0.25 to 0.45 m
# into the reveal and looks at the hall (forward d component +0.38 or more in all 317), so the corridor
# arris is 0.5 m behind the operator's shoulder and cannot enter a frame that is not turned round. Nobody
# turned round. The wall thickness openDepth 0.90 therefore stays untested by photograph, with the reason
# now counted rather than suspected: the archive holds no frame that looks back into a reveal. The lower
# bound of 0.422 m from the body argument stands, and nothing above it is a measurement.
#   hwq run --gb 3 --label "reveal depth" -- python -u tools/reveal_depth.py
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
CLASSES = ('b1', 'b1p', 'b4', 'b5', 'b5p')
DSTEP = 0.010
FRONTW = 0.15
BACKW = 0.35
HS = (9.0, 9.3, 9.6, 9.9, 10.2, 10.5, 10.8)
MINFR = 8
BEAT = 0.70
TOL = 0.10
SPREADMAX = 0.15
MARGIN = 20
NULLOFF = (0.60, 0.95)
INSET = 0.12

src = io.open('index.html', encoding='utf-8').read()
mo = re.search(r'const WALLF=\{openings:\[(.*?)\],\s*\n', src, re.S)
OPEN = [(float(a), float(b)) for a, b in re.findall(r'\[([0-9.]+),([0-9.]+)\]', mo.group(1))]
DN = float(re.search(r'dNorth:(-?[0-9.]+)', src).group(1))
DEPTH = float(re.search(r'openDepth:\s*([0-9.]+)', src).group(1))
DR = DN - DEPTH
DS = np.arange(DN + 0.30, DR - 0.70 - 1e-9, -DSTEP)


def sweep(cam, img, uplane):
    """mean-normalised intensity along d on the plane u = uplane, or None if the sweep is not in view."""
    got = np.zeros(len(DS))
    cnt = np.zeros(len(DS))
    for h in HS:
        pts = np.array([O + uplane * HU + d * HD + np.array([0.0, h, 0.0]) for d in DS])
        x, y, z = cam.project(pts)
        ok = z > 0.05
        ok = np.logical_and(ok, x > MARGIN)
        ok = np.logical_and(ok, x < cam.w - MARGIN)
        ok = np.logical_and(ok, y > MARGIN)
        ok = np.logical_and(ok, y < cam.h - MARGIN)
        if ok.sum() < 0.9 * len(DS):
            continue
        xi = np.clip(x.astype(int), 0, img.shape[1] - 1)
        yi = np.clip(y.astype(int), 0, img.shape[0] - 1)
        v = img[yi, xi].astype(np.float64)
        got[ok] += v[ok]
        cnt[ok] += 1
    if (cnt > 0).sum() < 0.9 * len(DS) or cnt.max() < 3:
        return None
    out = np.full(len(DS), np.nan)
    nz = cnt > 0
    out[nz] = got[nz] / cnt[nz]
    if np.isnan(out).any():
        return None
    return out - out.mean()


def grad(prof):
    g = np.abs(np.gradient(prof))
    return np.convolve(g, np.ones(3) / 3.0, mode='same')


def peak(g, lo, hi):
    win = np.logical_and(DS >= lo, DS <= hi)
    i = int(np.argmax(np.where(win, g, -1)))
    return float(DS[i]), float(g[i])


def main():
    print('THE DECISION RULE, WRITTEN OUT BEFORE THE NUMBERS ARE OPENED.')
    print('   Each reveal is a stone face on u = jamb from the hall arris on d %.3f back to the corridor'
          % DN)
    print('   arris drawn on %.3f, %.2f m of wall. Every frame standing inside an opening is sampled along'
          % (DR, DEPTH))
    print('   sweeps in d ON that plane over %d heights, read on its own, and the number read is the'
          % len(HS))
    print('   SEPARATION of the hall arris (strongest gradient within %.2f m of %.3f) and the corridor'
          % (FRONTW, DN))
    print('   arris (strongest within %.2f m of %.3f). THE NULL is the same sweep on an invented plane in'
          % (BACKW, DR))
    print('   the open air of the aperture, judged in the same band; a jamb is live when %d or more frames'
          % MINFR)
    print('   read it and the real plane beats the invented one in %.0f%% of them. Two live jambs from two'
          % (100 * BEAT))
    print('   openings within %.2f m, each with a 10th-to-90th half-width under %.2f m, are needed for a'
          % (TOL, SPREADMAX))
    print('   claim, and nothing finer than 0.05 m is claimed.')
    print('')
    frames = []
    for cn in CLASSES:
        try:
            fr = U.load_class(cn)
        except Exception as e:
            print('   %s: not loaded (%s)' % (cn, e))
            continue
        for k, (cam, ip) in sorted(fr.items()):
            q = cam.center - O
            frames.append((cn, k, cam, ip, float(q @ HU), float(q @ HD), float(q[1])))
    print('   %d posed frames offered from %s' % (len(frames), ', '.join(CLASSES)))
    print('')
    results = {}
    for oi, (u0, u1) in enumerate(OPEN, 1):
        inside = [f for f in frames if u0 + INSET < f[4] < u1 - INSET and -1.3 < f[5] < 0.6
                  and 8.5 < f[6] < 11.3]
        if not inside:
            continue
        for jname, uj, s in (('west', u0, +1), ('east', u1, -1)):
            seps, wins, used = [], 0, {}
            for cn, k, cam, ip, cu, cd, ch in inside:
                if s * (cu - uj) < INSET:
                    continue
                img = cv2.imread(ip, cv2.IMREAD_GRAYSCALE)
                if img is None:
                    continue
                prof = sweep(cam, img, uj)
                if prof is None:
                    continue
                g = grad(prof)
                df, gf = peak(g, DN - FRONTW, DN + FRONTW)
                db, gb = peak(g, DR - BACKW, DR + BACKW)
                unull = None
                for off in NULLOFF:
                    if abs(cu - (uj + s * off)) >= 0.20:
                        unull = uj + s * off
                        break
                if unull is None:
                    continue
                nprof = sweep(cam, img, unull)
                if nprof is None:
                    continue
                _, nb = peak(grad(nprof), DR - BACKW, DR + BACKW)
                seps.append(df - db)
                wins += 1 if gb > nb else 0
                used[cn] = used.get(cn, 0) + 1
            if not seps:
                continue
            seps = np.array(seps)
            n = len(seps)
            med = float(np.median(seps))
            p10, p90 = float(np.percentile(seps, 10)), float(np.percentile(seps, 90))
            half = 0.5 * (p90 - p10)
            live = n >= MINFR and wins / n >= BEAT
            usable = live and half <= SPREADMAX
            results[(oi, jname)] = dict(n=n, wins=wins, med=med, p10=p10, p90=p90, half=half,
                                        live=live, usable=usable, used=used)
            print('   opening %2d %-4s jamb u %.3f: %3d frames (%s), real beats invented in %3d (%.0f%%)'
                  % (oi, jname, uj, n, ', '.join('%s %d' % t for t in sorted(used.items())), wins,
                     100.0 * wins / n))
            print('        separation median %.3f m, 10th to 90th %.3f to %.3f (half-width %.3f): %s'
                  % (med, p10, p90, half,
                     'LIVE and usable' if usable else 'live but SPREAD TOO WIDE to use' if live
                     else 'not live' + ('' if n >= MINFR else ' (too few frames)')))
    print('')
    if not results:
        print('   NO FRAME READS ANY REVEAL. Nothing is concluded and %.2f stands untested.' % DEPTH)
        return
    use = {k: r for k, r in results.items() if r['usable']}
    if len(use) < 2 or len(set(k[0] for k in use)) < 2:
        print('   FEWER THAN TWO USABLE JAMBS FROM TWO OPENINGS (%d usable), so by the rule above no depth'
              % len(use))
        print('   is claimed. The drawn %.2f m stands untested by this.' % DEPTH)
        return
    meds = [r['med'] for r in use.values()]
    if max(meds) - min(meds) > TOL:
        print('   THE USABLE JAMBS DISAGREE: medians %s spread %.3f m, more than the %.2f m tolerance, so'
              % (', '.join('%.3f' % m for m in meds), max(meds) - min(meds), TOL))
        print('   they are not measuring one thickness and no number is claimed. %.2f stands untested.' % DEPTH)
        return
    m = float(np.median(meds))
    print('   %d USABLE JAMBS FROM %d OPENINGS AGREE: medians %s, claimed as %.2f m against %.2f drawn,'
          % (len(use), len(set(k[0] for k in use)), ', '.join('%.3f' % v for v in meds), round(m, 2), DEPTH))
    print('   a difference of %+.0f mm.' % (1000 * (m - DEPTH)))
    if abs(m - DEPTH) <= 0.05:
        print('   Inside 0.05 m, so the drawn thickness is CONFIRMED rather than corrected, and for the first')
        print('   time it is a measurement.')
    else:
        print('   Outside 0.05 m at every usable jamb independently, so the drawn thickness is wrong by that')
        print('   much and the file should carry %.2f m.' % round(m, 2))


if __name__ == '__main__':
    main()
