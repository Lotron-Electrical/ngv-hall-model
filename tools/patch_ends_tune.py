"""THE TWO ENDS, MEASURED APART, DRAWN APART (2026-09-10, tools/ends_audit.py, the remaining bands).

The rule all evening has been: the two ends are drawn alike unless something measures them apart. The
whole-elevation audit now measures them apart in three places, with each end's own spread under the
difference, so each place gets its own number and the rule is kept rather than broken.

1. THE BACK WALL'S FALLOFF. At h 12.6 the west reads 0.688 of its own lit band and the east 0.856; at
   13.2 the west 0.553 and the east 0.408. One ramp fitted the west and left the east 0.26 under at 12.6
   and 0.20 over at 13.2, in opposite directions on the same texel. ENDW.backRamp becomes {west, east},
   the west's as it was; the east's texels 235, 215, 200, 190 at 12.5 to 13.1 and 120 at 13.3, and 251 at
   11.3 where the east reads 0.983 against a rendered 0.876. topBackWestMat carries the west's map and
   topBackMat the east's.
   The west's own 12.6 band still read 0.857 with its texel at 163, because an 80th percentile over a
   band reads the band's bottom edge and the render's bands sit about 0.05 m under the photograph's:
   the texel at 12.5 goes 223 to 200 so the edge that band actually reads is darker.

2. THE SHADE UNDER THE GALLERY. The east's stone under its soffit reads 0.21 at plane h 4.4 to 4.8
   against the west's ramp landing 0.33 there. groundShade becomes {west, east}; the east's last three
   texels fall further (130, 120, 70).

3. THE FOOT OF EACH END. The east's lit lobby front (groundLit.east) reads 0.735 against 0.86 at plane
   h 2.0 to 2.4, so its day colour rises 0x656155 to 0x6e6a5d, and its top comes down 3.0 to 2.85: the
   band at plane 2.6 still read 0.708 where the photographs have 0.344, the same 0.05 to 0.1 m offset
   between the render's bands and the photograph's. The WEST's foot reads 0.46 to 0.51 of its lit band
   from the floor to plane h 0.8 (face 1.5), on 183 frames, against a rendered 0.32: a paler base than
   the stone over it, weaker than the east's 0.78. groundLit.west {top:1.5, day:0x4c4940}.

  python tools/patch_ends_tune.py            # apply to index.html
  python tools/patch_ends_tune.py --check     # report only
"""
import io, sys

WEST_RAMP = ("[[8.34,244],[9.10,244],[9.30,255],[9.90,255],[10.50,255],[10.70,253],[10.90,251],[11.10,249],[11.30,247],"
             "[11.50,243],[11.70,239],[11.90,236],[12.10,234],[12.30,231],[12.50,223],[12.70,184],[12.90,170],[13.10,165],[13.30,168],[13.50,168]]")
EAST_RAMP = ("[[8.34,244],[9.10,244],[9.30,255],[9.90,255],[10.50,255],[10.70,253],[10.90,251],[11.10,251],[11.30,251],"
             "[11.50,247],[11.70,243],[11.90,240],[12.10,238],[12.30,236],[12.50,235],[12.70,215],[12.90,200],[13.10,190],[13.30,120],[13.50,120]]")
WEST_SHADE = "[[1.40,255],[2.63,235],[3.19,206],[3.74,175],[4.11,172],[4.48,168],[4.85,163],[5.30,200]]"
EAST_SHADE = "[[0.90,255],[1.25,242],[2.05,242],[2.63,255],[3.19,200],[3.30,196],[3.45,146],[3.75,146],[3.92,165],[4.00,180],[4.15,180],[4.30,163],[4.48,158],[4.85,155],[5.30,110]]"   # synced to index.html after the east foot passes two and three (patch_east_foot2.py, patch_east_foot3.py)

PAIRS = [
    ("groundLit:{east:{top:3.0, day:0x656155}}, groundShade:" + WEST_SHADE + ",",
     "groundLit:{east:{top:3.2, day:0x777467}, west:{top:1.5, day:0x4c4940}}, groundShade:{west:" + WEST_SHADE + ", east:" + EAST_SHADE + "},"),

    ("backRamp:" + WEST_RAMP.replace("[12.50,200]", "[12.50,223]") + ",",
     "backRamp:{west:" + WEST_RAMP + ", east:" + EAST_RAMP + "},"),

    (""" const backRampTex=rampTex(W.backRamp,W.floors[1],W.top);
 if(backRampTex){ topBackMat.map=backRampTex; topBackWestMat.map=backRampTex; }""",
     """ // per end since the audit measured the two falloffs apart (2026-09-10, tools/patch_ends_tune.py): the west's on
 // topBackWestMat, the east's on topBackMat, each from its own deck's frames.
 { const R=W.backRamp||{}; const tw=rampTex(R.west||R,W.floors[1],W.top), te=rampTex(R.east||R.west||R,W.floors[1],W.top);
   if(tw) topBackWestMat.map=tw; if(te) topBackMat.map=te; }"""),

    ("""  if(W.groundShade){ const t=rampTex(W.groundShade,0,W.groundTop);""",
     """  { const GS=W.groundShade&&(Array.isArray(W.groundShade)?W.groundShade:W.groundShade[side]); if(GS){ const t=rampTex(GS,0,W.groundTop);"""),

    ("""   const uS=uF-s*0.006; quad([[uS,0,0],[uS,D,0],[uS,D,W.groundTop],[uS,0,W.groundTop]],m,'end-ground-shade'); }""",
     """   const uS=uF-s*0.006; quad([[uS,0,0],[uS,D,0],[uS,D,W.groundTop],[uS,0,W.groundTop]],m,'end-ground-shade'); } }"""),
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
            print('NOT FOUND, nothing changed: %s' % old[:80].replace('\n', ' '))
            sys.exit(1)
        if not check:
            s = s.replace(old, new, 1)
    if check:
        return
    io.open(p, 'w', encoding='utf-8', newline='\n').write(s)
    print('patched %s' % p)


if __name__ == '__main__':
    main()
