# 2026-09-10: HOW HIGH IS THE BARRIER ON THE GALLERY, ASKED BY WHAT YOU CAN SEE OVER IT.
#
# THE BLACK BAND IN THE EAST GALLERY RENDER NOW HAS A NAME. index.html line 4859 draws gallery-handrail,
# an OPAQUE Lambert quad across the full width of the gallery at deck + railTops.east = 9.865, and a deck
# camera stands 0.164 m behind it with its eye on 9.810. A 60 mm bar 0.164 m from a lens subtends about
# 18 degrees of vertical view, which is roughly a third of a portrait frame straight across the middle.
# That is the band, and tools/rail_band.py has already shown that 28 of 29 photographs from those same
# standpoints have no such bar in them.
#
# SO THE JOB IS TO MEASURE THE BARRIER RATHER THAN GO ON BRACKETING IT, and the way to do that is the
# only class of argument that has held up all day: light either arrived or it did not.
#
# THE INSTRUMENT. A camera standing on a gallery deck looks out over the barrier at the north wall of the
# hall, 15 to 45 m away, which carries TWELVE OPENINGS whose positions this file now knows well. For each
# camera and each opening, the sightline to the bottom of that opening is traced to the plane of the
# barrier, giving the height h at which the view passes it. Then the photograph is asked whether that
# opening is actually there: an opening is a hole into an unlit corridor, so it reads dark against the
# lit pier beside it, which is the same test tools/opening_holes.py ran with a 4 per cent control.
#   an opening SEEN at crossing height h  =>  nothing opaque stands on h, so the barrier top is below it
#   an opening HIDDEN at crossing height h  =>  something opaque stands on or above h
# The barrier top is the height where those two swap over. Nothing is fitted to an edge, no gradient is
# measured, and no line is searched for near a drawn one.
#
# THE CONTROLS, three of them, stated before it runs.
#   THE HEADS. The same openings are tested at their TOPS, h 11.0, which no barrier on a deck can hide.
#   If those are not visible the instrument is broken and the run says so instead of reporting a height.
#   THE OTHER END. West is run by the same code on frames the east never sees.
#   THE TWELVE. Each opening is an independent instance, so a barrier height that only one of them
#   supports is not a measurement.
#
# WHAT IT CANNOT DO. It finds the top of the OPAQUE part. Glass above that is invisible to it. And the
# camera stands so close to the barrier that the sightline drops only a few centimetres crossing it, so
# the crossing height is close to the eye height: this measures the barrier against the SPREAD OF EYE
# HEIGHTS in the clips and can be no sharper than that spread allows.
#   python tools/rail_over.py [west|east|both]
import sys

import cv2
import numpy as np

sys.path.insert(0, 'tools')
import underside_geom as U

O = np.array([-54.907447, -1.43545, 3.040286])
HU = np.array([0.975681, 0, 0.219196])
HD = np.array([0.219196, 0, -0.975681])
DN = -0.030
SILL, HEAD = 8.740, 11.165
# the openings as index.html now draws them, opening 3 included at its measured place
OPEN = [[4.098, 5.310], [7.697, 8.911], [11.487, 12.700],
        [15.227, 16.440], [18.917, 20.130], [22.565, 23.778],
        [26.213, 27.426], [29.963, 31.175], [33.642, 34.853],
        [37.177, 38.383], [40.906, 42.118], [44.526, 45.739]]
ENDS = {'west': {'face': 4.194, 'deck': 8.34, 'ups': 0.757, 'rail': 1.459, 'sense': -1.0},
        'east': {'face': 48.056, 'deck': 8.34, 'ups': 0.755, 'rail': 1.525, 'sense': 1.0}}
CLASSES = ('b1', 'b3', 'b5', 'b7s', 'b6g')
DWIDTH = 15.364
LOW = 8.94                       # the bottom of an opening, the thing a barrier can hide
CTRL = (10.00, 10.80)            # a band of the SAME openings that no barrier on a deck reaches


