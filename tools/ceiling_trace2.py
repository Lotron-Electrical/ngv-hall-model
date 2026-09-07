"""Trace the slabs of the canopy from any ortho tile on the 4 mm huv grid, either way up.

The slabs read two ways: from the ROOF VOID they are dark glass set in white concrete (topside
orthos), from the HALL they are bright glass in a near-black matrix (underside orthos, the bake,
registered photographs). The geometry is the same; only the polarity flips, so one tracer serves
both. Every polygon it writes carries where it came from (source name, gsd at its centroid, the
tile's registration state), so the pane file can say for every slab which image shaped it.

Method, per tile (mm per px from the tile meta, 4 mm on this grid):
  1. local matrix level: a 250 mm max/min envelope, blurred; glassness = (matrix - g) / contrast for
     the topside and (g - matrix) / contrast for the underside; a slab is glassness > THR with the
     local contrast above a floor (a smeared cell has no contrast and traces nothing: no slab is
     invented where the image is mush)
  2. clean (open 3x3, fill holes), split touching slabs at their necks (distance-transform
     watershed, h-maxima), merge back the pairs whose neck is at least NECK of the smaller part's
     inscribed radius (the same rule tools/trace_pieces.py settled on for the bake)
  3. drop what is not a slab: under 45 mm equivalent diameter, longer than 800 mm (a member),
     thinner than 28 mm inscribed, or more than half inside a steel band of the lattice (the
     bands are cut out of a slab that merely touches one, as merge_panes.py does)
  4. polygonise (approxPolyDP at EPS_MM, 3..12 vertices, convex hull when the result is not
     convex, because the viewer fan-triangulates every pane)
  5. write pieces as hu/hv metres with source, gsd, area, eq diameter, shape class and the tile's
     registration note. --lattice says which lattice the tile's metres are on: 'new' (default) for
     anything rendered from posed cameras in the hall frame (topside, underside, registered photos:
     their pixels ARE hall metres, the steel bands are the viewer's NEW lattice, no remap later);
     'old' only for the bake ortho, whose pixels were aligned to the OLD 7.4285 x 7.3855 lattice and
     must be remapped by tools/ceiling_assemble.py (the reason merge_panes.py remaps).

    python tools/ceiling_trace2.py --tile <dir with tile.png mask.png gsd.npy meta.json> --side top|under
        --name <source name> --out <json> [--preview <jpg>] [--thr 0.45] [--x0 --y0 --w --h : a window]

Output json: {"source":..., "side":..., "mm_per_px":..., "grid": {...}, "pieces":[{"pts":[[hu,hv],...],
"area_m2":..., "eqd_mm":..., "gsd_mm":..., "glassness":..., "shape": "rect|tri|irregular", "colour": [r,g,b]|null}]}
Colour is the median of the tile's own pixels inside the slab (meaningful for underside tiles; a
topside colour is the concrete-side grey and is written as null).
"""
import argparse
import json
import os
import sys

import cv2
import numpy as np
from PIL import Image
from scipy import ndimage as ndi
from skimage.morphology import h_maxima
from skimage.segmentation import watershed

Image.MAX_IMAGE_PIXELS = None
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import trackA_geom as G

GRID = dict(hu0=-56.635125, hv0=0.15882, mm=4.0)
LATTICES = dict(old=dict(PU=7.4285, PV=7.3855, HU0=-45.492375, HV0=11.237070),
                new=dict(PU=7.36, PV=7.50, HU0=-45.321133, HV0=11.294317))   # funnel-vertex phase each
LAT = LATTICES['new']
THR = 0.45
CONTRAST_MIN = 25.0
NECK = 0.85            # tuned on the ortho-walk window 2026-09-08: 0.55 left the emblem rows' rectangles bridged
H_MAX_PX = 1.0
EPS_MM = 9.0
MIN_EQD_MM, MAX_LEN_MM, MIN_INSCRIBED_MM = 45.0, 800.0, 28.0
BAND_RIDGE, BAND_OTHER = 0.125, 0.090      # merge_panes' steel bands: half-widths in metres


