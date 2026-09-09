# 2026-09-10: MAP THE BACK WALL OF A GALLERY FROM THE PHOTOGRAPHS AND SEE WHAT THIS FILE IS MISSING.
#
# WHERE THIS CAME FROM. Looking through the balcony clips by eye for something else, the gallery
# interiors plainly show DOORWAYS in the back wall. index.html draws a door in the WEST gallery back wall
# (westTopDoor) and nothing of the kind in the east: the east back wall carries an exit sign and three
# lamps and is otherwise a blank quad from the deck to the canopy. If there is a door in it, that is a
# hole in the balconies rather than a number that is slightly off.
#
# THE INSTRUMENT IS THE ONE THAT WORKED ON THE NORTH WALL. A doorway into an unlit space is dark and flat
# against lit ashlar, which is exactly what tools/opening_holes.py used to confirm twelve openings with a
# 4 per cent control. Here it is turned into a map rather than a yes or no: the back wall plane is ruled
# into cells, every posed camera that can see a cell contributes its brightness, and the median over all
# of them is drawn as a picture of the wall in world coordinates. Features appear where they are, in
# metres, with no edge finder and no fitting.
#
# WHY A MAP AND NOT A TEST. A test needs to know what it is looking for. Nothing here knows what is on
# that wall, so the honest move is to build the picture and look at it, then measure whatever it shows.
# The model's own furniture, the exit sign and the lamps, is marked on the output as a check: if they do
# not land on anything, the map is not registered and nothing in it can be trusted.
#
# WHAT IT CANNOT DO. It is a median over frames taken from different angles, so anything not ON the wall
# plane, a person, a case, a plinth, smears rather than resolves. A sharp rectangle in the map is a
# feature of the wall; a soft blob is somebody standing in front of it.
#   python tools/gallery_backwall.py [west|east|both]
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
CLASSES = ('b3', 'b3p', 'b6g', 'b6gp', 'b7s', 'b7sp', 'day4k', 'b5', 'b5p', 'b1', 'b1p', 'b4')
DSTEP = HSTEP = 0.05


def model():
    src = io.open('index.html', encoding='utf-8').read()

    def g(pat):
        return float(re.search(pat, src).group(1))

    def endw(key):
        return float(re.search(r'const ENDW=\{[^}]*?\b' + key + r':\s*(-?[0-9.]+)', src).group(1))

    lam = re.search(r'wallLamps:\{east:\[(.*?)\]\}', src)
    return {'deck': 8.34, 'top': endw('top'), 'recess': endw('face'),
            'dSouth': g(r'dSouth:([0-9.]+)'),
            'wface': 4.194, 'eface': 48.056,
            'exit_e': [13.5, 10.69],
            'lamps_e': [[float(a), float(b)] for a, b in
                        re.findall(r'\[([0-9.]+),([0-9.]+)\]', lam.group(1))] if lam else []}


