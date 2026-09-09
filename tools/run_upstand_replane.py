# 2026-09-09: re-sample both solid upstands on the planes they are now believed to stand on.
#
# The west solid moved 0.484 m behind its face this evening. The rays that measured it were produced by a
# tool that walks its height ladder on the FACE plane, so the measurement was made by sampling one plane
# and solving for another. That is not wrong in itself, and it is not the corridor's fault either: the
# corridor's aperture was a hard mask, while this is a sampling surface and the feature was never clipped.
# But the west offset is 0.484 m, the largest anywhere in this model, and the only way to know it does not
# matter is to move the ladder onto the answer and see whether the answer moves with it.
#
# THE EAST IS THE CONTROL AND ITS OFFSET IS ZERO, so its re-run should reproduce itself exactly. If the
# east shifts too then the difference is the re-run and not the plane.
import os
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
RUNS = (('west', '3.710', '9.097'), ('east', '48.056', '9.095'))
for end, plane, topd in RUNS:
    print('')
    print('=' * 96)
    print('%s solid upstand, ladder walked on u %s instead of the drawn face' % (end.upper(), plane))
    print('=' * 96)
    sys.stdout.flush()
    env = dict(os.environ, END=end, TAG='-upR', POLARITY='shade', HLO='8.30', HHI='9.30',
               UPLANE=plane, TOPD=topd)
    r = subprocess.run([sys.executable, '-u', os.path.join(HERE, 'west_far.py')],
                       env=env, capture_output=True, text=True)
    sys.stdout.write(r.stdout)
    if r.returncode != 0:
        sys.stdout.write(r.stderr[-1200:])
    sys.stdout.flush()
