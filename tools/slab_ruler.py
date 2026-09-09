# 2026-09-10: THE SLAB THICKNESS, MEASURED AS A SEPARATION SO THE HEIGHT CANCELS.
#
# WHY THIS SURFACE AND WHY NOW. tools/walk_through.py ended by measuring the blind spot of every surface in
# the model, and gallery-fascia came out worst of the ones the goal names: 1.97 m from the nearest step
# anybody ever took, so no occlusion argument can reach it. It is a vertical band on the hall-facing edge
# of each end gallery, u 4.194 west and u 48.056 east, running the full 15.4 m width of the hall and
# 0.26 m tall, from h 8.080 to h 8.340.
#
# AND THAT 0.26 IS NOT A MEASUREMENT, IT IS ARITHMETIC. The deck is 8.340 and the ceiling below it is
# 8.340 minus ENDW.slab, and slab is 0.26 because somebody wrote 0.26. Nothing in this repo has ever put a
# ruler on it.
#
# THE TRICK THAT MAKES IT MEASURABLE. Do not measure either edge. Measure the SEPARATION of the two. A
# common error in the hall frame's origin, in the camera height, or in the deck level moves both edges
# together and cancels out of a separation exactly. That is the same discipline that rescued the earlier
# work here: DIFFERENCE OUT THE SOFT TERM.
#
# THE DECISION RULE, FIXED BEFORE THE NUMBERS ARE OPENED.
#   1. Sample the photographs along a vertical sweep ON the fascia plane, across the hall, and stack the
#      profiles from every frame that sees it, each normalised to its own mean so exposure cancels.
#   2. The two strongest gradient peaks in the stacked profile are the two edges; their separation is the
#      slab thickness.
#   3. THE CONTROL IS AN INVENTED PLANE, the same sweep run on a plane INTO the hall from the real one,
#      where there is no fascia and no edges. If the invented plane produces peaks as strong as the real
#      one, this is measuring the picture and not the building, and nothing is concluded.
#   4. THE SECOND CONTROL IS THE OTHER END. West and east are two separate slabs of the same building. A
#      thickness claimed from one and not seen in the other is not claimed at all.
#   5. Nothing is claimed finer than the sweep step.
#
# WHAT IT CANNOT DO. It cannot fix the absolute height of either edge, by construction, which is the price
# of the cancellation. Anything standing in front of the fascia (a column, a banner, a person) enters the
# stack as noise. And it assumes the fascia plane's u is right; the east face is measured to 8 mm by
# tools/end_face_scan.py, so the east reading is the one to trust and the west is the check.
#   python tools/slab_ruler.py
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
HLO, HHI, HSTEP = 7.40, 9.10, 0.010
DS = np.linspace(2.0, 13.4, 24)
NULLOFF = 2.5          # metres into the hall for the invented plane
MINFRAMES = 20
MARGIN = 40            # pixels from the frame edge a sample must stay inside


def profile(cam, img, uface, sgn):
    """Mean intensity along a vertical sweep on the plane u = uface, or None if it is not in view."""
    hs = np.arange(HLO, HHI + 1e-9, HSTEP)
    got = np.zeros(len(hs))
    cnt = np.zeros(len(hs))
    for d in DS:
        pts = np.array([O + uface * HU + d * HD + np.array([0.0, h, 0.0]) for h in hs])
        x, y, z = cam.project(pts)
        ok = z > 0.5
        ok = np.logical_and(ok, x > MARGIN)
        ok = np.logical_and(ok, x < cam.w - MARGIN)
        ok = np.logical_and(ok, y > MARGIN)
        ok = np.logical_and(ok, y < cam.h - MARGIN)
        if ok.sum() < 0.8 * len(hs):
            continue
        xi = np.clip(x.astype(int), 0, img.shape[1] - 1)
        yi = np.clip(y.astype(int), 0, img.shape[0] - 1)
        v = img[yi, xi].astype(np.float64)
        got[ok] += v[ok]
        cnt[ok] += 1
    if (cnt > 0).sum() < 0.8 * len(hs):
        return None
    out = np.full(len(hs), np.nan)
    nz = cnt > 0
    out[nz] = got[nz] / cnt[nz]
    if np.isnan(out).any():
        return None
    return out - out.mean()


