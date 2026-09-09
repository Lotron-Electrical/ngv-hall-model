# 2026-09-10: THE OPENINGS DO NOT MISS AT RANDOM, AND THE ORDER IN THE MISSES SAYS THEY HAVE DEPTH.
#
# WHERE THIS CAME FROM. tools/opening_jambs.py walked the opening-against-pier contrast SIDEWAYS and found
# each opening's centre from the photographs. Ten of the twelve cleared its null. Their misses have a
# median of only 41 mm, but they disagree with each other by 171 mm between quartiles, so the median is a
# claim smaller than its own spread and that file refuses to place anything on it.
#
# BUT THE MISSES ARE ORDERED. The west openings read +0.221 m and the east ones -0.098 m and the sign
# changes in the middle of the hall. Scatter does not do that. That is the signature of DEPTH: an opening
# is not a hole in a sheet, it is a tube 0.9 m long, and a tube seen from one side shows a dark patch
# pulled towards the viewer and narrowed, because the rays aimed at the far jamb hit the side of the
# reveal instead of going through. Every camera in the pool stands in the hall, so an opening at the west
# end is seen from its east and reads east, and an opening at the east end reads west.
#
# SO THE SIZE OF THE ORDER IS THE LENGTH OF THE TUBE. Forward-model it: for a candidate reveal depth D,
# take the frames that actually contributed to each opening, and for each stop on the walk ask whether the
# ray from that camera through the front plane still lies inside the aperture after D metres, in u AND in
# height. That gives a predicted profile, medianed over frames and read at half maximum exactly the way
# the measured one was, so the prediction and the measurement go through the same edge finder.
#
# THE CONTROL COSTS NOTHING AND IS THE WHOLE POINT. D = 0 is a hole in a sheet, and it predicts a shift of
# exactly zero for every opening, for any camera anywhere. That is a control with an independently known
# answer rather than a stability test, and it is what the run turns on.
#
# WHAT CAME OUT, WRITTEN HERE BECAUSE THE FIRST TITLE OF THIS FILE PROMISED MORE THAN IT DELIVERS. Zero
# depth is refuted outright: 0 of 2000 resamples of the openings land on it. So these apertures have depth
# and the ordered misses are not evidence that the openings are misplaced. But the DEPTH ITSELF IS NOT
# MEASURED. The shift fit lands on 0.20 m against a drawn 0.900, and the same model there predicts the
# aperture should read 0.960 m wide when the walk read 1.185: the measurement shows the shift WITHOUT the
# narrowing that a tube must also produce. Asymmetric lighting on the two reveal faces would pull the dark
# patch sideways without closing it down, and this run cannot separate that from geometry. So the number
# is a lower bound on the built depth, openDepth stays where it is, and what this run actually buys is a
# tighter placement bound: 85 mm rms once the parallax is taken out, against 162 mm raw.
#
# WHAT IT CANNOT DO. It assumes the reveal sides read as wall rather than as hole, it uses the drawn sill
# and head to decide the vertical clipping, and it inherits every camera pose. It measures the depth of
# the aperture as it reads from the hall, so a splay reads as less depth than is built.
#   python tools/jamb_parallax.py
import io
import json
import re
import sys

import numpy as np

sys.path.insert(0, 'tools')
import underside_geom as U

O = np.array([-54.907447, -1.43545, 3.040286])
HU = np.array([0.975681, 0, 0.219196])
HD = np.array([0.219196, 0, -0.975681])
CLASSES = ('walk', 'night', 'day4k')
DEPTHS = np.arange(0.0, 2.001, 0.05)

src = io.open('index.html', encoding='utf-8').read()
mo = re.search(r'const WALLF=\{openings:\[(.*?)\],\s*\n', src, re.S)
OPEN = [[float(a), float(b)] for a, b in re.findall(r'\[([0-9.]+),([0-9.]+)\]', mo.group(1))]
DN = float(re.search(r'dNorth:(-?[0-9.]+)', src).group(1))
SILL = float(re.search(r'openY:\[([0-9.]+),', src).group(1))
HEAD = float(re.search(r'openY:\[[0-9.]+,([0-9.]+)\]', src).group(1))
DRAWN = float(re.search(r'openDepth:\s*([0-9.]+)', src).group(1))

P = json.loads(io.open('jamb-profile.json', encoding='utf-8').read())
USTEP, REACH = P['ustep'], P['reach']
MEAS = {r['opening']: r for r in P['rows'] if r['over_null']}
LO, HI = SILL + 0.35, HEAD - 0.35
LEV = np.linspace(LO, HI, 9)
print('index.html draws the reveal %.3f m deep, the sill on %.3f and the head on %.3f'
      % (DRAWN, SILL, HEAD))
print('%d openings cleared the null in the sideways walk and carry a measured centre' % len(MEAS))


