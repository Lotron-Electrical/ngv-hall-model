# 2026-09-09: go straight at the number named last night as the least supported in this model.
#
# The lower gallery floor 6.33 has no ray and no lens behind it. Zero lenses in the whole archive stand on
# it, the west end yields no lower-tier edge, and the east's two lower-tier fits both fail the near-far
# test. It rests on one 2009 photograph and one inherited file.
#
# BUT THERE IS A BOUNDARY EXACTLY ON IT THAT NOTHING HAS EVER LOOKED AT. The model draws an APRON from
# h 5.40 up to the lower floor, and the lower solid upstand from that floor up. They are different
# surfaces: the apron is the lit face under the balcony, the upstand is the dark parapet on it. So the
# level itself is a material boundary on the face plane, lighter below and darker above, which is exactly
# the polarity this instrument was built to find.
#
# AND EVERY LADDER RUN ON THE LOWER TIER TONIGHT STARTED ABOVE IT. The solid run began on 6.35 and the
# rail run on 6.70, both at or over the floor, so the apron boundary was outside the search by
# construction. Nobody excluded it on evidence; it was simply never in the window.
import os
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
PLANE = {'west': '4.194', 'east': '48.056'}
for end in ('west', 'east'):
    print('')
    print('=' * 96)
    print('%s apron top, which IS the lower gallery floor, ladder 5.85 to 6.85' % end.upper())
    print('=' * 96)
    sys.stdout.flush()
    env = dict(os.environ, END=end, TAG='-apron', POLARITY='lit', HLO='5.85', HHI='6.85',
               UPLANE=PLANE[end])
    r = subprocess.run([sys.executable, '-u', os.path.join(HERE, 'west_far.py')],
                       env=env, capture_output=True, text=True)
    sys.stdout.write(r.stdout[-1100:])
    if r.returncode != 0:
        sys.stdout.write(r.stderr[-800:])
    sys.stdout.flush()