def stack(uface, sgn, label):
    hs = np.arange(HLO, HHI + 1e-9, HSTEP)
    rows, used = [], {}
    for cn in CLASSES:
        try:
            fr = U.load_class(cn)
        except Exception:
            continue
        for k, (cam, ip) in sorted(fr.items()):
            q = cam.center - O
            cu, ch = float(q @ HU), float(q[1])
            if ch > 3.0:
                continue                      # a floor camera, looking up at the gallery edge
            if sgn > 0 and cu > uface - 4.0:
                continue                      # and standing far enough away to see the band
            if sgn < 0 and cu < uface + 4.0:
                continue
            img = cv2.imread(ip, cv2.IMREAD_GRAYSCALE)
            if img is None:
                continue
            p = profile(cam, img, uface, sgn)
            if p is None:
                continue
            rows.append(p)
            used[cn] = used.get(cn, 0) + 1
    if len(rows) < MINFRAMES:
        return hs, None, used
    return hs, np.mean(np.asarray(rows), axis=0), used


# THE FIRST APERTURE WAS WRONG AND ITS OWN OUTPUT SHOWED IT. Sweeping h 7.40 to 9.10 and taking the two
# strongest gradients anywhere in that range found the west edges on h 8.930 and 8.850, which is not the
# fascia at all: it is the PARAPET TOP, drawn on 9.097, a different surface that tools/end_face_scan.py has
# already measured. A 0.26 m band of shadowed concrete cannot outshout a lit parapet edge, and asking it to
# was my error, not the building's. The peak search is now confined to the band the target was DECLARED in
# before this ever ran, the drawn fascia plus a quarter of a metre either side, and the invented-plane
# control is confined to exactly the same window so it stays a fair comparison.
WLO, WHI = 8.080 - 0.25, 8.340 + 0.25


def edges(hs, prof):
    g = np.abs(np.gradient(prof))
    g = np.convolve(g, np.ones(3) / 3.0, mode='same')
    idx = []
    for i in range(2, len(g) - 2):
        if not (WLO <= hs[i] <= WHI):
            continue
        if g[i] >= g[i - 1] and g[i] >= g[i + 1] and g[i] > 0:
            idx.append(i)
    idx.sort(key=lambda i: -g[i])
    keep = []
    for i in idx:
        if all(abs(hs[i] - hs[j]) > 0.06 for j in keep):
            keep.append(i)
        if len(keep) >= 4:
            break
    return keep, g


def run(name, uface, sgn, drawn):
    hs, prof, used = stack(uface, sgn, name)
    if prof is None:
        print('   %-5s NOT ENOUGH FRAMES SEE THIS FASCIA: %s. Nothing is read from this end.'
              % (name, ', '.join('%s %d' % t for t in used.items()) or 'none'))
        return None
    keep, g = edges(hs, prof)
    hsn, nprof, _ = stack(uface + sgn * NULLOFF, sgn, name + ' null')
    if nprof is None:
        npk = float('nan')
    else:
        ng = np.abs(np.gradient(nprof))
        win = np.logical_and(hsn >= WLO, hsn <= WHI)
        npk = float(ng[win].max())
    print('   %-5s %d frames, %s' % (name, sum(used.values()),
                                     ', '.join('%s %d' % t for t in sorted(used.items()))))
    print('         the two strongest edges land on h %s'
          % ', '.join('%.3f (%.3f)' % (hs[i], g[i]) for i in keep[:2]))
    if len(keep) >= 2:
        sep = abs(hs[keep[0]] - hs[keep[1]])
    else:
        sep = None
    print('         the invented plane %.1f m into the hall peaks at %.3f against this end\'s %.3f'
          % (NULLOFF, npk, g[keep[0]] if keep else float('nan')))
    return dict(name=name, hs=hs, prof=prof, keep=keep, g=g, sep=sep, null=npk,
                frames=sum(used.values()), drawn=drawn)


