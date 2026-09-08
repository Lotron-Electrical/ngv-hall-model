# 2026-09-09: does the instrument follow the model, or measure the wall?
# The audit's finding, on the unfixed code: the same 25 frames measuring the SAME east parapet returned
# h 9.057 when the model drew it 8.90 and h 9.093 when the model drew it 9.02. A 0.120 m move in the model
# came back as a 0.036 m move in the "measurement", so 30 percent of every apparent confirmation was the
# model confirming itself. This runs both cases and prints the absolute height each one lands on. If the
# two agree to a few millimetres the instrument is measuring the wall.
#   python tools/follow_test.py <class> <west|east> <level name> <drawn A> <drawn B> [frames]
import sys, os, subprocess, json, tempfile
cls, end, name, a, b = sys.argv[1], sys.argv[2], sys.argv[3], float(sys.argv[4]), float(sys.argv[5])
n = sys.argv[6] if len(sys.argv) > 6 else '25'
out = []
for v in (a, b):
    jf = os.path.join(tempfile.gettempdir(), 'follow-%s.json' % v)
    env = dict(os.environ, LEVELS_SET='%s=%s' % (name, v), LEVEL_JSON=jf)
    subprocess.run([sys.executable, '-u', 'tools/end_levels.py', cls, end, n],
                   env=env, capture_output=True, text=True)
    if not os.path.exists(jf): print('  drawn %.3f: no result' % v); out.append(None); continue
    j = json.load(open(jf))
    rec = j['levels'].get(name)
    if not rec: print('  drawn %.3f: %s not resolved' % (v, name)); out.append(None); continue
    print('  drawn %6.3f  offset %+0.3f (n %d)  ->  absolute h %.3f' % (v, rec['median'], rec['n'], v + rec['median']))
    out.append(v + rec['median'])
if out[0] is not None and out[1] is not None:
    d = abs(out[0] - out[1]); gain = d / abs(a - b) if a != b else 0
    print('  the two disagree by %.0f mm; follow gain %.2f (0.00 is an instrument, 1.00 is an echo)' % (d * 1000, gain))
