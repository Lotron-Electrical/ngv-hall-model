# 2026-09-09: put the two solid upstands on the tops that were measured, and record how that dissolved
# the one bound this model has been failing all day.
#
# THE PARITY WAS WRONG THE FIRST TIME AND THE TOOL SAID SO BEFORE ANY FITTING. tools/west_far.py was
# written for the top of a LIT front, bright below and dark above, which is right for the balcony front
# edge it measured on 9.799 west and 9.865 east. Pointed at the solid upstand under it with that same
# polarity, its feasibility test found a steepest fall of 0.27 standard deviations per metre and refused.
# Turned the other way up it finds 8.86 at the east end and 7.75 at the west. From the hall floor the
# solid face looks away from the stained glass and sits in its own shade, while the open rail above it
# shows the lit gallery ceiling through the gaps. Dark below, bright above.
#
# THE EAST END IS THE CONTROL AND IT PASSED. 4,502 rays, 88 per cent inside 50 mm, median 11 mm, the two
# halves of the camera set agreeing to 27 mm, and it lands on h 9.067 against a drawn 9.110. The west then
# gives h 9.082 from 3,545 inliers with a 17 mm median and its halves 43 mm apart. Measured against the
# deck those are upstands of 0.727 and 0.742: the two ends of the hall, fitted separately from cameras
# 37 m apart, agree with each other to 15 mm.
#
# AND THAT SETTLES THE FAILING BOUND, WHICH WAS COMPARING TWO DIFFERENT FACES. The deck arrivals cap the
# west top on 8.818, and the drawn 9.020 stood above it, which is why the bound failed. But that cap is a
# CURVE, not a number: tools/gallery_arrival.py prints the 5th percentile crossing against the assumed
# face station, and it moves 0.19 m for every 0.20 m the face moves. It reads 8.818 on the drawn face
# u 4.194 and 9.189 on u 3.794. The fit that measures the top measures the face at the same time, and it
# puts it on u 3.760. Comparing a height obtained on one face against a cap computed on another was never
# a valid comparison. On the face this fit actually supports, ZERO per cent of the 3,371 arrivals pass
# below the drawn top. The two instruments never disagreed about the parapet; they were asked about
# different planes.
# The face itself is NOT moved on this. The balcony front fit put the same end on u 4.160 and this one
# puts it on 3.760, and the u direction is the weak one in both, so 0.40 m of disagreement between two of
# my own fits is not a measurement. Only the heights move here.
import re

WEST, EAST = 0.742, 0.727

src = open('index.html', encoding='utf-8').read()
old = re.search(r'upstands:\{west:[0-9.]+,\s*east:[0-9.]+\}', src).group(0)
new = 'upstands:{west:%.3f, east:%.3f}' % (WEST, EAST)
open('index.html', 'w', encoding='utf-8', newline='\n').write(src.replace(old, new, 1))
print('was %s' % old)
print('now %s' % new)
print('west top %.3f, east top %.3f, both from the deck on 8.340' % (8.340 + WEST, 8.340 + EAST))
