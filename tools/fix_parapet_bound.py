# 2026-09-09: rewrite the parapet-top bound so it compares a height and a cap ON THE SAME FACE.
#
# The old check took the top drawn at one face station and the arrival percentile computed at ANOTHER, and
# called the difference an overshoot. That is not a comparison. The arrival cap is a CURVE in the assumed
# face station and it moves about 0.19 m for every 0.20 m the face moves, so which face you pick decides
# the verdict before any measuring happens. Picked at the drawn face u 4.194 it reads 8.818 and the west
# failed; picked at u 3.794 it reads 9.189 and nothing fails at all.
#
# THE FIT SUPPLIES BOTH NUMBERS AT ONCE, which is what makes the comparison legitimate rather than a
# convenient choice. tools/west_far.py with the shade polarity and a ladder narrowed to h 8.30 to 9.30
# fits a LINE, so it returns the face station and the height together: west (u 3.760, h 9.082) from 3,545
# inliers with a 17 mm median, east (u 48.005, h 9.067) from 3,973 with 11 mm. The east is the control and
# it lands 43 mm under its drawn top. So the check evaluates each end's own cap curve at each end's own
# measured face, and the two ends stay the same experiment: both curves come from the 0.6 m matched
# setback run that the previous version of this bound already used.
import io

OLD_START = "POSE_MISS = 0.091"
OLD_END = "          'tools/gallery_arrival.py')\n"

NEW = '''POSE_MISS = 0.091
# The 5th percentile crossing height against the assumed face station, both ends at the matched 0.6 m
# setback, tools/gallery_arrival.py. These are the curves, not a single number, which is the whole point.
CAP = {
    'west': ((3.394, 9.544), (3.594, 9.370), (3.794, 9.189), (3.994, 9.002), (4.194, 8.818),
             (4.394, 8.632), (4.594, 8.446), (4.794, 8.261), (4.994, 8.073), (5.194, 7.886)),
    'east': ((47.056, 8.541), (47.256, 8.650), (47.456, 8.762), (47.656, 8.872), (47.856, 8.975),
             (48.056, 9.078), (48.256, 9.183), (48.456, 9.289), (48.656, 9.401), (48.856, 9.502)),
}
# where the upstand-top line fit puts each end: face station, height, inliers, median residual
TOPFIT = {'west': (3.760, 9.082, 3545, 0.017), 'east': (48.005, 9.067, 3973, 0.011)}


def cap_at(side, uf):
    xs = [p[0] for p in CAP[side]]
    ys = [p[1] for p in CAP[side]]
    if uf <= xs[0]:
        return ys[0]
    if uf >= xs[-1]:
        return ys[-1]
    for i in range(len(xs) - 1):
        if xs[i] <= uf <= xs[i + 1]:
            t = (uf - xs[i]) / (xs[i + 1] - xs[i])
            return ys[i] + t * (ys[i + 1] - ys[i])
    return ys[-1]


for side, upk, npts in (('east', 'upEast', 1941), ('west', 'upWest', 3371)):
    uf, htop, ninl, med = TOPFIT[side]
    cap = cap_at(side, uf)
    over = htop - cap
    drawn_top = G['deck'] + G[upk]
    check('the %s parapet top clears the light that got over it, on the same face' % side,
          over <= 1.5 * POSE_MISS,
          'the upstand-top line fit puts this end on face u %.3f and height %.3f, from %d inliers with a '
          '%.0f mm median. The %d arrivals that reached a camera on that deck from inside the building '
          'give a 5th percentile of %.3f on that same face, so the top stands %+.3f m into light that '
          'arrived, against a bar of %.3f m. The model draws the top on %.3f, deck %.3f plus an upstand '
          'of %.3f. The old form of this check read the cap on the DRAWN face instead of the measured '
          'one, which is how the west came to fail it by 0.202 m: that cap moves 0.19 m for every 0.20 m '
          'the face moves, so the face choice decided the verdict.'
          % (uf, htop, ninl, 1000 * med, npts, cap, over, 1.5 * POSE_MISS, drawn_top, G['deck'],
             G[upk]),
          'tools/west_far.py + tools/gallery_arrival.py')
check('the two ends agree on how tall the solid upstand is',
      abs((TOPFIT['west'][1] - G['deck']) - (TOPFIT['east'][1] - G['deck'])) <= 0.10,
      'fitted separately from cameras 37 m apart with opposite views, the two ends give upstands of '
      '%.3f and %.3f m above the deck, %.0f mm apart. The model draws %.3f west and %.3f east.'
      % (TOPFIT['west'][1] - G['deck'], TOPFIT['east'][1] - G['deck'],
         1000 * abs(TOPFIT['west'][1] - TOPFIT['east'][1]), G['upWest'], G['upEast']),
      'tools/west_far.py')
for side, upk in (('west', 'upWest'), ('east', 'upEast')):
    check('the %s upstand is drawn on the height that was measured' % side,
          abs((G['deck'] + G[upk]) - TOPFIT[side][1]) <= 0.02,
          'drawn top %.3f against a measured %.3f, %+.3f m out.'
          % (G['deck'] + G[upk], TOPFIT[side][1], (G['deck'] + G[upk]) - TOPFIT[side][1]),
          'tools/west_far.py')
'''

target = 'tools/check_bounds.py'
s = io.open(target, encoding='utf-8').read()
i = s.index(OLD_START)
j = s.index(OLD_END, i) + len(OLD_END)
s = '%s%s%s' % (s[:i], NEW, s[j:])
io.open(target, 'w', encoding='utf-8', newline='\n').write(s)
print('parapet-top bound rewritten to compare on a common face')
