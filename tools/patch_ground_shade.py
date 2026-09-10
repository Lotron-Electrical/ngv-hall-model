"""THE END GROUND WALL DARKENS TOWARD THE GALLERY OVER IT, AND THE SIM DRAWS IT FLAT (2026-09-10,
tools/ends_audit.py).

Below the galleries the audit reads the west end at 0.34 of the frame's own lit band at h 2.0 falling
to 0.27 at 3.2, 0.26 at 4.0 and 0.12 at 5.2 (183 frames, spreads 0.01 to 0.08); the render is flat at
0.36 to 0.41 across the whole of it. The east reads 0.26 falling to 0.21 against a flat 0.42 to 0.48.
Both ends, one direction, one surface: the stone gets darker as it approaches the soffit of the
gallery standing over it, which is what a wall under a deep overhang does, and the sim has no such
gradient anywhere on it.

WHY A MULTIPLY OVERLAY AND NOT A NEW MATERIAL. The end ground wall is drawn with the shared `stone`
photo material: the scan's own albedo through the recess-mask shader, lit, and it is the surface the
player walks up to. Replacing it with a flat unlit colour to carry a ramp would trade a measured
texture for a measured tone and lose the first. So the ramp is a separate face a few millimetres in
front of it, white where nothing is asked and darker where the photographs are darker, drawn with
MULTIPLY blending and no depth write. The stone underneath is untouched; only the shading over it is
added, which is what was actually missing.

THE NUMBERS ARE THE WEST'S, AND THE RECORD SAYS SO. The two ends disagree on how much: mapped onto the
face plane through each pick's own geometry the west wants 0.81 to 0.64 over h 3.2 to 4.9 and the east
0.75 to 0.46. The west carries 183 frames and the east 23, and the east's own bands scatter (0.18 at
one band between 0.26 and 0.32 at its neighbours), so the ramp is the west's and the east is left to
land where it lands. What it lands on is measured after the render and written down either way.

THE OVERLAY MUST BE TRANSPARENT EVEN THOUGH IT IS OPAQUE, and the first render found that out. Drawn in
the opaque pass with depthWrite off it lands in an arbitrary order against the stone and darkened the
wall by about a tenth even where its texel is 255, which is meant to be the identity. transparent:true
puts it in the pass that runs after every opaque surface, so it multiplies what is already there.
The last texel was corrected once as well: 128 left h 5.0 to 5.2 at 0.26 and 0.24 against 0.16 and 0.12,
so it is 80.

  python tools/patch_ground_shade.py            # apply to index.html
  python tools/patch_ground_shade.py --check     # report only
"""
import io, sys

RAMP = "[[1.40,255],[2.63,235],[3.19,206],[3.74,175],[4.11,172],[4.48,168],[4.85,163],[5.30,80]]"

PAIRS = [
    ("stoneBase:{west:null, east:null}, lowRamp:",
     "stoneBase:{west:null, east:null}, groundShade:" + RAMP + ", lowRamp:"),

    ("""  // the ground's soffit (the lobby ceiling) and back wall""",
     """  // THE SHADE UNDER THE GALLERY (2026-09-10, tools/ends_audit.py). The stone below the galleries is flat in
  // the sim and darkens with height in the hall, at both ends, as it approaches the soffit standing over it:
  // the west reads 0.34 of its own lit band at h 2.0 and 0.12 at 5.2 against a flat rendered 0.36 to 0.41.
  // A face a few millimetres in front of the stone, MULTIPLY blended and not depth written, carries the
  // measured falloff without touching the scan's albedo underneath. The ramp is the west's 183 frames; the
  // east's 23 are left to land where they land, and where they land is recorded.
  if(W.groundShade){ const t=rampTex(W.groundShade,0,W.groundTop);
   const m=new THREE.MeshBasicMaterial({map:t, side:THREE.DoubleSide, blending:THREE.MultiplyBlending, transparent:true, depthWrite:false, name:'end-ground-shade'});
   const uS=uF-s*0.006; quad([[uS,0,0],[uS,D,0],[uS,D,W.groundTop],[uS,0,W.groundTop]],m,'end-ground-shade'); }
  // the ground's soffit (the lobby ceiling) and back wall"""),
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