def walk(c, hw):
    return np.arange(c - hw - REACH, c + hw + REACH + 1e-9, USTEP)


# THE SAME FRAMES, CHOSEN THE SAME WAY. A prediction built on a different set of cameras than the
# measurement would be a different experiment, so the acceptance test here is the one opening_jambs.py
# used, minus the pixels: a stop counts when at least 12 of its 18 sample points land in the picture,
# and a frame counts for an opening when at least 80 per cent of its stops do.
pool = {oi: [] for oi in MEAS}
nf = 0
for cname in CLASSES:
    try:
        frames = U.load_class(cname)
    except Exception:
        continue
    for k, (cam, ip) in sorted(frames.items()):
        q = cam.center - O
        cu, cd, ch = float(q @ HU), float(q @ HD), float(q[1])
        if ch > 3.0 or cd < 3.0:
            continue
        nf += 1
        for oi in MEAS:
            u0, u1 = OPEN[oi - 1]
            us = walk(0.5 * (u0 + u1), 0.5 * (u1 - u0))
            hit = 0
            for uc in us:
                uu = np.array([uc - USTEP / 2, uc + USTEP / 2])
                pts = np.array([O + u * HU + DN * HD + np.array([0.0, lv, 0.0])
                                for u in uu for lv in LEV])
                x, y, z = cam.project(pts)
                ok = np.logical_and.reduce([z > 0.5, x > 1, x < cam.w - 2, y > 1, y < cam.h - 2])
                if ok.sum() >= 12:
                    hit += 1
            if hit >= 0.8 * len(us):
                pool[oi].append((cu, cd, ch))
print('%d frames stand in the hall; the openings drew %d to %d of them each'
      % (nf, min(len(v) for v in pool.values()), max(len(v) for v in pool.values())))
thin = [oi for oi in MEAS if len(pool[oi]) < 20]
if thin:
    print('   openings %s drew fewer than 20 frames and are dropped'
          % ', '.join(str(v) for v in thin))
    for oi in thin:
        MEAS.pop(oi)
if len(MEAS) < 5:
    sys.exit('   too few openings carry both a measurement and a camera pool. Nothing can be judged.')


def predict(oi, D):
    """the profile this depth would produce, read by the same edge finder as the measurement"""
    u0, u1 = OPEN[oi - 1]
    us = walk(0.5 * (u0 + u1), 0.5 * (u1 - u0))
    frac = np.zeros((len(pool[oi]), len(us)))
    for n, (cu, cd, ch) in enumerate(pool[oi]):
        kk = D / (cd - DN)
        ue = us[:, None] + kk * (us[:, None] - cu)
        he = LEV[None, :] + kk * (LEV[None, :] - ch)
        inu = np.logical_and(ue >= u0, ue <= u1)
        inh = np.logical_and(he >= SILL, he <= HEAD)
        face = np.logical_and(us[:, None] >= u0, us[:, None] <= u1)
        frac[n] = np.logical_and(np.logical_and(inu, inh), face).mean(axis=1)
    m = 1.0 - np.median(frac, axis=0)               # bright where the wall is, dark through the tube
    i = int(np.argmin(m))
    base = float(np.percentile(m, 85))
    half = base - 0.5 * (base - float(m[i]))
    left = [us[j] for j in range(len(us)) if us[j] < us[i] and m[j] > half]
    right = [us[j] for j in range(len(us)) if us[j] > us[i] and m[j] > half]
    if not left or not right:
        return None
    a, b = max(left), min(right)
    return 0.5 * (a + b) - 0.5 * (u0 + u1), b - a


meas = {oi: MEAS[oi]['found'] - MEAS[oi]['drawn'] for oi in MEAS}
print('')
print('   depth    predicted shifts, west to east                                   rms against measured')
best, curve = None, []
for D in DEPTHS:
    pr = {oi: predict(oi, D) for oi in sorted(MEAS)}
    if any(v is None for v in pr.values()):
        continue
    res = np.array([pr[oi][0] - meas[oi] for oi in sorted(MEAS)])
    rms = float(np.sqrt(np.mean(res ** 2)))
    curve.append((D, rms, dict(pr)))
    if best is None or rms < best[1]:
        best = (D, rms, pr)
    if abs(D % 0.25) < 1e-6:
        print('   %.2f     %s   %.4f'
              % (D, ' '.join('%+.2f' % pr[oi][0] for oi in sorted(MEAS)), rms))
if not curve:
    sys.exit('   no depth produced a readable profile. Nothing can be judged.')
zero = [c for c in curve if abs(c[0]) < 1e-9][0]
D, rms, pr = best
print('')
print('   MEASURED   %s' % ' '.join('%+.2f' % meas[oi] for oi in sorted(MEAS)))
print('   BEST FIT   %s   at a depth of %.2f m'
      % (' '.join('%+.2f' % pr[oi][0] for oi in sorted(MEAS)), D))
