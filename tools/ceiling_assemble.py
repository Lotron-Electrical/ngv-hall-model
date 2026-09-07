"""Assemble the traced slabs of every source into one pane file with provenance, no fill.

Inputs are the json files tools/ceiling_trace2.py writes (one per source tile), in PRIORITY order:
where two sources both traced a slab at the same place, the earlier one wins (topside first: its
shapes are crisp; then the registered photographs and the posed underside frames; the bake last).
A later piece is dropped when it overlaps an earlier one by more than OVERLAP of its own area; a
colour-less piece (topside) takes its colour from the best underside source that covers its
centroid, by median over its polygon, and says which.

Frames: a trace says which lattice its metres are on ("lattice": "new" for anything rendered from
posed cameras in the hall frame, "old" for the bake ortho). Only OLD traces are remapped, by
bay-fractional coordinate per axis exactly as tools/merge_panes.py does; NEW traces are hall metres
already. Every piece is then checked
against the NEW steel bands with merge_panes' own metric (ridge 0.125 m, cross / X / both diamonds
0.090 m): a piece more than half inside a band is dropped, one that touches a band is clipped by
shapely and re-hulled.

    python tools/ceiling_assemble.py --traces a.json b.json ... --out-dir <dir> [--colour-from <underside tile dirs>]
        [--name pieces]

Writes <name>.bin (NGVP, the viewer's format), <name>.json (every piece with its provenance),
<name>-coverage.json (per bay: pieces, glass m2, cover of the bay plan, share by source, and how
much of the bay NO source resolved), and prints the table. Nothing is placed by rule.
"""
import argparse
import json
import os
import struct
import sys

import numpy as np
from PIL import Image
from shapely import STRtree
from shapely.geometry import Polygon, box
from shapely.ops import unary_union

Image.MAX_IMAGE_PIXELS = None
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

OLD = dict(PU=7.4285, PV=7.3855, hu0=-56.635125, hv0=0.158820)
NEW = dict(PU=7.36, PV=7.50, hu0=-56.361133, hv0=0.044317)
NB_U, NB_V = 8, 2
# The real plate (2026-09-08, the NGV panorama + the roof-void coverage + the bake's dark west half
# bay): along u it ends on the VERTEX phase, one bay past the outer columns, so the bay grid of
# NEW (ridge-phase bay boxes) is clipped to it: bay 0 and bay 7 are the half coffers at the walls.
PLATE = dict(hu0=-45.321133 - 7.36, hu1=-45.321133 + 6 * 7.36, hv0=0.044317, hv1=15.044317)
BOARD_DU, BOARD_DV = 58.3053, 0.4556
BAND_RIDGE, BAND_OTHER = 0.125, 0.090
OVERLAP = 0.35
GRID = dict(hu0=-56.635125, hv0=0.15882, mm=4.0)


def remap(hu, hv):
    return (NEW['hu0'] + (np.asarray(hu, float) - OLD['hu0']) * (NEW['PU'] / OLD['PU']),
            NEW['hv0'] + (np.asarray(hv, float) - OLD['hv0']) * (NEW['PV'] / OLD['PV']))


def steel_dist(hu, hv):
    """(distance to the nearest ridge centre line, distance to the nearest cross / hip / diamond
    line) on the NEW lattice; merge_panes' metric: both the shader's diamond (PU on both axes) and
    the true midpoint diamond are steel, so the piece is right under either shader."""
    PU, PV = NEW['PU'], NEW['PV']
    # funnel vertices of the NEW lattice: plate corner + (i + 0.5) PU
    fu = (hu - NEW['hu0']) / PU - 0.5; fv = (hv - NEW['hv0']) / PV - 0.5
    du = (fu - np.round(fu)) * PU; dv = (fv - np.round(fv)) * PV
    d_ridge = np.minimum(np.abs(np.abs(du) - PU / 2), np.abs(np.abs(dv) - PV / 2))
    d_cross = np.minimum(np.abs(du), np.abs(dv))
    d_hip = np.abs(np.abs(du) - np.abs(dv)) * 0.7071
    d_dia1 = np.abs(np.abs(du) + np.abs(dv) - PU / 2) * 0.7071
    # the true midpoint diamond: |du|/(PU/2) + |dv|/(PV/2) = 1, distance approximated by the normal
    nrm = np.hypot(2 / PU, 2 / PV)
    d_dia2 = np.abs(np.abs(du) * 2 / PU + np.abs(dv) * 2 / PV - 1) / nrm
    return d_ridge, np.minimum.reduce([d_cross, d_hip, d_dia1, d_dia2])


