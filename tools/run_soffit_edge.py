# 2026-09-09: measure the deck for the first time, by measuring the slab it sits on.
#
# The gallery deck 8.34 is the most load-bearing number on these balconies. The solid upstand, the rail,
# the fascia, the floor and the ceiling below are all drawn as offsets from it, so every balcony height
# this file quotes is that number plus something. It has never been measured. It is CORROBORATED, by
# twenty-two cameras that leaned through an opening with their feet between 7.93 and 8.51, which is a
# 0.58 m bracket and is not the same as a measurement.
#
# AND IT CANNOT BE MEASURED DIRECTLY FROM THE HALL FLOOR, because the deck is a horizontal surface hidden
# behind its own parapet. Nobody standing below it has ever seen it. What IS visible is the underside of
# the slab that carries it: a dark fascia band whose BOTTOM edge is the slab soffit, drawn on 8.34 minus
# 0.26. Below that edge is the lower gallery's lit interior, above it is dark stone, so going up the face
# the brightness falls. That is the 'lit' polarity this instrument already knows how to find.
#
# SO MEASURE THE SOFFIT AND THE DECK FOLLOWS FROM THE SLAB. It converts the deck from corroborated to
# measured-minus-one-assumption, which is a real improvement on a 0.58 m bracket, and it says so plainly
# rather than pretending the slab thickness was measured too.
import os
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
PLANE = {'west': '4.194', 'east': '48.056'}
for end in ('west', 'east'):
    print('')
    print('=' * 96)
    print('%s slab soffit, the underside of the top gallery deck, ladder 7.55 to 8.65' % end.upper())
    print('=' * 96)
    sys.stdout.flush()
    env = dict(os.environ, END=end, TAG='-soffit', POLARITY='lit', HLO='7.55', HHI='8.65',
               UPLANE=PLANE[end])
    r = subprocess.run([sys.executable, '-u', os.path.join(HERE, 'west_far.py')],
                       env=env, capture_output=True, text=True)
    sys.stdout.write(r.stdout[-1100:])
    if r.returncode != 0:
        sys.stdout.write(r.stderr[-800:])
    sys.stdout.flush()
