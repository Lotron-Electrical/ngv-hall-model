"""The final pane file for the canopy: the traced panes of track B, remapped onto the measured
lattice, plus a matched synthetic infill and the measured motifs where the bake showed nothing.

    python tools/merge_panes.py            (one command, idempotent, ~25 s, ~600 MB peak)

Inputs (track B, E:/sitecapture-captures/ngv-site/agent-ref-ceiling/trackB/): pieces-atlas-merged.json
(2833 traced pieces on the OLD lattice: the core class-4 cells, the clean parts of artefact cells,
and the v29 second-source pieces), class-merged.npy + quality.npy (the 0.5 m cell classes of the
old ortho), bottom-ortho.png (colour samples for the smeared cells). Track C's reference-stats.json
supplies the photo targets and the motif geometry.

Frames.  OLD lattice (every track-B file): PU 7.4285, PV 7.3855, plate corner (-56.635125, 0.158820).
NEW lattice (the GLB's twelve column heads, index.html CANOPY): PU 7.36, PV 7.50, plate corner
(-56.361133, 0.044317), funnel vertices at hu = -45.321133 + i*PU, hv = 3.794317 + j*PV, 7 x 2 bays.
REMAP: every vertex keeps its bay-fractional coordinate, fu = (hu - hu0_old)/PU_old, hu_new =
hu0_new + fu*PU_new (same for v). That is one global affine per axis, so the per-bay warp field track B
fitted rides across unchanged. Board frame of the NGVP file: uu = hu + 58.3053, vv = hv + 0.4556;
the file origin (u0, v0) is the NEW plate corner in board coordinates.

Steel (index.html canopyMaterial paints these from the lattice phase, and this script measures them
with the shader's own formula, steel_dist): the bay ridge dEdge < 0.11 m; the + cross through the
vertex, the main X and the diamond dJ < 0.076 m. The shader's diamond is dDiam = |dm.x + dm.y - PU/2|
* 0.7071 with PU on BOTH axes, which meets the crest and edge ridges 70 mm short of their midpoints
(49 mm perpendicular) - not the true midpoint diamond of the brief's words. By default (DIAMOND
'both', --diamond) the pieces keep clear of both diamonds, so the file is right under the shader as it
is and after the one-line fix that would make it the midpoint diamond. No piece comes closer than
0.12 m to a ridge centre line or 0.085 m to the other lines, vertex- and edge-exact (the bands are cut
at 0.125 / 0.090, the raster gate one pixel wider, and validate() proves the minima): a traced piece
that crosses a band is clipped, one more than half inside a band is dropped.

Rules (the brief, 2026-09-06): 1 traced pieces first (outline_source atlas / atlas-second, colour_source
atlas); 2 every 0.5 m cell the bake could not trace gets synthetic pieces matched to the traced cells
of the same bay (cover, density, size, per m2 of the band-free plan so a cell on a joint holds less),
blended 20 % of the way towards the photographs, laid the way French laid them: rows of 3-6 similar
rectangles along the ribs 100-150 mm off, triangles in the wedges along the diagonals, chips elsewhere,
30-60 mm of matrix between pieces, never overlapping; the piece COUNT is capped too (pooled over 1 m
blocks, motifs excluded, see Budget); 3 the square-ring-with-X emblems at the measured offsets round
every crest node and a radial fan of clear wedges round every funnel vertex, in synthetic cells only;
4 synthetic colours from the bay's own traced palette (area weighted, clear share kept), or the ortho's
own colour in smeared cells; 5 symmetry is measured, never used to fill; 6-7 statistics and validity,
below; 8 idempotent (two runs give byte-identical files).

Fixer's pass (2026-09-07, after the skeptic): the shader-exact steel and the union of the two diamonds;
the 5 mm clearance shortfall (raster gate one pixel wide of the exact band, vertex- and edge-exact
enforcement); targets per band-free m2 with shrinkage pooling for thin bays; the count cap that binds
every non-motif pass (the old +0.5 rounding gave every cell a third piece); honest fan / emblem
accounting; a translated and a shifted symmetry control; vertex-exact validity under both diamonds.
The traced blobs over 450 mm eq were NOT split: by area the photographs hold half their glass in pieces
over 295 mm eq and a tenth over 661 mm (reference-stats, area-weighted p50/p90), so the file (10 % of
its glass over 330 mm, 0.6 % over 661) has fewer big slabs than the ceiling, not more.

Outputs (E:/sitecapture-captures/ngv-site/agent-ref-ceiling/merge/): pieces-merged.bin (NGVP),
pieces-merged.json, coverage.png, colour-source.png, overlay-full.jpg, overlay-colour.jpg,
crop-1/2/3.jpg (2 m windows at 1:1), merge-report.json, pieces-stats.txt.
"""
import argparse
import colorsys
import json
import math
import os
import struct
import subprocess
import sys
import time

import cv2
import numpy as np
from PIL import Image
from shapely import STRtree
from shapely.geometry import LineString, Polygon, box
from shapely.geometry.polygon import orient
from shapely.ops import unary_union

Image.MAX_IMAGE_PIXELS = None

TRACKB = 'E:/sitecapture-captures/ngv-site/agent-ref-ceiling/trackB'
REF_STATS = 'E:/sitecapture-captures/ngv-site/agent-ref-ceiling/reference/reference-stats.json'
OUT_DEFAULT = 'E:/sitecapture-captures/ngv-site/agent-ref-ceiling/merge'
HERE = os.path.dirname(os.path.abspath(__file__))

# ----------------------------------------------------------------------------- the two lattices
OLD = dict(PU=7.4285, PV=7.3855, hu0=-56.635125, hv0=0.158820)
NEW = dict(PU=7.36, PV=7.50, hu0=-56.361133, hv0=0.044317)
NB_U, NB_V = 7, 2
PU, PV = NEW['PU'], NEW['PV']
HU0, HV0 = NEW['hu0'], NEW['hv0']
HU1, HV1 = HU0 + NB_U * PU, HV0 + NB_V * PV
BOARD_DU, BOARD_DV = 58.3053, 0.4556           # uu = hu + BOARD_DU, vv = hv + BOARD_DV (index.html BOARD)
MPP = 0.005                                    # raster pitch (m/px), the ortho's own
CELL = 0.5                                     # bookkeeping cell (m)
W_PX, H_PX = int(round((HU1 - HU0) / MPP)), int(round((HV1 - HV0) / MPP))      # 10304 x 3000
NC, NR = int(math.ceil((HU1 - HU0) / CELL - 1e-9)), int(math.ceil((HV1 - HV0) / CELL - 1e-9))   # 104 x 30
CLEAR_RIDGE, CLEAR_MEMBER = 0.125, 0.090       # keep-clear half-widths from the line centre: the brief's 0.12 / 0.085 + 5 mm
CLEAR_MIN_RIDGE, CLEAR_MIN_MEMBER = 0.12, 0.085   # the brief's minima, held vertex-exact (validate() proves it)
PAINT_RIDGE, PAINT_MEMBER = 0.11, 0.076        # what the shader paints (the 'inside a band' test)
RASTER_GUARD = 0.005                           # the raster gate is one pixel wider than the exact band: a vertex can
                                               # slip up to a pixel past a rasterised edge (the skeptic's 5 mm)
DIAMOND = 'both'                               # the diamond the pieces keep clear of. 'shader': what index.html
                                               # canopyMaterial paints, dDiam = |dm.x + dm.y - PU/2| * 0.7071 with PU on
                                               # BOTH axes, so it meets the crest and edge ridges 70 mm short of their
                                               # midpoints (49 mm perpendicular); 'midpoint': the true line through the
                                               # bay-edge midpoints (the brief's words); 'both': their union, so the file
                                               # is safe under either shader. Set from --diamond.
X_SCALE = (PU * PV / math.hypot(PU, PV)) / (PU * 0.7071)   # the shader measures the X with PU*0.7071: 0.99 x the true
                                                           # perpendicular distance, so its X band is that much wider
GAP_MIN, GAP_MAX = 0.030, 0.060                # matrix between synthetic pieces
GAP_PX = int(round(GAP_MIN / MPP))             # 6 px: the blocked raster grows every piece by this
MIN_EQ_MM, MAX_VERTS = 45.0, 12
BLEND = 0.20                                   # synthetic targets: local + BLEND x (photo - local): 20 % of the way
PHOTO = dict(cover=0.37, density=12.5, eq_p10=110, eq_p50=195, eq_p90=330, aspect_p50=1.45,
             rect=0.53, tri=0.24, irregular=0.23, axis=0.67, diag=0.21)
MIN_PIECES_FOR_LOCAL = 60                      # a bay with fewer traced pieces borrows its neighbours
# HSV lift track B applied to the bake's washed-out colours (trace_pieces.COLOUR_LIFT)
COLOUR_LIFT = dict(white_s_max=0.18, white_s_scale=0.5, white_v=0.96, chroma_s_gain=1.7, chroma_v_gain=1.45)
CLEAR_RGB = (240, 241, 245)
SRC_COL = {'atlas': (40, 230, 60), 'atlas-second': (230, 40, 230), 'synthetic': (60, 160, 255), 'motif': (255, 210, 40)}
CSRC_COL = {'atlas': (40, 230, 60), 'atlas-neighbour': (40, 200, 200), 'bay-palette': (60, 120, 255), 'motif': (255, 210, 40)}


def log(*a):
    print(time.strftime('%H:%M:%S'), *a, flush=True)


# ----------------------------------------------------------------------------- frames
def remap(hu, hv):
    """OLD-lattice huv -> NEW-lattice huv (bay-fractional coordinates kept)."""
    return (HU0 + (np.asarray(hu) - OLD['hu0']) * (PU / OLD['PU']),
            HV0 + (np.asarray(hv) - OLD['hv0']) * (PV / OLD['PV']))


def unmap(hu, hv):
    """NEW -> OLD huv (for sampling the bottom ortho)."""
    return (OLD['hu0'] + (np.asarray(hu) - HU0) * (OLD['PU'] / PU),
            OLD['hv0'] + (np.asarray(hv) - HV0) * (OLD['PV'] / PV))


def frac(hu, hv, L):
    return (np.asarray(hu) - L['hu0']) / L['PU'], (np.asarray(hv) - L['hv0']) / L['PV']