def load_tile(d, window=None):
    meta = json.load(open(os.path.join(d, 'meta.json')))
    # a tile dir is either a photo tile (tile.png) or an agent's whole-plate render (ortho.png)
    name = 'tile.png' if os.path.exists(os.path.join(d, 'tile.png')) else 'ortho.png'
    im = Image.open(os.path.join(d, name)); mk = Image.open(os.path.join(d, 'mask.png'))
    px0, py0 = int(meta.get('px0', 0)), int(meta.get('py0', 0))
    if window:
        x, y, w, h = window
        im = im.crop((x, y, x + w, y + h)); mk = mk.crop((x, y, x + w, y + h))
    img = np.array(im.convert('RGB')); mask = np.array(mk) > 0
    gsd = np.load(os.path.join(d, 'gsd.npy'), mmap_mode='r') if os.path.exists(os.path.join(d, 'gsd.npy')) else None
    if window:
        gsd = np.array(gsd[y:y + h, x:x + w]) if gsd is not None else np.full(mask.shape, np.nan, np.float32)
        px0 += x; py0 += y
    elif gsd is None:
        gsd = np.full(mask.shape, np.nan, np.float32)
    return img, mask, gsd, meta, px0, py0


def glassness(gray, mask, side, mpp):
    k = max(3, int(250 / mpp) | 1)
    hi = cv2.GaussianBlur(cv2.dilate(gray, np.ones((7, 7), np.uint8)), (0, 0), k / 3)
    lo = cv2.GaussianBlur(cv2.erode(gray, np.ones((7, 7), np.uint8)), (0, 0), k / 3)
    contrast = np.maximum(hi - lo, 1.0)
    gl = (hi - gray) / contrast if side == 'top' else (gray - lo) / contrast
    gl[~mask] = 0
    return gl, contrast


def split_necks(binary, mpp):
    """Distance-transform watershed at the necks, then merge back every pair whose neck is at least
    NECK of the smaller part's inscribed radius. One pass over the boundary pairs with a union-find,
    props measured once: the first version re-measured every label after every merge and took
    minutes on an underside window full of streak slivers."""
    dist = ndi.distance_transform_edt(binary)
    peaks = h_maxima(dist, H_MAX_PX)
    markers, n = ndi.label(peaks)
    if n == 0:
        return ndi.label(binary)[0]
    lab = watershed(-dist, markers, mask=binary)
    nl = int(lab.max())
    if nl == 0:
        return lab
    # inscribed radius per label, measured once
    radius = ndi.maximum(dist, lab, index=np.arange(1, nl + 1))
    radius = np.concatenate([[0.0], radius])
    # neck between a and b: the largest distance value on the pixels where the two labels touch
    neck = {}
    for a, b, da, db in ((lab[:, :-1], lab[:, 1:], dist[:, :-1], dist[:, 1:]), (lab[:-1, :], lab[1:, :], dist[:-1, :], dist[1:, :])):
        t = (a != b) & (a > 0) & (b > 0)
        if not t.any():
            continue
        pa, pb = a[t], b[t]
        lo, hi = np.minimum(pa, pb), np.maximum(pa, pb)
        d = np.maximum(da[t], db[t])
        key = lo.astype(np.int64) * (nl + 1) + hi
        order = np.argsort(key)
        key, d = key[order], d[order]
        first = np.r_[True, key[1:] != key[:-1]]
        seg_max = np.maximum.reduceat(d, np.flatnonzero(first))
        for k, m in zip(key[first], seg_max):
            neck[int(k)] = max(neck.get(int(k), 0.0), float(m))
    parent = np.arange(nl + 1)

    def find(x):
        while parent[x] != x:
            parent[x] = parent[parent[x]]
            x = parent[x]
        return x
    for k, m in neck.items():
        lo, hi = divmod(k, nl + 1)
        if m >= NECK * min(radius[lo], radius[hi]):
            ra, rb = find(lo), find(hi)
            if ra != rb:
                parent[max(ra, rb)] = min(ra, rb)
    roots = np.array([find(i) for i in range(nl + 1)])
    return roots[lab]


