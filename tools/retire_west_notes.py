# 2026-09-09: retire the three entries on the unmeasured list that the upstand fit has answered, and put
# what actually remains in their place.
import io

target = 'tools/check_bounds.py'
s = io.open(target, encoding='utf-8').read()

OLD1 = ("             'WHICH of the west numbers is wrong: the arrivals cap the top on 8.818 against a "
        "drawn 9.020,'\n"
        "             ' but a top 0.20 m lower, a deck 0.20 m lower and a face 0.20 m further into the "
        "hall all fit'\n"
        "             ' the same rays, and 16 cameras from one clip at one station cannot separate them. "
        "The bound'\n"
        "             ' below fails; the fix is not identified, tools/gallery_arrival.py',\n")
NEW1 = ("             'ANSWERED: which of the west numbers was wrong. It was the FACE. A top 0.20 m "
        "lower, a deck'\n"
        "             ' 0.20 m lower and a face 0.20 m over all fitted the same rays, and the upstand-top "
        "line fit'\n"
        "             ' separates them because a line carries both at once: face u 3.760, height 9.082. "
        "The cap'\n"
        "             ' read on THAT face is 9.220, so nothing was ever over it, tools/west_far.py',\n")

OLD2 = ("             'the west upstand is still drawn on 0.68 against an arrival cap of 0.478. That cap "
        "is one-sided'\n"
        "             ' and from one clip, so it is not a value and the upstand is NOT moved on it; the "
        "bound below'\n"
        "             ' fails and says so, tools/gallery_arrival.py',\n")
NEW2 = ("             'ANSWERED: the west upstand is no longer a cap but a measurement, 0.742 m, and the "
        "east 0.727 m,'\n"
        "             ' fitted separately from cameras 37 m apart and agreeing to 15 mm. Both are drawn "
        "on those'\n"
        "             ' numbers now, tools/west_far.py, tools/apply_upstands.py',\n")

OLD3 = ("             'and the two west instruments only agree if the parapet is NOT the solid the sim "
        "draws: the deck'\n"
        "             ' arrivals cap a solid on 8.818 while the hall floor sees an edge on 9.59. A low "
        "solid upstand'\n"
        "             ' with an open rail above it satisfies both. Nothing is drawn that way yet.',\n")
NEW3 = ("             'STILL OPEN at the west end: two of my own fits on the same face disagree in u. The "
        "balcony'\n"
        "             ' front puts it on 4.160 and the upstand top on 3.760. u is the weak direction in "
        "both, so'\n"
        "             ' 0.40 m between them is not a measurement and the face is NOT moved on it',\n")

n = 0
for old, new in ((OLD1, NEW1), (OLD2, NEW2), (OLD3, NEW3)):
    if old in s:
        s = s.replace(old, new, 1)
        n += 1
    else:
        print('   did not match:\n%s' % old[:90])
io.open(target, 'w', encoding='utf-8', newline='\n').write(s)
print('%d of 3 notes retired' % n)
