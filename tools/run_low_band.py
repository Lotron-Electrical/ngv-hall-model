# 2026-09-09: the LOWER gallery tier has never been fitted, at either end, by anything.
#
# Everything measured on these balconies today has been the top tier: its solid upstand top, its rail top,
# its fascia, its face station. The lower tier is drawn entirely from other people's numbers, floor 6.33
# from endwalls.json, a 0.52 upstand from one 2009 Commons photograph of bar stools behind glass, and a
# 0.89 rail from the same source. Not one of those has a ray behind it.
#
# THE INSTRUMENT IS ALREADY BUILT AND IS INDIFFERENT TO WHICH BAND IT IS POINTED AT. tools/west_far.py
# walks a height ladder on the end's face plane, takes the strongest brightness step of a named polarity
# per station, and turns each into a ray. It was written for the top tier only because that is where the
# question was. Pointed a metre and a half lower it should find the lower tier's two edges the same way,
# and then the near-far split can say whether it really found them.
#
# TWO RUNS PER END, BECAUSE THE TWO EDGES HAVE OPPOSITE POLARITY, which is also the parity test: a
# detector told to find a dark-above-light edge cannot return a light-above-dark one, so if both come back
# where they should, that is two independent facts and not one detector following the drawing.
#   the solid upstand top: dark below, lit interior above, so the shade polarity
#   the rail top: the lit hall wall above it and the dark glass below, so the lit polarity
# The ladders are kept narrow for the reason recorded in west_far.py: a wide fan from a floor camera
# reaches the stained-glass junction, which is the brightest edge in the building and swamps everything.
import os
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
RUNS = (
    # tag, polarity, ladder low, ladder high, what it should find
    ('-low', 'shade', '6.35', '7.35', 'the lower solid upstand top, drawn on 6.85'),
    ('-lowrail', 'lit', '6.70', '7.70', 'the lower rail top, drawn on 7.22'),
)

for end in ('west', 'east'):
    for tag, pol, hlo, hhi, what in RUNS:
        env = dict(os.environ, END=end, TAG=tag, POLARITY=pol, HLO=hlo, HHI=hhi)
        print('')
        print('=' * 100)
        print('%s end, %s (ladder %s to %s, %s polarity)' % (end.upper(), what, hlo, hhi, pol))
        print('=' * 100)
        sys.stdout.flush()
        r = subprocess.run([sys.executable, '-u', os.path.join(HERE, 'west_far.py')],
                           env=env, capture_output=True, text=True)
        sys.stdout.write(r.stdout)
        if r.returncode != 0:
            sys.stdout.write(r.stderr[-1500:])
            print('   REFUSED, and a refusal is a result: this band does not carry a usable edge here')
        sys.stdout.flush()
