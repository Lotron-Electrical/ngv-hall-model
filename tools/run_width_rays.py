# 2026-09-09: regenerate both ends' parapet ladders with the hall station saved, so the width can be asked.
import os
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
RUNS = (('-upW', 'shade', '8.30', '9.30', 'the solid upstand top'),
        ('-railW', 'lit', '9.30', '10.30', 'the rail top'))
PLANE = {'west': '3.710', 'east': '48.056'}
for end in ('west', 'east'):
    for tag, pol, hlo, hhi, what in RUNS:
        plane = PLANE[end] if tag == '-upW' else ('4.194' if end == 'west' else '48.056')
        print('')
        print('=' * 96)
        print('%s %s, ladder on u %s' % (end.upper(), what, plane))
        print('=' * 96)
        sys.stdout.flush()
        env = dict(os.environ, END=end, TAG=tag, POLARITY=pol, HLO=hlo, HHI=hhi, UPLANE=plane)
        r = subprocess.run([sys.executable, '-u', os.path.join(HERE, 'west_far.py')],
                           env=env, capture_output=True, text=True)
        sys.stdout.write(r.stdout[-900:])
        if r.returncode != 0:
            sys.stdout.write(r.stderr[-800:])
        sys.stdout.flush()
