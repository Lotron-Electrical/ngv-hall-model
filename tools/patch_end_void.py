"""THE BLACK BAR ACROSS EACH END, AND THE TRUSS STANDING INSIDE THE WEST BALCONY (2026-09-10).

Lloyd, after the previous push: "you left some black horizontal bars on each end", and "down one end
the stage lighting is intersecting with the balcony". Two separate defects, both real, both visible
from the hall floor (look-w.jpg, look-e.jpg).

THE BLACK BAR. Removing the stone over the galleries was right about the brick and wrong about the
emptiness. tools/back_wall_top.py had already measured what stands over the crossing and the number
was in the record before this: the west reads 0.268 of its own lit band over 27 frames (spread 0.066,
CLAIM) and the east 0.325 over 4 (RECORD ONLY). A void reads 0.038 in the render, which is the black
bar. So something IS there and it is dark, about a quarter of the lit wall, and the quad comes back
with a material measured for that instead of the hall's lit brick, which is what Lloyd objected to.
ENDW.backTop goes away again; the wall runs to W.top and the dark face over the head does the cutting,
which is the only reading that carries the height AND the tone.

THE TRUSS. RIG.u0 was 1.0, from a note reading "from about 1 m in from the west wall". The west end
WALL is at u 0.344 but the west gallery projects 3.85 m into the hall in front of it, so its face is
at u 4.194 and the truss ran 3.2 m through the balcony at h 9.0, between its deck (8.34) and its head
(11.09). Steel cannot stand inside a floor. This is a BOUND, not a measurement: u0 goes to 4.29, one
tenth of a metre clear of the measured gallery face, and the note it came from is no longer readable
against this geometry. b3_000161, the only posed frame that looks along that wall, foreshortens u 0
to 14 into 200 blurred pixels and cannot say where the steel really stops, so where the truss ENDS is
named as unmeasured rather than invented. RIG_PHOT, the photometric array of 23 fixtures from u 1.5,
is NOT moved: its positions and count are what the calibrated house level is derived from, and the
drawn truss and the lit array now disagree at the west end by about 3 m, which is written here.

  python tools/patch_end_void.py            # apply to index.html
  python tools/patch_end_void.py --check     # report only
"""
import io, sys