def bay_of(hu, hv):
    return (int(min(NB_U - 1, max(0, (hu - HU0) // PU))), int(min(NB_V - 1, max(0, (hv - HV0) // PV))))


def cell_of(hu, hv):
    return (int(min(NC - 1, max(0, (hu - HU0) // CELL))), int(min(NR - 1, max(0, (hv - HV0) // CELL))))


def vertex(i, j):
    return HU0 + (i + 0.5) * PU, HV0 + (j + 0.5) * PV


def to_px(pts):
    """huv (k,2) -> raster pixel-centre coordinates (float)."""
    return np.stack([(pts[:, 0] - HU0) / MPP - 0.5, (pts[:, 1] - HV0) / MPP - 0.5], axis=1)


def steel_dist(hu, hv):
    """Distances (m) from points to the steel lines exactly as index.html canopyMaterial measures them on the
    NEW lattice (lat.xy = the funnel-vertex phase, lat.zw = PU, PV): dCross, dDiag (the shader's metric, PU*0.7071
    per unit of bay fraction, 0.99 x the true perpendicular distance), dDiam of the shader (dm.x + dm.y = PU/2),
    the true midpoint diamond (dm.x/(PU/2) + dm.y/(PV/2) = 1, perpendicular), and dEdge (the ridge)."""
    hu = np.asarray(hu, np.float64); hv = np.asarray(hv, np.float64)
    ou, ov = vertex(0, 0)
    qx = (hu - ou) / PU; qy = (hv - ov) / PV
    fx = qx - np.floor(qx + 0.5); fy = qy - np.floor(qy + 0.5)
    dmx = np.abs(fx) * PU; dmy = np.abs(fy) * PV
    cross = np.minimum(dmx, dmy)
    diag = np.minimum(np.abs(fx - fy), np.abs(fx + fy)) * PU * 0.7071
    diam_s = np.abs(dmx + dmy - PU * 0.5) * 0.7071
    diam_m = np.abs(dmx / (PU / 2) + dmy / (PV / 2) - 1.0) / math.sqrt((2.0 / PU) ** 2 + (2.0 / PV) ** 2)
    edge = np.minimum(PU * 0.5 - dmx, PV * 0.5 - dmy)
    return cross, diag, diam_s, diam_m, edge


def member_clearance(pts, diamond=None):
    """(min member distance, min ridge distance) over the vertices of a polygon, the shader's metrics; the
    member distance takes the diamond(s) DIAMOND names."""
    diamond = DIAMOND if diamond is None else diamond
    cross, diag, diam_s, diam_m, edge = steel_dist(pts[:, 0], pts[:, 1])
    m = np.minimum(cross, diag)
    if diamond in ('shader', 'both'):
        m = np.minimum(m, diam_s)
    if diamond in ('midpoint', 'both'):
        m = np.minimum(m, diam_m)
    return float(m.min()), float(edge.min())


def paint_masks(ridge=PAINT_RIDGE, member=PAINT_MEMBER):
    """Two 5 mm masks of the steel index.html paints, from its own formula at the pixel centres: with the
    shader's diamond (what the viewer draws today) and with the midpoint diamond; cross, X and ridge are the
    shader's exactly. Row-chunked (the full distance fields would be 600 MB)."""
    ps = np.zeros((H_PX, W_PX), np.uint8); pm = np.zeros((H_PX, W_PX), np.uint8)
    xs = HU0 + (np.arange(W_PX) + 0.5) * MPP
    for y0 in range(0, H_PX, 200):
        y1 = min(H_PX, y0 + 200)
        ys = HV0 + (np.arange(y0, y1) + 0.5) * MPP
        hu, hv = np.meshgrid(xs, ys)
        cross, diag, diam_s, diam_m, edge = steel_dist(hu, hv)
        base = (np.minimum(cross, diag) < member) | (edge < ridge)
        ps[y0:y1] = base | (diam_s < member); pm[y0:y1] = base | (diam_m < member)
    return ps, pm


# ----------------------------------------------------------------------------- polygons
def shoelace(p):
    x, y = p[:, 0], p[:, 1]
    return 0.5 * float(np.dot(x, np.roll(y, -1)) - np.dot(y, np.roll(x, -1)))


def ccw(p):
    return p if shoelace(p) > 0 else p[::-1].copy()


def is_convex(p, tol=1e-9):
    n = len(p)
    sgn = 0
    for i in range(n):
        a, b, c = p[i], p[(i + 1) % n], p[(i + 2) % n]
        cr = (b[0] - a[0]) * (c[1] - b[1]) - (b[1] - a[1]) * (c[0] - b[0])
        if abs(cr) < tol:
            continue
        s = 1 if cr > 0 else -1
        if sgn == 0:
            sgn = s
        elif s != sgn:
            return False
    return True


def tidy(geom, eps=0.004):
    """shapely (Multi)Polygon -> convex CCW numpy polygon with 3..MAX_VERTS vertices, or None.
    The largest part is kept; it is simplified, then its convex hull is taken (the viewer
    fan-triangulates every pane, so only convex outlines are safe)."""
    if geom is None or geom.is_empty:
        return None
    if geom.geom_type == 'MultiPolygon' or geom.geom_type == 'GeometryCollection':
        parts = [g for g in geom.geoms if g.geom_type == 'Polygon' and g.area > 0]
        if not parts:
            return None
        geom = max(parts, key=lambda g: g.area)
    if geom.geom_type != 'Polygon' or geom.area <= 0:
        return None
    hull = geom.convex_hull
    if hull.geom_type != 'Polygon':
        return None
    e = eps
    for _ in range(8):
        s = hull.simplify(e, preserve_topology=True)
        pts = np.array(s.exterior.coords)[:-1]
        if 3 <= len(pts) <= MAX_VERTS:
            pts = np.array(Polygon(pts).convex_hull.exterior.coords)[:-1]
            if 3 <= len(pts) <= MAX_VERTS:
                return ccw(pts)
        e *= 1.5
    return None


def rect_poly(cx, cy, w, h, ang):
    c, s = math.cos(ang), math.sin(ang)
    loc = np.array([[-w / 2, -h / 2], [w / 2, -h / 2], [w / 2, h / 2], [-w / 2, h / 2]])
    return ccw(np.stack([cx + loc[:, 0] * c - loc[:, 1] * s, cy + loc[:, 0] * s + loc[:, 1] * c], axis=1))


def tri_poly(cx, cy, base, height, ang, right=False, flip=1):
    """Isoceles (or right-angled) triangle, base along `ang`, apex on the +normal side."""
    if right:
        loc = np.array([[-base / 2, -height / 3], [base / 2, -height / 3], [base / 2, 2 * height / 3]])
    else:
        loc = np.array([[-base / 2, -height / 3], [base / 2, -height / 3], [0, 2 * height / 3]])
    loc[:, 1] *= flip
    c, s = math.cos(ang), math.sin(ang)
    return ccw(np.stack([cx + loc[:, 0] * c - loc[:, 1] * s, cy + loc[:, 0] * s + loc[:, 1] * c], axis=1))


def chip_poly(cx, cy, area, aspect, ang, rng):
    """Irregular convex chip: 5-7 points on a jittered ellipse, convex hull, scaled to `area`."""
    n = int(rng.integers(5, 8))
    th = np.sort(rng.uniform(0, 2 * math.pi, n))
    a = math.sqrt(aspect); b = 1 / a
    rad = rng.uniform(0.82, 1.18, n)
    loc = np.stack([a * rad * np.cos(th), b * rad * np.sin(th)], axis=1)
    hull = cv2.convexHull(loc.astype(np.float32)).reshape(-1, 2).astype(np.float64)
    if len(hull) < 3:
        return None
    A = abs(shoelace(hull))
    if A <= 0:
        return None
    hull *= math.sqrt(area / A)
    c, s = math.cos(ang), math.sin(ang)
    return ccw(np.stack([cx + hull[:, 0] * c - hull[:, 1] * s, cy + hull[:, 0] * s + hull[:, 1] * c], axis=1))


# ----------------------------------------------------------------------------- colours
def lift_colour(rgb, L=COLOUR_LIFT):
    r, g, b = [c / 255.0 for c in rgb]
    h, s, v = colorsys.rgb_to_hsv(r, g, b)
    if s < L['white_s_max']:
        s2 = s * L['white_s_scale']; v2 = max(v, L['white_v'])
    else:
        s2 = min(1.0, s * L['chroma_s_gain']); v2 = min(1.0, v * L['chroma_v_gain'])
    r2, g2, b2 = colorsys.hsv_to_rgb(h, s2, v2)
    return (int(round(r2 * 255)), int(round(g2 * 255)), int(round(b2 * 255)))


def is_clear(rgb):
    return colorsys.rgb_to_hsv(*[c / 255.0 for c in rgb])[1] < 0.18


def jitter_colour(rgb, rng, dh=0.015, dv=0.06):
    h, s, v = colorsys.rgb_to_hsv(*[c / 255.0 for c in rgb])
    if s >= 0.18:
        h = (h + rng.uniform(-dh, dh)) % 1.0
    v = min(1.0, max(0.3, v * rng.uniform(1 - dv, 1 + dv)))
    r, g, b = colorsys.hsv_to_rgb(h, s, v)
    return (int(round(r * 255)), int(round(g * 255)), int(round(b * 255)))


# the motif palette (track C, close-up 2 family medians, the least clipped source; lifted the way the
# traced colours were so the emblems sit in the same colour space as the pieces round them)
FAMILY_RGB = dict(red=(195, 55, 42), orange=(198, 102, 57), amber=(231, 172, 86), yellow=(244, 230, 106),
                  green=(104, 173, 82), cyan=(128, 214, 242), blue=(66, 108, 184), violet=(132, 40, 205),
                  magenta=(170, 53, 124), lilac=(180, 150, 235), pink=(200, 140, 150), peach=(240, 170, 138),
                  white=(245, 243, 241))
FAMILY_LIFTED = {k: lift_colour(v) for k, v in FAMILY_RGB.items()}
FAMILY_LIFTED['white'] = CLEAR_RGB
# ring colours of 16 measured emblems: red/orange 4, blue/cyan 3, lilac/violet 4, pink/peach 3, white 1
RING_FAMILIES = [('red', 'orange', 'lilac'), ('red', 'orange', 'lilac'), ('red', 'orange', 'white'), ('orange', 'red', 'lilac'),
                 ('blue', 'cyan', 'magenta'), ('cyan', 'blue', 'magenta'), ('blue', 'cyan', 'white'),
                 ('violet', 'lilac', 'white'), ('lilac', 'violet', 'pink'), ('violet', 'lilac', 'peach'), ('lilac', 'violet', 'white'),
                 ('pink', 'peach', 'lilac'), ('peach', 'pink', 'white'), ('pink', 'peach', 'white'),
                 ('white', 'white', 'lilac'), ('white', 'white', 'blue')]


# ----------------------------------------------------------------------------- the steel
def bay_lines(i, j, diamond=None):
    """(p0, p1, kind) of the steel lines of bay (i, j): 'ridge' (bay edge), 'cross', 'X', 'diamond' (through
    the bay-edge midpoints) and 'diamond-shader' (index.html's dm.x + dm.y = PU/2: from the vertical-ridge
    midpoint to a point PU/2, not PV/2, up the cross arm; extended 0.12 m past both ends, the extensions lie
    inside the ridge and cross bands, and band_geoms clips them to the bay)."""
    diamond = DIAMOND if diamond is None else diamond
    cu, cv = vertex(i, j)
    u0, v0, u1, v1 = cu - PU / 2, cv - PV / 2, cu + PU / 2, cv + PV / 2
    L = [((u0, v0), (u1, v0), 'ridge'), ((u1, v0), (u1, v1), 'ridge'), ((u1, v1), (u0, v1), 'ridge'), ((u0, v1), (u0, v0), 'ridge'),
         ((cu, v0), (cu, v1), 'cross'), ((u0, cv), (u1, cv), 'cross'),
         ((u0, v0), (u1, v1), 'X'), ((u0, v1), (u1, v0), 'X')]
    if diamond in ('midpoint', 'both'):
        L += [((cu, v0), (u1, cv), 'diamond'), ((u1, cv), (cu, v1), 'diamond'), ((cu, v1), (u0, cv), 'diamond'), ((u0, cv), (cu, v0), 'diamond')]
    if diamond in ('shader', 'both'):
        ext = 0.12 / math.sqrt(2)
        for sx in (-1, 1):
            for sy in (-1, 1):
                a = (cu + sx * (PU / 2 + ext), cv - sy * ext); b = (cu - sx * ext, cv + sy * (PU / 2 + ext))
                L.append((a, b, 'diamond-shader'))
    return L


def band_geoms(clear_ridge=CLEAR_RIDGE, clear_member=CLEAR_MEMBER, diamond=None):
    """Union of the keep-clear bands of every bay as one shapely geometry (+ per-bay list). The X band is
    X_SCALE wider (the shader's metric); the shader-diamond band is clipped to its bay."""
    per_bay = {}
    for i in range(NB_U):
        for j in range(NB_V):
            cu, cv = vertex(i, j)
            bay_box = box(cu - PU / 2, cv - PV / 2, cu + PU / 2, cv + PV / 2)
            polys = []
            for p0, p1, kind in bay_lines(i, j, diamond):
                w = clear_ridge if kind == 'ridge' else clear_member * (X_SCALE if kind == 'X' else 1.0)
                g = LineString([p0, p1]).buffer(w, cap_style='flat', join_style='mitre')
                if kind == 'diamond-shader':
                    g = g.intersection(bay_box)
                polys.append(g)
            per_bay[(i, j)] = unary_union(polys)
    outer = box(HU0 - 1, HV0 - 1, HU1 + 1, HV1 + 1).difference(box(HU0, HV0, HU1, HV1))
    return unary_union(list(per_bay.values()) + [outer]), per_bay


def rasterise_geom(geom, raster, value=1):
    polys = [geom] if geom.geom_type == 'Polygon' else list(geom.geoms)
    for g in polys:
        if g.geom_type != 'Polygon':
            continue
        ext = to_px(np.array(g.exterior.coords))
        cv2.fillPoly(raster, [np.round(ext * 8).astype(np.int32)], value, lineType=cv2.LINE_8, shift=3)
        for ring in g.interiors:
            pts = to_px(np.array(ring.coords))
            cv2.fillPoly(raster, [np.round(pts * 8).astype(np.int32)], 0, lineType=cv2.LINE_8, shift=3)
    return raster


def triangles_of_bay(i, j):
    """The 16 triangles of bay (i, j): each sub-square (quadrant) cut by the main X and the diamond.
    Returns list of (pts(3,2), kinds[3]) with kinds per edge (edge k = pts[k] -> pts[k+1]):
    'ridge', 'cross', 'X', 'diamond'. The diamond edge of the two outer triangles (touching the ridges)
    is the midpoint diamond, that of the two inner ones (touching the cross) is the shader's, so with
    DIAMOND 'both' every row and wedge is laid off the union band's own edge."""
    cu, cv = vertex(i, j)
    tris = []
    t = PU / (PU + PV)                           # where the shader's diamond crosses the X
    for sx in (-1, 1):
        for sy in (-1, 1):
            N = (cu + sx * PU / 2, cv + sy * PV / 2)     # crest node (bay corner)
            Mu = (cu + sx * PU / 2, cv)                  # midpoint of the vertical ridge (hu = const)
            Mv = (cu, cv + sy * PV / 2)                  # midpoint of the horizontal ridge (hv = const)
            V = (cu, cv)                                 # funnel vertex
            C = ((N[0] + V[0]) / 2, (N[1] + V[1]) / 2)   # sub-square centre
            Mv_s = (cu, cv + sy * PU / 2); C_s = (cu + sx * t * PU / 2, cv + sy * t * PV / 2)
            oMv, oC = (Mv_s, C_s) if DIAMOND == 'shader' else (Mv, C)
            iMv, iC = (Mv, C) if DIAMOND == 'midpoint' else (Mv_s, C_s)
            tris.append((np.array([N, oMv, oC]), ['ridge', 'diamond', 'X']))       # touches the horizontal ridge
            tris.append((np.array([N, oC, Mu]), ['X', 'diamond', 'ridge']))       # touches the vertical ridge
            tris.append((np.array([Mu, iC, V]), ['diamond', 'X', 'cross']))       # touches the horizontal cross arm
            tris.append((np.array([iMv, V, iC]), ['cross', 'X', 'diamond']))      # touches the vertical cross arm
    return tris


# ----------------------------------------------------------------------------- the raster
class Raster:
    """5 mm rasters over the NEW plate: glass occupancy, the blocked mask (the keep-clear bands one pixel
    wide of the exact geometry + glass grown by the minimum matrix gap) and the two paint masks (what the
    shader draws as steel, with its own diamond and with the midpoint one)."""

    def __init__(self, bands_gate):
        self.occ = np.zeros((H_PX, W_PX), np.uint8)
        self.blocked = np.zeros((H_PX, W_PX), np.uint8)
        rasterise_geom(bands_gate, self.blocked)
        self.bands = self.blocked.copy()
        # what the shader paints, from its own formula at the pixel centres: paint = its diamond (what the
        # viewer draws), paint_mid = the midpoint diamond (what it would draw after the one-line fix)
        self.paint, self.paint_mid = paint_masks()
        self.kern = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (2 * GAP_PX + 1, 2 * GAP_PX + 1))
        # distance (px) from the keep-clear bands: the first chip pass keeps out of the strips along
        # the ribs so the rows of rectangles can have them
        self.ribdist = cv2.distanceTransform((self.bands == 0).astype(np.uint8), cv2.DIST_L2, 3).astype(np.uint16)

    def window(self, pts, pad):
        px = to_px(pts)
        x0 = int(math.floor(px[:, 0].min())) - pad; x1 = int(math.ceil(px[:, 0].max())) + pad + 1
        y0 = int(math.floor(px[:, 1].min())) - pad; y1 = int(math.ceil(px[:, 1].max())) + pad + 1
        if x0 < 0 or y0 < 0 or x1 > W_PX or y1 > H_PX:
            return None
        loc = np.zeros((y1 - y0, x1 - x0), np.uint8)
        cv2.fillPoly(loc, [np.round((px - [x0, y0]) * 8).astype(np.int32)], 1, lineType=cv2.LINE_8, shift=3)
        return x0, y0, x1, y1, loc

    def free(self, pts):
        """True when the piece touches neither a band nor a grown neighbour."""
        w = self.window(pts, 1)
        if w is None:
            return False
        x0, y0, x1, y1, loc = w
        return not (loc & self.blocked[y0:y1, x0:x1]).any()

    def band_share(self, pts, paint=False):
        w = self.window(pts, 1)
        if w is None:
            return 1.0
        x0, y0, x1, y1, loc = w
        a = loc.sum()
        m = self.paint if paint else self.bands
        return float((loc & m[y0:y1, x0:x1]).sum()) / max(1, a)

    def occupy(self, pts):
        w = self.window(pts, GAP_PX + 1)
        if w is None:
            return
        x0, y0, x1, y1, loc = w
        self.occ[y0:y1, x0:x1] |= loc
        self.blocked[y0:y1, x0:x1] |= cv2.dilate(loc, self.kern)

    def overlap_share(self, pts):
        """Share of the piece already occupied (no gap)."""
        w = self.window(pts, 1)
        if w is None:
            return 1.0
        x0, y0, x1, y1, loc = w
        return float((loc & self.occ[y0:y1, x0:x1]).sum()) / max(1, loc.sum())


# ----------------------------------------------------------------------------- pieces
class Piece:
    __slots__ = ('pts', 'rgb', 'csrc', 'osrc', 'bay', 'cell', 'area', 'eq_mm', 'flags', 'raw_rgb', 'motif')

    def __init__(self, pts, rgb, csrc, osrc, flags=None, raw_rgb=None, motif=None):
        self.pts = ccw(np.asarray(pts, np.float64))
        self.rgb = tuple(int(c) for c in rgb)
        self.csrc, self.osrc = csrc, osrc
        self.flags = list(flags or [])
        self.raw_rgb = raw_rgb
        self.motif = motif
        self.update()

    def update(self):
        self.area = abs(shoelace(self.pts))
        self.eq_mm = 2 * math.sqrt(self.area / math.pi) * 1000
        c = self.pts.mean(axis=0)
        self.bay = bay_of(c[0], c[1])
        self.cell = cell_of(c[0], c[1])

    def poly(self):
        return Polygon(self.pts)

    def centroid(self):
        p = self.pts; k = len(p)
        A = 0; cu = 0; cv = 0
        for i in range(k):
            x1, y1 = p[i]; x2, y2 = p[(i + 1) % k]
            w = x1 * y2 - x2 * y1
            A += w; cu += (x1 + x2) * w; cv += (y1 + y2) * w
        A *= 0.5
        return (cu / (6 * A), cv / (6 * A)) if abs(A) > 1e-12 else tuple(p.mean(axis=0))


# ----------------------------------------------------------------------------- 1. the traced pieces
def load_traced():
    d = json.load(open(os.path.join(TRACKB, 'pieces-atlas-merged.json')))
    out = []
    for n, p in enumerate(d['pieces']):
        hu, hv = remap(p['hu'], p['hv'])
        flags = ['old_class_%d' % p['cell_class']]
        if p.get('clipped'):
            flags.append('clipped_old')
        if p.get('big'):
            flags.append('big')
        pc = Piece(np.stack([hu, hv], axis=1), p['rgb'], 'atlas', 'atlas-second' if p.get('from_second') else 'atlas',
                   flags, raw_rgb=tuple(p['raw_rgb']))
        pc.flags.append('trackB_%d' % n)
        out.append(pc)
    return out, d


def clip_to_bands(pieces, band_tree, band_polys, log_counts):
    """Re-check every traced piece against the NEW bands: > 50 % inside -> dropped, otherwise the
    band is cut out and the largest remainder kept (convex hull, so it stays fan-safe)."""
    kept = []
    for pc in pieces:
        poly = pc.poly()
        idx = band_tree.query(poly)
        hit = [band_polys[k] for k in idx if band_polys[k].intersects(poly)]
        if not hit:
            kept.append(pc)
            continue
        inter = sum(poly.intersection(b).area for b in hit)
        if inter > 0.5 * poly.area:
            log_counts['band_drop'] += 1
            continue
        if inter <= 1e-7:
            kept.append(pc)
            continue
        band_u = unary_union(hit)
        pts = tidy(poly.difference(band_u))
        if pts is None:
            log_counts['band_drop'] += 1
            continue
        # the hull of the remainder may creep back over the band (a corner of the union): shave until the
        # remainder is clear of the band AND every vertex holds the brief's minimum
        for k in range(4):
            p2 = Polygon(pts)
            mm, me = member_clearance(pts)
            if p2.intersection(band_u).area <= 1e-9 and mm >= CLEAR_MIN_MEMBER and me >= CLEAR_MIN_RIDGE:
                break
            pts = tidy(p2.difference(band_u.buffer(0.003 * (k + 1))))
            if pts is None:
                break
        if pts is None:
            log_counts['band_drop'] += 1
            continue
        mm, me = member_clearance(pts)
        if mm < CLEAR_MIN_MEMBER or me < CLEAR_MIN_RIDGE:
            log_counts['band_drop'] += 1
            continue
        if 2 * math.sqrt(abs(shoelace(pts)) / math.pi) * 1000 < MIN_EQ_MM:
            log_counts['band_drop_small'] += 1
            continue
        pc.pts = ccw(pts); pc.update(); pc.flags.append('clipped_new')
        log_counts['band_clip'] += 1
        kept.append(pc)
    return kept


def resolve_overlaps(pieces, log_counts, tol=0.01):
    """Traced pieces may overlap (second-source pieces were admitted up to 15 %, hulls of touching
    blobs overlap by slivers). In order, every piece is cut back from the ones already accepted;
    a piece that would lose more than half its area, or whose remainder is too small, is dropped."""
    accepted = []
    polys = []
    grid = {}                                  # 0.5 m spatial hash of the accepted polygons

    def keys_of(pts):
        c0, r0 = cell_of(pts[:, 0].min(), pts[:, 1].min()); c1, r1 = cell_of(pts[:, 0].max(), pts[:, 1].max())
        return [(c, r) for c in range(c0, c1 + 1) for r in range(r0, r1 + 1)]
    for n, pc in enumerate(pieces):
        poly = pc.poly()
        cand = set()
        for k in keys_of(pc.pts):
            cand.update(grid.get(k, ()))
        # neighbours closer than a pixel count too: two outlines sharing an edge both claim the
        # boundary pixels of a 5 mm raster, so every traced piece keeps 6 mm from the next
        hit = [polys[k] for k in cand if polys[k].distance(poly) < 0.005]
        if hit:
            inter = sum(poly.intersection(h).area for h in hit)
            if True:                           # touching or overlapping: both are cut back
                if inter > 0.5 * poly.area:
                    log_counts['overlap_drop'] += 1
                    continue
                rem = poly.difference(unary_union(hit).buffer(0.006, join_style='mitre'))
                pts = tidy(rem)
                if pts is None or 2 * math.sqrt(abs(shoelace(pts)) / math.pi) * 1000 < MIN_EQ_MM:
                    log_counts['overlap_drop'] += 1
                    continue
                p2 = Polygon(pts)
                if any(p2.distance(h) < 0.004 for h in hit):
                    # the hull of the remainder crept back: shave once more, then shrink the whole
                    # piece a few millimetres (a convex piece eroded stays convex), then give up
                    pts = tidy(p2.difference(unary_union(hit).buffer(0.009, join_style='mitre')))
                    p2 = Polygon(pts) if pts is not None else None
                    if p2 is None or any(p2.distance(h) < 0.004 for h in hit):
                        pts = tidy(poly.buffer(-0.006, join_style='mitre'))
                        p2 = Polygon(pts) if pts is not None else None
                        if p2 is None or any(p2.distance(h) < 0.004 for h in hit) or 2 * math.sqrt(p2.area / math.pi) * 1000 < MIN_EQ_MM:
                            log_counts['overlap_drop'] += 1
                            continue
                    if 2 * math.sqrt(p2.area / math.pi) * 1000 < MIN_EQ_MM:
                        log_counts['overlap_drop'] += 1
                        continue
                pc.pts = ccw(pts); pc.update()
                if inter > 1e-7:
                    pc.flags.append('overlap_clip'); log_counts['overlap_clip'] += 1
                else:
                    pc.flags.append('gap_clip'); log_counts['gap_clip'] += 1
                poly = p2
        accepted.append(pc); polys.append(poly)
        for k in keys_of(pc.pts):
            grid.setdefault(k, []).append(len(polys) - 1)
    return accepted


def finalise(pts):
    """Quantise a polygon to the file's millimetre grid and keep it strictly convex there: after
    rounding, a near-collinear vertex can turn concave by a hair, and the viewer's bevel ring then
    folds. Vertices with a non-positive turn are dropped until every turn is left-handed."""
    q = np.round(pts, 3)
    for _ in range(MAX_VERTS):
        n = len(q)
        if n < 3:
            return None
        keep = np.ones(n, bool)
        for i in range(n):
            a, b, c = q[i - 1], q[i], q[(i + 1) % n]
            cr = (b[0] - a[0]) * (c[1] - b[1]) - (b[1] - a[1]) * (c[0] - b[0])
            if cr <= 1e-9:
                keep[i] = False
                break                          # one at a time: the neighbours' turns change
        if keep.all():
            break
        q = q[keep]
    if len(q) < 3 or abs(shoelace(q)) < 1e-6:
        return None
    # a duplicate vertex after rounding
    d = np.hypot(*(np.roll(q, -1, axis=0) - q).T)
    if (d < 5e-4).any():
        q = q[d >= 5e-4]
        return finalise(q) if len(q) >= 3 else None
    return ccw(q)


# ----------------------------------------------------------------------------- 2. cells
def old_class_grid():
    """Old class per NEW cell (the cell centre mapped back to the old lattice), plus the old
    quality layers the colour sampler needs (bg = matrix level)."""
    cm = np.load(os.path.join(TRACKB, 'class-merged.npy'))
    q = np.load(os.path.join(TRACKB, 'quality.npy'))
    cls = np.zeros((NR, NC), np.uint8)
    bg = np.zeros((NR, NC), np.float32)
    for r in range(NR):
        for c in range(NC):
            hu, hv = HU0 + (c + 0.5) * CELL, HV0 + (r + 0.5) * CELL
            ho, vo = unmap(hu, hv)
            oc = int((ho - OLD['hu0']) // CELL); orow = int((vo - OLD['hv0']) // CELL)
            if 0 <= oc < cm.shape[1] and 0 <= orow < cm.shape[0]:
                cls[r, c] = cm[orow, oc]; bg[r, c] = q[5, orow, oc]
    return cls, bg


def cell_status(traced, cls, raster):
    """Per NEW cell: 'atlas' / 'atlas-second' (a class-4 cell holding traced pieces), 'synthetic'
    (everything else: no trace, or only the sparse artefact-cell recovery), plus the share of the
    cell outside the keep-clear bands (free) and the traced count/area per cell."""
    cnt = np.zeros((NR, NC), int); cnt2 = np.zeros((NR, NC), int); area = np.zeros((NR, NC))
    for pc in traced:
        c, r = pc.cell
        cnt[r, c] += 1; area[r, c] += pc.area
        if pc.osrc == 'atlas-second':
            cnt2[r, c] += 1
    free = np.zeros((NR, NC), np.float32)
    band = raster.bands
    for r in range(NR):
        y0, y1 = int(r * CELL / MPP), int(min(H_PX, (r + 1) * CELL / MPP))
        for c in range(NC):
            x0, x1 = int(c * CELL / MPP), int(min(W_PX, (c + 1) * CELL / MPP))
            sub = band[y0:y1, x0:x1]
            free[r, c] = 1.0 - sub.mean() if sub.size else 0.0
    status = np.full((NR, NC), 2, np.uint8)      # 0 atlas, 1 atlas-second, 2 synthetic
    for r in range(NR):
        for c in range(NC):
            if cls[r, c] == 4 and (cnt[r, c] > 0 or free[r, c] < 0.35):
                status[r, c] = 1 if cnt2[r, c] > cnt[r, c] / 2 else 0
    return status, free, cnt, area


# ----------------------------------------------------------------------------- 3. targets, palettes
def shape_stats(pts):
    """(aspect, shape class, orientation class) the way track C measured lf02 pieces: minAreaRect
    fill and vertex count -> rect / tri / irregular; long-axis angle mod 90 -> axis / diag / other."""
    P = pts.astype(np.float32)
    (cx, cy), (w, h), ang = cv2.minAreaRect(P)
    if min(w, h) <= 1e-6:
        return 1.0, 'irregular', 'other'
    area = abs(shoelace(pts))
    fill = area / (w * h)
    aspect = max(w, h) / min(w, h)
    k = len(cv2.approxPolyDP(P.reshape(-1, 1, 2), 0.012, True))
    if k == 3 or (fill < 0.62 and k <= 4):
        shape = 'tri'
    elif fill > 0.80 and k == 4:
        shape = 'rect'
    else:
        shape = 'irregular'
    if aspect < 1.15:
        ori = 'round'
    else:
        a = ang if w >= h else ang + 90
        a = a % 90
        d0 = min(a, 90 - a)
        if d0 <= 12:
            ori = 'axis'
        elif abs(a - 45) <= 12:
            ori = 'diag'
        else:
            ori = 'other'
    return aspect, shape, ori


def subset_stats(pieces, plan_m2, free_m2=None):
    n = len(pieces)
    if n == 0:
        return dict(n=0, n_motif=0, glass_m2=0.0, plan_m2=plan_m2, free_m2=free_m2, cover=0.0, cover_free=0.0, density=0.0, density_nonmotif=0.0)
    areas = np.array([p.area for p in pieces]); eq = np.array([p.eq_mm for p in pieces])
    sh = [shape_stats(p.pts) for p in pieces]
    asp = np.array([s[0] for s in sh])
    shapes = [s[1] for s in sh]; oris = [s[2] for s in sh]
    nel = sum(1 for o in oris if o != 'round')
    clear = np.array([is_clear(p.rgb) for p in pieces])
    n_motif = sum(1 for p in pieces if p.osrc == 'motif')
    eq_nm = np.array([p.eq_mm for p in pieces if p.osrc != 'motif']) if n > n_motif else eq
    return dict(n=n, n_motif=n_motif, glass_m2=float(areas.sum()), plan_m2=plan_m2, free_m2=free_m2,
                eq_nonmotif_p10_p50_p90=[float(np.percentile(eq_nm, q)) for q in (10, 50, 90)],
                cover=float(areas.sum() / plan_m2) if plan_m2 else 0.0,
                cover_free=float(areas.sum() / free_m2) if free_m2 else 0.0,
                density=float(n / plan_m2) if plan_m2 else 0.0, density_nonmotif=float((n - n_motif) / plan_m2) if plan_m2 else 0.0,
                eq_p10=float(np.percentile(eq, 10)), eq_p50=float(np.percentile(eq, 50)), eq_p90=float(np.percentile(eq, 90)),
                aspect_p50=float(np.median(asp)),
                rect=shapes.count('rect') / n, tri=shapes.count('tri') / n, irregular=shapes.count('irregular') / n,
                axis=oris.count('axis') / max(1, nel), diag=oris.count('diag') / max(1, nel), n_elongated=nel,
                clear_n=float(clear.mean()), clear_area=float(areas[clear].sum() / areas.sum()))


def bay_targets(traced, status, free):
    """Per bay: the traced cells' cover and density (per m2 of plan and per m2 of the glazed, band-free
    plan), pooled by shrinkage with the neighbours when the bay is thin (weight n / (n + 60)), and the
    synthetic targets = local + BLEND x (photo - local), expressed per m2 of glazed plan so a cell on a joint
    holds less and a free cell more, with the bay's own eq samples and palette."""
    by_bay = {}
    for i in range(NB_U):
        for j in range(NB_V):
            cells = [(r, c) for r in range(NR) for c in range(NC)
                     if bay_of(HU0 + (c + 0.5) * CELL, HV0 + (r + 0.5) * CELL) == (i, j)]
            tcells = [(r, c) for (r, c) in cells if status[r, c] < 2]
            ps = [p for p in traced if p.bay == (i, j) and status[p.cell[1], p.cell[0]] < 2]
            by_bay[(i, j)] = dict(cells=cells, tcells=tcells, pieces=ps)

    def est(ps, tc):
        plan = len(tc) * CELL * CELL
        fa = sum(float(free[r, c]) for (r, c) in tc) * CELL * CELL
        if plan <= 0 or fa <= 0 or not ps:
            return None
        return dict(cover=sum(p.area for p in ps) / plan, density=len(ps) / plan, fr=fa / plan)
    targets = {}
    for (i, j), d in by_bay.items():
        loc = est(d['pieces'], d['tcells']); n_loc = len(d['pieces'])
        ps, tc = list(d['pieces']), list(d['tcells'])
        pooled = [(i, j)]
        if n_loc < MIN_PIECES_FOR_LOCAL or len(tc) < 20:
            for di in (-1, 1):
                if 0 <= i + di < NB_U:
                    ps += by_bay[(i + di, j)]['pieces']; tc += by_bay[(i + di, j)]['tcells']; pooled.append((i + di, j))
        if len(ps) < MIN_PIECES_FOR_LOCAL:
            ps = [p for b in by_bay.values() for p in b['pieces']]; tc = [c for b in by_bay.values() for c in b['tcells']]
            pooled = ['all']
        nb = est(ps, tc) or dict(cover=0.27, density=8.0, fr=0.8)
        if loc is None:
            w = 0.0
        else:
            w = n_loc / (n_loc + MIN_PIECES_FOR_LOCAL) if len(pooled) > 1 else 1.0
        cover = w * (loc['cover'] if loc else 0) + (1 - w) * nb['cover']
        dens = w * (loc['density'] if loc else 0) + (1 - w) * nb['density']
        fr = w * (loc['fr'] if loc else 0) + (1 - w) * nb['fr']
        eqs = np.array([p.eq_mm for p in ps]) if ps else np.array([190.0])
        cover_t = cover + BLEND * (PHOTO['cover'] - cover); dens_t = dens + BLEND * (PHOTO['density'] - dens)
        # palette: area-weighted colours of the bay's own traced pieces (clear share kept)
        pal_src = d['pieces'] if len(d['pieces']) >= MIN_PIECES_FOR_LOCAL else ps
        pal_rgb = np.array([p.rgb for p in pal_src], np.float64); pal_w = np.array([p.area for p in pal_src])
        pal_w = pal_w / pal_w.sum()
        clears = [p.rgb for p in pal_src if is_clear(p.rgb)]
        clear_rgb = tuple(int(v) for v in np.median(np.array(clears), axis=0)) if clears else CLEAR_RGB
        eq_w = eqs ** 2; eq_w = eq_w / eq_w.sum()
        targets[(i, j)] = dict(cover_local=cover, density_local=dens, fr_local=fr, cover=cover_t, density=dens_t,
                               cover_free=cover_t / fr, density_free=dens_t / fr, mean_piece=cover / max(1e-6, dens),
                               cover_own=loc['cover'] if loc else None, density_own=loc['density'] if loc else None, w_local=w,
                               eq=eqs, eq_w=eq_w, pooled=pooled, n_local=n_loc, n_used=len(ps), pal_rgb=pal_rgb, pal_w=pal_w,
                               clear_rgb=clear_rgb, clear_share=float(pal_w[[is_clear(p.rgb) for p in pal_src]].sum()),
                               tcells=len(d['tcells']), cells=d['cells'])
    return targets


AREA_WEIGHTED = 0.5                            # share of synthetic size draws weighted by the traced piece's area (--area-weighted)
TOPUP_MAX = 1.3                                # a bay short of its synthetic cover target has its budgets raised at most this much
CELL_OVER = 1.25                               # a cell may hold up to this multiple of its own area budget (the block's budget binds)
COUNT_K = 2.5                                  # a piece may be at most this many times the area its count block still needs per
                                               # remaining count (keeps the block's area and count in step; --count-k)


def draw_eq(rng, t, area_weighted=None):
    """Equivalent diameter (mm) for a synthetic piece: the local traced distribution, blended
    BLEND towards the photograph's p10/p50/p90 (log-linear). Half the draws are area-weighted
    (a large traced blob is drawn in proportion to the glass it holds), so the synthetic cells
    carry the same share of big slabs as the traced ones and reach the same cover with a piece
    count nearer theirs."""
    if rng.uniform() < BLEND:
        u = rng.uniform()
        if u < 0.5:
            return float(np.exp(np.interp(u, [0.1, 0.5], np.log([PHOTO['eq_p10'], PHOTO['eq_p50']]))))
        return float(np.exp(np.interp(u, [0.5, 0.9], np.log([PHOTO['eq_p50'], PHOTO['eq_p90']]))))
    if rng.uniform() < (AREA_WEIGHTED if area_weighted is None else area_weighted):
        return float(rng.choice(t['eq'], p=t['eq_w']) * rng.uniform(0.9, 1.1))
    return float(rng.choice(t['eq']) * rng.uniform(0.9, 1.1))


def draw_colour(rng, t):
    k = int(rng.choice(len(t['pal_w']), p=t['pal_w']))
    return jitter_colour(tuple(int(v) for v in t['pal_rgb'][k]), rng, dh=0.01, dv=0.05)


# ----------------------------------------------------------------------------- 4. the ortho colour sampler
class OrthoSampler:
    """The bottom ortho warped onto the NEW plate raster (one affine per axis, the remap itself), so a
    synthetic piece in a smeared cell can take the colour the bake shows there."""

    def __init__(self, bg_grid):
        img = np.asarray(Image.open(os.path.join(TRACKB, 'bottom-ortho.png')).convert('RGB'))
        su, sv = PU / OLD['PU'], PV / OLD['PV']
        # old px -> new px: x' = (x + 0.5) * su - 0.5 + (OLD.hu0 - HU0)/MPP * su ... written as an affine
        tx = ((OLD['hu0'] - HU0) / MPP + 0.5) * su - 0.5
        ty = ((OLD['hv0'] - HV0) / MPP + 0.5) * sv - 0.5
        M = np.array([[su, 0, tx], [0, sv, ty]], np.float64)
        self.img = cv2.warpAffine(img, M, (W_PX, H_PX), flags=cv2.INTER_LINEAR, borderMode=cv2.BORDER_CONSTANT)
        del img
        self.bg = bg_grid

    def sample(self, pts):
        """Median RGB inside the piece eroded 2 px, or None when it reads as matrix."""
        px = to_px(pts)
        x0 = int(px[:, 0].min()) - 1; x1 = int(px[:, 0].max()) + 2; y0 = int(px[:, 1].min()) - 1; y1 = int(px[:, 1].max()) + 2
        if x0 < 0 or y0 < 0 or x1 > W_PX or y1 > H_PX:
            return None
        loc = np.zeros((y1 - y0, x1 - x0), np.uint8)
        cv2.fillPoly(loc, [np.round((px - [x0, y0]) * 8).astype(np.int32)], 1, lineType=cv2.LINE_8, shift=3)
        loc = cv2.erode(loc, np.ones((5, 5), np.uint8))
        if loc.sum() < 6:
            return None
        pix = self.img[y0:y1, x0:x1][loc > 0]
        med = np.median(pix, axis=0)
        grey = 0.299 * med[0] + 0.587 * med[1] + 0.114 * med[2]
        chroma = med.max() - med.min()
        c, r = cell_of(*pts.mean(axis=0))
        bg = float(self.bg[r, c])
        if grey > bg + 22 or (chroma > 32 and grey > bg + 10):
            return tuple(int(round(v)) for v in med)
        return None


# ----------------------------------------------------------------------------- 5. budgets
class Budget:
    """Glass area and piece count the synthetic cells may hold: the bay's targets per m2 of glazed plan
    times the cell's own band-free area. The AREA budget is per 0.5 m cell (with a random slack of up to
    one typical piece, so the last piece straddles the budget without bias). The COUNT cap is pooled over
    1 m blocks of 2 x 2 cells (an integer cap of ~2 per quarter-metre cell stalls a cell that took two row
    rectangles at half its area, while the cell next door holds one slab and a count it cannot use); the
    block's cap is the sum of its synthetic cells' fractional caps rounded stochastically, and a piece is
    admitted while the block has count left AND the piece is at least half the area the block still needs
    per remaining count (so counts are spent on pieces big enough to reach the cover). Motif pieces take
    area, not count: the emblems and fans are the photographs' own, and the traced cells hold them merged
    into blobs."""
    BLK = 2

    def __init__(self, status, free, targets, cnt, area):
        self.mean_piece_floor = float(np.median([t['mean_piece'] for t in targets.values()]))
        self.area_used = area.copy()
        self.count = cnt.copy()
        self.area_budget = np.zeros((NR, NC))
        self.slack = np.zeros((NR, NC))
        self.count_cap = np.zeros((NR, NC))          # fractional, per cell (reporting); the binding cap is per block
        self.motif_count = np.zeros((NR, NC), int)
        self.status = status
        for (i, j), t in targets.items():
            for (r, c) in t['cells']:
                fa = float(free[r, c]) * CELL * CELL
                rng = np.random.default_rng([c, r, 11])
                self.area_budget[r, c] = t['cover_free'] * fa
                self.slack[r, c] = t['mean_piece'] * rng.uniform()
                self.count_cap[r, c] = t['density_free'] * fa
        B = self.BLK
        self.NRB, self.NCB = (NR + B - 1) // B, (NC + B - 1) // B
        self.blk_cap = np.zeros((self.NRB, self.NCB), int)
        self.blk_area = np.zeros((self.NRB, self.NCB))
        self.blk_slack = np.zeros((self.NRB, self.NCB))
        for R in range(self.NRB):
            for C in range(self.NCB):
                rng = np.random.default_rng([C, R, 13])
                cap = 0.0
                for r in range(R * B, min(NR, R * B + B)):
                    for c in range(C * B, min(NC, C * B + B)):
                        if status[r, c] == 2:
                            cap += self.count_cap[r, c]; self.blk_area[R, C] += self.area_budget[r, c]
                self.blk_cap[R, C] = int(math.floor(cap)) + (1 if rng.uniform() < cap - math.floor(cap) else 0)
                self.blk_slack[R, C] = self.mean_piece_floor * rng.uniform()
        # running block totals (non-motif count, area) over the synthetic cells, kept by add()
        self.blk_n = np.zeros((self.NRB, self.NCB), int); self.blk_a = np.zeros((self.NRB, self.NCB))
        for r in range(NR):
            for c in range(NC):
                if status[r, c] == 2:
                    self.blk_n[r // B, c // B] += int(cnt[r, c]); self.blk_a[r // B, c // B] += float(area[r, c])

    def _blk(self, cell):
        c, r = cell
        return r // self.BLK, c // self.BLK

    def _blk_state(self, R, C):
        return int(self.blk_n[R, C]), float(self.blk_a[R, C])

    def room(self, cell, area):
        """Area: the cell may hold up to CELL_OVER x its own budget (a cell whose neighbour in the block is
        mostly steel takes some of that neighbour's glass), the block as a whole its budget plus one
        typical piece of random slack."""
        c, r = cell
        if self.status[r, c] < 2:
            return False
        if self.area_used[r, c] + area > CELL_OVER * self.area_budget[r, c] + self.slack[r, c]:
            return False
        R, C = self._blk(cell)
        n, a = self._blk_state(R, C)
        return a + area <= self.blk_area[R, C] + self.blk_slack[R, C]

    def remaining(self, cell):
        c, r = cell
        return self.area_budget[r, c] - self.area_used[r, c]

    def count_floor(self, cell):
        """The smallest piece the block still accepts (half the area it needs per remaining count)."""
        R, C = self._blk(cell)
        n, a = self._blk_state(R, C)
        left = self.blk_cap[R, C] - n
        return 1e9 if left <= 0 else 0.5 * max(0.0, self.blk_area[R, C] - a) / left

    def room_count(self, cell, area=None):
        R, C = self._blk(cell)
        n, a = self._blk_state(R, C)
        left = self.blk_cap[R, C] - n
        if left <= 0:
            return False
        if area is None:
            return True
        need = max(0.0, self.blk_area[R, C] - a)
        mean_need = need / left
        return 0.5 * mean_need <= area <= COUNT_K * max(mean_need, 0.5 * self.mean_piece_floor)

    def add(self, pc):
        c, r = pc.cell
        self.area_used[r, c] += pc.area; self.count[r, c] += 1
        if pc.osrc == 'motif':
            self.motif_count[r, c] += 1
        if self.status[r, c] == 2:
            R, C = r // self.BLK, c // self.BLK
            self.blk_a[R, C] += pc.area
            if pc.osrc != 'motif':
                self.blk_n[R, C] += 1


# ----------------------------------------------------------------------------- 6. motifs
def emblem_pieces(cx, cy, along, rng, families, clear_rgb):
    """The square ring with X in local coordinates: x along the ridge, y across. Outer 0.89 x 0.74 m:
    two stacks of three 95 x 220 mm rectangles either side, two rectangles above and below the inner
    X-square (0.34 m: four clear triangles split by a 40 mm matrix X). Returns (pts, rgb, part)."""
    fa, fb, fc = families
    colA = jitter_colour(FAMILY_LIFTED[fa], rng); colB = jitter_colour(FAMILY_LIFTED[fb], rng); colC = jitter_colour(FAMILY_LIFTED[fc], rng)
    if fa == 'white':
        colA = clear_rgb
    if fb == 'white':
        colB = clear_rgb
    if fc == 'white':
        colC = clear_rgb
    out = []
    ca, sa = math.cos(along), math.sin(along)

    def world(loc):
        loc = np.asarray(loc, np.float64)
        return np.stack([cx + loc[:, 0] * ca - loc[:, 1] * sa, cy + loc[:, 0] * sa + loc[:, 1] * ca], axis=1)
    xs = [(-0.445, -0.35, colA), (-0.3075, -0.2125, colB), (0.2125, 0.3075, colB), (0.35, 0.445, colA)]
    ys = [(-0.37, -0.15), (-0.11, 0.11), (0.15, 0.37)]
    for x0, x1, col in xs:
        for y0, y1 in ys:
            out.append((world([[x0, y0], [x1, y0], [x1, y1], [x0, y1]]), jitter_colour(col, rng, 0.005, 0.03), 'ring'))
    n_row = 3 if rng.uniform() < 0.35 else 2
    xr = np.linspace(-0.17, 0.17, n_row + 1)
    for k in range(n_row):
        x0, x1 = xr[k] + (0.02 if k else 0), xr[k + 1] - (0.02 if k < n_row - 1 else 0)
        for y0, y1 in ((0.21, 0.37), (-0.37, -0.21)):
            out.append((world([[x0, y0], [x1, y0], [x1, y1], [x0, y1]]), jitter_colour(colC, rng, 0.005, 0.03), 'ring'))
    inner_col = clear_rgb if rng.uniform() < 13 / 16 else jitter_colour(FAMILY_LIFTED['amber'], rng)
    h = 0.17; a = 0.0283
    for rot in range(4):
        tri = np.array([[0, a], [h - a, h], [-(h - a), h]])
        c, s = math.cos(rot * math.pi / 2), math.sin(rot * math.pi / 2)
        tri = np.stack([tri[:, 0] * c - tri[:, 1] * s, tri[:, 0] * s + tri[:, 1] * c], axis=1)
        out.append((world(tri), inner_col, 'inner'))
    return out


def place_emblems(raster, budget, status, targets, pieces, report):
    """16 round every crest node: two per ridge arm side at 1.47 and 2.45 m along the ridge,
    0.58-0.66 m off its axis. Only where the centre cell is synthetic; ring pieces that cross a
    band are clipped (dropped when more than half inside), the emblem stands when 60 % of its
    pieces do."""
    placed = skipped_edge = skipped_traced = skipped_blocked = skipped_no_arm = 0
    k_fam = 0
    detail = []
    for i in range(NB_U + 1):
        for j in range(NB_V + 1):
            nu, nv = HU0 + i * PU, HV0 + j * PV
            for arm in ((1, 0), (-1, 0), (0, 1), (0, -1)):
                au, av = arm
                # the arm exists when the ridge continues that way (2 sides x 2 positions per arm)
                if (au == 1 and i >= NB_U) or (au == -1 and i <= 0) or (av == 1 and j >= NB_V) or (av == -1 and j <= 0):
                    skipped_no_arm += 4
                    continue
                along = math.atan2(av, au)
                for side in (1, -1):
                    su, sv = -av * side, au * side          # unit normal of the arm, times side
                    for s_along in (1.47, 2.45):
                        rng = np.random.default_rng([i * 131 + j * 17, int(au + 2) * 7 + int(av + 2), side + 2, int(s_along * 100)])
                        off = rng.uniform(0.58, 0.66)
                        s = s_along
                        cx, cy = nu + au * s + su * off, nv + av * s + sv * off
                        # the side exists when the plate does: a plate-edge ridge has emblems inside only
                        if not (HU0 < cx < HU1 and HV0 < cy < HV1):
                            skipped_edge += 1
                            continue
                        bi, bj = bay_of(cx, cy)
                        c, r = cell_of(cx, cy)
                        if status[r, c] < 2:
                            skipped_traced += 1
                            continue
                        # At the measured offsets the ring's far corners touch the X (first emblem)
                        # and the diamond (second): the triangle is 1.7 m wide out there and two
                        # rings need 1.9 m. The photographs show exactly that, corner pieces cut
                        # short by the diagonals, so the centres stay measured and the clip rule
                        # below trims the corner pieces.
                        fams = RING_FAMILIES[int(rng.integers(len(RING_FAMILIES)))]
                        parts = emblem_pieces(cx, cy, along, rng, fams, targets[(bi, bj)]['clear_rgb'])
                        cand = []
                        for pts, col, part in parts:
                            share = raster.band_share(pts)
                            if share > 0.5:
                                continue
                            if share > 0:
                                # cut the band out (exact geometry) and keep the convex remainder
                                hit = band_hits(pts)
                                pts2 = tidy(Polygon(pts).difference(hit)) if hit is not None else None
                                if pts2 is None or 2 * math.sqrt(abs(shoelace(pts2)) / math.pi) * 1000 < MIN_EQ_MM:
                                    continue
                                pts = pts2
                            if not raster.free(pts):
                                continue
                            cand.append((pts, col, part))
                        if len(cand) < 0.6 * len(parts):
                            skipped_blocked += 1
                            continue
                        for pts, col, part in cand:
                            pc = Piece(pts, col, 'motif', 'motif', ['emblem', part], motif='emblem')
                            raster.occupy(pc.pts); budget.add(pc); pieces.append(pc)
                        placed += 1
                        detail.append(dict(node=[i, j], arm=[au, av], side=side, s=round(s, 3), off=round(off, 3), centre=[round(cx, 3), round(cy, 3)], n=len(cand)))
    nominal = (NB_U + 1) * (NB_V + 1) * 16
    report['emblems'] = dict(nominal_positions=nominal, no_arm_beyond_plate=skipped_no_arm, centre_outside_plate=skipped_edge,
                             inside_plate=nominal - skipped_no_arm - skipped_edge, placed=placed, skipped_traced_cell=skipped_traced,
                             skipped_blocked=skipped_blocked, positions=detail)
    log('emblems: %d nominal positions round %d nodes, %d on arms beyond the plate, %d with the centre outside the plate, %d inside; placed %d, skipped %d in traced cells, %d blocked by traced pieces' % (
        nominal, (NB_U + 1) * (NB_V + 1), skipped_no_arm, skipped_edge, nominal - skipped_no_arm - skipped_edge, placed, skipped_traced, skipped_blocked))


_BAND_TREE = None
_BAND_POLYS = None


def band_hits(pts):
    poly = Polygon(pts)
    idx = _BAND_TREE.query(poly)
    hit = [_BAND_POLYS[k] for k in idx if _BAND_POLYS[k].intersects(poly)]
    return unary_union(hit) if hit else None


def place_fans(raster, budget, status, targets, pieces, report):
    """The radial fan round every funnel vertex: in each of the eight 45-degree sectors between the
    cross arms and the X arms, clear wedges pointing at the vertex, one at r 0.35-0.58 and two at
    r 0.64-0.98 (within ~1 m), 40 mm of matrix between them. Only where the cells are synthetic."""
    placed = partial = skipped = 0
    detail = []
    for i in range(NB_U):
        for j in range(NB_V):
            cu, cv = vertex(i, j)
            rng = np.random.default_rng([i, j, 77])
            clear_rgb = targets[(i, j)]['clear_rgb']
            n_ok = n_try = 0
            for sec in range(8):
                th0 = sec * math.pi / 4
                for (r0, r1, nsplit) in ((0.36, 0.58, 1), (0.64, 0.98, 2)):
                    # angular margin so the wedge sides stay clear of the bands (+ a gap)
                    m0 = math.asin(min(0.99, (CLEAR_MEMBER + 0.03) / r0)); m1 = math.asin(min(0.99, (CLEAR_MEMBER + 0.03) / r1))
                    a0, a1 = th0 + m0, th0 + math.pi / 4 - m0
                    b0, b1 = th0 + m1, th0 + math.pi / 4 - m1
                    if a1 - a0 < 0.05 or b1 - b0 < 0.05:
                        continue
                    for k in range(nsplit):
                        gap = 0.04 / r1
                        fa0 = a0 + (a1 - a0) * k / nsplit + (gap / 2 if k else 0)
                        fa1 = a0 + (a1 - a0) * (k + 1) / nsplit - (gap / 2 if k < nsplit - 1 else 0)
                        fb0 = b0 + (b1 - b0) * k / nsplit + (gap / 2 if k else 0)
                        fb1 = b0 + (b1 - b0) * (k + 1) / nsplit - (gap / 2 if k < nsplit - 1 else 0)
                        pts = np.array([[cu + r0 * math.cos(fa0), cv + r0 * math.sin(fa0)], [cu + r1 * math.cos(fb0), cv + r1 * math.sin(fb0)],
                                        [cu + r1 * math.cos(fb1), cv + r1 * math.sin(fb1)], [cu + r0 * math.cos(fa1), cv + r0 * math.sin(fa1)]])
                        n_try += 1
                        c, rr = cell_of(*pts.mean(axis=0))
                        if status[rr, c] < 2:
                            continue
                        if raster.band_share(pts) > 0 or not raster.free(pts):
                            continue
                        col = clear_rgb if rng.uniform() < 0.85 else draw_colour(rng, targets[(i, j)])
                        pc = Piece(pts, col, 'motif', 'motif', ['fan'], motif='fan')
                        raster.occupy(pc.pts); budget.add(pc); pieces.append(pc); n_ok += 1
            if n_ok == n_try:
                placed += 1
            elif n_ok > 0:
                partial += 1
            else:
                skipped += 1
            detail.append(dict(vertex=[i, j], wedges=n_ok, of=n_try))
    wedges = sum(d['wedges'] for d in detail); of = sum(d['of'] for d in detail)
    report['fans'] = dict(complete=placed, partial=partial, skipped=skipped, wedges_placed=wedges, wedges_possible=of,
                          best=max(d['wedges'] for d in detail) if detail else 0, vertices=detail)
    log('fans: %d complete (all %d wedges), %d partial, %d empty; %d of %d wedges placed, best vertex %d' % (
        placed, of // max(1, len(detail)), partial, skipped, wedges, of, report['fans']['best']))


# ----------------------------------------------------------------------------- 7. synthetic infill
def colour_for(rng, t, pts, status_cls, sampler, counts):
    """Synthetic colour: the ortho's own colour in a smeared (class 2) cell when it reads as glass,
    else a draw from the bay palette."""
    c, r = cell_of(*pts.mean(axis=0))
    if status_cls[r, c] == 2 and sampler is not None:
        raw = sampler.sample(pts)
        if raw is not None:
            counts['atlas-neighbour'] += 1
            return lift_colour(raw), 'atlas-neighbour', raw
    counts['bay-palette'] += 1
    return draw_colour(rng, t), 'bay-palette', None


REJ = dict(small=0, traced_cell=0, budget=0, count=0, band=0, blocked=0, ok=0)


def try_place(raster, budget, pts):
    if pts is None or len(pts) < 3:
        return False
    pc_cell = cell_of(*pts.mean(axis=0))
    A = abs(shoelace(pts))
    if 2 * math.sqrt(A / math.pi) * 1000 < MIN_EQ_MM:
        REJ['small'] += 1
        return False
    if budget.status[pc_cell[1], pc_cell[0]] < 2:
        REJ['traced_cell'] += 1
        return False
    if not budget.room(pc_cell, A):
        REJ['budget'] += 1
        return False
    if not budget.room_count(pc_cell, A):
        REJ['count'] += 1
        return False
    if raster.band_share(pts) > 0:
        REJ['band'] += 1
        return False
    if not raster.free(pts):
        REJ['blocked'] += 1
        return False
    REJ['ok'] += 1
    return True


def place_rows(raster, budget, status, targets, cls, sampler, pieces, counts):
    """Rows of 3-6 similar rectangles along every rib, 100-150 mm off it, on the inner side of each of
    the 16 triangles of a bay; along the diagonals some runs are right triangles with the hypotenuse
    on the rib instead (the sawtooth French laid along the X). A second row further in now and then."""
    n_rect = n_tri = 0
    for i in range(NB_U):
        for j in range(NB_V):
            t = targets[(i, j)]
            for ti, (tri, kinds) in enumerate(triangles_of_bay(i, j)):
                for e in range(3):
                    P0, P1 = tri[e], tri[(e + 1) % 3]
                    P2 = tri[(e + 2) % 3]
                    d = P1 - P0; L = float(np.hypot(*d)); ux, uy = d / L
                    nx, ny = -uy, ux
                    if (P2[0] - P0[0]) * nx + (P2[1] - P0[1]) * ny < 0:
                        nx, ny = -nx, -ny
                    ang = math.atan2(uy, ux)
                    kind = kinds[e]
                    half = CLEAR_RIDGE if kind == 'ridge' else CLEAR_MEMBER
                    diag = kind in ('X', 'diamond')
                    rng = np.random.default_rng([i, j, ti, e, 5])
                    for row in range(2):
                        if row == 1 and rng.uniform() > 0.45:
                            break
                        short = rng.uniform(0.085, 0.10)
                        off = half + rng.uniform(0.10, 0.15) + short / 2 + row * (short + rng.uniform(GAP_MIN, GAP_MAX) + rng.uniform(0, 0.08))
                        s = rng.uniform(0.15, 0.45)
                        while s < L - 0.3:
                            n_run = int(rng.integers(3, 7))
                            use_tri = rng.uniform() < (0.45 if diag else 0.12)
                            long = rng.uniform(0.20, 0.26)
                            col = draw_colour(rng, t)
                            if rng.uniform() < 0.25:
                                s += rng.uniform(0.3, 0.9)
                                continue
                            for k in range(n_run):
                                ln = long * rng.uniform(0.95, 1.05)
                                if s + ln > L - 0.15:
                                    break
                                cx = P0[0] + ux * (s + ln / 2) + nx * off; cy = P0[1] + uy * (s + ln / 2) + ny * off
                                if use_tri:
                                    base = ln * rng.uniform(1.0, 1.15)
                                    pts = tri_poly(cx, cy, base, base * rng.uniform(0.45, 0.6), ang, right=rng.uniform() < 0.5)
                                else:
                                    pts = rect_poly(cx, cy, ln, short, ang)
                                if try_place(raster, budget, pts):
                                    rgb, csrc, raw = colour_for(rng, t, pts, cls, sampler, counts)
                                    if csrc == 'bay-palette':
                                        rgb = jitter_colour(col, rng, 0.005, 0.04)
                                    pc = Piece(pts, rgb, csrc, 'synthetic', ['row', kind], raw_rgb=raw)
                                    raster.occupy(pc.pts); budget.add(pc); pieces.append(pc)
                                    if use_tri:
                                        n_tri += 1
                                    else:
                                        n_rect += 1
                                s += ln + rng.uniform(GAP_MIN, GAP_MAX)
                            s += rng.uniform(0.10, 0.40)
    log('rows: %d rectangles, %d sawtooth triangles; rejections so far %s' % (n_rect, n_tri, json.dumps(REJ)))
    return n_rect, n_tri


def place_wedges(raster, budget, status, targets, cls, sampler, pieces, counts):
    """Triangles filling the wedge at every corner of the 16 triangles (edges parallel to the two ribs)."""
    n = 0
    for i in range(NB_U):
        for j in range(NB_V):
            t = targets[(i, j)]
            for ti, (tri, kinds) in enumerate(triangles_of_bay(i, j)):
                rng = np.random.default_rng([i, j, ti, 9])
                for v in range(3):
                    A = tri[v]; B = tri[(v + 1) % 3]; C = tri[(v + 2) % 3]
                    e1 = (B - A) / np.hypot(*(B - A)); e2 = (C - A) / np.hypot(*(C - A))
                    k1 = kinds[v]; k2 = kinds[(v + 2) % 3]
                    h1 = CLEAR_RIDGE if k1 == 'ridge' else CLEAR_MEMBER; h2 = CLEAR_RIDGE if k2 == 'ridge' else CLEAR_MEMBER
                    # inset the corner along both edges by the band + a 100-150 mm gap
                    cosang = float(np.dot(e1, e2)); sinang = math.sqrt(max(1e-6, 1 - cosang ** 2))
                    g1 = h2 + rng.uniform(0.10, 0.15); g2 = h1 + rng.uniform(0.10, 0.15)
                    # point at distance g1 from edge2 and g2 from edge1
                    apex = A + e1 * (g1 / sinang) + e2 * (g2 / sinang)
                    for m in range(3):
                        if m and rng.uniform() > 0.6:
                            break
                        leg = rng.uniform(0.18, 0.30)
                        start = apex + (e1 + e2) / np.hypot(*(e1 + e2)) * (m * (leg * 0.9 + rng.uniform(GAP_MIN, GAP_MAX)) / max(0.4, sinang))
                        pts = np.array([start, start + e1 * leg, start + e2 * leg * rng.uniform(0.85, 1.15)])
                        if try_place(raster, budget, pts):
                            rgb, csrc, raw = colour_for(rng, t, pts, cls, sampler, counts)
                            pc = Piece(pts, rgb, csrc, 'synthetic', ['wedge'], raw_rgb=raw)
                            raster.occupy(pc.pts); budget.add(pc); pieces.append(pc); n += 1
    log('wedges: %d corner triangles' % n)
    return n


def nearest_line_dirs(hu, hv):
    """(axis direction, diagonal direction) of the nearest ridge/cross and the nearest X/diamond line."""
    i, j = bay_of(hu, hv)
    best_ax = (1e9, 0.0); best_dg = (1e9, 0.0)
    for p0, p1, kind in bay_lines(i, j):
        x0, y0 = p0; x1, y1 = p1
        dx, dy = x1 - x0, y1 - y0
        L2 = dx * dx + dy * dy
        tt = max(0.0, min(1.0, ((hu - x0) * dx + (hv - y0) * dy) / L2))
        d = math.hypot(hu - (x0 + tt * dx), hv - (y0 + tt * dy))
        ang = math.atan2(dy, dx)
        if abs(dx) < 1e-9 or abs(dy) < 1e-9:
            if d < best_ax[0]:
                best_ax = (d, ang)
        else:
            if d < best_dg[0]:
                best_dg = (d, ang)
    return best_ax[1], best_dg[1]


def place_chips(raster, budget, status, targets, cls, sampler, pieces, counts, rib_clear_m=0.0, refill=True, tag='chip', budget_frac=1.0):
    """Fill every synthetic cell to its budget with pieces drawn from the local size distribution:
    rectangles / triangles / irregular chips in the photograph's mix, aligned with the nearest rib
    (67 %), the nearest diagonal (21 %) or at random. rib_clear_m keeps the candidate centres that
    far from the band edges (pass 1 leaves the strips along the ribs to the rows); refill adds a
    round of smaller chips for the holes."""
    n = 0; tries = 0
    rib_px = int(round(rib_clear_m / MPP))
    cpx = int(round(CELL / MPP)); M = int(round(0.36 / MPP))       # the cell plus a margin for pieces up to ~700 mm
    order = [(r, c) for r in range(NR) for c in range(NC)]
    for (r, c) in order:
        if status[r, c] < 2:
            continue
        t = targets[bay_of(HU0 + (c + 0.5) * CELL, HV0 + (r + 0.5) * CELL)]
        rng = np.random.default_rng([c, r, 3])
        x0, y0 = c * cpx - M, r * cpx - M; x1, y1 = c * cpx + cpx + M, r * cpx + cpx + M
        X0, Y0, X1, Y1 = max(0, x0), max(0, y0), min(W_PX, x1), min(H_PX, y1)
        fails = 0
        dist = None
        # the sizes this cell will try, largest first: a glazier sets the big slabs and fills the
        # holes with chips, and drawing them up front keeps the size distribution honest (a piece
        # that finds no room is skipped, never shrunk to fit)
        need = CELL_OVER * budget.area_budget[r, c] * budget_frac - budget.area_used[r, c]
        if need <= 0:
            continue
        sizes = []
        while sum(sizes) < need * 2.0 and len(sizes) < 40:
            sizes.append(math.pi * (draw_eq(rng, t) / 2000) ** 2)
        sizes.sort(reverse=True)
        queue = list(sizes)
        refilled = False
        while budget.area_used[r, c] < CELL_OVER * budget.area_budget[r, c] * budget_frac and fails < 25 and budget.room_count((c, r))                 and budget._blk_state(*budget._blk((c, r)))[1] < budget.blk_area[budget._blk((c, r))] * budget_frac:
            if not queue:
                if refilled or not refill:
                    break
                # a second, smaller round for the holes the big pieces left
                refilled = True
                queue = sorted([math.pi * (0.8 * draw_eq(rng, t) / 2000) ** 2 for _ in range(20)], reverse=True)
            tries += 1
            if dist is None:
                free = (raster.blocked[Y0:Y1, X0:X1] == 0).astype(np.uint8)
                dist = cv2.distanceTransform(free, cv2.DIST_L2, 5) * MPP     # metres to the nearest blocked pixel
                # candidate centres lie in this cell only
                cell_mask = np.zeros_like(free)
                cy0, cx0 = r * cpx - Y0, c * cpx - X0
                cell_mask[max(0, cy0):max(0, cy0) + cpx, max(0, cx0):max(0, cx0) + cpx] = 1
                if rib_px:
                    cell_mask &= (raster.ribdist[Y0:Y1, X0:X1] >= rib_px).astype(np.uint8)
                dcell = np.where(cell_mask > 0, dist, 0.0)
            area = queue.pop(0)
            if not budget.room((c, r), area):
                continue
            if not budget.room_count((c, r), area):
                if area < budget.count_floor((c, r)):
                    break                      # the queue is sorted: nothing smaller will pass either
                continue
            u = rng.uniform()
            aspect = max(1.0, float(np.exp(rng.normal(math.log(1.35), 0.40))))
            us = rng.uniform()
            if us < 0.50:
                shape = 'rect'; w = math.sqrt(area * aspect); h = area / w; r_in = h / 2
            elif us < 0.76:
                shape = 'tri'; base = math.sqrt(2 * area * aspect); ht = 2 * area / base
                side = math.sqrt((base / 2) ** 2 + ht ** 2); r_in = base * ht / (base + 2 * side)
            else:
                shape = 'chip'; r_in = math.sqrt(area / math.pi) / math.sqrt(aspect) * 0.9
            ok = dcell >= r_in * 0.92
            ys, xs = np.nonzero(ok)
            if xs.size == 0:
                continue                       # no hole this big: the next (smaller) size is tried
            # prefer the roomier spots (the larger holes get filled first, as a glazier would)
            wgt = dcell[ys, xs] ** 2; wgt /= wgt.sum()
            placed = False
            for attempt in range(5):
                k = int(rng.choice(xs.size, p=wgt))
                cx = HU0 + (X0 + xs[k] + rng.uniform()) * MPP; cy = HV0 + (Y0 + ys[k] + rng.uniform()) * MPP
                ax, dg = nearest_line_dirs(cx, cy)
                if attempt == 0:
                    ang = ax if u < PHOTO['axis'] else (dg if u < PHOTO['axis'] + PHOTO['diag'] else rng.uniform(0, math.pi))
                else:
                    ang = rng.choice([ax, ax + math.pi / 2, dg, dg + math.pi / 2, rng.uniform(0, math.pi)])
                if shape == 'rect':
                    pts = rect_poly(cx, cy, w, h, ang)
                elif shape == 'tri':
                    pts = tri_poly(cx, cy, base, ht, ang, right=rng.uniform() < 0.5, flip=1 if rng.uniform() < 0.5 else -1)
                else:
                    pts = chip_poly(cx, cy, area, aspect, ang, rng)
                if try_place(raster, budget, pts):
                    rgb, csrc, raw = colour_for(rng, t, pts, cls, sampler, counts)
                    pc = Piece(pts, rgb, csrc, 'synthetic', [tag], raw_rgb=raw)
                    raster.occupy(pc.pts); budget.add(pc); pieces.append(pc); n += 1
                    fails = 0; dist = None; placed = True
                    break
            if not placed:
                fails += 1
    log('%s: %d placed in %d tries; rejections %s' % (tag, n, tries, json.dumps(REJ)))
    return n


# ----------------------------------------------------------------------------- 8. NGVP
def write_ngvp(pieces, path):
    u0, v0 = HU0 + BOARD_DU, HV0 + BOARD_DV
    buf = bytearray(b'NGVP')
    buf += struct.pack('<IffH', len(pieces), u0, v0, 1000)
    for pc in pieces:
        r, g, b = pc.rgb
        buf += struct.pack('<4B', r, g, b, len(pc.pts))
        for hu, hv in pc.pts:
            mu = int(round((hu - HU0) * 1000)); mv = int(round((hv - HV0) * 1000))
            assert 0 <= mu <= 65535 and 0 <= mv <= 65535
            buf += struct.pack('<HH', mu, mv)
    with open(path, 'wb') as f:
        f.write(buf)
    return u0, v0, len(buf)


def read_ngvp_like_viewer(path, rect):
    """The exact reader logic of index.html buildGlassPieces: header, per-piece k < 3 skip, the
    |2A| < 2e-6 skip, centroid outside the snapped rect -> dropped. Returns (n, kept, dropped
    reasons, pieces as [(rgb, poly in hall huv)])."""
    buf = open(path, 'rb').read()
    assert buf[:4] == b'NGVP'
    n, u0, v0, mm = struct.unpack_from('<IffH', buf, 4)
    o = 18
    out = []; drops = dict(k=0, area=0, rect=0)
    su0, sv0, su1, sv1 = rect
    for _ in range(n):
        r, g, b, k = struct.unpack_from('<4B', buf, o); o += 4
        uv = []
        for _j in range(k):
            a, bb = struct.unpack_from('<HH', buf, o); o += 4
            uv.append((u0 + a / mm, v0 + bb / mm))
        if k < 3:
            drops['k'] += 1; continue
        A = 0; cu = 0; cv = 0
        for jj in range(k):
            p, q = uv[jj], uv[(jj + 1) % k]
            w = p[0] * q[1] - q[0] * p[1]
            A += w; cu += (p[0] + q[0]) * w; cv += (p[1] + q[1]) * w
        if abs(A) < 2e-6:
            drops['area'] += 1; continue
        A *= 0.5; cu /= 6 * A; cv /= 6 * A
        hcu, hcv = cu - BOARD_DU, cv - BOARD_DV
        if hcu < su0 or hcu > su1 or hcv < sv0 or hcv > sv1:
            drops['rect'] += 1; continue
        out.append(((r, g, b), [(u - BOARD_DU, v - BOARD_DV) for u, v in uv]))
    assert o == len(buf), 'file not consumed to the last byte'
    return n, len(out), drops, out, (u0, v0, mm)


# ----------------------------------------------------------------------------- 9. validity
def validate(path, raster, report):
    n, kept, drops, pcs, hdr = read_ngvp_like_viewer(path, (HU0, HV0, HU1, HV1))
    bad = dict(not_simple=0, not_ccw=0, zero_area=0, verts=0, outside=0, not_convex=0,
               px_on_paint_shader=0, px_on_paint_midpoint=0, vertex_in_paint_shader=0, vertex_in_paint_midpoint=0,
               vertex_in_paint_ridge=0, vertex_under_clear_member=0, vertex_under_clear_ridge=0)
    mins = dict(cross=9.0, diag=9.0, diam_shader=9.0, diam_midpoint=9.0, edge=9.0)
    labels = np.zeros((H_PX, W_PX), np.int32)
    areas_px = np.zeros(len(pcs) + 1, np.int64)
    overlaps = []
    for idx, (rgb, poly) in enumerate(pcs, 1):
        pts = np.array(poly)
        k = len(pts)
        if not 3 <= k <= MAX_VERTS:
            bad['verts'] += 1
        A = shoelace(pts)
        if abs(A) < 1e-6:
            bad['zero_area'] += 1
        if A <= 0:
            bad['not_ccw'] += 1
        sp = Polygon(pts)
        if not (sp.is_valid and sp.is_simple):
            bad['not_simple'] += 1
        if not is_convex(pts, tol=1e-10):
            bad['not_convex'] += 1
        if (pts[:, 0] < HU0).any() or (pts[:, 0] > HU1).any() or (pts[:, 1] < HV0).any() or (pts[:, 1] > HV1).any():
            bad['outside'] += 1
        cross, diag, diam_s, diam_m, edge = steel_dist(pts[:, 0], pts[:, 1])
        for key, arr in (('cross', cross), ('diag', diag), ('diam_shader', diam_s), ('diam_midpoint', diam_m), ('edge', edge)):
            mins[key] = min(mins[key], float(arr.min()))
        ms = float(np.minimum(np.minimum(cross, diag), diam_s).min()); mm = float(np.minimum(np.minimum(cross, diag), diam_m).min())
        if ms < PAINT_MEMBER:
            bad['vertex_in_paint_shader'] += 1
        if mm < PAINT_MEMBER:
            bad['vertex_in_paint_midpoint'] += 1
        if float(edge.min()) < PAINT_RIDGE:
            bad['vertex_in_paint_ridge'] += 1
        both = min(ms, mm) if DIAMOND == 'both' else (ms if DIAMOND == 'shader' else mm)
        if both < CLEAR_MIN_MEMBER:
            bad['vertex_under_clear_member'] += 1
        if float(edge.min()) < CLEAR_MIN_RIDGE:
            bad['vertex_under_clear_ridge'] += 1
        px = to_px(pts)
        x0 = max(0, int(px[:, 0].min()) - 1); x1 = min(W_PX, int(px[:, 0].max()) + 2)
        y0 = max(0, int(px[:, 1].min()) - 1); y1 = min(H_PX, int(px[:, 1].max()) + 2)
        loc = np.zeros((y1 - y0, x1 - x0), np.uint8)
        cv2.fillPoly(loc, [np.round((px - [x0, y0]) * 8).astype(np.int32)], 1, lineType=cv2.LINE_8, shift=3)
        a = int(loc.sum()); areas_px[idx] = a
        win = labels[y0:y1, x0:x1]
        prev = win[loc > 0]
        occ = prev[prev > 0]
        if occ.size:
            for other in np.unique(occ):
                ov = int((occ == other).sum())
                if ov > 0.01 * min(a, areas_px[other]):
                    overlaps.append((idx, int(other), ov, a, int(areas_px[other])))
        if raster.paint[y0:y1, x0:x1][loc > 0].any():
            bad['px_on_paint_shader'] += 1
        if raster.paint_mid[y0:y1, x0:x1][loc > 0].any():
            bad['px_on_paint_midpoint'] += 1
        win[loc > 0] = idx
    del labels
    report['validity'] = dict(file_pieces=n, viewer_kept=kept, viewer_drops=drops, header=dict(u0=hdr[0], v0=hdr[1], mm=hdr[2]),
                              bad=bad, vertex_min_distance_m=mins, clearance_required=dict(member=CLEAR_MIN_MEMBER, ridge=CLEAR_MIN_RIDGE),
                              painted=dict(member=PAINT_MEMBER, ridge=PAINT_RIDGE), diamond=DIAMOND,
                              overlap_pairs_over_1pct=len(overlaps), overlap_examples=overlaps[:20])
    log('validity: %d in file, viewer keeps %d (drops %s); bad %s; vertex minima %s; overlapping pairs > 1%%: %d' % (
        n, kept, drops, bad, {k: round(v, 4) for k, v in mins.items()}, len(overlaps)))
    return pcs


# ----------------------------------------------------------------------------- 10. symmetry (a check only)
def symmetry_check(pieces, status, report):
    """Mirror NCC of the glass mask across three ridge lines at 20 mm/px: the crest line (hv 7.544)
    and the ridges between bays 2|3 and 3|4. Reported for the traced cells only and for all cells;
    the unmirrored comparison of the same two strips is the control."""
    S = 0.02
    W2, H2 = int(round((HU1 - HU0) / S)), int(round((HV1 - HV0) / S))
    mask = np.zeros((H2, W2), np.uint8)
    for pc in pieces:
        px = np.stack([(pc.pts[:, 0] - HU0) / S - 0.5, (pc.pts[:, 1] - HV0) / S - 0.5], axis=1)
        cv2.fillPoly(mask, [np.round(px * 8).astype(np.int32)], 1, lineType=cv2.LINE_8, shift=3)
    tr = np.zeros((H2, W2), np.uint8)
    f = int(round(CELL / S))
    for r in range(NR):
        for c in range(NC):
            if status[r, c] < 2:
                tr[r * f:(r + 1) * f, c * f:(c + 1) * f] = 1

    def ncc(a, b, m):
        a = a[m > 0].astype(np.float64); b = b[m > 0].astype(np.float64)
        if a.size < 100:
            return None
        a -= a.mean(); b -= b.mean()
        d = math.sqrt((a * a).sum() * (b * b).sum())
        return float((a * b).sum() / d) if d > 0 else None
    res = {}
    # crest line: mirror the two bay rows
    half = int(round(PV / S))
    top = mask[:half]; bot = mask[half:2 * half][::-1]
    tt = tr[:half] & tr[half:2 * half][::-1]
    # controls: 'translated' = the other strip unmirrored at the same lattice phase (the steel's own share of
    # the correlation: a mirrored NCC no higher than this is the lattice, not the glass); 'shifted' = the
    # mirrored strip rolled a third of its width (breaks the lattice alignment as well)
    res['crest_hv_7.544'] = dict(all=ncc(top, bot, np.ones_like(tt)), traced=ncc(top, bot, tt),
                                 control_translated=ncc(top, mask[half:2 * half], np.ones_like(tt)),
                                 control_shifted=ncc(top, np.roll(bot, W2 // 3, axis=1), np.ones_like(tt)))
    for i in (3, 4):
        x = int(round(i * PU / S)); w = int(round(PU / S))
        left = mask[:, x - w:x]; right = mask[:, x:x + w][:, ::-1]
        tt = tr[:, x - w:x] & tr[:, x:x + w][:, ::-1]
        res['ridge_hu_%.3f' % (HU0 + i * PU)] = dict(all=ncc(left, right, np.ones_like(tt)), traced=ncc(left, right, tt),
                                                   control_translated=ncc(left, mask[:, x:x + w], np.ones_like(tt)),
                                                   control_shifted=ncc(left, np.roll(right, H2 // 3, axis=0), np.ones_like(tt)))
    report['symmetry_ncc'] = res
    log('symmetry NCC: %s' % json.dumps(res))


# ----------------------------------------------------------------------------- 11. outputs
def draw_pieces(img, pieces, scale, colour_fn, fill=True, thickness=1):
    for pc in pieces:
        px = to_px(pc.pts) * scale
        pts = np.round(px * 8).astype(np.int32)
        col = colour_fn(pc)
        if fill:
            cv2.fillPoly(img, [pts], col, lineType=cv2.LINE_AA, shift=3)
        else:
            cv2.polylines(img, [pts], True, col, thickness, lineType=cv2.LINE_AA, shift=3)


def cell_maps(status, pieces, out):
    S = 8
    img = np.zeros((NR * S + 30, NC * S, 3), np.uint8)
    cols = {0: SRC_COL['atlas'], 1: SRC_COL['atlas-second'], 2: SRC_COL['synthetic']}
    has_traced = np.zeros((NR, NC), bool); csrc_cnt = {}
    for pc in pieces:
        c, r = pc.cell
        if pc.osrc in ('atlas', 'atlas-second') and status[r, c] == 2:
            has_traced[r, c] = True
        csrc_cnt.setdefault((r, c), {}).setdefault(pc.csrc, 0)
        csrc_cnt[(r, c)][pc.csrc] += 1
    for r in range(NR):
        for c in range(NC):
            col = cols[int(status[r, c])]
            cv2.rectangle(img, (c * S, r * S), (c * S + S - 1, r * S + S - 1), col, -1)
            if has_traced[r, c]:
                cv2.rectangle(img, (c * S + 2, r * S + 2), (c * S + S - 3, r * S + S - 3), SRC_COL['atlas'], -1)
    cv2.putText(img, 'green atlas, magenta atlas-second, blue synthetic (green core = synthetic cell holding traced pieces); row 0 = south, col 0 = west', (4, NR * S + 18), cv2.FONT_HERSHEY_SIMPLEX, 0.36, (255, 255, 255), 1)
    Image.fromarray(img).save(os.path.join(out, 'coverage.png'))
    img2 = np.zeros((NR * S + 30, NC * S, 3), np.uint8)
    for r in range(NR):
        for c in range(NC):
            d = csrc_cnt.get((r, c))
            if not d:
                continue
            k = max(d, key=d.get)
            cv2.rectangle(img2, (c * S, r * S), (c * S + S - 1, r * S + S - 1), CSRC_COL[k], -1)
    cv2.putText(img2, 'majority colour source per cell: green atlas, teal atlas-neighbour (ortho in a smeared cell), blue bay-palette, yellow motif', (4, NR * S + 18), cv2.FONT_HERSHEY_SIMPLEX, 0.36, (255, 255, 255), 1)
    Image.fromarray(img2).save(os.path.join(out, 'colour-source.png'))


def overlays(pieces, raster, sampler, out):
    s = 2000 / W_PX
    base = cv2.resize(sampler.img, (2000, int(round(H_PX * s))), interpolation=cv2.INTER_AREA)
    base = (base * 0.35).astype(np.uint8)
    draw_pieces(base, pieces, s, lambda pc: SRC_COL[pc.osrc])
    cv2.putText(base, 'outline source: green atlas, magenta atlas-second, blue synthetic, yellow motif (over the bake ortho, remapped)', (6, base.shape[0] - 8), cv2.FONT_HERSHEY_SIMPLEX, 0.45, (255, 255, 255), 1)
    Image.fromarray(base).save(os.path.join(out, 'overlay-full.jpg'), quality=90)
    black = np.zeros((int(round(H_PX * s)), 2000, 3), np.uint8)
    steel = cv2.resize(raster.paint, (2000, black.shape[0]), interpolation=cv2.INTER_AREA)
    black[steel > 0] = (22, 22, 24)
    draw_pieces(black, pieces, s, lambda pc: pc.rgb)
    Image.fromarray(black).save(os.path.join(out, 'overlay-colour.jpg'), quality=90)


def crops(pieces, raster, sampler, status, out, report):
    """Three 2 m windows at 1:1 (400 px): a traced/synthetic boundary, a bay corner with its emblems,
    a funnel vertex with its fan. Left: the remapped ortho with outlines by source and the steel in
    red; right: the pieces in their colour on the plate."""
    CW = int(round(2.0 / MPP))
    # 1. boundary: the synthetic cell with the most traced-status neighbours, mid-plate
    best = None
    for r in range(2, NR - 2):
        for c in range(4, NC - 4):
            if status[r, c] != 2:
                continue
            nb = sum(1 for dr in (-1, 0, 1) for dc in (-1, 0, 1) if status[r + dr, c + dc] < 2)
            # prefer a half/half window
            win = status[r - 1:r + 3, c - 1:c + 3]
            sc = -abs((win < 2).mean() - 0.5) + 0.01 * nb
            if best is None or sc > best[0]:
                best = (sc, r, c)
    _, r, c = best
    w1 = (HU0 + (c - 1) * CELL, HV0 + (r - 1) * CELL, 'boundary')
    # 2. a crest node with emblems: the interior node with the most emblem pieces
    em = {}
    for pc in pieces:
        if pc.motif == 'emblem':
            i = int(round((pc.pts[:, 0].mean() - HU0) / PU)); j = int(round((pc.pts[:, 1].mean() - HV0) / PV))
            em[(i, j)] = em.get((i, j), 0) + 1
    # the node sits 0.25 m from the window's left edge, so the two emblems at 1.47 m along the +u
    # arm (either side of the ridge) fit inside the 2 m window
    if em:
        (i, j) = max(em, key=em.get)
        w2 = (HU0 + i * PU - 0.06, HV0 + j * PV - 1.0, 'node %d,%d' % (i, j))
    else:
        w2 = (HU0 + 3 * PU - 0.06, HV0 + PV - 1.0, 'node 3,1')
    # 3. a vertex with a fan
    fa = {}
    for pc in pieces:
        if pc.motif == 'fan':
            fa[bay_of(*pc.pts.mean(axis=0))] = fa.get(bay_of(*pc.pts.mean(axis=0)), 0) + 1
    if fa:
        (i, j) = max(fa, key=fa.get)
    else:
        (i, j) = (3, 0)
    cu, cv = vertex(i, j)
    w3 = (cu - 1.0, cv - 1.0, 'vertex %d,%d' % (i, j))
    names = []
    for n, (hu, hv, tag) in enumerate((w1, w2, w3), 1):
        x0 = int(round((hu - HU0) / MPP)); y0 = int(round((hv - HV0) / MPP))
        x0 = max(0, min(W_PX - CW, x0)); y0 = max(0, min(H_PX - CW, y0))
        left = sampler.img[y0:y0 + CW, x0:x0 + CW].copy()
        left[raster.paint[y0:y0 + CW, x0:x0 + CW] > 0] = (110, 20, 20)
        right = np.zeros((CW, CW, 3), np.uint8)
        right[raster.paint[y0:y0 + CW, x0:x0 + CW] > 0] = (26, 26, 28)
        # cell grid on the left, coloured by status
        for r in range(NR):
            for c in range(NC):
                cx0 = int(c * CELL / MPP) - x0; cy0 = int(r * CELL / MPP) - y0
                if -100 < cx0 < CW and -100 < cy0 < CW:
                    col = {0: (0, 90, 0), 1: (90, 0, 90), 2: (0, 40, 120)}[int(status[r, c])]
                    cv2.rectangle(left, (cx0, cy0), (cx0 + 99, cy0 + 99), col, 1)
        sub = [pc for pc in pieces if pc.pts[:, 0].max() >= HU0 + x0 * MPP and pc.pts[:, 0].min() <= HU0 + (x0 + CW) * MPP
               and pc.pts[:, 1].max() >= HV0 + y0 * MPP and pc.pts[:, 1].min() <= HV0 + (y0 + CW) * MPP]
        for pc in sub:
            px = to_px(pc.pts) - [x0, y0]
            pts = np.round(px * 8).astype(np.int32)
            cv2.polylines(left, [pts], True, SRC_COL[pc.osrc], 1, lineType=cv2.LINE_AA, shift=3)
            cv2.fillPoly(right, [pts], pc.rgb, lineType=cv2.LINE_AA, shift=3)
        img = np.concatenate([left, right], axis=1)
        cv2.putText(img, '%s  hu %.2f hv %.2f  2 m at 5 mm/px; left: ortho + outlines (green atlas, magenta 2nd, blue synthetic, yellow motif), red = steel; right: the file' % (tag, HU0 + x0 * MPP, HV0 + y0 * MPP), (6, CW - 8), cv2.FONT_HERSHEY_SIMPLEX, 0.38, (255, 255, 255), 1)
        name = 'crop-%d.jpg' % n
        Image.fromarray(img).save(os.path.join(out, name), quality=92)
        names.append(dict(file=name, tag=tag, hu=HU0 + x0 * MPP, hv=HV0 + y0 * MPP))
    report['crops'] = names


# ----------------------------------------------------------------------------- main
def main():
    global _BAND_TREE, _BAND_POLYS, DIAMOND, AREA_WEIGHTED, COUNT_K
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('--out', default=OUT_DEFAULT)
    ap.add_argument('--no-stats', action='store_true', help='skip the pieces_stats.py printout')
    ap.add_argument('--diamond', default=DIAMOND, choices=['shader', 'midpoint', 'both'],
                    help="the diamond band the pieces keep clear of: index.html's own (shader), the true midpoint one, or both (default)")
    ap.add_argument('--order', default='rows,slabs,wedges,chips', help='the synthetic passes, in order')
    ap.add_argument('--area-weighted', type=float, default=AREA_WEIGHTED, help='share of synthetic size draws weighted by area (big traced slabs drawn in proportion to the glass they hold)')
    ap.add_argument('--count-k', type=float, default=COUNT_K, help='upper bound on a piece, in multiples of the area its block still needs per remaining count')
    args = ap.parse_args()
    DIAMOND = args.diamond
    AREA_WEIGHTED = args.area_weighted
    COUNT_K = args.count_k
    t0 = time.time()
    os.makedirs(args.out, exist_ok=True)
    report = dict(lattice=dict(old=OLD, new=NEW, remap='fu = (hu - hu0_old)/PU_old; hu_new = hu0_new + fu*PU_new (same for v)',
                               plate_new=[HU0, HV0, HU1, HV1], board=dict(du=BOARD_DU, dv=BOARD_DV, u0=HU0 + BOARD_DU, v0=HV0 + BOARD_DV),
                               bands=dict(clear_ridge=CLEAR_RIDGE, clear_member=CLEAR_MEMBER, clear_min_ridge=CLEAR_MIN_RIDGE, clear_min_member=CLEAR_MIN_MEMBER,
                                          paint_ridge=PAINT_RIDGE, paint_member=PAINT_MEMBER, raster_guard=RASTER_GUARD, diamond=DIAMOND, x_scale=X_SCALE,
                                          shader_diamond='dDiam = |dm.x + dm.y - PU/2| * 0.7071 (PU on both axes)')),
                  raster=dict(mpp=MPP, w=W_PX, h=H_PX, cells=[NC, NR]))
    counts = dict(band_drop=0, band_drop_small=0, band_clip=0, overlap_drop=0, overlap_clip=0, gap_clip=0)

    # the steel: exact keep-clear bands (the traced pieces are cut with these), the raster gate one pixel wider,
    # and the two paint masks from the shader's own formula
    bands_clear, per_bay = band_geoms()
    bands_gate, _ = band_geoms(CLEAR_RIDGE + RASTER_GUARD, CLEAR_MEMBER + RASTER_GUARD)
    _BAND_POLYS = [g for g in (bands_clear.geoms if bands_clear.geom_type != 'Polygon' else [bands_clear])]
    _BAND_TREE = STRtree(_BAND_POLYS)
    raster = Raster(bands_gate)
    log('diamond %s; bands rasterised: keep-clear gate %.1f%% of the plate, painted %.1f%% (shader diamond) / %.1f%% (midpoint diamond)' % (
        DIAMOND, 100 * raster.bands.mean(), 100 * raster.paint.mean(), 100 * raster.paint_mid.mean()))

    # 1. traced pieces -> new lattice -> new bands -> no overlaps
    traced, tb = load_traced()
    n0 = len(traced)
    remap_check = []
    for pc in traced[:: max(1, n0 // 5)][:5]:
        n = int([f for f in pc.flags if f.startswith('trackB_')][0].split('_')[1])
        src = tb['pieces'][n]
        fo = frac(src['hu'][0], src['hv'][0], OLD); fn = frac(pc.pts[0, 0], pc.pts[0, 1], NEW)
        remap_check.append(dict(trackB_index=n, old_huv=[src['hu'][0], src['hv'][0]], old_frac=[float(fo[0]), float(fo[1])],
                                new_huv=[float(pc.pts[0, 0]), float(pc.pts[0, 1])], new_frac=[float(fn[0]), float(fn[1])]))
    report['remap_check'] = remap_check
    traced = clip_to_bands(traced, _BAND_TREE, _BAND_POLYS, counts)
    traced = resolve_overlaps(traced, counts)
    for pc in traced:
        raster.occupy(pc.pts)
    log('traced: %d in, %d after the new bands (%d clipped, %d dropped, %d too small after clipping) and overlaps (%d clipped, %d dropped)' % (
        n0, len(traced), counts['band_clip'], counts['band_drop'], counts['band_drop_small'], counts['overlap_clip'], counts['overlap_drop']))
    report['traced'] = dict(n_in=n0, n_kept=len(traced), **counts)

    # 2. cells, targets, palettes
    cls, bg = old_class_grid()
    status, free, cnt, area = cell_status(traced, cls, raster)
    report['cells'] = dict(atlas=int((status == 0).sum()), atlas_second=int((status == 1).sum()), synthetic=int((status == 2).sum()),
                           synthetic_with_traced=int(((status == 2) & (cnt > 0)).sum()),
                           old_class_in_new_grid={str(k): int((cls == k).sum()) for k in range(5)})
    log('cells: %s' % json.dumps(report['cells']))
    targets = bay_targets(traced, status, free)
    report['targets'] = {'%d,%d' % k: dict(cover_local=t['cover_local'], density_local=t['density_local'], cover_own=t['cover_own'], density_own=t['density_own'],
                                           w_local=t['w_local'], fr_traced=t['fr_local'], cover_target=t['cover'], density_target=t['density'],
                                           cover_target_per_free_m2=t['cover_free'], density_target_per_free_m2=t['density_free'],
                                           pooled=[list(p) if isinstance(p, tuple) else p for p in t['pooled']], traced_pieces=t['n_local'], traced_cells=t['tcells'],
                                           clear_share_palette=t['clear_share'], eq_p50_local=float(np.median(t['eq'])))
                         for k, t in targets.items()}
    budget = Budget(status, free, targets, cnt, area)
    sampler = OrthoSampler(bg)
    log('ortho warped onto the new plate')

    # 3. motifs, then the infill
    pieces = list(traced)
    place_emblems(raster, budget, status, targets, pieces, report)
    place_fans(raster, budget, status, targets, pieces, report)
    ccount = {'atlas-neighbour': 0, 'bay-palette': 0}
    # the rows along the ribs first (the count cap binds, and the rows are the look French gave the ribs),
    # then the big slabs of the interior (clear of the strips along the ribs), the corner wedges, and a last
    # pass of chips for what is left (--order swaps them)
    n_c1 = n_rect = n_tri = n_w = n_c2 = 0
    for pas in args.order.split(','):
        if pas == 'slabs':
            n_c1 = place_chips(raster, budget, status, targets, cls, sampler, pieces, ccount, rib_clear_m=0.28, refill=False, tag='slab', budget_frac=0.6)
        elif pas == 'rows':
            n_rect, n_tri = place_rows(raster, budget, status, targets, cls, sampler, pieces, ccount)
        elif pas == 'wedges':
            n_w = place_wedges(raster, budget, status, targets, cls, sampler, pieces, ccount)
        elif pas == 'chips':
            n_c2 = place_chips(raster, budget, status, targets, cls, sampler, pieces, ccount, rib_clear_m=0.0, refill=True, tag='chip')
    # 3a. top-up: a bay whose synthetic cells landed under their cover target (cells that are slivers
    # between bands hold nothing, and a block at its count cap stops short) has the budgets of its
    # blocks raised by the shortfall (at most x TOPUP_MAX) and the chip pass run once more
    scale = {}
    for (i, j), t in targets.items():
        got = 0.0; want = 0.0
        for R in range(budget.NRB):
            for C in range(budget.NCB):
                if budget.blk_cap[R, C] > 0 and bay_of(HU0 + (C + 0.5) * Budget.BLK * CELL, HV0 + (R + 0.5) * Budget.BLK * CELL) == (i, j):
                    got += budget.blk_a[R, C]; want += budget.blk_area[R, C]
        scale[(i, j)] = min(TOPUP_MAX, max(1.0, want / got)) if got > 0 else 1.0
    for R in range(budget.NRB):
        for C in range(budget.NCB):
            f = scale[bay_of(HU0 + (C + 0.5) * Budget.BLK * CELL, HV0 + (R + 0.5) * Budget.BLK * CELL)]
            if f > 1.0 and budget.blk_cap[R, C] > 0:
                budget.blk_area[R, C] *= f; budget.blk_cap[R, C] = int(round(budget.blk_cap[R, C] * f))
                for r in range(R * Budget.BLK, min(NR, R * Budget.BLK + Budget.BLK)):
                    for c in range(C * Budget.BLK, min(NC, C * Budget.BLK + Budget.BLK)):
                        budget.area_budget[r, c] *= f; budget.count_cap[r, c] *= f
    n_top = place_chips(raster, budget, status, targets, cls, sampler, pieces, ccount, rib_clear_m=0.0, refill=True, tag='topup') if max(scale.values()) > 1.0 else 0
    report['topup'] = dict(scale={'%d,%d' % k: round(v, 3) for k, v in scale.items()}, pieces=n_top)
    report['synthetic'] = dict(order=args.order, area_weighted=AREA_WEIGHTED, count_k=COUNT_K, topup=n_top, slabs=n_c1, rows_rect=n_rect, rows_tri=n_tri, wedges=n_w, chips=n_c2, colour_draws=ccount, rejections=dict(REJ))
    # how the synthetic cells and count blocks ended against their budgets (what stopped them)
    sc = status == 2
    au = budget.area_used[sc]; ab = np.maximum(budget.area_budget[sc], 1e-9)
    bn = np.zeros_like(budget.blk_cap); ba = np.zeros_like(budget.blk_area)
    for R in range(budget.NRB):
        for C in range(budget.NCB):
            bn[R, C], ba[R, C] = budget._blk_state(R, C)
    live = budget.blk_cap > 0
    report['budget_summary'] = dict(cells=int(sc.sum()), area_fill_mean=float((au / ab).mean()), area_fill_p10_p50_p90=[float(v) for v in np.percentile(au / ab, [10, 50, 90])],
                                    cells_area_under_85=int((au < 0.85 * ab).sum()), mean_area_budget=float(ab.mean()), mean_area_used=float(au.mean()),
                                    blocks=int(live.sum()), blocks_at_count_cap=int((bn[live] >= budget.blk_cap[live]).sum()),
                                    blocks_at_count_cap_area_under_85=int(((bn[live] >= budget.blk_cap[live]) & (ba[live] < 0.85 * budget.blk_area[live])).sum()),
                                    block_count_fill=float(bn[live].sum() / budget.blk_cap[live].sum()), block_area_fill=float(ba[live].sum() / budget.blk_area[live].sum()))
    log('budget: %s' % json.dumps(report['budget_summary']))

    # 3b. the exact clearance, vertex by vertex, on everything: the raster gate is a pixel coarse, so any
    # piece under the brief's minimum is cut back with the exact bands or dropped
    enforced = []; n_enf_clip = n_enf_drop = 0
    for pc in pieces:
        mm, me = member_clearance(pc.pts)
        if mm >= CLEAR_MIN_MEMBER and me >= CLEAR_MIN_RIDGE:
            enforced.append(pc); continue
        hit = band_hits(pc.pts)
        pts = tidy(pc.poly().difference(hit.buffer(0.003))) if hit is not None else None
        if pts is not None:
            mm, me = member_clearance(pts)
        if pts is None or mm < CLEAR_MIN_MEMBER or me < CLEAR_MIN_RIDGE or 2 * math.sqrt(abs(shoelace(pts)) / math.pi) * 1000 < MIN_EQ_MM:
            n_enf_drop += 1; continue
        pc.pts = ccw(pts); pc.update(); pc.flags.append('clearance_clip'); n_enf_clip += 1
        enforced.append(pc)
    pieces = enforced
    report['clearance_pass'] = dict(clipped=n_enf_clip, dropped=n_enf_drop)
    log('clearance pass: %d pieces cut back to the exact bands, %d dropped' % (n_enf_clip, n_enf_drop))

    # 4. order: traced, motif, synthetic (the viewer does not care; the json reads better)
    order = {'atlas': 0, 'atlas-second': 1, 'motif': 2, 'synthetic': 3}
    pieces.sort(key=lambda p: (order[p.osrc], p.bay, p.cell))
    final = []; n_final_drop = 0
    for pc in pieces:
        q = finalise(pc.pts)
        if q is None:
            n_final_drop += 1
            continue
        pc.pts = q; pc.update(); final.append(pc)
    pieces = final
    report['quantisation'] = dict(dropped=n_final_drop)
    log('quantised to mm: %d pieces, %d dropped as degenerate' % (len(pieces), n_final_drop))

    # 5. statistics
    def stats_block(sel_pieces, plan, free_m2=None):
        return subset_stats(sel_pieces, plan, free_m2)
    per_bay = {}
    fa = lambda cl: float(sum(free[r, c] for (r, c) in cl)) * CELL * CELL
    for (i, j), t in targets.items():
        cells = t['cells']
        tcells = [(r, c) for (r, c) in cells if status[r, c] < 2]; scells = [(r, c) for (r, c) in cells if status[r, c] == 2]
        allp = [p for p in pieces if p.bay == (i, j)]
        tp = [p for p in allp if status[p.cell[1], p.cell[0]] < 2]; sp = [p for p in allp if status[p.cell[1], p.cell[0]] == 2]
        per_bay['%d,%d' % (i, j)] = dict(all=stats_block(allp, PU * PV, fa(cells)), traced_cells=stats_block(tp, len(tcells) * CELL * CELL, fa(tcells)),
                                          synthetic_cells=stats_block(sp, len(scells) * CELL * CELL, fa(scells)),
                                          by_outline={k: len([p for p in allp if p.osrc == k]) for k in order},
                                          by_colour_source={k: dict(n=len([p for p in allp if p.csrc == k]), area=sum(p.area for p in allp if p.csrc == k)) for k in CSRC_COL},
                                          n_cells=len(cells), n_traced_cells=len(tcells), n_synthetic_cells=len(scells))
    all_t = [p for p in pieces if status[p.cell[1], p.cell[0]] < 2]; all_s = [p for p in pieces if status[p.cell[1], p.cell[0]] == 2]
    tcl = [(r, c) for r in range(NR) for c in range(NC) if status[r, c] < 2]; scl = [(r, c) for r in range(NR) for c in range(NC) if status[r, c] == 2]
    overall = dict(all=stats_block(pieces, NB_U * NB_V * PU * PV, fa(tcl + scl)), traced_cells=stats_block(all_t, len(tcl) * CELL * CELL, fa(tcl)),
                   synthetic_cells=stats_block(all_s, len(scl) * CELL * CELL, fa(scl)),
                   by_outline={k: len([p for p in pieces if p.osrc == k]) for k in order},
                   by_colour_source={k: dict(n=len([p for p in pieces if p.csrc == k]), area=sum(p.area for p in pieces if p.csrc == k)) for k in CSRC_COL},
                   ngv=dict(pieces=10000, cover=[0.35, 0.40], plate_m2=NB_U * NB_V * PU * PV))
    report['stats'] = dict(per_bay=per_bay, overall=overall, photo_targets=PHOTO)
    # rule 6: traced vs synthetic per bay, cover and density (non-motif and total), flagged past +-15 %
    r6 = {}
    for k, d in list(per_bay.items()) + [('overall', overall)]:
        t, s = d['traced_cells'], d['synthetic_cells']
        ratio = lambda a, b: (b / a - 1.0) if a else None
        r6[k] = dict(cover=ratio(t['cover'], s['cover']), cover_free=ratio(t['cover_free'], s['cover_free']),
                     density_nonmotif=ratio(t['density'], s['density_nonmotif']), density_total=ratio(t['density'], s['density']))
    report['rule6_ratios'] = r6
    within = lambda key: sum(1 for k, v in r6.items() if k != 'overall' and v[key] is not None and abs(v[key]) <= 0.15)
    report['rule6_within_15pct_bays'] = dict(cover=within('cover'), cover_free=within('cover_free'), density_nonmotif=within('density_nonmotif'), density_total=within('density_total'))
    log('rule 6, bays within 15%% of traced: cover %d/14, glazed-area cover %d/14, non-motif density %d/14, total density %d/14' % tuple(report['rule6_within_15pct_bays'].values()))
    # the big pieces against the photographs (area-weighted: the reference's own yardstick for slabs)
    areas = np.array([p.area for p in pieces]); eqs = np.array([p.eq_mm for p in pieces]); order_eq = np.argsort(eqs)
    cum = np.cumsum(areas[order_eq]) / areas.sum()
    aw = [float(eqs[order_eq][np.searchsorted(cum, q)]) for q in (0.1, 0.5, 0.9)]
    report['big_pieces'] = dict(file_eq_area_weighted_p10_p50_p90=aw, photo_eq_area_weighted_p10_p50_p90=[165, 295, 661],
                                n_over_330=int((eqs > 330).sum()), n_over_450=int((eqs > 450).sum()), n_over_661=int((eqs > 661).sum()),
                                area_share_over_330=float(areas[eqs > 330].sum() / areas.sum()), area_share_over_450=float(areas[eqs > 450].sum() / areas.sum()),
                                area_share_over_661=float(areas[eqs > 661].sum() / areas.sum()), largest_eq=float(eqs.max()))
    log('big pieces: area-weighted eq p10/p50/p90 %.0f/%.0f/%.0f mm (photo 165/295/661); over 330/450/661 mm: %d/%d/%d pieces, %.1f/%.1f/%.1f%% of the glass' % (
        *aw, report['big_pieces']['n_over_330'], report['big_pieces']['n_over_450'], report['big_pieces']['n_over_661'],
        100 * report['big_pieces']['area_share_over_330'], 100 * report['big_pieces']['area_share_over_450'], 100 * report['big_pieces']['area_share_over_661']))
    log('overall: %d pieces, %.1f m2 = %.1f%% of the %.0f m2 plate, %.1f /m2; traced cells %.1f%% %.1f/m2, synthetic cells %.1f%% %.1f/m2' % (
        overall['all']['n'], overall['all']['glass_m2'], 100 * overall['all']['cover'], NB_U * NB_V * PU * PV, overall['all']['density'],
        100 * overall['traced_cells']['cover'], overall['traced_cells']['density'], 100 * overall['synthetic_cells']['cover'], overall['synthetic_cells']['density']))

    # 6. files
    bin_path = os.path.join(args.out, 'pieces-merged.bin')
    u0, v0, nbytes = write_ngvp(pieces, bin_path)
    log('wrote %s: %d pieces, %d bytes, origin (%.6f, %.6f)' % (bin_path, len(pieces), nbytes, u0, v0))
    validate(bin_path, raster, report)
    symmetry_check(pieces, status, report)
    recs = []
    for pc in pieces:
        recs.append(dict(hu=[round(float(x), 4) for x in pc.pts[:, 0]], hv=[round(float(x), 4) for x in pc.pts[:, 1]], rgb=list(pc.rgb),
                         colour_source=pc.csrc, outline_source=pc.osrc, bay=list(pc.bay), cell=list(pc.cell), eq_mm=round(pc.eq_mm, 1),
                         area_m2=round(pc.area, 6), flags=pc.flags, raw_rgb=list(pc.raw_rgb) if pc.raw_rgb else None))
    with open(os.path.join(args.out, 'pieces-merged.json'), 'w') as f:
        json.dump(dict(frame=dict(lattice=NEW, board=dict(du=BOARD_DU, dv=BOARD_DV, u0=u0, v0=v0), note='vertices in NEW hu/hv; NGVP = board (hu + du, hv + dv) - origin, mm, CCW, convex'),
                       cells=dict(size=CELL, cols=NC, rows=NR, origin=[HU0, HV0], status_legend={'0': 'atlas', '1': 'atlas-second', '2': 'synthetic'}, status=status.tolist()),
                       pieces=recs), f)
    cell_maps(status, pieces, args.out)
    overlays(pieces, raster, sampler, args.out)
    crops(pieces, raster, sampler, status, args.out, report)
    report['runtime_s'] = time.time() - t0
    try:
        import resource  # noqa
    except ImportError:
        pass
    try:
        import psutil
        report['peak_rss_mb'] = psutil.Process().memory_info().peak_wset / 1e6
    except Exception:
        try:
            import ctypes, ctypes.wintypes
            class PMC(ctypes.Structure):
                _fields_ = [('cb', ctypes.wintypes.DWORD), ('PageFaultCount', ctypes.wintypes.DWORD), ('PeakWorkingSetSize', ctypes.c_size_t),
                            ('WorkingSetSize', ctypes.c_size_t), ('QuotaPeakPagedPoolUsage', ctypes.c_size_t), ('QuotaPagedPoolUsage', ctypes.c_size_t),
                            ('QuotaPeakNonPagedPoolUsage', ctypes.c_size_t), ('QuotaNonPagedPoolUsage', ctypes.c_size_t), ('PagefileUsage', ctypes.c_size_t), ('PeakPagefileUsage', ctypes.c_size_t)]
            pmc = PMC(); pmc.cb = ctypes.sizeof(PMC)
            ctypes.windll.psapi.GetProcessMemoryInfo(ctypes.windll.kernel32.GetCurrentProcess(), ctypes.byref(pmc), pmc.cb)
            report['peak_rss_mb'] = pmc.PeakWorkingSetSize / 1e6
        except Exception:
            report['peak_rss_mb'] = None
    with open(os.path.join(args.out, 'merge-report.json'), 'w') as f:
        json.dump(report, f, indent=1, default=lambda o: o.tolist() if hasattr(o, 'tolist') else str(o))
    log('done in %.0f s, peak RSS %s MB' % (report['runtime_s'], report.get('peak_rss_mb')))
    if not args.no_stats:
        out = subprocess.run([sys.executable, os.path.join(HERE, 'pieces_stats.py'), bin_path], capture_output=True, text=True, timeout=600)
        with open(os.path.join(args.out, 'pieces-stats.txt'), 'w') as f:
            f.write(out.stdout + out.stderr)
        print(out.stdout[-6000:]); print(out.stderr[-2000:])


if __name__ == '__main__':
    main()
