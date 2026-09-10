"""THERE IS NOTHING OVER THE GALLERIES: THE BACK WALL SIMPLY ENDS (2026-09-10, an hour after
tools/patch_stone_base.py, which raised the stone instead of removing it).

Lloyd looked at the sandbox after that push and said it plainly: "there is a brick wall coming down
from the ceiling that shouldn't be there." He is right, and the measurement agrees with him once it
is asked the right question, which the first patch never did.

WHAT THE FIRST PATCH GOT RIGHT AND WHAT IT GOT WRONG. tools/back_wall_top.py measures a LOCUS: the
height at which the lit cream wall stops being lit, h 12.90 west and 13.20 east. It cannot say what
stops it, and the first patch chose the reading that kept the existing quad, sliding the end wall's
stone up until it cut the view at the measured place. That reproduces the height and nothing else.

THE STEP SIZE IS THE EVIDENCE, AND IT WAS IN THE OUTPUT ALL ALONG. The rule fixed blind fires on a
fall under 0.55 of the frame's own lit band, and it fired on 114 west frames, so the photograph's
edge is a HARD one. With the stone raised, the render's edge was a step to 0.82 west and 0.77 east:
far too soft to have tripped the blind rule, because stone over cream is one lit surface over
another. With the stone gone and the back wall simply ending, the render's edge is a step to 0.46
and 0.51, which is the hard edge the photographs show. So the two readings of the same locus are
separable after all, and the photographs pick the open one.

WHAT MOVES: ENDW.stoneBase becomes null at both ends and the quad is not drawn; ENDW.backTop {west
12.90, east 13.20} caps the gallery's back wall at the measured height instead of running it to
W.top 13.5. Over it the hall sees the dark void under the canopy, which is what the frames show
over the cream and what the render now draws.

THE CHECK, RENDERED: west 13.10 against the claim 12.90 spread 0.25, east 13.20 against 13.20
spread 0.10. Both inside spread plus one rung, no correction.

  python tools/patch_back_top.py            # apply to index.html
  python tools/patch_back_top.py --check     # report only
"""
import io, sys

PAIRS = [
    ("""  { const sb=(W.stoneBase&&W.stoneBase[side])||W.head;
    quad([[uF,0,sb],[uF,D,sb],[uF,D,top],[uF,0,top]],stone,'end-wall'); }""",
     """  // AND AN HOUR LATER THERE IS NOTHING THERE AT ALL. Lloyd looked at the sandbox with the stone raised
  // and said "there is a brick wall coming down from the ceiling that shouldn't be there". The ladder only
  // ever measured a LOCUS, the height at which the lit wall stops being lit, and raising the stone was the
  // reading of it that kept this quad. The step SIZE separates the two readings and it was in the output
  // all along: the blind rule fires on a fall under 0.55 and it fired on 114 west frames, so the hall's
  // edge is hard, while stone over cream rendered a step to only 0.82 west and 0.77 east. With this quad
  // gone and the back wall simply ending, the render steps to 0.46 and 0.51, which is the hall's own edge.
  // So the stone over the galleries is not drawn, and stoneBase stays in ENDW as the record of what it was.
  { const sb=(W.stoneBase&&W.stoneBase[side]); if(sb)
    quad([[uF,0,sb],[uF,D,sb],[uF,D,top],[uF,0,top]],stone,'end-wall'); }"""),

    ("""  quad([[uB,0,fl[1]],[uB,D,fl[1]],[uB,D,top],[uB,0,top]],side==='west'?topBackWestMat:topBackMat,'gallery-back');""",
     """  // W.backTop, not W.top: the wall ends where the ladder says the lit cream ends (west 12.90, east 13.20)
  // and over it the hall sees the dark void under the canopy, which is what the frames show (back_wall_top.py).
  { const bt=(W.backTop&&W.backTop[side])||top;
    quad([[uB,0,fl[1]],[uB,D,fl[1]],[uB,D,bt],[uB,0,bt]],side==='west'?topBackWestMat:topBackMat,'gallery-back'); }"""),

    ("stoneBase:{west:12.38, east:12.93},",
     "stoneBase:{west:null, east:null}, backTop:{west:12.90, east:13.20},"),
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