PAIRS = [
    # 1. the material, next to the other end-gallery materials
    (""" const topSoffitMat=dnm(0x13100d,0x332c26,'gallery-soffit');""",
     """ // WHAT STANDS OVER THE GALLERY, MEASURED RATHER THAN GUESSED (2026-09-10, tools/back_wall_top.py `above`).
 // Over the height at which the lit cream wall stops, the same ladder reads 0.268 of that frame's own lit band at
 // the west (27 frames, spread 0.066, CLAIM) and 0.325 at the east (4 frames, RECORD ONLY, inside the west's
 // spread). A lit stone face would read near 1 and the hall's brick did; an empty void renders 0.038 and that was
 // the black bar Lloyd saw across each end. So the surface is there and it is dark, and this is the west claim
 // carried through the render the way topBackWestMat was, and it took TWO corrections, which is one more than the
 // recipe allows and is said so here. 0.268 of the lit wall's own colour is 0x232214 and it rendered 0.113. The
 // first correction was computed in linear light through an ASSUMED tone map and landed 0.421, an overshoot, so
 // the model was wrong. The second is not a model at all: two rendered points (input 35 -> output 15, input 72 ->
 // output 56) give the response itself, out = 1.108 x in - 23.8, and the input that lands 0.268 x 133 = 36 is 54.
 // 0x36341f. Measuring the response beats assuming it, and the third render below is what decides.
 // Night is not touched, because no night frame faces it.
 const endVoidMat=dnm(0x050505,0x36341f,'gallery-over');
 const topSoffitMat=dnm(0x13100d,0x332c26,'gallery-soffit');"""),

    # 2. the quad comes back, with the dark material
    ("""  { const sb=(W.stoneBase&&W.stoneBase[side]); if(sb)
    quad([[uF,0,sb],[uF,D,sb],[uF,D,top],[uF,0,top]],stone,'end-wall'); }""",
     """  // AND IT IS DRAWN AGAIN, DARK, AN HOUR AFTER IT CAME OUT. Taking it out was right about the brick and wrong
  // about the emptiness: the ladder had already measured 0.268 of the lit band over the crossing at the west,
  // and an empty void renders 0.038, which is the black bar across each end that Lloyd saw next. The face is
  // there, it is dark, and endVoidMat carries the measured tone. stoneBase is the base it stands on.
  { const sb=(W.stoneBase&&W.stoneBase[side]); if(sb)
    quad([[uF,0,sb],[uF,D,sb],[uF,D,top],[uF,0,top]],endVoidMat,'end-wall'); }"""),

    # 3. the back wall runs to the top again; the dark face does the cutting
    ("""  // W.backTop, not W.top: the wall ends where the ladder says the lit cream ends (west 12.90, east 13.20)
  // and over it the hall sees the dark void under the canopy, which is what the frames show (back_wall_top.py).
  { const bt=(W.backTop&&W.backTop[side])||top;
    quad([[uB,0,fl[1]],[uB,D,fl[1]],[uB,D,bt],[uB,0,bt]],side==='west'?topBackWestMat:topBackMat,'gallery-back'); }""",
     """  // to the top again (2026-09-10): W.backTop capped this wall for an hour, while the face over the head was not
  // drawn at all. With the dark face back the cut is made by the face, where it was measured, and a second cap
  // here would only be a second answer to one question.
  quad([[uB,0,fl[1]],[uB,D,fl[1]],[uB,D,top],[uB,0,top]],side==='west'?topBackWestMat:topBackMat,'gallery-back');"""),

    # 4. the numbers
    ("stoneBase:{west:null, east:null}, backTop:{west:12.90, east:13.20},",
     "stoneBase:{west:12.38, east:12.93},"),

    # 5. the truss cannot stand inside the west balcony
    ("""const RIG={d:2.2, y:9.0, u0:1.0, u1:46.0, side:0.30, chord:0.025, seg:0.30, fixEvery:2.0};""",
     """// u0 WAS 1.0 AND THE TRUSS STOOD INSIDE THE WEST BALCONY (Lloyd, 2026-09-10: "down one end the stage
// lighting is intersecting with the balcony"). The note above says "about 1 m in from the west wall", and the
// west end WALL is at u 0.344; but the gallery projects 3.85 m into the hall in front of it, so its face is at
// u 4.194 and 3.2 m of steel ran through the balcony at h 9.0, between its deck 8.34 and its head 11.09.
// 4.29 is a BOUND and not a measurement: one tenth of a metre clear of the measured face, because steel cannot
// stand inside a floor. Where the truss really ends is UNMEASURED. b3_000161 is the only posed frame that looks
// along that wall and it foreshortens u 0 to 14 into about 200 blurred pixels. RIG_PHOT (23 fixtures from
// u 1.5) is not moved with it: the calibrated house level is derived from that count and those positions, so
// the drawn truss and the lit array now disagree at the west end by about 3 m. That is an open defect, named.
const RIG={d:2.2, y:9.0, u0:4.29, u1:46.0, side:0.30, chord:0.025, seg:0.30, fixEvery:2.0};"""),
]


def main():
    p = 'index.html'
    s = io.open(p, encoding='utf-8').read()
    check = '--check' in sys.argv
    for old, new in PAIRS:
        if new in s:
            print('already applied: %s...' % new[:60].replace('\n', ' '))
            continue
        if old not in s:
            print('NOT FOUND, nothing changed: %s...' % old[:60].replace('\n', ' '))
            sys.exit(1)
        if not check:
            s = s.replace(old, new, 1)
    if check:
        return
    io.open(p, 'w', encoding='utf-8', newline='\n').write(s)
    print('patched %s' % p)


if __name__ == '__main__':
    main()