def band_polys(hu_lo, hu_hi, hv_lo, hv_hi, step=0.02):
    """The steel bands as a raster-derived polygon set is heavy; instead clip by a fine sampling:
    return a function that says whether a point is in a band."""
    def inband(hu, hv):
        dr, do = steel_dist(np.asarray(hu), np.asarray(hv))
        return (dr < BAND_RIDGE) | (do < BAND_OTHER)
    return inband


def clip_to_bands(poly, inband):
    """Cut the steel out of a slab that overlaps a band: sample the polygon at 20 mm, keep the hull
    of the points clear of the band (a slab is convex in the file anyway)."""
    minx, miny, maxx, maxy = poly.bounds
    xs = np.arange(minx, maxx + 1e-9, 0.02); ys = np.arange(miny, maxy + 1e-9, 0.02)
    X, Y = np.meshgrid(xs, ys)
    pts = np.stack([X.ravel(), Y.ravel()], 1)
    from shapely import contains_xy
    inside = contains_xy(poly, pts[:, 0], pts[:, 1])
    pts = pts[inside]
    if len(pts) == 0:
        return None
    keep = ~inband(pts[:, 0], pts[:, 1])
    if keep.sum() < 0.5 * len(pts):
        return None
    if keep.all():
        return poly
    from shapely.geometry import MultiPoint
    hull = MultiPoint(pts[keep]).convex_hull
    if hull.geom_type != 'Polygon' or hull.area < 0.0016:
        return None
    return hull


def load_traces(paths):
    out = []
    for p in paths:
        d = json.load(open(p))
        old = d.get('lattice', 'old') == 'old'
        for pc in d['pieces']:
            if old:
                hu, hv = remap([q[0] for q in pc['pts']], [q[1] for q in pc['pts']])
            else:
                hu = [q[0] for q in pc['pts']]; hv = [q[1] for q in pc['pts']]
            poly = Polygon(zip(hu, hv))
            if not poly.is_valid or poly.area < 1e-5:
                poly = poly.buffer(0)
                if poly.is_empty or poly.geom_type != 'Polygon':
                    continue
            out.append(dict(pc, poly=poly, trace=os.path.basename(p), registration=d.get('registration'), lattice='old' if old else 'new'))
    return out


def colour_lookup(dirs):
    """median RGB over a polygon from the first underside tile (in order) whose mask covers its centroid."""
    tiles = []
    for d in dirs:
        meta = json.load(open(os.path.join(d, 'meta.json')))
        img = np.array(Image.open(os.path.join(d, 'tile.png')).convert('RGB'))
        mask = np.array(Image.open(os.path.join(d, 'mask.png'))) > 0
        tiles.append((os.path.basename(d.rstrip('/\\')), meta, img, mask))

    def lookup(poly_old):
        cx, cy = poly_old.centroid.x, poly_old.centroid.y
        for name, meta, img, mask in tiles:
            x = int((cx - GRID['hu0']) * 1000 / GRID['mm']) - int(meta.get('px0', 0))
            y = int((cy - GRID['hv0']) * 1000 / GRID['mm']) - int(meta.get('py0', 0))
            if 0 <= y < mask.shape[0] and 0 <= x < mask.shape[1] and mask[y, x]:
                minx, miny, maxx, maxy = poly_old.bounds
                x0 = int((minx - GRID['hu0']) * 1000 / GRID['mm']) - int(meta.get('px0', 0)); x1 = int((maxx - GRID['hu0']) * 1000 / GRID['mm']) - int(meta.get('px0', 0))
                y0 = int((miny - GRID['hv0']) * 1000 / GRID['mm']) - int(meta.get('py0', 0)); y1 = int((maxy - GRID['hv0']) * 1000 / GRID['mm']) - int(meta.get('py0', 0))
                x0, y0 = max(x0, 0), max(y0, 0); x1, y1 = min(x1 + 1, mask.shape[1]), min(y1 + 1, mask.shape[0])
                sub = img[y0:y1, x0:x1]; sm = mask[y0:y1, x0:x1]
                if sm.sum() < 4:
                    continue
                # erode 2 px in from the polygon edge by sampling the polygon interior only
                from shapely import contains_xy
                yy, xx = np.mgrid[y0:y1, x0:x1]
                hu = GRID['hu0'] + (xx + int(meta.get('px0', 0)) + 0.5) * GRID['mm'] / 1000
                hv = GRID['hv0'] + (yy + int(meta.get('py0', 0)) + 0.5) * GRID['mm'] / 1000
                ins = contains_xy(poly_old.buffer(-0.008), hu.ravel(), hv.ravel()).reshape(sub.shape[:2]) & sm
                if ins.sum() < 4:
                    ins = sm
                return [int(v) for v in np.median(sub[ins], axis=0)], name
        return None, None
    return lookup