M = model()
BACK = {'west': M['wface'] - M['recess'], 'east': M['eface'] + M['recess']}
which = sys.argv[1] if len(sys.argv) > 1 else 'east'
for end in (('west', 'east') if which == 'both' else (which,)):
    uB, s = BACK[end], (-1.0 if end == 'west' else 1.0)
    ds = np.arange(0.2, M['dSouth'] - 0.2 + 1e-9, DSTEP)
    hs = np.arange(M['deck'], M['top'] + 1e-9, HSTEP)
    acc = [[[] for _ in ds] for _ in hs]
    nf = 0
    inside = 0
    fus = []
    for cname in CLASSES:
        try:
            frames = U.load_class(cname)
        except Exception:
            continue
        for k, (cam, ip) in sorted(frames.items()):
            q = cam.center - O
            cu, cd, ch = float(q @ HU), float(q @ HD), float(q[1])
            # the camera has to be inside this gallery, between its face and its back wall
            if (cu - M['eface']) * s < 0.0 and end == 'east':
                continue
            if end == 'east' and not (M['eface'] - 0.5 < cu < uB):
                continue
            if end == 'west' and not (uB < cu < M['wface'] + 0.5):
                continue
            if not (0.0 < cd < M['dSouth']) or not (M['deck'] + 0.3 < ch < M['top']):
                continue
            inside += 1
            f = cam.R.T @ np.array([0, 0, 1.0])
            fus.append(float(f @ HU) * s)
            if float(f @ HU) * s < 0.15:          # it has to be looking AT the back wall
                continue
            im = cv2.imread(ip, cv2.IMREAD_GRAYSCALE)
            if im is None:
                continue
            nf += 1
            pts, idx = [], []
            for i, hv in enumerate(hs):
                for j, dv in enumerate(ds):
                    pts.append(O + uB * HU + dv * HD + np.array([0.0, hv, 0.0]))
                    idx.append((i, j))
            x, y, z = cam.project(np.asarray(pts))
            ok = np.logical_and.reduce([z > 0.3, x > 1, x < cam.w - 2, y > 1, y < cam.h - 2])
            for n in np.nonzero(ok)[0]:
                i, j = idx[n]
                acc[i][j].append(float(im[int(y[n]), int(x[n])]))
    print('')
    print('%s GALLERY BACK WALL on u %.3f: %d frames inside the gallery look at it' % (end.upper(), uB, nf))
    # THE ANSWER IS NOT "TOO FEW FRAMES", IT IS THAT THEY ALL FACE THE OTHER WAY, and saying which is
    # the whole value of the run. A count of zero with no reason attached invites somebody to try again
    # with looser filters; a count of zero WITH the reason closes the route.
    if nf < 8:
        print('   %d posed frames stand INSIDE this gallery and %d of them look at the back wall.'
              % (inside, nf))
        if fus:
            print('   their forward direction along the hall runs %+.2f to %+.2f, where +1 is straight'
                  % (min(fus), max(fus)))
            print('   at the back wall and -1 is straight out over the hall. Every one of them faces out.')
        print('   THIS IS THE REGISTRAR BLIND SPOT AND IT IS STRUCTURAL. The solver matches against a')
        print('   model of the HALL, so a frame aimed at the wall beside the operator has almost nothing')
        print('   in it to match and does not solve. The frames that SHOW this wall are exactly the ones')
        print('   with no pose, and the frames with a pose are exactly the ones looking away from it.')
        print('   So this wall cannot be mapped from the posed set at all, and what the model draws on')
        print('   it was placed from floor frames across the hall rather than from inside the gallery.')
        continue
    cov = np.array([[len(c) for c in row] for row in acc], dtype=float)
    val = np.array([[np.median(c) if len(c) >= 3 else np.nan for c in row] for row in acc])
    good = np.isfinite(val)
    print('   the map is %d by %d cells of %.0f mm, %d of them carry 3 or more readings (%.0f per cent)'
          % (len(hs), len(ds), 1000 * DSTEP, int(good.sum()), 100.0 * good.sum() / good.size))
    print('   d %.2f to %.2f, h %.2f to %.2f' % (ds[0], ds[-1], hs[0], hs[-1]))
    if good.sum() < 200:
        print('   too little coverage to read anything off')
        continue
    lo, hi = np.nanpercentile(val, 3), np.nanpercentile(val, 97)
    img = np.clip((val - lo) / max(hi - lo, 1e-6), 0, 1)
    img = np.where(good, img, 0.5)
    pic = (255 * img).astype(np.uint8)
    pic = cv2.cvtColor(pic, cv2.COLOR_GRAY2BGR)
    pic = cv2.flip(pic, 0)                        # h upward, as a wall elevation reads

    def px(dv, hv):
        return int((dv - ds[0]) / DSTEP), int((hs[-1] - hv) / HSTEP)

    for dv, hv in M['lamps_e'] if end == 'east' else []:
        cv2.circle(pic, px(dv, hv), 6, (0, 200, 255), 2)
    if end == 'east':
        cv2.rectangle(pic, px(M['exit_e'][0] - 0.175, M['exit_e'][1] + 0.1),
                      px(M['exit_e'][0] + 0.175, M['exit_e'][1] - 0.1), (0, 255, 0), 2)
    for hv in np.arange(np.ceil(hs[0]), hs[-1], 1.0):
        cv2.line(pic, px(ds[0], hv), (pic.shape[1] - 1, px(ds[0], hv)[1]), (90, 90, 90), 1)
        cv2.putText(pic, '%.0f' % hv, (3, px(ds[0], hv)[1] - 3), cv2.FONT_HERSHEY_SIMPLEX,
                    0.35, (120, 220, 120), 1)
    for dv in np.arange(np.ceil(ds[0]), ds[-1], 2.0):
        cv2.line(pic, px(dv, hs[0]), (px(dv, hs[0])[0], 0), (90, 90, 90), 1)
        cv2.putText(pic, 'd%.0f' % dv, (px(dv, hs[0])[0] + 2, pic.shape[0] - 5),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.35, (120, 220, 120), 1)
    out = 'backwall-%s.jpg' % end
    big = cv2.resize(pic, None, fx=4, fy=4, interpolation=cv2.INTER_NEAREST)
    cv2.imwrite(out, big, [cv2.IMWRITE_JPEG_QUALITY, 92])
    print('   wrote %s, %d by %d, with the drawn exit sign boxed and the drawn lamps ringed.'
          % (out, big.shape[1], big.shape[0]))
    print('   IF THOSE MARKS DO NOT LAND ON ANYTHING the map is not registered and nothing in it counts.')
