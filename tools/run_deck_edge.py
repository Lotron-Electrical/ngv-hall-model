# 2026-09-09: go straight for 8.34 itself, the number every other balcony number is an offset from.
#
# THE DECK IS THE MOST LOAD-BEARING UNMEASURED NUMBER IN THIS MODEL. The solid upstand, the rail, the
# fascia, the floor and the ceiling below are all drawn as offsets from it. It has been bounded and never
# measured: tools/deck_bound.py shows the lowest lens standing on it sits on h 9.03, so the floor is
# under that and 0.69 m of room is left above the drawn 8.34, which is a bound and not a number. The
# photometric route was tried and closed tonight, tools/run_soffit_edge.py walking the slab soffit at both
# ends and finding dark stone under dark stone.
#
# AND THE CALIBRATION ROUTE CLOSED THIS EVENING TOO. A lens height is unmeasurable in the abstract, but it
# cancels out of a DIFFERENCE if the same operator stands on a known floor and an unknown one in the same
# capture. Every class in the archive was checked for that tonight and not one of them does it: walk and
# night are 888 frames entirely on the hall floor, and every balcony class is entirely raised, 9.07 to
# 10.29. The only class holding both is b6s, three frames, and it is the one class already known to carry
# a pose contradiction. So there is no operator standing on two floors and no lens height to transfer.
#
# WHAT HAS NOT BEEN TRIED IS THE INSTRUMENT THAT WORKED ON EVERYTHING ELSE TONIGHT. The apron scan proved
# a level can be found where two materials meet on a face plane, and the corridor and the jambs both
# turned on the same move: fix the coordinate the geometry cannot separate, and every ray answers on its
# own. Here the STATION IS ALREADY MEASURED. The west end face stands on u 4.194 and the east on 48.056,
# both from the end-face scans, so a horizontal line on that plane has one unknown per ray and nothing to
# slide along, which is the condition the apron never had.
#
# THE LEVEL IS A MATERIAL BOUNDARY ON THAT PLANE. Below it is the underside and fascia of the top gallery;
# above it is the parapet, which this evening's recess work concluded is glazed on the face with the solid
# set 0.484 m back. Glass over fascia or parapet over fascia, either way the surface changes on the level.
#
# BOTH POLARITIES ARE RUN, AND THAT IS A CONTROL AND NOT A CONVENIENCE. A detector that reports the same
# line whichever way up its filter is pointed has found a gradient rather than an edge, which is exactly
# how the soffit line 0.2 m above each front top was killed this afternoon.
import os
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
PLANE = {'west': '4.194', 'east': '48.056'}
for end in ('west', 'east'):
    for pol in ('lit', 'dark'):
        print('')
        print('=' * 96)
        print('%s DECK LEVEL, ladder 7.85 to 8.85 on the measured face plane %s, polarity %s'
              % (end.upper(), PLANE[end], pol))
        print('=' * 96)
        sys.stdout.flush()
        env = dict(os.environ, END=end, TAG='-deck' + ('' if pol == 'lit' else 'D'), POLARITY=pol,
                   HLO='7.85', HHI='8.85', UPLANE=PLANE[end])
        r = subprocess.run([sys.executable, '-u', os.path.join(HERE, 'west_far.py')],
                           env=env, capture_output=True, text=True)
        sys.stdout.write(r.stdout[-1300:])
        if r.returncode != 0:
            sys.stdout.write(r.stderr[-700:])
        sys.stdout.flush()
