"""THE LOWER TIER RECESS IS NOT NEAR BLACK, AND IT BRIGHTENS UPWARD (2026-09-10, tools/ends_audit.py).

The whole-elevation audit reads the west recess at 0.09 of the frame's own lit band at h 5.4 rising to
0.21 at h 7.4 and 0.19 at 8.0, on 183 frames with spreads of 0.03 to 0.06. The render gives a flat
0.030 over the whole of it: six to seven times too dark, over 2.7 m of the elevation, at both ends.

THIS DOES NOT OVERTURN THE 2026-09-09 READING, IT REFERENCES IT DIFFERENTLY, and that distinction is
the whole point. lowBackMat 0x16120f came from d4_000049, where the recess reads 0.1 to 0.15 of THE
STONE beside it in that frame; this reads it against the LIT CREAM BACK WALL in the same frame as the
comparison being made. Sunlit stone and lamp-lit cream are not the same reference and the two numbers
are not the same quantity. The audit's is the one that governs here, because the audit is the thing
that decides whether the end looks right from the hall.

WHAT MOVES. lowBackMat's day colour goes from 0x16120f to 0x312822, chosen so texel 255 lands the
profile's own maximum (0.212 x 133 = 28 through the measured render response out = 0.02274 x in^1.826),
and ENDW.lowRamp carries the shape up the recess as texels 255 x (v / 0.212)^0.5476. Night is untouched:
the recess is unlit in every night frame and no night frame was read here.
  The ramp builder written for the back wall an hour ago is lifted out of its closure into rampTex(R,
  h0, h1) and both walls call it, because a second copy of it would be a second thing to correct.

THE RECESS IS AN OPEN VOID IN THIS MODEL and the ramp is drawn on its back wall, which is the surface
the rays in this audit actually land on. It is not a claim about the light in the room behind.

  python tools/patch_low_ramp.py            # apply to index.html
  python tools/patch_low_ramp.py --check     # report only
"""
import io, sys

RAMP = ("[[5.30,161],[5.50,163],[5.70,174],[5.90,178],[6.10,187],[6.30,195],[6.50,208],[6.70,208],"
        "[6.90,235],[7.10,244],[7.30,255],[7.50,253],[7.70,247],[7.90,242],[8.08,242]]")

OLD_TEX = """ const backRampTex=(()=>{ const R=W.backRamp; if(!R) return null; const H=512, c=document.createElement('canvas');
  c.width=1; c.height=H; const x=c.getContext('2d'), h0=W.floors[1], h1=W.top;
  for(let i=0;i<H;i++){ const h=h1-(i+0.5)/H*(h1-h0); let n=R[0][1];
   for(let k=0;k<R.length-1;k++){ if(h>=R[k][0]&&h<=R[k+1][0]){ const t=(h-R[k][0])/Math.max(R[k+1][0]-R[k][0],1e-6);
     n=R[k][1]+t*(R[k+1][1]-R[k][1]); break; } if(h>R[R.length-1][0]) n=R[R.length-1][1]; if(h<R[0][0]) n=R[0][1]; }
   n=Math.round(Math.max(0,Math.min(255,n))); x.fillStyle='rgb('+n+','+n+','+n+')'; x.fillRect(0,i,1,1); }
  const t=new THREE.CanvasTexture(c); t.colorSpace=THREE.SRGBColorSpace; return t; })();
 if(backRampTex){ topBackMat.map=backRampTex; topBackWestMat.map=backRampTex; }"""

NEW_TEX = """ // rampTex: a measured vertical profile as a one-pixel-wide canvas over a quad that spans h0 to h1. Row 0 of
 // the canvas is h1, which is where quad() puts v = 1 on these faces. Used by the gallery back wall and by the
 // lower tier's recess, both measured by tools/ends_audit.py against each frame's own lit band.
 const rampTex=(R,h0,h1)=>{ if(!R) return null; const H=512, c=document.createElement('canvas');
  c.width=1; c.height=H; const x=c.getContext('2d');
  for(let i=0;i<H;i++){ const h=h1-(i+0.5)/H*(h1-h0); let n;
   if(h<=R[0][0]) n=R[0][1]; else if(h>=R[R.length-1][0]) n=R[R.length-1][1];
   else for(let k=0;k<R.length-1;k++){ if(h>=R[k][0]&&h<=R[k+1][0]){ const t=(h-R[k][0])/Math.max(R[k+1][0]-R[k][0],1e-6);
     n=R[k][1]+t*(R[k+1][1]-R[k][1]); break; } }
   n=Math.round(Math.max(0,Math.min(255,n))); x.fillStyle='rgb('+n+','+n+','+n+')'; x.fillRect(0,i,1,1); }
  const t=new THREE.CanvasTexture(c); t.colorSpace=THREE.SRGBColorSpace; return t; };
 const backRampTex=rampTex(W.backRamp,W.floors[1],W.top);
 if(backRampTex){ topBackMat.map=backRampTex; topBackWestMat.map=backRampTex; }"""

PAIRS = [
    ("stoneBase:{west:null, east:null}, backRamp:",
     "stoneBase:{west:null, east:null}, lowRamp:" + RAMP + ", backRamp:"),

    (OLD_TEX, NEW_TEX),

    (""" const lowBackMat=dnm(0x0a0908,0x16120f,'gallery-back-low');   /* 0.1-0.15x the stone by day: the lower tier is unlit in d4_000049 (2026-09-09) */""",
     """ // THE RECESS BRIGHTENS UPWARD AND IT IS NOT NEAR BLACK (2026-09-10, tools/ends_audit.py). Against each
 // frame's own lit band the west recess reads 0.09 at h 5.4, 0.13 at 6.4, 0.18 at 7.0, 0.21 at 7.4 and 0.19
 // at 8.0, on 183 frames with spreads of 0.03 to 0.06; the render was a flat 0.030. The 2026-09-09 reading
 // (0.1 to 0.15 of the stone in d4_000049) is not overturned, it is a different reference: sunlit stone in
 // one frame against lamp-lit cream in this one. The day colour lands the profile's maximum at texel 255 and
 // ENDW.lowRamp carries the shape; night is untouched, because no night frame was read here.
 const lowBackMat=dnm(0x0a0908,0x312822,'gallery-back-low');   /* was 0x16120f, 0.1-0.15x the stone by day (d4_000049, 2026-09-09) */
 { const t=rampTex(W.lowRamp,W.groundTop,W.floors[1]-W.slab); if(t) lowBackMat.map=t; }"""),
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
