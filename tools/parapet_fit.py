# 2026-09-09: WHICH HEIGHT IS THE EAST PARAPET, decided without assuming the instrument is unbiased.
# The east upstand (ENDW.upstands.east 0.77, parapet top 9.11) rests on four captures reading about +0.09 m
# above a drawn 9.02. Two later findings undercut that basis: the comparison that challenged it was built
# on unrefined poses and is void, and the strict readings are dominated by one 1.07-second look, which
# grouped per independent look reads +0.004 rather than +0.107. So the number has never been settled.
# The obstacle is the follow bias: an edge finder started from the drawn line partly echoes it, so a
# reading taken against one drawn value cannot be compared with a reading taken against another. The
# measured gain for this very edge was 0.45, which means a single-draw reading is not a measurement.
# THE WAY OUT IS TO STOP ASSUMING THE GAIN AND FIT IT. A following instrument returns
#     A(d) = truth + g * (d - truth) = (1-g)*truth + g*d
# for a drawn height d, so A is LINEAR in d with slope g. Read the same edge in the same frames at three
# draws, fit the line, and both unknowns fall out:
#     g     = slope
#     truth = intercept / (1 - g)
# Three draws rather than two for two reasons. The residual about the line is a check on the model itself,
# because nothing forces a real instrument to be linear. And the spacing is what conditions the answer: the
# slope divides by the draw separation, so with two draws 0.09 m apart a 0.02 m read error becomes 0.22 of
# gain, and it was exactly that which returned an impossible 1.58 for b1. The draws are now 0.38 m apart,
# as wide as the 0.25 m search window allows while still bracketing the candidate heights in every window
# and still clearing the deck line 0.55 m below.
# A GAIN OUTSIDE ITS PHYSICAL RANGE IS A REFUSAL, NOT A DISAGREEMENT. A following instrument cannot move
# further than the drawing moved (g > 1) or against it (g < 0); a capture that reports one is noise-
# dominated and states nothing about the height, so it is dropped BEFORE its height is looked at rather
# than after. Near g = 1 the capture is only reading the drawing back and truth is not recoverable at all.
# BOTH ENDS, ONE INSTRUMENT, ONE DRAW SET. The west parapet was called settled within 21 mm by the old
# per-frame pooling and has never been through this test, so it is measured here the same way rather than
# taken on trust. The draw set has to work for both candidate heights at both ends: every draw must sit
# within the 0.25 m search window of whatever the truth turns out to be, or that draw's window does not
# contain the real edge and its reading is of something else; and the lowest draw must clear the deck line
# 8.34 by more than 2.2 window widths or the tool refuses it as inseparable. That leaves 8.92 to 9.20,
# which is a 0.28 m separation, three times the first attempt's and as wide as this geometry allows.
# Run tools/parapet_fit.sh first; this reads what it wrote.
import json, os
import numpy as np
D = 'E:/sitecapture-captures/ngv-site/agent-ref-walls/leveljson'
DRAWS = [('a', 8.92), ('b', 9.06), ('c', 9.20)]
END = os.environ.get('END', 'east')
# THE PAN CLASSES ARE IN THIS LIST FOR ONE REASON: RANGE. Every capture above reads the parapet from the
# hall floor, 28 to 40 m away, where the 0.09 m in dispute is a handful of pixels and, worse, where the
# instrument mostly reads the drawing back (fitted gain 0.66 to 0.70). b3p stands ON the east gallery, a
# couple of metres from the parapet it is measuring. Its poses are worse in absolute terms, 0.100 m of
# position error against the accepted frames' centimetres, but that error is spent on a target ten times
# closer, so what reaches the measurement is ten times smaller. This is the first time any capture has
# looked at this edge from beside it rather than from across the room.
CAPS = ['walk', 'night', 'day4k', 'b1', 'b3', 'b6g', 'b7s', 'b1p', 'b3p', 'b5p', 'b7sp', 'b6gp']
KEY = 'top parapet top'
DECK = 8.34

def read(tag, cap):
    p = os.path.join(D, 'fit-%s-%s-%s.json' % (tag, cap, END))
    if not os.path.exists(p): return None
    try: j = json.load(open(p))
    except Exception: return None
    return j.get('levels', {}).get(KEY)

print('%s end' % END)
print('%-7s %6s %7s %7s %7s %6s %7s %7s %8s' % ('capture', 'looks', 'A(low)', 'A(mid)', 'A(high)', 'gain', 'resid', 'truth', 'upstand'))
rows = []
for cap in CAPS:
    r = [read(t, cap) for t, _ in DRAWS]
    if any(x is None for x in r):
        print('%-7s   did not report this level at every draw' % cap); continue
    d = np.array([v for _, v in DRAWS]); a = np.array([d[i] + r[i]['median'] for i in range(len(r))])
    looks = min(x['looks'] for x in r)
    g, c = np.polyfit(d, a, 1)
    resid = float(np.abs(a - (g * d + c)).max())
    note = ''
    if not (0.0 <= g <= 0.85): note = 'gain outside its physical range, noise not signal'
    elif resid > 0.05: note = 'not linear in the drawing, the model does not hold here'
    if note:
        print('%-7s %6d %7.3f %7.3f %7.3f %6.2f %7.3f   %s' % (cap, looks, a[0], a[1], a[2], g, resid, note)); continue
    truth = float(c / (1.0 - g))
    print('%-7s %6d %7.3f %7.3f %7.3f %6.2f %7.3f %7.3f %8.3f' % (cap, looks, a[0], a[1], a[2], g, resid, truth, truth - DECK))
    rows.append((cap, g, truth))

print('')
if len(rows) >= 3:
    t = np.array([x[2] for x in rows]); gg = np.array([x[1] for x in rows])
    print('%d captures survive, follow gain median %.2f (range %.2f)' % (len(rows), np.median(gg), gg.max() - gg.min()))
    print('parapet top: median %.3f, range %.3f, captures %s' % (np.median(t), t.max() - t.min(), ' '.join('%.3f' % x for x in sorted(t))))
    print('implied east upstand %.3f above the deck %.2f' % (np.median(t) - DECK, DECK))
    print('VERDICT: %s' % ('the captures agree, this is measured' if t.max() - t.min() <= 0.10 else 'the captures disagree by more than 0.10 m, NOT measured'))
else:
    print('%d captures survive, fewer than three, nothing can be pooled' % len(rows))