def patch(im, cam, u0, u1, lo, hi):
    """mean brightness of a rectangle on the wall face, or None if it is not usefully in shot"""
    us = np.linspace(u0 + 0.12, u1 - 0.12, 7)
    ls = np.linspace(lo, hi, 5)
    pts = np.array([O + u * HU + DN * HD + np.array([0.0, lv, 0.0]) for u in us for lv in ls])
    x, y, z = cam.project(pts)
    ok = np.logical_and.reduce([z > 0.5, x > 1, x < cam.w - 2, y > 1, y < cam.h - 2])
    if ok.sum() < 25:
        return None
    if (x[ok].max() - x[ok].min()) < 8 or (y[ok].max() - y[ok].min()) < 4:
        return None
    v = np.array([float(im[int(y[i]), int(x[i])]) for i in np.nonzero(ok)[0]])
    return float(v.mean())


def seen(im, cam, u0, u1, lo, hi):
    """does this band of this opening read as a hole against the pier beside it"""
    w = u1 - u0
    a = patch(im, cam, u0, u1, lo, hi)
    b = patch(im, cam, u1 + 0.25 * w, u1 + 1.25 * w, lo, hi)
    if a is None or b is None:
        return None
    return a < 0.72 * b


which = sys.argv[1] if len(sys.argv) > 1 else 'both'
for end in (('west', 'east') if which == 'both' else (which,)):
    E = ENDS[end]
    uF, s = E['face'], E['sense']
    obs, ctrl = [], []
    nframes = 0
    for cname in CLASSES:
        try:
            frames = U.load_class(cname)
        except Exception:
            continue
        for k, (cam, ip) in sorted(frames.items()):
            q = cam.center - O
            cu, cd, ch = float(q @ HU), float(q @ HD), float(q[1])
            back = (cu - uF) * s
            if back < 0.02 or back > 3.5:
                continue
            if not (0.5 < cd < 14.9) or not (E['deck'] + 0.4 < ch < E['deck'] + 2.4):
                continue
            f = cam.R.T @ np.array([0, 0, 1.0])
            if float(f @ HU) * s > -0.15:
                continue
            im = None
            for oi, (u0, u1) in enumerate(OPEN):
                ou = 0.5 * (u0 + u1)
                if (ou - uF) * s > -2.0:          # the target must be down the hall, not beside us
                    continue
                # AND IT MUST NOT BE EDGE ON. The far openings are seen so obliquely from a deck that
                # the opening and the pier beside it land on the same few pixels, which is what made
                # the first run of this fail its own control.
                w2 = O + ou * HU + DN * HD + np.array([0.0, LOW, 0.0]) - cam.center
                w2 = w2 / np.linalg.norm(w2)
                if abs(float(w2 @ HD)) < 0.35:
                    continue
                # where the sightline to the bottom of this opening crosses the barrier plane
                t = (uF - cu) / (ou - cu)
                if not (0.0 < t < 1.0):
                    continue
                hx = ch + t * (LOW - ch)
                dx = cd + t * (0.0 - cd)
                if not (0.3 < dx < DWIDTH - 0.3):
                    continue
                if im is None:
                    im = cv2.imread(ip, cv2.IMREAD_GRAYSCALE)
                    if im is None:
                        break
                    nframes += 1
                v = seen(im, cam, u0, u1, LOW - 0.10, LOW + 0.30)
                if v is not None:
                    obs.append((hx, v, oi + 1, k))
                c = seen(im, cam, u0, u1, CTRL[0], CTRL[1])
                if c is not None:
                    ctrl.append(c)
    print('')
    print('%s GALLERY: %d frames stand on the deck, %d sightlines to the bottom of an opening'
          % (end.upper(), nframes, len(obs)))
    if len(ctrl) >= 12:
        print('   THE CONTROL: a band of the same openings on h %.2f to %.2f, which no barrier on a deck'
              % CTRL)
        print('   reaches and the gallery soffit does not clip,')
        print('   read as holes in %.0f per cent of %d readings.' % (100.0 * np.mean(ctrl), len(ctrl)))
    if len(obs) < 20:
        print('   too few sightlines to measure anything')
        continue
    if len(ctrl) >= 12 and np.mean(ctrl) < 0.35:
        print('   THE CONTROL FAILS: the instrument cannot even see the parts nothing hides, so it is in')
        print('   no position to say what hides the rest. No height is reported.')
        continue
    vis = [o for o in obs if o[1]]
    hid = [o for o in obs if not o[1]]
    print('   %d openings SEEN over the barrier, %d not seen' % (len(vis), len(hid)))
    # A HIDDEN READING IS ONLY WORTH SOMETHING IF THE INSTRUMENT WOULD HAVE SEEN IT. At a control rate
    # of about a half, one reading in two fails to register a hole that nothing is hiding, so "not seen"
    # here is mostly the instrument and not the barrier. Only the POSITIVE readings carry an argument,
    # and they carry it in one direction: light arrived, so nothing opaque stood on that crossing.
    rate = float(np.mean(ctrl)) if ctrl else 0.0
    if rate < 0.75:
        print('   THE NOT-SEEN READINGS ARE DISCARDED. The control says this instrument registers an')
        print('   opening it can certainly see only %.0f per cent of the time, so a miss is as likely to'
              % (100 * rate))
        print('   be the instrument as a barrier. Only what IS seen is used, and it says one thing:')
        print('   nothing opaque stands on the height that sightline crossed.')
    # AND A SIGHTLINE ONLY ARGUES ABOUT WHAT IT ACTUALLY CROSSED. This file draws GLASS from the upstand
    # top up to the handrail, and glass does not block a view, so a crossing that lands in the glass
    # contradicts nothing however clearly the opening is seen. The first version of this counted those
    # as refutations of the handrail, which they are not.
    rt, ut = E['deck'] + E['rail'], E['deck'] + E['ups']
    inhand = [o for o in vis if rt - 0.06 <= o[0] <= rt]
    insolid = [o for o in vis if o[0] <= ut]
    inglass = [o for o in vis if ut < o[0] < rt - 0.06]
    above = [o for o in vis if o[0] > rt]
    print('   this file draws a SOLID upstand to h %.3f, GLASS from there to h %.3f, and an OPAQUE'
          % (ut, rt - 0.06))
    print('   handrail on h %.3f to %.3f.' % (rt - 0.06, rt))
    print('   of the %d sightlines that were seen: %d crossed the solid, %d crossed the glass, %d crossed'
          % (len(vis), len(insolid), len(inglass), len(inhand)))
    print('   the opaque handrail and %d passed clear above the lot.' % len(above))
    nsolid = len(set(o[2] for o in insolid))
    nhand = len(set(o[2] for o in inhand))
    if len(insolid) >= 8 and nsolid >= 3:
        print('   THE SOLID UPSTAND IS REFUTED: %d sightlines on %d different openings were seen through'
              % (len(insolid), nsolid))
        print('   a height this file fills with solid stone. The opaque top is below h %.3f, %.3f m over'
              % (min(o[0] for o in insolid), min(o[0] for o in insolid) - E['deck']))
        print('   the deck.')
    elif len(inhand) >= 8 and nhand >= 3:
        print('   THE OPAQUE HANDRAIL IS REFUTED BY OCCLUSION: %d sightlines on %d different openings were'
              % (len(inhand), nhand))
        print('   seen through the 60 mm the handrail occupies. An opaque bar across the whole gallery')
        print('   cannot be seen through, whatever it looks like.')
    else:
        print('   NO LEVERAGE FROM THESE STANDPOINTS, and that is the finding rather than a failure.')
        print('   Every deck camera stands with its eye between the upstand top and the handrail, which')
        print('   is exactly where a person stands, so nearly every sightline to a far opening crosses')
        print('   the barrier plane inside the GLASS. Glass blocks nothing, so seeing the opening through')
        print('   it contradicts nothing. Only %d sightlines crossed the opaque handrail and %d crossed'
              % (len(inhand), len(insolid)))
        print('   the solid, which is not enough of either to refuse or confirm them.')
        print('   THIS IS WHY THE HANDRAIL HAS BEEN SO HARD TO PIN DOWN. An occlusion argument needs the')
        print('   thing to stand between the lens and something known, and from a deck this one almost')
        print('   never does. tools/rail_band.py, which reads the pixels the bar itself would fill, is')
        print('   the right instrument for it, and it is where the 1.080 to 1.465 bracket comes from.')
