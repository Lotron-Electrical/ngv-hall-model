# 2026-09-09: re-run both north wall edges with the constants pointed at the measured wall.
#
# tools/wall_lines.py had been carrying a sill of 8.99, a head of 11.35 and a face on -0.090 while the
# model moved to 8.740, 11.165 and -0.030. Its outputs are the rays that measured the wall's depth, the
# opening head lean and the opening height, so those numbers were derived through slightly wrong sampling
# even though the ladder was wide enough that nothing was clipped. Asserting that is not the same as
# checking it. This re-runs both edges so the same questions can be put to the corrected rays.
import os
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
for edge in ('sill', 'head'):
    print('')
    print('=' * 96)
    print('%s, ladder centred on the MEASURED value and walked on the MEASURED plane' % edge.upper())
    print('=' * 96)
    sys.stdout.flush()
    r = subprocess.run([sys.executable, '-u', os.path.join(HERE, 'wall_lines.py')],
                       env=dict(os.environ, EDGE=edge), capture_output=True, text=True)
    sys.stdout.write(r.stdout)
    if r.returncode != 0:
        sys.stdout.write(r.stderr[-1200:])
    sys.stdout.flush()
