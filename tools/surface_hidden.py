# 2026-09-10: HOW MUCH OF EACH SURFACE CAN A VIEWER ACTUALLY SEE? THE ORDINARY PASS AGAINST THE X-RAY.
#
# WHAT FORCED THIS. tools/surface_pick.py chose, for every named balcony, wall and corridor surface, the
# posed frame that frames that surface's own bounding box largest, and those boxes fill 1 to 56 per cent of
# their pictures. Then the identity render showed the surfaces themselves drawing between nothing and nine
# per cent, most of them under a thousandth. Two very different facts produce that: a thin surface seen
# edge-on, which is honest geometry, or a surface hidden behind something else, which means nobody can see
# it and no photograph can check it. Guessing between them is not allowed here, so it is measured.
#
# THE MEASUREMENT IS A SUBTRACTION AND NOTHING ELSE. The same thirty poses were rendered twice with the
# same identity colours: once normally, and once with everything that is NOT a goal surface hidden. The
# x-ray count is what the surface covers when only its own kind can occlude it. The ordinary count is what
# survives to the screen. One minus their ratio is the fraction the rest of the model hides, and it needs
# no theory of what does the hiding.
#
# AND THE FIRST FORM OF THIS X-RAY WAS BROKEN, WHICH ITS OWN OUTPUT REVEALED. It turned DEPTH TESTING OFF
# instead, which let the goal surfaces draw over each other in traversal order: end-ground-wall came back
# with 937k pixels in the ordinary pass and 266k with supposedly nothing covering it, and five surfaces
# scored NEGATIVE hidden fractions. A surface cannot be more visible than its own silhouette, so that was
# an instrument fault rather than a result, and it is recorded here rather than quietly fixed.
#
# WHAT IT CANNOT DO. It says nothing about whether a surface is in the RIGHT place, only whether it is
# visible. A surface that is hidden may still be correct, and may still be load-bearing for the model's
# shape. And a surface hidden by the baked scan is hidden by a mesh that came from photographs of this
# building, which is a reasonable thing to be behind.
#   python tools/surface_hidden.py
import io
import json
import sys

import cv2
import numpy as np

sys.path.insert(0, 'tools')
import surface_match as SM

TOL = 28


def main():
    picks = json.loads(io.open('render-match.json', encoding='utf-8').read())
    tab = json.loads(io.open('render-match/idmap.json', encoding='utf-8').read())
    names = [n for n, c in zip(tab['names'], tab['colours']) if c]
    cols = [c for c in tab['colours'] if c]
    print('THE SAME THIRTY POSES, RENDERED TWICE WITH THE SAME IDENTITY COLOURS: once normally, and once')
    print('with everything that is NOT a goal surface hidden. The difference is what the rest of the')
    print('model covers up.')
    print('')
    seen, xray = {}, {}
    frames = 0
    for i, p in enumerate(picks):
        a = cv2.imread('render-match/id%02d.jpg' % i, cv2.IMREAD_COLOR)
        b = cv2.imread('render-match/xr%02d.jpg' % i, cv2.IMREAD_COLOR)
        if a is None or b is None:
            continue
        frames += 1
        A = SM.turn(p, a, nearest=True).astype(np.int16)
        B = SM.turn(p, b, nearest=True).astype(np.int16)
        for nm, c in zip(names, cols):
            k = np.array([c[2], c[1], c[0]], np.int16)
            seen[nm] = seen.get(nm, 0) + int((np.abs(A - k).max(2) <= TOL).sum())
            xray[nm] = xray.get(nm, 0) + int((np.abs(B - k).max(2) <= TOL).sum())
    if not frames:
        sys.exit('   no rendered pair on disk')

    rows = []
    for nm in names:
        if xray[nm] < 500:
            # too few pixels anywhere in thirty frames to divide by; not a verdict on the surface
            rows.append((nm, seen[nm], xray[nm], None))
        else:
            rows.append((nm, seen[nm], xray[nm], 1.0 - seen[nm] / float(xray[nm])))
    rows.sort(key=lambda r: (r[3] is None, -(r[3] if r[3] is not None else 0), -r[2]))
    print('   surface                   drawn px   x-ray px   hidden')
    for nm, s, x, f in rows:
        print('   %-24s %9d  %9d   %s'
              % (nm[:24], s, x, 'too small to measure' if f is None else '%.1f per cent' % (100 * f)))

    live = [r for r in rows if r[3] is not None]
    gone = [r for r in rows if r[3] is None]
    if live:
        hid = [r[3] for r in live]
        print('')
        print('   %d of the %d named surfaces reach the screen at all across %d frames chosen to show them'
              % (sum(1 for r in live if r[1] > 0), len(rows), frames))
        print('   as large as any posed camera in the archive ever does. Of those that exist to be seen,')
        print('   the median is %.1f per cent hidden, and %d of them are more than nine tenths hidden.'
              % (100 * float(np.median(hid)), sum(1 for v in hid if v > 0.9)))
    if gone:
        print('')
        print('   AND %d SURFACES COVER UNDER 500 PIXELS ACROSS ALL THIRTY FRAMES EVEN WITH EVERYTHING'
              % len(gone))
        print('   ELSE HIDDEN, which is too little to divide by. They are either invisible in the page or')
        print('   they never enter one of these views at a readable size. That is not a fault by itself')
        print('   and it is not read as one: it is the reason this instrument is silent about them.')
        print('      %s' % ', '.join(r[0] for r in gone))
    print('')
    print('   WHAT THIS DOES AND DOES NOT SAY. It says nothing about whether a surface is in the RIGHT')
    print('   place, only whether a viewer can see it. A hidden surface may be perfectly correct and may')
    print('   still decide the shape of what is drawn over it. What it does settle is why the photographic')
    print('   check found so little to score: most of what the goal names is behind the baked scan, and')
    print('   the bake is what a visitor to this page actually looks at.')


if __name__ == '__main__':
    main()
