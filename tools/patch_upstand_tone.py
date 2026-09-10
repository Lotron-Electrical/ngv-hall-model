"""THE DECK FASCIA AND THE PARAPET ARE 2.4 TIMES TOO BRIGHT (2026-09-10, tools/ends_audit.py).

upstandMat draws the top slab's fascia and the solid upstand behind the front glass, and its day
colour 0x4a4540 was set "about the stone", by relation and not by measurement. The whole-elevation
audit measures it directly, at both ends, in the frames where it is looked at: against each frame's
own h 10.0-11.0 lit band the west reads 0.194, 0.188 and 0.188 over h 8.2 to 8.6 (183 frames, spreads
0.018 to 0.042) and the east reads 0.164 to 0.184 over h 8.0 to 9.0 (23 frames). The render gave
0.444 west and 0.513 east.

The west carries the number, and the response is the one measured on this pipeline (out = 0.02274 x
in^1.826 in 8-bit sRGB, three rendered points): 0.185 x 133 = 24.6 wants an input of 46 where 74
stands, so 0x4a4540 becomes 0x2e2b28. Night is untouched; no night frame was read here.

  python tools/patch_upstand_tone.py            # apply to index.html
  python tools/patch_upstand_tone.py --check     # report only
"""
import io, sys

PAIRS = [
    (""" const upstandMat=dnm(0x0a0908,0x4a4540,'gallery-parapet');   /* the top slab's fascia and the 0.56 upstand: about the stone */""",
     """ // MEASURED, NOT RELATED (2026-09-10, tools/ends_audit.py). 0x4a4540 was set "about the stone"; the audit reads
 // this surface against each frame's own lit band at 0.19 west (183 frames, h 8.2 to 8.6) and 0.17 east (23
 // frames, h 8.0 to 9.0) where the render gave 0.44 and 0.51. 0x2e2b28 lands 0.185 through the measured render
 // response. Night is untouched, because no night frame was read here.
 const upstandMat=dnm(0x0a0908,0x2e2b28,'gallery-parapet');   /* was 0x4a4540, "about the stone" by relation */"""),
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
            print('NOT FOUND, nothing changed')
            sys.exit(1)
        if not check:
            s = s.replace(old, new, 1)
    if check:
        return
    io.open(p, 'w', encoding='utf-8', newline='\n').write(s)
    print('patched %s' % p)


if __name__ == '__main__':
    main()