def steel_band(hu, hv):
    """distance-based: inside the ridge band or the cross / hip / diamond band of the chosen lattice
    (both diamonds, the shader's and the true midpoint one, as merge_panes.py keeps clear of both)."""
    PU, PV = LAT['PU'], LAT['PV']
    du = (hu - LAT['HU0']) / PU; dv = (hv - LAT['HV0']) / PV
    fu = du - np.round(du); fv = dv - np.round(dv)         # offset from the nearest vertex, in modules
    d_ridge = np.minimum(np.abs(np.abs(fu) - 0.5) * PU, np.abs(np.abs(fv) - 0.5) * PV)
    d_cross = np.minimum(np.abs(fu) * PU, np.abs(fv) * PV)
    x, y = fu * PU, fv * PV
    d_hip = np.abs(np.abs(x) - np.abs(y)) * 0.7071
    d_dia1 = np.abs(np.abs(x) + np.abs(y) - PU / 2) * 0.7071
    d_dia2 = np.abs(np.abs(x) * 2 / PU + np.abs(y) * 2 / PV - 1) / np.hypot(2 / PU, 2 / PV)
    return (d_ridge < BAND_RIDGE) | (d_cross < BAND_OTHER) | (d_hip < BAND_OTHER) | (d_dia1 < BAND_OTHER) | (d_dia2 < BAND_OTHER)


