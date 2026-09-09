# 2026-09-09: the west face returned a deck edge on h 8.645 from 145 rays with 100 per cent agreement.
# Before anything moves 0.3 m, find out whether that number is the wall or the window.
#
# THE FIRST RUN LOOKS STRONG AND SITS EXACTLY WHERE AN ARTEFACT WOULD. tools/run_deck_edge.py walked a
# ladder from 7.85 to 8.85 on the measured west face plane and the dark-above detector returned 145
# detections, every one of them agreeing on u 4.189 h 8.645 inside 80 mm, with an 8 mm residual and a
# condition number of 6. That would be the best-conditioned balcony fit in the archive.
#
# BUT THE DETECTOR AVERAGES 40 SAMPLES EITHER SIDE OF A CANDIDATE, and a sample is 5 mm, so it cannot see
# an edge within 0.20 m of either end of its ladder. The usable band of that run was 8.05 to 8.65, and
# 8.645 is five millimetres under its ceiling. The apron scan died of exactly this three hours ago, and
# the rule written then was that a minimum on the edge of a sweep is not a minimum.
#
# THE POOLED PROFILE SAYS THE SAME THING OUT LOUD. Its steepest rise was reported between 8.840 and 8.845
# as 49.77 standard deviations per metre, and the identical 49.769 appears again on the drawn 9.020 and
# again on 9.320, both far outside the sampled ladder. A slope that is constant across a metre of
# extrapolation is the profile running out of data, not the building.
#
# SO MOVE THE LADDER AND SEE WHETHER THE ANSWER FOLLOWS IT. A real edge stands still while the window
# around it changes; an artefact of the window walks with it. This is the same test that killed the
# soffit line 0.2 m above each front top this afternoon and that the corridor passed an hour ago when its
# ladder was moved 260 mm.
#   7.40 to 9.40 puts the usable band 7.60 to 9.20, so 8.645 is comfortably inside it and free to stay.
#   7.60 to 9.00 puts it 7.80 to 8.80, a different ceiling again.
#   8.00 to 9.60 puts it 8.20 to 9.40, whose floor is above the answer's own neighbourhood.
# If 8.645 is real it survives all three. If it is the ceiling, it will be found near each new one.
import os
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
LADDERS = [('7.40', '9.40'), ('7.60', '9.00'), ('8.00', '9.60')]
for lo, hi in LADDERS:
    print('')
    print('=' * 96)
    print('WEST DECK LEVEL, ladder %s to %s, usable %.2f to %.2f, dark-above'
          % (lo, hi, float(lo) + 0.20, float(hi) - 0.20))
    print('=' * 96)
    sys.stdout.flush()
    env = dict(os.environ, END='west', TAG='-deckL%s' % lo.replace('.', ''), POLARITY='dark',
               HLO=lo, HHI=hi, UPLANE='4.194')
    r = subprocess.run([sys.executable, '-u', os.path.join(HERE, 'west_far.py')],
                       env=env, capture_output=True, text=True)
    sys.stdout.write(r.stdout[-900:])
    if r.returncode != 0:
        sys.stdout.write(r.stderr[-700:])
    sys.stdout.flush()
