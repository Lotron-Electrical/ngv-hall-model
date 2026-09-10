"""THE EAST GROUND LEVEL IS PALE TO ABOUT h 3.3 AND DARK ABOVE; THE SIM HAD DARK STONE THROUGHOUT
(2026-09-10, tools/ends_audit.py, east-low-pair.jpg).

The audit's largest remaining block was the east's bands h 0 to 2.4: 0.70 to 0.87 of the lit band in
the photographs against 0.35 in the render, thirteen bands. Two readings were tried and refuted before
this one, and both are kept. First, the carpet being too dark: it WAS (tools/floor_tone.py, both decks
agree, dayGainOf('floor') 0.8 to 1.69), but lifting it moved these bands by nothing, so they are not
carpet in the render. Second, open floor under the east gallery: the bands drawn on b7s_000908 sit over
a pale surface with people at its foot, and for half an hour this file drew the east ground wall at the
plate end instead of the face. That made the bands WORSE (0.21 to 0.25, the unlit lobby back wall),
and the geometry refutes the reading anyway: a band on the plane u 51.894 above its own floor line
cannot be floor, whatever it looks like at 48 m, and for it to be floor the wall would have to stand
18 m beyond the plate end.

So it is a pale WALL. The east's ground level, the entrance end, reads 0.70 to 0.87 of the lit band
from the floor up to plane h 2.6, which passes the gallery face at h 3.3, and 0.18 to 0.30 from plane
h 2.8 up, which is the stone under the soffit's shadow. A lit lobby front to about 3.3 m with the
doors in it, and stone above. The west's same bands read 0.33 to 0.41: dark stone from the floor, and
the west keeps its stone.

WHAT MOVES. ENDW.groundLit {east:{top:3.3, day:0x656155}}: a face 5 mm in front of the stone, behind
the doors, from the floor to `top`, a dnm material whose day colour lands 0.78 x 133 through the
measured render response (out = 0.02274 x in^1.826) and is corrected once by the render. The shade
overlay above it stays; the doors stay where they were measured.

THE RENDER CORRECTED THE TOP ONCE: at 3.3 the bands at plane h 2.6 to 3.0 read 0.71 and 0.69 where the
photographs have 0.34 and 0.18, so the pale front stops lower; 3.0 on the face is plane h 2.5, which is
where the photographs' 0.87 becomes 0.34. The colour landed 0.735 against 0.78 first time and stands.

  python tools/patch_east_ground_lit.py            # apply to index.html
  python tools/patch_east_ground_lit.py --check     # report only
"""
import io, sys

PAIRS = [
    ("stoneBase:{west:null, east:null}, groundShade:",
     "stoneBase:{west:null, east:null}, groundLit:{east:{top:3.0, day:0x656155}}, groundShade:"),

    ("""  // the ground wall and its doors
  quad([[uF,0,0],[uF,D,0],[uF,D,W.groundTop],[uF,0,W.groundTop]],stone,'end-ground-wall');""",
     """  // the ground wall and its doors
  quad([[uF,0,0],[uF,D,0],[uF,D,W.groundTop],[uF,0,W.groundTop]],stone,'end-ground-wall');
  // THE EAST GROUND LEVEL IS PALE TO ABOUT 3.3 M (2026-09-10, tools/ends_audit.py, east-low-pair.jpg). From the
  // west deck the east end reads 0.70 to 0.87 of the lit gallery band from the floor to plane h 2.6, which passes
  // this face at 3.3, and 0.18 to 0.30 above that; the render had stone at 0.35 throughout. Two other readings were
  // tried first and refuted, the carpet (lifted, moved nothing here) and open floor under the gallery (a band on a
  // plane above its own floor line cannot be floor). A lit lobby front with the doors in it, stone over it. The
  // west's same bands read 0.33 to 0.41, dark stone, and the west keeps its stone.
  { const GL=W.groundLit&&W.groundLit[side]; if(GL){ const gm=dnm(0x0a0908,GL.day,'end-ground-lit'), uG=uF-s*0.003;   /* 3 mm into the hall: uF+s is INTO the end, behind the stone, and drawn there it was never seen */
    quad([[uG,0,0],[uG,D,0],[uG,D,GL.top],[uG,0,GL.top]],gm,'end-ground-lit'); } }"""),
]


def main():
    p = 'index.html'
    s = io.open(p, encoding='utf-8').read()
    check = '--check' in sys.argv
    for old, new in PAIRS:
        if new in s:
            print('already applied')
            continue
        if old not in s:
            print('NOT FOUND, nothing changed: %s' % old[:70].replace('\n', ' '))
            sys.exit(1)
        if not check:
            s = s.replace(old, new, 1)
    if check:
        return
    io.open(p, 'w', encoding='utf-8', newline='\n').write(s)
    print('patched %s' % p)


if __name__ == '__main__':
    main()