def write_ngvp(pieces, path):
    u0, v0 = NEW['hu0'] + BOARD_DU, NEW['hv0'] + BOARD_DV
    buf = bytearray(b'NGVP')
    buf += struct.pack('<IffH', len(pieces), u0, v0, 1000)
    for pc in pieces:
        r, g, b = pc['colour']
        pts = list(pc['poly'].exterior.coords)[:-1]
        tol = 0.004
        while len(pts) > 12:          # the file holds 12 vertices: simplify, never truncate
            tol *= 1.5
            pts = list(pc['poly'].simplify(tol, preserve_topology=True).exterior.coords)[:-1]
        # counter-clockwise in (u, v)
        a2 = sum(pts[k][0] * pts[(k + 1) % len(pts)][1] - pts[(k + 1) % len(pts)][0] * pts[k][1] for k in range(len(pts)))
        if a2 < 0:
            pts = pts[::-1]
        buf += struct.pack('<4B', r, g, b, len(pts))
        for hu, hv in pts:
            mu = int(round((hu - NEW['hu0']) * 1000)); mv = int(round((hv - NEW['hv0']) * 1000))
            mu = min(max(mu, 0), 65535); mv = min(max(mv, 0), 65535)
            buf += struct.pack('<HH', mu, mv)
    open(path, 'wb').write(buf)
    return len(buf)


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('--traces', nargs='+', required=True)
    ap.add_argument('--out-dir', required=True)
    ap.add_argument('--name', default='pieces')
    ap.add_argument('--colour-from', nargs='*', default=[])
    ap.add_argument('--resolved-masks', nargs='*', default=[], help='tile dirs whose masks count as "resolved" for the coverage table')
    args = ap.parse_args()
    os.makedirs(args.out_dir, exist_ok=True)
    cands = load_traces(args.traces)
    print(f'{len(cands)} traced pieces from {len(args.traces)} traces')
    inband = band_polys(0, 0, 0, 0)
    kept = []; tree = None; polys = []
    drops = dict(band=0, overlap=0, small=0)
    for pc in cands:
        poly = clip_to_bands(pc['poly'], inband)
        if poly is None:
            drops['band'] += 1; continue
        if poly.area < 0.0016:
            drops['small'] += 1; continue
        if polys:
            tree = STRtree(polys)
            hit = tree.query(poly)
            ov = 0.0
            for k in hit:
                ov += poly.intersection(polys[k]).area
            if ov > OVERLAP * poly.area:
                drops['overlap'] += 1; continue
        pc = dict(pc, poly=poly)
        kept.append(pc); polys.append(poly)
    print('kept', len(kept), 'dropped', drops)
    lookup = colour_lookup(args.colour_from) if args.colour_from else None
    n_col = dict(own=0, looked=0, none=0)
    for pc in kept:
        if pc.get('colour'):
            pc['colour_source'] = pc['source']; n_col['own'] += 1
        elif lookup:
            # the tiles are hall metres on the shared 4 mm grid, as the NEW-lattice pieces are
            col, src = lookup(pc['poly'])
            if col:
                pc['colour'] = col; pc['colour_source'] = src; n_col['looked'] += 1
        if not pc.get('colour'):
            pc['colour'] = [128, 128, 128]; pc['colour_source'] = None; n_col['none'] += 1
    print('colour:', n_col)
    out_bin = os.path.join(args.out_dir, args.name + '.bin')
    nb = write_ngvp(kept, out_bin)
    recs = []
    for pc in kept:
        r = {k: v for k, v in pc.items() if k not in ('poly', 'pts')}
        r['pts_new'] = [[round(x, 4), round(y, 4)] for x, y in list(pc['poly'].exterior.coords)[:-1]]
        recs.append(r)
    json.dump(dict(frame=dict(lattice=NEW, board=dict(du=BOARD_DU, dv=BOARD_DV)), n=len(recs), drops=drops, colour=n_col, pieces=recs),
              open(os.path.join(args.out_dir, args.name + '.json'), 'w'))
    # coverage per bay on the NEW lattice
    resolved = None
    if args.resolved_masks:
        resolved = np.zeros((3693, 14857), bool)
        for d in args.resolved_masks:
            meta = json.load(open(os.path.join(d, 'meta.json'))); m = np.array(Image.open(os.path.join(d, 'mask.png'))) > 0
            px0, py0 = int(meta.get('px0', 0)), int(meta.get('py0', 0))
            h, w = m.shape
            # the tile may start before the grid origin (the pano's south edge is 29 px above it)
            y0, x0 = max(py0, 0), max(px0, 0); y1, x1 = min(py0 + h, resolved.shape[0]), min(px0 + w, resolved.shape[1])
            resolved[y0:y1, x0:x1] |= m[y0 - py0:y1 - py0, x0 - px0:x1 - px0]
    table = {}
    tree = STRtree(polys)
    for i in range(NB_U):
        for j in range(NB_V):
            bu0 = max(NEW['hu0'] + i * NEW['PU'], PLATE['hu0']); bu1 = min(NEW['hu0'] + (i + 1) * NEW['PU'], PLATE['hu1'])
            b = box(bu0, NEW['hv0'] + j * NEW['PV'], bu1, NEW['hv0'] + (j + 1) * NEW['PV'])
            idx = tree.query(b)
            inside = [k for k in idx if polys[k].centroid.within(b)]
            glass = sum(polys[k].area for k in inside)
            by_src = {}
            for k in inside:
                by_src[kept[k]['source']] = by_src.get(kept[k]['source'], 0) + 1
            row = dict(pieces=len(inside), glass_m2=round(glass, 2), cover=round(glass / b.area, 3), by_source=by_src)
            if resolved is not None:
                # the bay box in grid px (the grid is hall metres)
                x0 = int((bu0 - GRID['hu0']) * 1000 / GRID['mm']); x1 = int((bu1 - GRID['hu0']) * 1000 / GRID['mm'])
                y0 = int((NEW['hv0'] + j * NEW['PV'] - GRID['hv0']) * 1000 / GRID['mm']); y1 = int((NEW['hv0'] + (j + 1) * NEW['PV'] - GRID['hv0']) * 1000 / GRID['mm'])
                row['resolved'] = round(float(resolved[max(y0, 0):y1, max(x0, 0):x1].mean()), 3)
            table[f'{i},{j}'] = row
    json.dump(table, open(os.path.join(args.out_dir, args.name + '-coverage.json'), 'w'), indent=1)
    print('bay   pieces  glass m2  cover  resolved  sources')
    for k, r in table.items():
        print(f"{k:5s} {r['pieces']:6d} {r['glass_m2']:8.2f} {r['cover']:6.1%} {r.get('resolved', float('nan')):8.1%}  {r['by_source']}")
    print(f'wrote {out_bin} ({nb} bytes, {len(kept)} pieces)')


if __name__ == '__main__':
    main()