def polygonise(sub, eps_px):
    cnts, _ = cv2.findContours(sub.astype(np.uint8), cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    if not cnts:
        return None
    c = max(cnts, key=cv2.contourArea)
    ap = cv2.approxPolyDP(c, eps_px, True).reshape(-1, 2)
    if len(ap) < 3:
        return None
    if len(ap) > 12 or not cv2.isContourConvex(ap.reshape(-1, 1, 2)):
        ap = cv2.convexHull(ap).reshape(-1, 2)
        if len(ap) > 12:
            ap = cv2.approxPolyDP(ap.reshape(-1, 1, 2), eps_px * 1.5, True).reshape(-1, 2)
    return ap.astype(float)


def shape_class(sub, ap):
    area = float(sub.sum())
    (cx, cy), (w, h), ang = cv2.minAreaRect(np.argwhere(sub)[:, ::-1].astype(np.float32))
    fill = area / max(w * h, 1)
    hull = cv2.convexHull(np.argwhere(sub)[:, ::-1].astype(np.int32))
    sol = area / max(cv2.contourArea(hull), 1)
    # a blurred corner costs a vertex at 4 mm/px, so the fill decides, not the vertex count
    if fill > 0.78 and len(ap) <= 6:
        return 'rect'
    if len(ap) == 3 or (fill < 0.62 and sol > 0.9 and len(ap) <= 4):
        return 'tri'
    return 'irregular'


def trace(img, mask, gsd, meta, px0, py0, side, name, thr=THR, absolute=None):
    mpp = GRID['mm']
    gray = cv2.cvtColor(img, cv2.COLOR_RGB2GRAY).astype(np.float32)
    if absolute is not None:
        # a source whose steel is clipped to black (the NGV panorama: steel exactly 0): a slab is any
        # pixel whose brightest channel clears the threshold, so dark purples and blues count too.
        # gl is kept as the record of how far above the threshold the slab sits.
        vmax = img.max(axis=2).astype(np.float32)
        gl = vmax / absolute
        binary = (vmax > absolute) & mask
    else:
        gl, contrast = glassness(gray, mask, side, mpp)
        binary = (gl > thr) & (contrast > CONTRAST_MIN) & mask
    binary = cv2.morphologyEx(binary.astype(np.uint8), cv2.MORPH_OPEN, np.ones((3, 3), np.uint8)) > 0
    binary = ndi.binary_fill_holes(binary)
    # members are long: take them out before the watershed so they do not seed a hundred slivers
    lab0, n0 = ndi.label(binary)
    for i, sl in enumerate(ndi.find_objects(lab0), 1):
        if sl is None:
            continue
        if max(sl[0].stop - sl[0].start, sl[1].stop - sl[1].start) * mpp > MAX_LEN_MM:
            binary[lab0 == i] = False
    lab = split_necks(binary, mpp)
    H, W = mask.shape
    yy, xx = np.mgrid[0:H, 0:W]
    hu_px = GRID['hu0'] + (px0 + xx + 0.5) * mpp / 1000
    hv_px = GRID['hv0'] + (py0 + yy + 0.5) * mpp / 1000
    band = steel_band(hu_px, hv_px)
    pieces = []
    eps_px = EPS_MM / mpp
    for i, sl in enumerate(ndi.find_objects(lab), 1):
        if sl is None:
            continue
        sub = (lab[sl] == i)
        area_px = float(sub.sum())
        eqd = 2 * np.sqrt(area_px / np.pi) * mpp
        if eqd < MIN_EQD_MM:
            continue
        b = band[sl]
        if (sub & b).sum() > 0.5 * area_px:
            continue
        sub = sub & ~b                                       # the band is cut out of a slab that touches it
        if sub.sum() * mpp * mpp < (MIN_EQD_MM / 2) ** 2 * np.pi:
            continue
        if ndi.distance_transform_edt(np.pad(sub, 1)).max() * mpp * 2 < MIN_INSCRIBED_MM:
            continue
        ap = polygonise(sub, eps_px)
        if ap is None:
            continue
        ys, xs = np.where(sub)
        cy, cx = ys.mean(), xs.mean()
        g_here = gsd[sl][sub]; g_here = g_here[np.isfinite(g_here)]
        pts = [[float(GRID['hu0'] + (px0 + sl[1].start + x) * mpp / 1000), float(GRID['hv0'] + (py0 + sl[0].start + y) * mpp / 1000)] for x, y in ap]
        # counter-clockwise in (hu, hv) as the NGVP writer expects
        a2 = 0.0
        for k in range(len(pts)):
            x1, y1 = pts[k]; x2, y2 = pts[(k + 1) % len(pts)]
            a2 += x1 * y2 - x2 * y1
        if a2 < 0:
            pts = pts[::-1]
        col = None
        if side == 'under':
            px = img[sl][sub]
            col = [int(v) for v in np.median(px, axis=0)]
        pieces.append(dict(pts=[[round(p[0], 4), round(p[1], 4)] for p in pts], area_m2=round(float(sub.sum()) * mpp * mpp * 1e-6, 5),
                           eqd_mm=round(float(eqd), 1), gsd_mm=round(float(np.median(g_here) * 1000), 1) if len(g_here) else None,
                           glassness=round(float(gl[sl][sub].mean()), 3), shape=shape_class(sub, ap), colour=col,
                           source=name, side=side))
    return pieces, lab


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('--tile', required=True)
    ap.add_argument('--side', required=True, choices=['top', 'under'])
    ap.add_argument('--name', required=True)
    ap.add_argument('--out', required=True)
    ap.add_argument('--preview', default='')
    ap.add_argument('--thr', type=float, default=THR)
    ap.add_argument('--absolute', type=float, default=None, help='slab = max(R,G,B) > this (sources whose steel is black)')
    ap.add_argument('--window', default='', help='x,y,w,h in tile px')
    ap.add_argument('--lattice', default='new', choices=['new', 'old'])
    args = ap.parse_args()
    global LAT
    LAT = LATTICES[args.lattice]
    window = [int(v) for v in args.window.split(',')] if args.window else None
    img, mask, gsd, meta, px0, py0 = load_tile(args.tile, window)
    pieces, lab = trace(img, mask, gsd, meta, px0, py0, args.side, args.name, args.thr, args.absolute)
    cover = sum(p['area_m2'] for p in pieces) / max(mask.sum() * GRID['mm'] ** 2 * 1e-6, 1e-9)
    print(f'{args.name}: {len(pieces)} pieces, {cover:.1%} of the covered area, median eq diameter {np.median([p["eqd_mm"] for p in pieces]) if pieces else 0:.0f} mm')
    json.dump(dict(source=args.name, side=args.side, lattice=args.lattice, mm_per_px=GRID['mm'], grid=GRID, tile=args.tile, window=window,
                   registration=meta.get('registration', meta.get('reprojection', None)), n=len(pieces), cover_of_mask=cover, pieces=pieces),
              open(args.out, 'w'))
    if args.preview:
        vis = img.copy()[..., ::-1].copy()
        for p in pieces:
            pts = np.array([[(x - GRID['hu0']) * 1000 / GRID['mm'] - px0, (y - GRID['hv0']) * 1000 / GRID['mm'] - py0] for x, y in p['pts']], np.int32)
            cv2.polylines(vis, [pts.reshape(-1, 1, 2)], True, (0, 255, 0) if p['shape'] != 'irregular' else (0, 200, 255), 1)
        cv2.imwrite(args.preview, vis, [cv2.IMWRITE_JPEG_QUALITY, 88])


if __name__ == '__main__':
    main()
