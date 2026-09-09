# 2026-09-09: the head over the top gallery, measured at both ends, and the soffit depth refused.
#
# ENDW.head 11.1 and ENDW.soffitDepth 2.1 have sat on the unmeasured list together since they were
# written, on the grounds that nothing has ever seen the back edge of that soffit. Half of that is now
# wrong and half of it is more true than before.
#
# THE INSTRUMENT PASSED ITS CONTROL FIRST. Pointed at the balcony front top, an edge two other tools have
# already pinned, tools/soffit_back.py recovers u 4.110 h 9.795 against a measured u 4.194 h 9.799: four
# millimetres in height from 306 rays with a 13 mm median.
#
# THE HEAD IS FOUND AT BOTH ENDS. East: 197 rays, 24 mm median, u 48.118 h 11.093, and the near and far
# halves of the camera set agree to 0.09 m in station and 0.07 m in height. West: 75 rays, 13 mm median,
# u 4.258 h 11.082. Both ends land on the face within 65 mm and both land BELOW the drawn 11.100, by 7 mm
# and 18 mm. Weighted by support that is 11.090, and that is what the model is moved to. It is a 10 mm
# move and it is only worth making because two ends of the building, fitted separately, fell the same way.
#
# THE BACK EDGE IS NOT THERE, and the refusal is sharper than the old "nothing has ever seen it". The peel
# ran to five lines at each end and every one of them sits within 0.9 m of the face; not one lands near the
# drawn back edge on u 2.094 west or 50.156 east, which the ray fan does reach. The reason is photometric
# rather than geometric: from the far half of the hall the soffit is seen twelve degrees off edge-on, so
# 2.1 m of it subtends about 0.44 m of apparent height at forty metres, and its junction with the back
# wall is the darkest part of the darkest surface in the bay. soffitDepth stays unmeasured, now with a
# number against it instead of a shrug.
import re

HEAD = 11.090

src = open('index.html', encoding='utf-8').read()
old = re.search(r'head:[0-9.]+, soffitDepth:', src).group(0)
new = 'head:%.3f, soffitDepth:' % HEAD
open('index.html', 'w', encoding='utf-8', newline='\n').write(src.replace(old, new, 1))
print('was %s' % old)
print('now %s' % new)
print('east measured 11.093 on 197 rays, west 11.082 on 75; the drawn 11.100 sat above both')
