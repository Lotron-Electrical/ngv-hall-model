"""THE GALLERY FRONT GLASS TAKES NOTHING, AND THE SIM HAD IT TAKING A THIRD (2026-09-10,
tools/ends_audit.py).

The audit's bands between the deck and the rail top look straight through the west gallery's front
glass at its own lit back wall, and the band above the rail top looks at the same wall with no glass
in the way. That is a transmission measurement with its own control built in, and neither number
depends on exposure because both are ratios to the same reference.

WHAT IT SAYS. Through the glass (h 9.4, 9.6, 9.8 on the back-wall plane, which pass the face at 9.44,
9.62 and 9.81, all below the west rail top 9.799 + deck) the wall reads 1.010, 1.016 and 1.021 of the
frame's own h 10.0-11.0 reference, on 183 frames with spreads of 0.03 to 0.04. Above the rail it reads
1.016 and 1.010. So the glass takes nothing measurable: transmission 1.00, and if anything the band
under the rail is a hair brighter than the band over it. The render gave 0.714, 0.722 and 0.722.

railMat was a near-black at opacity 0.28, so it multiplied everything behind it by 0.72, and that is
exactly the 0.72 the render returns. It goes to 0.02. THE EAST POINTS THE SAME WAY AND MORE WEAKLY:
its own through-glass band reads 0.966 against a rendered 0.857, a ratio of 1.13 where the west asks
for 1.40. One material serves both ends and nothing measured says they differ in kind, so both take
the west's number and the east's residual is measured after the render and written down.

AND THE EAST'S TINTED BAND HAS TO BE RE-DERIVED, BECAUSE IT WAS MEASURED AGAINST THE OLD GLASS.
tools/face_band.py measured the floor seen through the band at 0.847 of the floor seen through the
clear glass ABOVE it, then turned that into an opacity using railMat's 0.72 transmission: 1 - 0.847 x
0.72 = 0.39. With the clear glass transmitting 1.00 the same measurement gives 1 - 0.847 x 1.00 =
0.153. The frames have not changed; only the number they were divided by has, and leaving 0.39 in
place would carry the old glass forward inside the new one.

  python tools/patch_rail_clear.py            # apply to index.html
  python tools/patch_rail_clear.py --check     # report only
"""
import io, sys

PAIRS = [
    (""" const railMat=new THREE.MeshBasicMaterial({color:0x0c1014, side:THREE.DoubleSide, transparent:true, opacity:0.28, name:'gallery-rail'});""",
     """ // THE FRONT GLASS TAKES NOTHING (2026-09-10, tools/ends_audit.py). The audit's bands under the west rail top
 // look through this glass at the gallery's own lit back wall and read 1.010, 1.016 and 1.021 of the frame's own
 // h 10-11 reference on 183 frames, against 1.016 and 1.010 for the bands ABOVE the rail, where no glass stands.
 // Transmission 1.00 with its control built in. At opacity 0.28 this material multiplied everything behind it by
 // 0.72, which is exactly what the render returned. 0.02 keeps the surface without taking the light. The east
 // asks for 1.13 where the west asks for 1.40; one material serves both and nothing says they differ in kind.
 const railMat=new THREE.MeshBasicMaterial({color:0x0c1014, side:THREE.DoubleSide, transparent:true, opacity:0.02, name:'gallery-rail'});"""),

    ("""transparent:true, opacity:0.39, depthWrite:false, name:'gallery-glass-tinted'""",
     """transparent:true, opacity:0.153, depthWrite:false, name:'gallery-glass-tinted'"""),

    ("""  // undecided by the rule (0.847 against a 0.85 bar); the strength is what the frames give.""",
     """  // undecided by the rule (0.847 against a 0.85 bar); the strength is what the frames give.
  // RE-DERIVED 2026-09-10 WHEN THE CLEAR GLASS WAS MEASURED. The 0.39 came from 1 - 0.847 x 0.72, the 0.72 being
  // railMat's transmission at the time. The audit now measures that transmission as 1.00, so the same frames give
  // 1 - 0.847 x 1.00 = 0.153. Nothing about the photographs changed; only the number they were divided by."""),
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
