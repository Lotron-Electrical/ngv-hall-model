# 2026-09-10: THE GLASS SEEN THROUGH, FROM THE OPPOSITE DECK.
#
# WHAT WAS SEEN BY EYE FIRST. In b5_000072, shot from north opening 6 looking at the west gallery 20 m
# off, the lit back wall of that gallery stops reading lit on exactly the drawn glass top, 9.799: above
# the line the wall is seen in the open, below it through glass, and the people standing in the west top
# door are clear above the line and dimmed below it. The provenance had railTops down as "not measurable
# from this archive" because no camera on a deck can see its own glass top and glass blocks no sightline.
# But a camera on the OTHER deck, or in an opening across the hall, looks THROUGH the glass at a lit wall,
# and glass that is looked through is not invisible: it takes a fraction of the light. That is a tone step
# on the back wall at the height of the glass top, and it needs no edge of the glass itself.
#
# THE INSTRUMENT. Sample every posed frame that looks at an end gallery from across the hall along vertical
# sweeps ON that gallery's back wall plane, across the wall but clear of its doors and signs, stack the
# profiles with each frame normalised to its own mean, and take the gradient. The glass top is a step
# down, bright above and dimmed below.
#
# THE DECISION RULE, FIXED BEFORE THE NUMBERS ARE OPENED.
#   1. THE WEST IS THE POSITIVE CONTROL. Its step was seen by eye, so the instrument must find it: the
#      strongest gradient in the window 9.30 to 10.40 must lie within 0.15 m of the drawn 9.799 and must
#      beat the strongest gradient on the plain stone above, 10.40 to 11.00, by a factor of 1.5. If the
#      control fails, the instrument is dead and NOTHING is said about the east.
#   2. With the control alive, the east is read the same way: the strongest gradient in the same window,
#      against the same plain-stone band, the same factor.
#   3. An east step that passes is the east glass top, claimed to no better than 0.10 m, and only moved
#      into the file if it differs from the drawn 9.865 by more than the spread of the per-frame readings.
#   4. An east window that does not beat its plain band says the east front does not read as glass from
#      across the hall, and that is recorded as such: not "no glass", but "no step where one is drawn".
#
# WHAT IT CANNOT DO. People stand on both decks and enter the stack as noise; the east is read from four
# frames on the west deck 48 m off, the west from thirteen in opening 6, 20 m off, so the east reading is
# the coarser one by a factor of two in every direction.
#
# THE RESULT (2026-09-10, first run): THE CONTROL FAILED ON STRENGTH AND PASSED ON POSITION, AND THE RULE
# DOES NOT LET THE SECOND HALF OF THAT SENTENCE COUNT. West, 56 frames: the strongest step in the window
# lands on h 9.820, 21 mm from the drawn 9.799, which is where the eye put it. But it is 0.574 against
# 0.564 on the band declared plain, a ratio of 1.02 where the rule asked 1.5. The band 10.40 to 11.00 is
# not plain stone from these viewpoints: the lit back wall ends under the beam and the face wall begins,
# and that edge is as strong as the glass. So the control fails by its own wording, the instrument is
# dead for this run, and NOTHING is said about the east, whose window peaked on 10.400 with 0.2 times
# its plain band and whose per-frame median sat on 9.730. The position agreement is a hint for the next
# version, which must declare a different null before it runs, not a result of this one.
#   python tools/glass_step.py
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
HSTEP = 0.02
HS = np.arange(8.90, 11.30 + 1e-9, HSTEP)
WIN = (9.30, 10.40)
PLAIN = (10.40, 11.00)
FACTOR = 1.5
NEAR = 0.15
DS = np.linspace(1.0, 12.0, 23)
MARGIN = 30

src = io.open('index.html', encoding='utf-8').read()
_i = src.index('const ENDW={')
BLOCK = src[_i:src.index('\n', _i)]


def endw(k):
    return float(re.search(r'\b' + k + r':\s*(-?[0-9.]+)', BLOCK).group(1))


def endw_side(k, side):
    return float(re.search(r'\b' + k + r':\{[^}]*\b' + side + r':\s*(-?[0-9.]+)', BLOCK).group(1))


DECK = float(re.search(r'floors:\[[0-9.]+,\s*([0-9.]+)\]', BLOCK).group(1))
ENDS = {
    'west': dict(back=endw('west') + 0.02, face=endw('west') + endw('face'), s=+1,
                 glass=DECK + endw_side('railTops', 'west'), classes=('b5', 'b1', 'b4'), look=-1),
    'east': dict(back=endw('east') - 0.02, face=endw('east') - endw('face'), s=-1,
                 glass=DECK + endw_side('railTops', 'east'), classes=('b7s', 'b3', 'b1', 'b5', 'b4'), look=+1),
}


def profile(cam, img, uplane):
    got = np.zeros(len(HS))
    cnt = np.zeros(len(HS))
    for d in DS:
        pts = np.array([O + uplane * HU + d * HD + np.array([0.0, h, 0.0]) for h in HS])
        x, y, z = cam.project(pts)
        ok = z > 1.0
        ok = np.logical_and(ok, x > MARGIN)
        ok = np.logical_and(ok, x < cam.w - MARGIN)
        ok = np.logical_and(ok, y > MARGIN)
        ok = np.logical_and(ok, y < cam.h - MARGIN)
        if ok.sum() < 0.9 * len(HS):
            continue
        xi = np.clip(x.astype(int), 0, img.shape[1] - 1)
        yi = np.clip(y.astype(int), 0, img.shape[0] - 1)
        v = img[yi, xi].astype(np.float64)
        got[ok] += v[ok]
        cnt[ok] += 1
    if (cnt > 0).sum() < 0.9 * len(HS) or cnt.max() < 8:
        return None
    out = np.full(len(HS), np.nan)
    nz = cnt > 0
    out[nz] = got[nz] / cnt[nz]
    if np.isnan(out).any():
        return None
    return out - out.mean()


