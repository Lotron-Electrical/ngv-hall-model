"""WHAT b7_001212 CAN AND CANNOT SAY ABOUT THE REVEAL DEPTH (2026-09-10, after tools/b7_tail_census.py).

The census left 1212 (u 2.96, d 0.61, h 9.05, facing east, refused by the gate) as the seed for a relocalisation
that could read the reveal depth of openings 1 and 2 from close by. Before spending a registration on it, this
asks the geometry what a camera there sees through an opening, and the frame what it shows.

THE GEOMETRY. From u west of an opening, the west jamb's reveal face looks away and only the EAST jamb's reveal
face is seen, through the aperture, and only as deep as the ray grazing the west jamb's hall arris reaches it:
d_vis = d_c - (d_c + 0.03) (u_e - u_c) / (u_w - u_c). Beyond that depth the west jamb hides everything, the
corridor included. For the census pose the visible depth of the east reveal is 0.68 m through opening 1, 0.16
through opening 2 and 0.09 through opening 3; over the pose's own uncertainty (a quarter of a metre) opening
1's figure runs from 0.27 to 1.41 m. So the reveal's corridor arris (0.90 deep as drawn) is in view through
opening 1 only for the upper half of the plausible poses, and through no other opening at all.

THE FRAME. Tone along rows 1200, 1500 and 1800 (median of 50 rows): wall 70 to 98; opening 2's dark slot x 1700
to 1735 (25 to 32); a band x 1740 to 1840 reading 60 to 90, the wall's own tone; opening 1's dark slot x 1850
to 1945 (24 to 38); wall again from 1960. Nothing in that band separates a lit reveal face from the lit wall
face, so the aperture's left boundary (the east jamb's hall arris) cannot be placed by tone, and the dark slot's
width says only where the light stops, not where the stone does.

WHAT FOLLOWS. The reveal depth is not readable from 1212 without (a) a pose good to about 5 cm and (b) the
corridor arris inside the visible depth, and (b) is not assured. Frames whose camera stands closer to the wall's
normal (a smaller d and a larger u, or the hall-floor cameras looking up) are the ones that see the reveal's far
arris; from the deck at u 3 the openings are slots seen edge-on. The relocalisation is not cancelled, but it is
no longer the promised route to openDepth: it would pin ten west-deck poses and nothing more.

Run:
  python tools/oblique_reveal.py
"""
OPENINGS = ((4.098, 5.310), (7.697, 8.911), (11.487, 12.700))
POSES = {'census': (2.96, 0.61), 'nearer, further west': (2.60, 0.30), 'further, further east': (3.30, 0.90)}
ROWS = {1200: {1700: 63, 1720: 62, 1740: 65, 1840: 65, 1860: 38, 1940: 30, 1960: 70},
        1500: {1700: 29, 1720: 25, 1740: 66, 1840: 60, 1860: 33, 1940: 31, 1960: 81},
        1800: {1700: 32, 1720: 31, 1740: 90, 1840: 32, 1860: 29, 1940: 63, 1960: 82}}


def visible_depth(uc, dc, uw, ue):
    return -0.03 - (dc - (dc + 0.03) * (ue - uc) / (uw - uc))


if __name__ == '__main__':
    for name, (uc, dc) in POSES.items():
        print('camera (%.2f, %.2f) %-22s visible depth of the east reveal: %s' % (uc, dc, name, '  '.join('opening %d %.2f m' % (k + 1, visible_depth(uc, dc, uw, ue)) for k, (uw, ue) in enumerate(OPENINGS))))
    for r, prof in ROWS.items():
        print('row %d: %s' % (r, ' '.join('%d:%d' % kv for kv in prof.items())))
    print('the reveal depth is not readable from b7_001212 without a pose to 5 cm, and the far arris is in view only through opening 1 and only for half the plausible poses.')
