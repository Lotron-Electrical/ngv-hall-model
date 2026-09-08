# 2026-09-09: does the jamb instrument measure the wall, or repeat the table?
# The audit's finding on the unfixed code: drawn width 1.256 measured 1.219, drawn 1.213 measured 1.189.
# The table moved 0.043 and the answer moved 0.030, a follow gain of 0.70, which means most of today's
# opening correction could have been the model agreeing with itself. This runs the same frames against two
# drawn widths and prints the ABSOLUTE width each one lands on. If they agree, the instrument is measuring.
#   python tools/wall_follow.py <class> <width A> <width B> [frames]
import sys, os, json, subprocess, tempfile
import numpy as np
cls, a, b = sys.argv[1], float(sys.argv[2]), float(sys.argv[3])
n = sys.argv[4] if len(sys.argv) > 4 else '25'
out = []
for w in (a, b):
    jf = os.path.join(tempfile.gettempdir(), 'wallfollow-%s-%s.json' % (cls, w))
    subprocess.run([sys.executable, '-u', 'tools/wall_edges.py', cls, n],
                   env=dict(os.environ, OPEN_WIDTH=str(w), WALL_JSON=jf), capture_output=True, text=True)
    if not os.path.exists(jf): print('  drawn %.3f: no result' % w); out.append(None); continue
    j = json.load(open(jf))['jambs']
    widths = []
    for k, v in j.items():
        if 'west jamb' not in k: continue
        ek = k.replace('west jamb', 'east jamb')
        if ek not in j: continue
        widths.append(w + j[ek]['median'] - v['median'])
    if not widths: print('  drawn %.3f: no opening had both jambs' % w); out.append(None); continue
    print('  drawn %6.3f  ->  measured width %.3f over %d openings (spread %.3f)'
          % (w, float(np.median(widths)), len(widths), float(max(widths) - min(widths))))
    out.append(float(np.median(widths)))
if out[0] is not None and out[1] is not None:
    d = abs(out[0] - out[1]); gain = d / abs(a - b) if a != b else 0
    print('  the two disagree by %.0f mm; follow gain %.2f (0.00 is an instrument, 1.00 is an echo)' % (d * 1000, gain))
