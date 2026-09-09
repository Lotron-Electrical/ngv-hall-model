# 2026-09-09: write the head measurement into the bounds and sharpen the soffit-depth entry.
import io

ANCHOR = "# --- the long walls ---"

BLOCK = '''# THE HEAD OVER THE TOP GALLERY, MEASURED AT BOTH ENDS, tools/soffit_back.py (2026-09-09). The soffit
# is the ceiling of the end bay: a horizontal surface running from the balcony face back to the end wall.
# Its FRONT edge is a horizontal line at constant (u, h) spanning the hall, which is the fourth
# orientation of the same two-unknown fit, and the parity is the lit one because the gallery back wall
# below it is bright and the soffit underside is 0.37 times that by day.
# The instrument passed a control first: pointed at the balcony front top, an edge two other tools had
# already pinned, it recovered h 9.795 against a measured 9.799 from 306 rays with a 13 mm median.
# endHead is ENDW.head, the ceiling over the top gallery. G['head'] is already taken by the north wall's
# opening head, which is a different object 0.15 m higher, and confusing the two would be easy.
G['endHead'] = grab(r'head:([0-9.]+), soffitDepth:')
HEADFIT = (('east', 48.118, 11.093, 197, 0.024), ('west', 4.258, 11.082, 75, 0.013))
check('the head over the top gallery is drawn where both ends measure it',
      max(abs(G['endHead'] - h) for _s, _u, h, _n, _m in HEADFIT) <= 0.02,
      'drawn on %.3f. East gives %.3f from %d rays with a %.0f mm median and its near and far camera '
      'halves agreeing to 0.07 m; west gives %.3f from %d rays with %.0f mm. The two ends agree with each '
      'other to %.0f mm and both landed BELOW the 11.100 this file used to draw, which is why it moved.'
      % (G['endHead'], HEADFIT[0][2], HEADFIT[0][3], 1000 * HEADFIT[0][4], HEADFIT[1][2], HEADFIT[1][3],
         1000 * HEADFIT[1][4], 1000 * abs(HEADFIT[0][2] - HEADFIT[1][2])),
      'tools/soffit_back.py')
check('the head sits on the face it belongs to',
      max(abs(u - (48.056 if s == 'east' else 4.194)) for s, u, _h, _n, _m in HEADFIT) <= 0.10,
      'the fit returns a station as well as a height, and it puts the head on u %.3f east against a drawn '
      '48.056 and u %.3f west against a drawn 4.194, so 0.062 and 0.064 m out. A line that is really the '
      'soffit front edge has to sit on the balcony face, and it does.'
      % (HEADFIT[0][1], HEADFIT[1][1]),
      'tools/soffit_back.py')

'''

target = 'tools/check_bounds.py'
s = io.open(target, encoding='utf-8').read()
assert ANCHOR in s, 'anchor moved'
assert 'HEADFIT' not in s, 'already added'
i = s.index(ANCHOR)
s = '%s%s%s' % (s[:i], BLOCK, s[i:])

OLD = "             'ENDW soffitDepth 2.1: nothing has ever seen the back edge of that soffit',\n"
NEW = ("             'ENDW soffitDepth 2.1, and the refusal is now sharper than nothing has seen it. The "
       "peel ran'\n"
       "             ' to five lines in the right band at each end and every one sits within 0.9 m of the "
       "face;'\n"
       "             ' none lands near the drawn back edge on u 2.094 west or 50.156 east, which the ray "
       "fan does'\n"
       "             ' reach. The cause is photometric: from the far half of the hall the soffit is seen "
       "twelve'\n"
       "             ' degrees off edge-on, so 2.1 m of it subtends about 0.44 m of apparent height across "
       "forty'\n"
       "             ' metres, and its junction with the back wall is the darkest part of the darkest "
       "surface in'\n"
       "             ' the bay, tools/soffit_back.py',\n")
assert OLD in s, 'soffit note moved'
s = s.replace(OLD, NEW, 1)
io.open(target, 'w', encoding='utf-8', newline='\n').write(s)
print('head bounds added and the soffit note sharpened')