print('')
print('   a hole in a SHEET, depth 0, predicts no shift at all and scores %.4f' % zero[1])
print('   the best depth is %.2f m and scores %.4f' % (D, rms))

# A BOOTSTRAP OVER THE OPENINGS, because ten numbers fitted by one parameter will always find a minimum
# and the question is whether that minimum would survive a different ten openings.
rng = np.random.default_rng(7)
keys = sorted(MEAS)
boot = []
for _ in range(2000):
    pick = rng.choice(len(keys), len(keys))
    sc = [(c[0], float(np.mean([(c[2][keys[i]][0] - meas[keys[i]]) ** 2 for i in pick])))
          for c in curve]
    boot.append(min(sc, key=lambda t: t[1])[0])
b = np.array(boot)
q1, q3 = float(np.percentile(b, 25)), float(np.percentile(b, 75))
print('   resampling the openings 2000 times puts it on %.2f m, quartiles %.2f to %.2f'
      % (float(np.median(b)), q1, q3))
frac0 = float(np.mean(b < 0.025))
print('   and %.0f per cent of those resamples land on zero depth.' % (100 * frac0))

print('')
gain = zero[1] - rms
wm = float(np.median([pr[oi][1] for oi in sorted(MEAS)]))
wq = float(np.median([MEAS[oi]['width'] for oi in sorted(MEAS)]))
drawnw = OPEN[0][1] - OPEN[0][0]
print('   the same fit predicts a read WIDTH of %.3f m. The walk actually read %.3f, on a drawn %.3f.'
      % (wm, wq, drawnw))

if frac0 > 0.2 or gain < 0.2 * zero[1]:
    print('   A SHEET EXPLAINS THE MISSES AS WELL AS A TUBE DOES, so nothing here is about depth and')
    print('   nothing moves.')
    sys.exit(0)

# WHAT IS ESTABLISHED AND WHAT IS NOT, AND THEY ARE NOT THE SAME THING.
print('')
print('   ZERO DEPTH IS REFUTED AND THAT IS THE SOLID PART. A hole in a sheet predicts no shift at all,')
print('   for any camera anywhere, and the misses are ordered along the hall with the sign changing in')
print('   the middle. %.0f per cent of 2000 resamples of the openings land on zero. So these apertures'
      % (100 * frac0))
print('   have DEPTH, which nothing in this project had shown before, and the ordered misses are')
print('   therefore NOT evidence that the openings are misplaced.')

# THE DEPTH ITSELF IS NOT MEASURED, AND THE FILE'S OWN WIDTH IS WHAT SAYS SO.
print('')
print('   THE DEPTH ITSELF IS NOT MEASURED, AND THIS RUN CONTAINS ITS OWN REASON. The shift fit lands')
print('   on %.2f m, quartiles %.2f to %.2f, against the %.3f this file draws. But the SAME model at'
      % (D, q1, q3, DRAWN))
print('   that depth predicts the aperture should read %.3f m wide and the walk read %.3f, which is'
      % (wm, wq))
print('   %.0f mm of disagreement in the one number the model also predicts. A tube narrows what you'
      % (1000 * abs(wq - wm)))
print('   see as well as shifting it, and the measurement shows the shift without the narrowing.')
print('   THERE IS A COMPETING EXPLANATION THAT DOES EXACTLY THAT. The two reveal faces are not lit the')
print('   same: one is turned towards the hall and one away, so the darker face pulls the centre of the')
print('   dark patch sideways WITHOUT closing it down. Shading of that kind produces the ordering with')
print('   little or no narrowing, and this run cannot separate it from geometry. So %.2f m is what the'
      % D)
print('   shift would need if occlusion were the whole story, and it is a LOWER bound on the built')
print('   depth rather than a value: a splayed or shaded reveal reads shallower than it is built.')
print('   openDepth stays at %.3f. Nothing moves on it.' % DRAWN)

# AND THE PLACEMENT BOUND TIGHTENS, WHICH IS THE PART THAT FEEDS BACK INTO THE WALL.
res0 = float(np.sqrt(np.mean([meas[oi] ** 2 for oi in sorted(MEAS)])))
print('')
print('   THE PLACEMENT BOUND TIGHTENS BECAUSE OF IT. Taken raw the openings scatter %.3f m rms from'
      % res0)
print('   where this file draws them. Take out the parallax that depth alone forces and the residual')
print('   falls to %.3f m rms. That is the bound on how far any one of these openings can be out, and'
      % rms)
print('   it is %.0f mm rather than the %.0f mm the sideways walk could claim on its own.'
      % (1000 * rms, 1000 * res0))
