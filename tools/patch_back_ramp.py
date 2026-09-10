"""THE GALLERY BACK WALL DIMS WITH HEIGHT; IT DOES NOT STOP (2026-09-10, tools/ends_audit.py).

The whole-elevation audit overturns the reading this file shipped twice this evening, and it does it
with the strongest set of frames yet used on this wall: 183 east-deck frames, every one of the 67
bands from h 0 to 13.4 carrying all 183, spreads of 0.01 to 0.09 through the lit band.

WHAT THE PROFILE SHOWS. Against each frame's own h 10.0-11.0 reference the west gallery's back wall
reads 1.02 at h 9.8, 1.00 at 10.4, 0.96 at 11.0, 0.92 at 11.4, 0.85 at 12.0, 0.78 at 12.4, 0.69 at
12.6, 0.62 at 12.8, 0.57 at 13.0 and 0.55 at 13.2. That is a SMOOTH FALL of about 45 per cent over
three and a half metres, which is what a wall lit by lamps standing below it looks like. There is no
step anywhere in it.

SO THE STEP THAT WAS SHIPPED TWICE WAS THE THRESHOLD, NOT THE WALL. back_wall_top.py asked each frame
for the height at which the wall falls under 0.55 of its own lit band, and a smooth ramp crosses 0.55
at about 13.2; asked for the strongest falling step in a 0.10 m ladder, per-frame noise on a ramp
returns one somewhere near the same place. Both rules answered, both answers agreed, and neither was
an edge. The claim "the lit wall ends at h 12.90" is withdrawn: it is the height at which a smooth
falloff passes a threshold that was chosen for a different question.
  THIS ALSO EXPLAINS BOTH OF LLOYD'S SIGHTINGS. Modelling a ramp as an edge needs something above the
  edge: brick gave "a brick wall coming down from the ceiling", an open void gave "black horizontal
  bars on each end". Neither artefact exists once the wall carries the ramp it actually has.

WHAT MOVES. ENDW.backRamp, the measured profile as 8-bit texels up the gallery back wall, baked into a
one-pixel-wide canvas and multiplied onto topBackMat and topBackWestMat. The texel for a target ratio
v is 255 x v^0.5476, from the render response measured on this pipeline (out = 0.02274 x in^1.826 in
8-bit sRGB, three rendered points), so texel 255 leaves the reference band exactly where it already
lands. ENDW.stoneBase goes back to null and the dark face over the head is not drawn: the fall is the
wall's own and does not need a second surface to make it.

THE TOP FOUR TEXELS WERE CORRECTED ONCE AGAINST THE RENDER, and the recipe expects that: the power law
is a fit to three points and it under-corrects at the bottom of its range. The first render left h 12.6
to 13.2 at 0.86, 0.80, 0.71 and 0.65 against 0.69, 0.62, 0.57 and 0.55, so each texel was multiplied by
(photo / render)^0.5476, giving 184, 170, 165 and 168. Everything from 11.6 to 12.4 landed first time.

ONE RAMP FOR BOTH ENDS, AND THE RECORD SAYS SO. It is measured at the west on 183 frames; the east
region carries 23 and is read through the hall's columns at 44 m. Drawing the two ends differently on
that difference would be worse than drawing them alike.

  python tools/patch_back_ramp.py            # apply to index.html
  python tools/patch_back_ramp.py --check     # report only
"""
import io, sys

RAMP = ("[[8.34,244],[9.10,244],[9.30,255],[9.90,255],[10.50,255],[10.70,253],[10.90,251],[11.10,249],"
        "[11.30,247],[11.50,243],[11.70,239],[11.90,236],[12.10,234],[12.30,231],[12.50,223],[12.70,184],"
        "[12.90,170],[13.10,165],[13.30,168],[13.50,168]]")

PAIRS = [
    # 1. the ramp itself, in ENDW
    ("stoneBase:{west:12.38, east:12.93},",
     "stoneBase:{west:null, east:null}, backRamp:" + RAMP + ","),

    # 2. build the texture and hang it on both back-wall materials
    (""" const topSoffitMat=dnm(0x13100d,0x332c26,'gallery-soffit');""",
     """ // THE MEASURED FALLOFF UP THE GALLERY BACK WALL (2026-09-10, tools/ends_audit.py). 183 east-deck frames,
 // every band carrying all 183, put the wall at 1.02 of its own h 10-11 reference at 9.8 and 0.55 at 13.2: a
 // smooth 45 per cent fall over three and a half metres, which is a wall lit from below and not a wall that
 // stops. ENDW.backRamp is that profile as texels, 255 x v^0.5476 from the render response measured on this
 // pipeline, so the reference band is left exactly where it lands and only the ramp is added. One pixel wide,
 // v = 0 at the deck and v = 1 at W.top, which is how quad() lays this face out.
 const backRampTex=(()=>{ const R=W.backRamp; if(!R) return null; const H=512, c=document.createElement('canvas');
  c.width=1; c.height=H; const x=c.getContext('2d'), h0=W.floors[1], h1=W.top;
  for(let i=0;i<H;i++){ const h=h1-(i+0.5)/H*(h1-h0); let n=R[0][1];
   for(let k=0;k<R.length-1;k++){ if(h>=R[k][0]&&h<=R[k+1][0]){ const t=(h-R[k][0])/Math.max(R[k+1][0]-R[k][0],1e-6);
     n=R[k][1]+t*(R[k+1][1]-R[k][1]); break; } if(h>R[R.length-1][0]) n=R[R.length-1][1]; if(h<R[0][0]) n=R[0][1]; }
   n=Math.round(Math.max(0,Math.min(255,n))); x.fillStyle='rgb('+n+','+n+','+n+')'; x.fillRect(0,i,1,1); }
  const t=new THREE.CanvasTexture(c); t.colorSpace=THREE.SRGBColorSpace; return t; })();
 if(backRampTex){ topBackMat.map=backRampTex; topBackWestMat.map=backRampTex; }
 const topSoffitMat=dnm(0x13100d,0x332c26,'gallery-soffit');"""),

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
