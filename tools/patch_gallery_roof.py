# 2026-09-09: the room behind the north wall is roofed by the stained-glass canopy, not by a flat lid.
p = 'index.html'; s = open(p, encoding='utf-8').read(); n = 0
def rep(a, b):
    global s, n
    if b in s: return
    assert s.count(a) == 1, (a[:60], s.count(a)); s = s.replace(a, b); n += 1
rep(" openY:[8.99,11.35], openDepth:0.9, corridor:{width:2.0, floor:8.34, ceil:11.4, lamps:[45.16]},",
    " openY:[8.99,11.35], openDepth:0.9, corridor:{width:2.0, floor:8.34, ceil:13.55, lamps:[45.16]},")
rep("  // the circulation gallery behind the openings (the 1968 second-floor plan): a dark corridor W wide\n"
    "  // past the reveals, its floor the second floor, seen only through the openings\n",
    "  // the gallery behind the openings (the 1968 second-floor plan gives its width; Lloyd's clip 153148\n"
    "  // frames 1040-1330, shot INSIDE it, give the rest): a room W wide past the reveals, its floor the second\n"
    "  // floor, ROOFED BY THE CANOPY. C.ceil is the built canopy's own underside at the north wall face, 13.55\n"
    "  // (tools/canopy-north.mjs samples the dense-cloud canopy: 13.55-13.61 at d 0, dipping to 12.77 at d 3.5\n"
    "  // with the module's fold). It read 11.4 from a lamp seen through an opening, and that same footage shows\n"
    "  // those lamps are spotlights mounted ON the canopy's steel. From the hall this changes nothing: the\n"
    "  // opening's head soffit (11.35) hides everything above it, which is why the roof was never observed.\n"
    "  // The WIDTH is still the plan's 2.0 and still unmeasured; the b6 gallery poses settle it.\n")
open(p, 'w', encoding='utf-8', newline='\n').write(s); print('patched', n)