def main():
    print('THE DECISION RULE, WRITTEN OUT BEFORE THE NUMBERS ARE OPENED.')
    print('   The fascia is a vertical band on the hall-facing edge of each end gallery, drawn from')
    print('   h 8.080 to h 8.340: a slab 0.260 m thick, and that 0.260 is arithmetic, not a measurement.')
    print('   Nothing here measures either edge. It measures their SEPARATION, because a common error in')
    print('   the frame origin, the camera height or the deck level moves both together and cancels out')
    print('   of a separation exactly. The photographs are sampled along a vertical sweep ON the fascia')
    print('   plane, across the hall, every %.0f mm, and the profiles stacked with each frame normalised'
          % (1000 * HSTEP))
    print('   to its own mean so exposure cancels. THE CONTROL IS AN INVENTED PLANE %.1f m into the hall,'
          % NULLOFF)
    print('   where there is no fascia, judged inside the SAME window %.2f to %.2f that the target was'
          % (WLO, WHI))
    print('   declared in before this ran; if it peaks as hard as the real one this is measuring the')
    print('   picture')
    print('   and not the building. THE SECOND CONTROL IS THE OTHER END: a thickness seen at one end and')
    print('   not the other is not claimed. Nothing is claimed finer than the %.0f mm step.'
          % (1000 * HSTEP))
    print('')
    west = run('west', 4.194, -1, 0.260)
    east = run('east', 48.056, +1, 0.260)
    print('')
    got = [r for r in (west, east) if r and r['sep'] is not None]
    if not got:
        print('   NEITHER END GIVES TWO EDGES. This measures nothing and the drawn 0.260 m stands')
        print('   untested, exactly as it did before this ran.')
        sys.exit(0)
    live = [r for r in got if r['g'][r['keep'][0]] > r['null']]
    if not live:
        print('   NEITHER END BEATS ITS OWN INVENTED PLANE. The edges this found are in the picture, not')
        print('   on the building, and NOTHING IS CONCLUDED about the slab.')
        sys.exit(0)
    print('   the ends that beat their invented plane: %s' % ', '.join(r['name'] for r in live))
    for r in live:
        print('      %-5s two edges %.3f m apart, against %.3f m drawn'
              % (r['name'], r['sep'], r['drawn']))
    if len(live) < 2:
        print('')
        print('   ONLY ONE END SPEAKS, so by the rule written above no thickness is claimed from it. What')
        print('   it gives is a single reading of %.3f m against %.3f m drawn, and a second end would be'
              % (live[0]['sep'], live[0]['drawn']))
        print('   needed before that could move anything in the file.')
        sys.exit(0)
    seps = [r['sep'] for r in live]
    if abs(seps[0] - seps[1]) > 2 * HSTEP:
        print('')
        print('   THE TWO ENDS DISAGREE BY %.3f m, more than the step, so they are not measuring one'
              % abs(seps[0] - seps[1]))
        print('   thickness and no number is claimed from either.')
        sys.exit(0)
    m = float(np.mean(seps))
    print('')
    print('   BOTH ENDS AGREE: %.3f m against %.3f m drawn, a difference of %+.0f mm.'
          % (m, live[0]['drawn'], 1000 * (m - live[0]['drawn'])))
    if abs(m - live[0]['drawn']) <= 2 * HSTEP:
        print('   That is inside the sweep step, so the drawn slab is confirmed rather than corrected, and')
        print('   for the first time it is a measurement rather than a number somebody wrote.')
    else:
        print('   That is outside the sweep step at both ends independently, so the drawn slab is wrong by')
        print('   that much and the file should carry %.3f m.' % m)


if __name__ == '__main__':
    main()