def grad(prof):
    g = np.gradient(prof)
    return np.convolve(g, np.ones(3) / 3.0, mode='same')


def step(g, lo, hi):
    """the strongest DOWNWARD step (bright above, dim below) inside [lo, hi]: gradient most negative."""
    win = np.logical_and(HS >= lo, HS <= hi)
    i = int(np.argmin(np.where(win, g, 1e9)))
    return float(HS[i]), float(-g[i])


def read(name):
    e = ENDS[name]
    rows, per, used = [], [], {}
    for cn in e['classes']:
        try:
            fr = U.load_class(cn)
        except Exception:
            continue
        for k, (cam, ip) in sorted(fr.items()):
            q = cam.center - O
            cu, ch = float(q @ HU), float(q[1])
            f = cam.R.T @ np.array([0.0, 0.0, 1.0])
            if e['look'] * float(f @ HU) < 0.5:
                continue                                   # must look toward that end
            if abs(cu - e['face']) < 8.0 or ch < DECK + 0.5:
                continue                                   # from across the hall, and up near deck level
            img = cv2.imread(ip, cv2.IMREAD_GRAYSCALE)
            if img is None:
                continue
            p = profile(cam, img, e['back'])
            if p is None:
                continue
            rows.append(p)
            used[cn] = used.get(cn, 0) + 1
            hs, gs = step(grad(p), *WIN)
            per.append(hs)
    if len(rows) < 3:
        print('   %-5s only %d frames see this back wall from across the hall. Nothing is read.'
              % (name, len(rows)))
        return None
    prof = np.mean(np.asarray(rows), axis=0)
    g = grad(prof)
    hs, gs = step(g, *WIN)
    _, gp = step(g, *PLAIN)
    per = np.array(per)
    print('   %-5s %d frames (%s): strongest step in %.2f to %.2f on h %.3f, strength %.3f; plain stone '
          '%.2f to %.2f gives %.3f' % (name, len(rows), ', '.join('%s %d' % t for t in sorted(used.items())),
                                       WIN[0], WIN[1], hs, gs, PLAIN[0], PLAIN[1], gp))
    print('         per-frame step positions: median %.3f, 10th to 90th %.3f to %.3f; drawn glass top %.3f'
          % (float(np.median(per)), float(np.percentile(per, 10)), float(np.percentile(per, 90)), e['glass']))
    return dict(name=name, n=len(rows), h=hs, g=gs, plain=gp, per=per, glass=e['glass'],
                alive=gs > FACTOR * gp)


def main():
    print('THE DECISION RULE, WRITTEN OUT BEFORE THE NUMBERS ARE OPENED.')
    print('   Glass looked through takes light, so the lit back wall of a gallery seen from across the hall')
    print('   carries a step down on the glass top. Each frame is sampled on the back wall plane every')
    print('   %.0f mm, clear of doors, and stacked. THE WEST IS THE POSITIVE CONTROL: its step, seen by eye,'
          % (1000 * HSTEP))
    print('   must be the strongest downward gradient in %.2f to %.2f, within %.2f m of the drawn %.3f, and'
          % (WIN[0], WIN[1], NEAR, ENDS['west']['glass']))
    print('   beat the plain stone above (%.2f to %.2f) by %.1f times, or the instrument is dead and the'
          % (PLAIN[0], PLAIN[1], FACTOR))
    print('   east is not read. The east is read the same way, claimed to 0.10 m, and moved only if it')
    print('   differs from the drawn %.3f by more than the spread of its own frames.' % ENDS['east']['glass'])
    print('')
    west = read('west')
    east = read('east')
    print('')
    if west is None or not west['alive'] or abs(west['h'] - west['glass']) > NEAR:
        print('   THE CONTROL FAILS: the west step is not found where the eye saw it, so the instrument is')
        print('   dead and NOTHING is said about the east.')
        return
    print('   THE CONTROL PASSES: west step on %.3f against %.3f drawn, %.1f times the plain stone.'
          % (west['h'], west['glass'], west['g'] / max(west['plain'], 1e-9)))
    if east is None:
        return
    if not east['alive']:
        print('   THE EAST DOES NOT READ AS GLASS from across the hall: its window peaks on %.3f at %.1f times'
              % (east['h'], east['g'] / max(east['plain'], 1e-9)))
        print('   the plain stone, under the %.1f the rule asks. No step where one is drawn on %.3f. That is'
              % (FACTOR, east['glass']))
        print('   recorded as such and the file is not changed by it.')
        return
    spread = float(np.percentile(east['per'], 90) - np.percentile(east['per'], 10))
    print('   THE EAST READS: step on %.3f, %.1f times the plain stone, per-frame spread %.3f, drawn %.3f.'
          % (east['h'], east['g'] / max(east['plain'], 1e-9), spread, east['glass']))
    if abs(east['h'] - east['glass']) > max(spread, 0.10):
        print('   Outside its own spread from the drawn line: railTops east should carry %.3f above the deck.'
              % (east['h'] - DECK))
    else:
        print('   Inside its own spread of the drawn line: the east glass top is CONFIRMED where it is drawn,')
        print('   the first photograph to speak for it.')


if __name__ == '__main__':
    main()
