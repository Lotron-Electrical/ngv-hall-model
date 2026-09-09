"""Trace the glass pieces of the canopy from the bottom ortho and write an NGVP pane file (track B, goal 2).

Input: the ortho written by tools/ceiling_ortho.py (bottom-ortho.png, bottom-meta.json, quality.npy,
coverage.png in --src). Output (in --out, the scratch folder by default):
    pieces-atlas.bin        NGVP: 'NGVP', u32 count, f32 u0, f32 v0, u16 scale (1000 = mm), then per piece
                            u8 r,g,b,k and k x (u16 u, u16 v) in mm relative to (u0, v0), BOARD frame
                            (uu = hu + 58.3053, vv = hv + 0.4556), counter-clockwise in (u, v), convex
    pieces-atlas.json       per-piece records (bay, cell class, area, eq diameter, colour, flags) + the report
    pieces-atlas-all.bin    the same with the smeared cells (class 2) traced too (blurrier pieces, flagged)
    pieces-atlas-merged.bin (--second) the primary plus, in cells the primary cannot trace, pieces from
                            the second bake (v29), with overlaps rejected
    overlay-full.jpg        every polygon drawn over the ortho (2000 px wide)
    overlay-crop-*.jpg      three 1:1 crops (4 m windows at the ortho's 5 mm/px) with the polygons, the
                            window with the most traceable cells in each of three bays; non-traced
                            cells boxed (purple not glass, red smeared, orange artefact)
    coverage-bays.png       per-bay traceable share / pieces / coverage summary image

Method (all at the ortho's 5 mm/px):
  1. local matrix level bg = blur(min-filter 205 mm) of grey, local piece level hi = blur(max-filter 205 mm);
     glass = grey > bg + max(22, THR_FRAC (hi - bg))  OR  chroma > 32 and grey > bg + 10
  2. clean (open 3x3, fill holes), over-segment at the necks (distance transform, h-maxima h = 1.5 px,
     watershed on -distance), then merge back every pair whose neck is at least NECK_RATIO of the
     smaller part's inscribed radius (a blurred piece has no neck; two pieces bridged by blur do).
     --split intensity is the alternative (brightness watershed, saddle-depth merge, then the neck
     test); on this bake it found fewer pieces (1756 vs 1995 in the same cells) so distance is default
  3. polygonise: findContours + approxPolyDP at EPS_MM (9 mm), 3..12 vertices; a non-convex or
     self-crossing result is replaced by its convex hull (the viewer fan-triangulates every pane)
  4. joints: the lattice's steel joints (bay ridge 0.20 m, cross / X / diamond 0.12 m) hold no glass;
     a piece more than half inside a joint band is dropped, otherwise the band is cut out of it
  5. gates: equivalent diameter 45..700 mm, inscribed width >= 28 mm; the 0.5 m cell under the
     centroid must be class 4 (traceable) in quality.npy, or class 3 (artefact) with the piece
     clear of the per-pixel defect evidence (artefact_mask: 1-px step edges, black texels, the
     coverage edge, grown 40 mm) and solid (area / hull >= 0.8); class 2 too for the -all file.
     Cut-outs (bright rim, dark body), streaks (aspect > 4) and white slabs > 350 mm are dropped
  6. colour: median RGB of the interior (eroded 2 px), then HSV lift (COLOUR_LIFT) so the bake's
     washed-out tones match the reference photographs (see --calib)
Reporting: CORE figures (coverage, pieces/m2, median) are over whole class-4 cells only, so they
compare like for like with a reference photograph; artefact-cell pieces are listed as EXTRA.
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
from scipy import ndimage as ndi
from skimage.morphology import h_maxima
from skimage.segmentation import watershed

Image.MAX_IMAGE_PIXELS = None
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import ceiling_ortho as co

BOARD_DU, BOARD_DV = 58.3053, 0.4556        # uu = hu + BOARD_DU, vv = hv + BOARD_DV (index.html BOARD)
MIN_EQ_MM, MAX_EQ_MM = 45.0, 700.0
MIN_WIDTH_MM = 28.0                          # widest inscribed circle of a piece
BIG_MM = 350.0                               # above this a piece is flagged 'big' (a white one is dropped)
EPS_MM = 9.0
MAX_VERTS = 12
MIN_PX = 40                                  # components smaller than this never become pieces
H_MAXIMA_PX = 1.5
NECK_RATIO = 0.88
THR_FRAC = 0.42                              # glass = grey above bg + THR_FRAC x local contrast (or + 22 grey levels)
SPLIT = 'distance'                           # 'distance' (neck test on the distance transform) or 'intensity' (brightness
                                             # watershed then the neck test): on this bake intensity found FEWER pieces
                                             # (1756 vs 1995 in the same cells, same median) so distance stays the default
INT_H_LEVEL = 6.0                            # marker h-maxima on the smoothed grey (grey levels)
INT_DIP_FRAC = 0.22                          # a saddle shallower than this share of the lower peak's height = one slab
INT_DIP_MIN = 8.0                            # ... or shallower than this many grey levels
CROP_PX = 800                                # overlay crop window (ortho px, shown 1:1 = 4 m at 5 mm/px)
ART_GROW_MM = 40.0                           # defect evidence grown by this much before the piece test
ART_MAX_SHARE = 0.05                         # a piece in an artefact cell may overlap the grown evidence by this share
ART_MIN_SOLIDITY = 0.80                      # ... and must be this solid (area / convex hull area)
# HSV lift of the bake's piece colours (measured with --calib and on the traced raw colours):
#   bake raw chromatic pieces: S p25/50/75 0.37/0.51/0.69, V 0.51/0.63/0.76; bake clear glass V ~0.69
#   reference bc0db55c (well exposed): S 0.46/0.84/0.92, V 0.79/0.94/0.98; white share 0.30-0.34
# so S x1.7 puts the median at 0.87 and V x1.45 at 0.91; clear glass goes to near white.
COLOUR_LIFT = dict(white_s_max=0.18, white_s_scale=0.5, white_v=0.96, chroma_s_gain=1.7, chroma_v_gain=1.45)
HUE_NAMES = ['red', 'orange', 'yellow', 'yellow-green', 'green', 'green-cyan', 'cyan', 'azure', 'blue', 'violet', 'magenta', 'pink']


# ----------------------------------------------------------------------------- inputs
def load(src, tag):
    img = np.asarray(Image.open(os.path.join(src, 'bottom-ortho%s.png' % tag)).convert('RGB'))
    meta = json.load(open(os.path.join(src, 'bottom-meta%s.json' % tag)))
    q = np.load(os.path.join(src, 'quality%s.npy' % tag))
    cls = q[co.Q_LAYERS.index('class')].astype(np.uint8)
    cov = cv2.imread(os.path.join(src, 'coverage%s.png' % tag), cv2.IMREAD_GRAYSCALE) > 0
    return img, meta, cls, cov


# ----------------------------------------------------------------------------- segmentation
def glass_mask(img, mpp, thr_frac=THR_FRAC):
    """Glass = brighter than the local matrix level by max(22 grey, thr_frac x local contrast), or
    chromatic (chroma > 32) and a little brighter. bg / hi = min / max filtered grey over 205 mm
    (a window wider than any slab, so it always sees matrix and glass), lightly blurred.
    Returns (mask uint8, bg float32, gray uint8)."""
    g = cv2.cvtColor(img, cv2.COLOR_RGB2GRAY)
    chroma = img.max(axis=2).astype(np.int16) - img.min(axis=2).astype(np.int16)
    k = int(round(0.205 / mpp)) | 1
    ker = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (k, k))
    bg = cv2.GaussianBlur(cv2.erode(g, ker), (0, 0), 0.05 / mpp).astype(np.float32)
    hi = cv2.GaussianBlur(cv2.dilate(g, ker), (0, 0), 0.05 / mpp).astype(np.float32)
    gf = g.astype(np.float32)
    bright = gf > bg + np.maximum(22.0, thr_frac * (hi - bg))
    colour = (chroma > 32) & (gf > bg + 10)
    del hi, gf, chroma
    m = (bright | colour).astype(np.uint8)
    del bright, colour
    m = cv2.morphologyEx(m, cv2.MORPH_OPEN, np.ones((3, 3), np.uint8))
    m = ndi.binary_fill_holes(m).astype(np.uint8)
    return m, bg, g


def _boundary_pairs(labels, field, n):
    """For every pair of touching regions: the saddle of `field` across their shared boundary
    (max over boundary pixel pairs of min(field_a, field_b)). Returns (la, lb, saddle)."""
    pairs = []
    for a, b, d in ((labels[:, :-1], labels[:, 1:], np.minimum(field[:, :-1], field[:, 1:])),
                    (labels[:-1, :], labels[1:, :], np.minimum(field[:-1, :], field[1:, :]))):
        sel = (a != b) & (a > 0) & (b > 0)
        lo = np.minimum(a[sel], b[sel]).astype(np.int64); hi = np.maximum(a[sel], b[sel]).astype(np.int64)
        pairs.append((lo * (n + 1) + hi, d[sel]))
    key = np.concatenate([p[0] for p in pairs]); dv = np.concatenate([p[1] for p in pairs])
    uk, inv = np.unique(key, return_inverse=True)
    saddle = np.zeros(uk.size, np.float32)
    np.maximum.at(saddle, inv, dv)
    return (uk // (n + 1)).astype(np.int64), (uk % (n + 1)).astype(np.int64), saddle


def _merge_labels(labels, n, la, lb, merge):
    """Union-find merge of the label pairs flagged in `merge`; returns (dense labels, n merges)."""
    parent = np.arange(n + 1)

    def find(x):
        while parent[x] != x:
            parent[x] = parent[parent[x]]
            x = parent[x]
        return x
    nmerge = 0
    for a, b in zip(la[merge], lb[merge]):
        ra, rb = find(a), find(b)
        if ra != rb:
            parent[max(ra, rb)] = min(ra, rb)
            nmerge += 1
    roots = np.array([find(i) for i in range(n + 1)])
    _, dense = np.unique(roots, return_inverse=True)
    dense[0] = 0
    return dense[labels].astype(np.int32), nmerge


def split_pieces(mask, h_px=H_MAXIMA_PX, neck_ratio=NECK_RATIO):
    """Label the mask. Over-segment at every dip of the distance transform (h-maxima markers,
    watershed on -distance), then merge the pairs whose shared boundary is not a neck."""
    dist = ndi.distance_transform_edt(mask).astype(np.float32)
    hm = h_maxima(dist, h_px)
    markers, nm = ndi.label(hm)
    labels = watershed(-dist, markers, mask=mask.astype(bool)).astype(np.int32)
    n = int(labels.max())
    if n == 0:
        return labels, 0, 0
    rad = ndi.maximum(dist, labels, index=np.arange(1, n + 1))           # inscribed radius per region
    rad = np.concatenate([[0.0], rad])
    la, lb, neck = _boundary_pairs(labels, dist, n)
    merge = neck >= neck_ratio * np.minimum(rad[la], rad[lb])
    labels, nmerge = _merge_labels(labels, n, la, lb, merge)
    return labels, n, nmerge


def split_pieces_intensity(mask, gray, bg, h_level=INT_H_LEVEL, dip_frac=INT_DIP_FRAC, dip_min=INT_DIP_MIN, smooth_px=1.0):
    """Split on the BRIGHTNESS, not the shape: two slabs bridged by blur are two bright bodies with a
    dimmer saddle between them (the concrete gap, 30-60 mm, blurred but never as bright as the
    glass), whereas one slab is one body with no dip. Markers = h-maxima (h_level grey levels) of
    the lightly smoothed grey inside the mask; watershed on -grey; then every touching pair whose
    saddle is within dip_min grey levels, or dip_frac of the lower peak's height above the local
    matrix level, of that peak is merged back (no real dip). Falls back to the distance-transform
    neck test afterwards for the bright-bridged pairs the intensity cannot separate."""
    g = cv2.GaussianBlur(gray.astype(np.float32), (0, 0), smooth_px)
    g[mask == 0] = 0
    hm = h_maxima(g, h_level)
    hm &= mask.astype(bool)
    markers, nm = ndi.label(hm)
    labels = watershed(-g, markers, mask=mask.astype(bool)).astype(np.int32)
    n = int(labels.max())
    if n == 0:
        return labels, 0, 0
    idx = np.arange(1, n + 1)
    peak = np.concatenate([[0.0], ndi.maximum(g, labels, index=idx)])
    bgl = np.concatenate([[0.0], ndi.mean(bg, labels, index=idx)])
    la, lb, saddle = _boundary_pairs(labels, g, n)
    lowpeak = np.minimum(peak[la], peak[lb])
    height = lowpeak - np.minimum(bgl[la], bgl[lb])
    dip = lowpeak - saddle
    merge = dip < np.maximum(dip_min, dip_frac * height)
    labels, nmerge = _merge_labels(labels, n, la, lb, merge)
    return labels, n, nmerge


# ----------------------------------------------------------------------------- polygons
def is_convex(pts):
    n = len(pts)
    if n < 3:
        return False
    sgn = 0
    for i in range(n):
        a, b, c = pts[i], pts[(i + 1) % n], pts[(i + 2) % n]
        cr = (b[0] - a[0]) * (c[1] - b[1]) - (b[1] - a[1]) * (c[0] - b[0])
        if abs(cr) < 1e-9:
            continue
        s = 1 if cr > 0 else -1
        if sgn == 0:
            sgn = s
        elif s != sgn:
            return False
    return True


def polygonise(sub, eps_px):
    """Contour of a single-piece mask -> convex polygon with 3..MAX_VERTS vertices (pixel coords,
    float, relative to the sub-image origin) or None."""
    cs, _ = cv2.findContours(sub, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_NONE)
    if not cs:
        return None
    c = max(cs, key=cv2.contourArea)
    if cv2.contourArea(c) < 4:
        return None
    e = eps_px
    for _ in range(6):
        ap = cv2.approxPolyDP(c, e, True).reshape(-1, 2).astype(np.float64)
        if 3 <= len(ap) <= MAX_VERTS and is_convex(ap):
            return ap
        if len(ap) > MAX_VERTS:
            e *= 1.4
            continue
        break
    hull = cv2.convexHull(c).reshape(-1, 2)
    e = eps_px
    for _ in range(8):
        ap = cv2.approxPolyDP(hull.reshape(-1, 1, 2), e, True).reshape(-1, 2).astype(np.float64)
        if 3 <= len(ap) <= MAX_VERTS:
            return ap if is_convex(ap) else cv2.convexHull(ap.astype(np.float32)).reshape(-1, 2).astype(np.float64)
        e *= 1.4
    return None


def shoelace(p):
    x, y = p[:, 0], p[:, 1]
    return 0.5 * float(np.dot(x, np.roll(y, -1)) - np.dot(y, np.roll(x, -1)))


# ----------------------------------------------------------------------------- colour
def lift_colour(rgb, L=COLOUR_LIFT):
    r, g, b = [c / 255.0 for c in rgb]
    h, s, v = colorsys.rgb_to_hsv(r, g, b)
    if s < L['white_s_max']:
        s2 = s * L['white_s_scale']
        v2 = max(v, L['white_v'])
    else:
        s2 = min(1.0, s * L['chroma_s_gain'])
        v2 = min(1.0, v * L['chroma_v_gain'])
    r2, g2, b2 = colorsys.hsv_to_rgb(h, s2, v2)
    return (int(round(r2 * 255)), int(round(g2 * 255)), int(round(b2 * 255)))


def hue_bucket12(rgb):
    r, g, b = [c / 255.0 for c in rgb]
    h, s, v = colorsys.rgb_to_hsv(r, g, b)
    if s < 0.18:
        return 'white/grey'
    return HUE_NAMES[min(11, int(((h * 360 + 15) % 360) / 30))]


def calib(paths):
    """Piece colour statistics of reference photographs (black matrix, backlit glass): S / V of the
    chromatic pieces and the share of white pieces, for setting COLOUR_LIFT."""
    for p in paths:
        im = np.asarray(Image.open(p).convert('RGB'))
        if max(im.shape[:2]) > 2600:
            f = 2600 / max(im.shape[:2])
            im = cv2.resize(im, (int(im.shape[1] * f), int(im.shape[0] * f)), interpolation=cv2.INTER_AREA)
        g = cv2.cvtColor(im, cv2.COLOR_RGB2GRAY)
        m = (g > 90).astype(np.uint8)
        m = cv2.morphologyEx(m, cv2.MORPH_OPEN, np.ones((3, 3), np.uint8))
        lab, n = ndi.label(m)
        sizes = ndi.sum(m, lab, range(1, n + 1))
        S, V, W = [], [], 0
        for i, sz in enumerate(sizes, 1):
            if sz < 30:
                continue
            sel = lab == i
            med = np.median(im[sel], axis=0)
            h, s, v = colorsys.rgb_to_hsv(*(med / 255.0))
            if s < 0.18:
                W += 1
            else:
                S.append(s); V.append(v)
        if S:
            print('%s: %d pieces, white share %.2f, chromatic S p25/50/75 %s, V p25/50/75 %s' % (
                os.path.basename(p), len(S) + W, W / (len(S) + W), np.percentile(S, [25, 50, 75]).round(2), np.percentile(V, [25, 50, 75]).round(2)))


# ----------------------------------------------------------------------------- artefact evidence
def artefact_mask(gray, cov, mpp, grow_mm=ART_GROW_MM):
    """Per-pixel bake defects, grown by grow_mm: 1-px step edges (the seams of mis-projected patches
    and cut-outs; a real glass edge in this bake is 12-15 mm wide and survives a 1.2 px blur), near
    black texels (missing texture) and the edge of the atlas coverage. A piece in an 'artefact' cell
    is kept only when it stays clear of this mask (see trace_source)."""
    g = gray.astype(np.float32)
    gx = cv2.Sobel(g, cv2.CV_32F, 1, 0, ksize=3) / 8; gy = cv2.Sobel(g, cv2.CV_32F, 0, 1, ksize=3) / 8
    g0 = np.hypot(gx, gy); del gx, gy
    gb = cv2.GaussianBlur(g, (0, 0), 1.2); del g
    gx = cv2.Sobel(gb, cv2.CV_32F, 1, 0, ksize=3) / 8; gy = cv2.Sobel(gb, cv2.CV_32F, 0, 1, ksize=3) / 8
    g1 = np.hypot(gx, gy); del gx, gy, gb
    m = ((g0 > 14) & (g0 > 2.0 * (g1 + 1.0))).astype(np.uint8)
    del g0, g1
    m |= (gray < 15).astype(np.uint8)
    m |= (~cov).astype(np.uint8)
    k = int(round(grow_mm / 1000.0 / mpp)) * 2 + 1
    return cv2.dilate(m, np.ones((k, k), np.uint8)) > 0


# ----------------------------------------------------------------------------- tracing one source
def trace_source(img, meta, cls, cov, name, keep_classes=(4,), log=print, split=SPLIT, thr_frac=THR_FRAC):
    """All pieces of one ortho whose centroid cell is in keep_classes. Returns (pieces, counts)."""
    t0 = time.time()
    H, W = img.shape[:2]
    mpp = meta['mm_per_px'] / 1000.0
    hu0, hv0 = meta['hu0'], meta['hv0']
    cell = int(round(co.CELL_M / mpp))
    mask, bg, gray = glass_mask(img, mpp, thr_frac)
    mask[~cov] = 0
    log('%s: glass mask %.1f%% of the plate (%.1fs)' % (name, 100 * mask.mean(), time.time() - t0))
    if split == 'intensity':
        labels, nws, nmerge = split_pieces_intensity(mask, gray, bg)
        log('%s: intensity watershed %d regions, %d no-dip merges -> %d regions (%.1fs)' % (name, nws, nmerge, int(labels.max()), time.time() - t0))
        # second pass: the neck test on each region (a bright bridge between two slabs shows no dip
        # but does show a waist); done per region so the distance transform is local to it
        dist = ndi.distance_transform_edt(labels > 0).astype(np.float32)
        hm = h_maxima(dist, H_MAXIMA_PX)
        sub_markers, _ = ndi.label(hm)
        sub = watershed(-dist, sub_markers, mask=labels > 0).astype(np.int32)
        # a sub-region is a (label, sub) pair; keep the split only where it lies inside one label
        key = labels.astype(np.int64) * (int(sub.max()) + 1) + sub
        _, dense = np.unique(key, return_inverse=True)
        sub = dense.reshape(labels.shape).astype(np.int32)
        sub[labels == 0] = 0
        _, dense = np.unique(sub, return_inverse=True)
        sub = dense.reshape(labels.shape).astype(np.int32)
        n2 = int(sub.max())
        rad = np.concatenate([[0.0], ndi.maximum(dist, sub, index=np.arange(1, n2 + 1))])
        la, lb, neck = _boundary_pairs(sub, dist, n2)
        merge = neck >= NECK_RATIO * np.minimum(rad[la], rad[lb])
        labels, nm2 = _merge_labels(sub, n2, la, lb, merge)
        del dist, hm, sub_markers, sub, key
        log('%s: neck pass %d sub-regions, %d merges -> %d regions (%.1fs)' % (name, n2, nm2, int(labels.max()), time.time() - t0))
        nws = n2
    else:
        labels, nws, nmerge = split_pieces(mask)
        log('%s: %d watershed regions, %d neck merges -> %d regions (%.1fs)' % (name, nws, nmerge, int(labels.max()), time.time() - t0))
    nlab = int(labels.max())
    del bg
    joints = co.joint_mask_full(hu0, hv0, mpp, W, H) > 0
    art = artefact_mask(gray, cov, mpp)
    # usable share of every 0.5 m cell: 1 for a traceable cell, the artefact-free share for an
    # artefact cell (its pieces are gated per pixel), 0 otherwise; smeared cells count as 1 when
    # class 2 is traced (the -all file)
    bh, bw = cls.shape
    art_share = art[:bh * cell, :bw * cell].reshape(bh, cell, bw, cell).mean(axis=(1, 3))
    usable = np.zeros(cls.shape, np.float32)
    usable[cls == 4] = 1.0
    usable[cls == 3] = 1.0 - art_share[cls == 3]
    if 2 in keep_classes:
        usable[cls == 2] = 1.0
    log('%s: artefact mask covers %.1f%% of the plate; usable area %.1f m2 (traceable %.1f + artefact-cell remainder %.1f)' % (
        name, 100 * art.mean(), usable.sum() * co.CELL_M ** 2, (cls == 4).sum() * co.CELL_M ** 2, usable[cls == 3].sum() * co.CELL_M ** 2))
    objs = ndi.find_objects(labels)
    eps_px = EPS_MM / (mpp * 1000)
    pieces = []
    counts = dict(regions=nlab, tiny=0, small=0, huge=0, joint_drop=0, joint_clip=0, polygon_fail=0,
                  class_drop=0, artefact_touch=0, ragged=0, thin=0, cutout=0, streak=0, white_big=0, kept=0)
    cls_counts = {}
    for idx, sl in enumerate(objs, 1):
        if sl is None:
            continue
        sub = (labels[sl] == idx)
        area_px = int(sub.sum())
        if area_px < MIN_PX:
            counts['tiny'] += 1
            continue
        y0, x0 = sl[0].start, sl[1].start
        clipped = False
        jshare = float((sub & joints[sl]).sum()) / area_px
        if jshare > 0.5:
            counts['joint_drop'] += 1
            continue
        if jshare > 0.02:
            sub2 = sub & ~joints[sl]
            lab2, n2 = ndi.label(sub2)
            if n2 == 0:
                counts['joint_drop'] += 1
                continue
            sizes = ndi.sum(sub2, lab2, range(1, n2 + 1))
            sub = lab2 == (int(np.argmax(sizes)) + 1)
            area_px = int(sub.sum())
            clipped = True
            counts['joint_clip'] += 1
            if area_px < MIN_PX:
                counts['tiny'] += 1
                continue
        eq_mm = 2 * math.sqrt(area_px / math.pi) * mpp * 1000
        if eq_mm < MIN_EQ_MM:
            counts['small'] += 1
            continue
        if eq_mm > MAX_EQ_MM:
            counts['huge'] += 1
            continue
        ys, xs = np.nonzero(sub)
        cy, cx = ys.mean() + y0, xs.mean() + x0
        ci, cj = min(int(cx // cell), cls.shape[1] - 1), min(int(cy // cell), cls.shape[0] - 1)
        c = int(cls[cj, ci])
        cls_counts[c] = cls_counts.get(c, 0) + 1
        if c not in keep_classes:
            counts['class_drop'] += 1
            continue
        art_share_p = float((sub & art[sl]).sum()) / area_px
        if c == 3:
            # an artefact cell: the piece must stay clear of the defect evidence and look like a slab
            if art_share_p > ART_MAX_SHARE:
                counts['artefact_touch'] += 1
                continue
            hull_a = cv2.contourArea(cv2.convexHull(np.stack(np.nonzero(sub)[::-1], axis=1).astype(np.int32)))
            if hull_a > 0 and area_px / hull_a < ART_MIN_SOLIDITY:
                counts['ragged'] += 1
                continue
        elif art_share_p > 0.5:
            counts['artefact_touch'] += 1
            continue
        dist = ndi.distance_transform_edt(np.pad(sub, 1))
        if dist.max() * 2 * mpp * 1000 < MIN_WIDTH_MM:
            counts['thin'] += 1
            continue
        # cut-outs: a bake artefact where the slab's interior shows the void behind it and only a
        # bright rim survives (grey / black body with a white outline); real slabs are brightest inside
        gsub = gray[sl]
        inner3 = cv2.erode(sub.astype(np.uint8), np.ones((7, 7), np.uint8)) > 0
        if inner3.sum() >= 12:
            ring = sub & ~inner3
            gi, gr = float(np.median(gsub[inner3])), float(np.median(gsub[ring]))
            csub = img[sl]
            ci_ = float(np.median(csub[inner3].max(axis=1).astype(np.int16) - csub[inner3].min(axis=1).astype(np.int16)))
            if gr - gi > 30 and ci_ < 20 and gi < 175:
                counts['cutout'] += 1
                continue
        # smears: a motion-blurred streak is far longer than any slab (real slabs reach ~3:1)
        (rw, rh) = cv2.minAreaRect(np.stack([xs, ys], axis=1).astype(np.float32))[1]
        if min(rw, rh) > 0 and max(rw, rh) / min(rw, rh) > 4.0 and eq_mm > 120:
            counts['streak'] += 1
            continue
        poly = polygonise(sub.astype(np.uint8), eps_px)
        if poly is None:
            counts['polygon_fail'] += 1
            continue
        poly = poly + np.array([x0, y0], np.float64)
        A = shoelace(poly)
        if A < 0:
            poly = poly[::-1]; A = -A
        if A * (mpp * 1000) ** 2 < math.pi * (MIN_EQ_MM / 2) ** 2:
            counts['small'] += 1
            continue
        inner = cv2.erode(sub.astype(np.uint8), np.ones((5, 5), np.uint8)) > 0
        pix = img[sl][inner] if inner.sum() >= 6 else img[sl][sub]
        med = np.median(pix, axis=0)
        raw_rgb = tuple(int(round(v)) for v in med)
        rgb = lift_colour(raw_rgb)
        # a white slab wider than 350 mm does not exist in this ceiling (slabs run 100-250 mm): a white
        # region that big is an over-exposed smear along a crest or a wall ghost
        eq_poly = 2 * math.sqrt(A * mpp * mpp / math.pi) * 1000
        if eq_poly > BIG_MM and colorsys.rgb_to_hsv(*[c / 255.0 for c in raw_rgb])[1] < COLOUR_LIFT['white_s_max']:
            counts['white_big'] += 1
            continue
        hu = hu0 + (poly[:, 0] + 0.5) * mpp
        hv = hv0 + (poly[:, 1] + 0.5) * mpp
        bay_i = int(np.clip((hu.mean() - co.PLATE[0]) // co.PU, 0, co.NB_U - 1))
        bay_j = int(np.clip((hv.mean() - co.PLATE[1]) // co.PV, 0, co.NB_V - 1))
        pieces.append(dict(hu=hu.round(4).tolist(), hv=hv.round(4).tolist(), rgb=rgb, raw_rgb=raw_rgb,
                           area_m2=float(A * mpp * mpp), eq_mm=float(2 * math.sqrt(A * mpp * mpp / math.pi) * 1000),
                           bay=[bay_i, bay_j], cell=[ci, cj], cell_class=c, clipped=clipped, k=len(poly), src=name,
                           big=bool(eq_poly > BIG_MM)))
        counts['kept'] += 1
    log('%s: pieces kept %d; %s (%.1fs)' % (name, counts['kept'], json.dumps(counts), time.time() - t0))
    log('%s: regions by cell class (after the size gates): %s' % (name, json.dumps({co.CLASS_NAMES[k]: v for k, v in sorted(cls_counts.items())})))
    return pieces, counts, usable


def merge_second(primary, second, cls1, cls2, mpp, hu0, hv0, shape, log=print):
    """Add pieces of the second source in cells where it is traceable and the primary is not; any
    piece overlapping an existing one by more than 15 % of its area is rejected."""
    H, W = shape
    occ = np.zeros((H, W), np.uint8)
    for p in primary:
        pts = np.stack([(np.array(p['hu']) - hu0) / mpp, (np.array(p['hv']) - hv0) / mpp], axis=1)
        cv2.fillPoly(occ, [np.round(pts).astype(np.int32)], 1)
    added, rejected, wrong_cell = [], 0, 0
    for p in second:
        ci, cj = p['cell']
        # only cells the primary calls not-glass (1) or artefact (3): a cell smeared (2) in one bake of
        # the same photographs is smeared in the other, whatever its classifier says
        if not (cls1[cj, ci] in (1, 3) and cls2[cj, ci] == 4):
            wrong_cell += 1
            continue
        pts = np.stack([(np.array(p['hu']) - hu0) / mpp, (np.array(p['hv']) - hv0) / mpp], axis=1)
        pm = np.zeros((H, W), np.uint8) if False else None
        x0, y0 = int(pts[:, 0].min()) - 1, int(pts[:, 1].min()) - 1
        x1, y1 = int(pts[:, 0].max()) + 2, int(pts[:, 1].max()) + 2
        x0, y0 = max(0, x0), max(0, y0); x1, y1 = min(W, x1), min(H, y1)
        loc = np.zeros((y1 - y0, x1 - x0), np.uint8)
        cv2.fillPoly(loc, [np.round(pts - [x0, y0]).astype(np.int32)], 1)
        a = loc.sum()
        if a == 0 or (loc & occ[y0:y1, x0:x1]).sum() > 0.15 * a:
            rejected += 1
            continue
        occ[y0:y1, x0:x1] |= loc
        q = dict(p); q['from_second'] = True
        added.append(q)
    log('second source: %d candidate pieces, %d in cells not eligible (primary traceable or smeared, or second not traceable), %d overlapping, %d added' % (
        len(second), wrong_cell, rejected, len(added)))
    return primary + added


# ----------------------------------------------------------------------------- outputs
def write_ngvp(pieces, hu0, hv0, path):
    u0 = hu0 + BOARD_DU
    v0 = hv0 + BOARD_DV
    buf = bytearray(b'NGVP')
    buf += struct.pack('<IffH', len(pieces), u0, v0, 1000)
    for p in pieces:
        r, g, b = p['rgb']
        buf += struct.pack('<4B', r, g, b, p['k'])
        for uu, vv in zip(p['hu'], p['hv']):
            mu = int(round((uu - hu0) * 1000)); mv = int(round((vv - hv0) * 1000))
            buf += struct.pack('<HH', max(0, min(65535, mu)), max(0, min(65535, mv)))
    with open(path, 'wb') as f:
        f.write(buf)
    return u0, v0, len(buf)


def summarise(pieces, cls, cell, mpp, hu0, hv0, traceable_classes=(4,), log=print, usable=None):
    """Per-bay and total statistics. The CORE numbers (coverage %, pieces / m2, median) are over the
    whole cells of class 4 (traceable) and the pieces whose centroid cell is class 4: that is the
    like-for-like figure against a reference photograph. Pieces recovered from the clean parts of
    artefact cells (class 3, gated per pixel) and, for the -all file, from smeared cells (class 2)
    are reported as EXTRA: count, glass area and the cells they came from. `usable` (per-cell share
    of the plan area the tracer could use, see trace_source) gives the all-in denominator."""
    cell_m2 = co.CELL_M ** 2
    rep = dict(per_bay=[], size=None, colour=None, cells=None)
    core_cls = 4
    extra_cls = [c for c in traceable_classes if c != core_cls]
    if usable is None:
        usable = np.isin(cls, list(traceable_classes)).astype(np.float32)

    def stats(ps, core_m2, all_m2, bay_m2=None):
        core = [p for p in ps if p['cell_class'] == core_cls]
        extra = [p for p in ps if p['cell_class'] in extra_cls]
        area_c = sum(p['area_m2'] for p in core); area_e = sum(p['area_m2'] for p in extra)
        eq = sorted(p['eq_mm'] for p in ps)
        d = dict(pieces=len(ps), glass_m2=area_c + area_e,
                 core_pieces=len(core), core_glass_m2=area_c, core_m2=core_m2,
                 core_coverage=float(area_c / core_m2) if core_m2 else None,
                 core_pieces_per_m2=float(len(core) / core_m2) if core_m2 else None,
                 extra_pieces=len(extra), extra_glass_m2=area_e, extra_cells_m2=all_m2 - core_m2,
                 usable_m2=all_m2, coverage_of_usable=float((area_c + area_e) / all_m2) if all_m2 else None,
                 pieces_per_m2_usable=float(len(ps) / all_m2) if all_m2 else None,
                 median_eq_mm=float(np.median(eq)) if eq else None,
                 core_median_eq_mm=float(np.median([p['eq_mm'] for p in core])) if core else None)
        if bay_m2:
            d['coverage_of_bay'] = float((area_c + area_e) / bay_m2)
        return d

    for i in range(co.NB_U):
        for j in range(co.NB_V):
            u0, v0, u1, v1 = co.bay_rect(i, j)
            c0, c1 = int((u0 - hu0) / mpp / cell), int(math.ceil((u1 - hu0) / mpp / cell))
            r0, r1 = int((v0 - hv0) / mpp / cell), int(math.ceil((v1 - hv0) / mpp / cell))
            sub = cls[r0:r1, c0:c1]; subu = usable[r0:r1, c0:c1]
            ncore = int((sub == core_cls).sum())
            ps = [p for p in pieces if p['bay'] == [i, j]]
            d = dict(i=i, j=j, cells=int(sub.size), traceable_cells=ncore, traceable_share=float(ncore / max(1, sub.size)),
                     smeared=int((sub == 2).sum()), artefact=int((sub == 3).sum()), not_glass=int((sub == 1).sum()),
                     extra_cells=int(np.isin(sub, extra_cls).sum() if extra_cls else 0))
            d.update(stats(ps, ncore * cell_m2, float(subu.sum()) * cell_m2, co.PU * co.PV))
            rep['per_bay'].append(d)
    eq = np.array([p['eq_mm'] for p in pieces]) if pieces else np.zeros(0)
    bands = [(0, 50), (50, 100), (100, 150), (150, 250), (250, 400), (400, 700)]
    rep['size'] = dict(n=len(pieces), median_eq_mm=float(np.median(eq)) if eq.size else None,
                       p10=float(np.percentile(eq, 10)) if eq.size else None, p90=float(np.percentile(eq, 90)) if eq.size else None,
                       bands={'%d-%d' % b: int(((eq >= b[0]) & (eq < b[1])).sum()) for b in bands},
                       verts={str(k): sum(1 for p in pieces if p['k'] == k) for k in range(3, MAX_VERTS + 1)})
    hb = {}
    for p in pieces:
        k = hue_bucket12(p['rgb'])
        d = hb.setdefault(k, dict(n=0, area=0.0))
        d['n'] += 1; d['area'] += p['area_m2']
    tot = sum(d['area'] for d in hb.values()) or 1.0
    order = HUE_NAMES + ['white/grey']
    rep['colour'] = {k: dict(n=hb[k]['n'], area_share=hb[k]['area'] / tot) for k in order if k in hb}
    rep['cells'] = {co.CLASS_NAMES[k]: int((cls == k).sum()) for k in range(5)}
    T = stats(pieces, float((cls == core_cls).sum()) * cell_m2, float(usable.sum()) * cell_m2)
    T['clipped_at_joints'] = sum(1 for p in pieces if p.get('clipped'))
    T['from_second'] = sum(1 for p in pieces if p.get('from_second'))
    rep['totals'] = T
    log('TOTAL %d pieces, %.1f m2 glass. CORE (class-4 cells, %.1f m2): %d pieces, %.1f m2 = %.1f%% coverage, %.1f pieces/m2, median %.0f mm. '
        'EXTRA from %s cells (%.1f m2 usable): %d pieces, %.1f m2. All-in over %.1f m2 usable: %.1f%% coverage, %.1f pieces/m2. '
        'Median %.0f mm (p10 %.0f, p90 %.0f); %d clipped at joints' % (
            T['pieces'], T['glass_m2'], T['core_m2'], T['core_pieces'], T['core_glass_m2'], 100 * (T['core_coverage'] or 0),
            T['core_pieces_per_m2'] or 0, T['core_median_eq_mm'] or 0, '/'.join(co.CLASS_NAMES[c].split(' ')[0] for c in extra_cls) or 'no',
            T['extra_cells_m2'], T['extra_pieces'], T['extra_glass_m2'], T['usable_m2'], 100 * (T['coverage_of_usable'] or 0),
            T['pieces_per_m2_usable'] or 0, rep['size']['median_eq_mm'] or 0, rep['size']['p10'] or 0, rep['size']['p90'] or 0,
            T['clipped_at_joints']))
    log('size bands (mm): %s; vertices: %s' % (json.dumps(rep['size']['bands']), json.dumps(rep['size']['verts'])))
    log('colour (area share): ' + ', '.join('%s %.1f%%' % (k, 100 * v['area_share']) for k, v in rep['colour'].items()))
    for b in rep['per_bay']:
        log('  bay %d,%d: core %3d/%3d cells (%3.0f%%): %4d pcs %5.2f m2 = %s cover, %s /m2, median %s mm | extra %3d pcs %5.2f m2 from %3d cells | whole-bay coverage %.1f%%' % (
            b['i'], b['j'], b['traceable_cells'], b['cells'], 100 * b['traceable_share'], b['core_pieces'], b['core_glass_m2'],
            '%3.0f%%' % (100 * b['core_coverage']) if b['core_coverage'] is not None else ' n/a',
            '%4.1f' % b['core_pieces_per_m2'] if b['core_pieces_per_m2'] is not None else ' n/a',
            '%3.0f' % b['core_median_eq_mm'] if b['core_median_eq_mm'] else 'n/a',
            b['extra_pieces'], b['extra_glass_m2'], b['extra_cells'], 100 * b['coverage_of_bay']))
    return rep


def overlays(img, pieces, cls, cell, mpp, hu0, hv0, out, tag, report, crops=None):
    H, W = img.shape[:2]
    s = 2000 / W
    full = cv2.resize(img, (2000, int(H * s)), interpolation=cv2.INTER_AREA)
    for p in pieces:
        pts = np.stack([(np.array(p['hu']) - hu0) / mpp * s, (np.array(p['hv']) - hv0) / mpp * s], axis=1)
        cv2.polylines(full, [np.round(pts).astype(np.int32)], True, (0, 255, 0) if not p.get('from_second') else (255, 0, 255), 1)
    Image.fromarray(full).save(os.path.join(out, 'overlay-full%s.jpg' % tag), quality=88)
    CW = CROP_PX                       # crop window in ortho pixels, shown 1:1
    nwin = CW // cell                  # cells per window side
    if crops is None:
        # the CW x CW window with the most traceable cells, one per bay, the best three bays at
        # least two bays apart (a west, a middle and an east sample)
        tr = (cls == 4).astype(np.float32)
        win = cv2.boxFilter(tr, -1, (nwin, nwin), normalize=False, anchor=(0, 0), borderType=cv2.BORDER_CONSTANT)
        best = []
        for i in range(co.NB_U):
            u0, _, u1, _ = co.bay_rect(i, 0)
            c0, c1 = max(0, int((u0 - hu0) / mpp / cell)), min(cls.shape[1] - nwin, int((u1 - hu0) / mpp / cell) - nwin + 1)
            if c1 <= c0:
                continue
            sub = win[:cls.shape[0] - nwin + 1, c0:c1]
            r, c = np.unravel_index(int(sub.argmax()), sub.shape)
            best.append((float(sub[r, c]), r, c + c0, i))
        crops = []
        for score, r, c, i in sorted(best, reverse=True):
            if all(abs(i - b) >= 2 for b in [q[2] for q in crops]):
                crops.append((r, c, i))
            if len(crops) == 3:
                break
    for n, (cy, cx, bay) in enumerate(crops):
        x0 = max(0, min(W - CW, cx * cell)); y0 = max(0, min(H - CW, cy * cell))
        crop = img[y0:y0 + CW, x0:x0 + CW].copy()
        # cell grid and class tint (traceable cells get no tint)
        for gy in range(0, CW, cell):
            for gx in range(0, CW, cell):
                c = int(cls[min(cls.shape[0] - 1, (y0 + gy) // cell), min(cls.shape[1] - 1, (x0 + gx) // cell)])
                if c != 4:
                    col = {0: (0, 0, 0), 1: (90, 40, 120), 2: (220, 30, 30), 3: (240, 150, 20)}[c]
                    cv2.rectangle(crop, (gx, gy), (gx + cell - 1, gy + cell - 1), col, 1)
        for p in pieces:
            hu = (np.array(p['hu']) - hu0) / mpp; hv = (np.array(p['hv']) - hv0) / mpp
            if hu.min() > x0 + CW or hu.max() < x0 or hv.min() > y0 + CW or hv.max() < y0:
                continue
            pts = np.stack([hu - x0, hv - y0], axis=1)
            cv2.polylines(crop, [np.round(pts).astype(np.int32)], True, (0, 255, 0) if not p.get('from_second') else (255, 0, 255), 1)
            cx_, cy_ = pts.mean(axis=0)
            cv2.circle(crop, (int(cx_), int(cy_)), 3, tuple(int(v) for v in p['rgb']), -1)
        cv2.putText(crop, 'bay %d  hu %.2f hv %.2f  %.1f m window 1:1 at %.0f mm/px; dots = lifted colour; boxed cells = not traced' % (
            bay, hu0 + x0 * mpp, hv0 + y0 * mpp, CW * mpp, mpp * 1000), (6, CW - 10), cv2.FONT_HERSHEY_SIMPLEX, 0.45, (255, 255, 255), 1)
        Image.fromarray(crop).save(os.path.join(out, 'overlay-crop-%d%s.jpg' % (n + 1, tag)), quality=92)
    S = 120
    im = np.zeros((2 * S + 40, 7 * S, 3), np.uint8)
    for b in report['per_bay']:
        x, y = b['i'] * S, b['j'] * S
        g = int(255 * min(1, b['traceable_share']))
        cv2.rectangle(im, (x, y), (x + S - 2, y + S - 2), (40, g, 40), -1)
        cv2.putText(im, '%d,%d' % (b['i'], b['j']), (x + 4, y + 16), cv2.FONT_HERSHEY_SIMPLEX, 0.45, (255, 255, 255), 1)
        cv2.putText(im, 'tr %.0f%%' % (100 * b['traceable_share']), (x + 4, y + 36), cv2.FONT_HERSHEY_SIMPLEX, 0.4, (255, 255, 255), 1)
        cv2.putText(im, '%d pcs' % b['pieces'], (x + 4, y + 54), cv2.FONT_HERSHEY_SIMPLEX, 0.4, (255, 255, 255), 1)
        cv2.putText(im, 'cov %s' % ('%.0f%%' % (100 * b['core_coverage']) if b['core_coverage'] else '-'), (x + 4, y + 72), cv2.FONT_HERSHEY_SIMPLEX, 0.4, (255, 255, 255), 1)
        cv2.putText(im, '%s /m2' % ('%.1f' % b['core_pieces_per_m2'] if b['core_pieces_per_m2'] else '-'), (x + 4, y + 90), cv2.FONT_HERSHEY_SIMPLEX, 0.4, (255, 255, 255), 1)
        cv2.putText(im, 'med %s +%d' % ('%.0f' % b['core_median_eq_mm'] if b['core_median_eq_mm'] else '-', b['extra_pieces']), (x + 4, y + 108), cv2.FONT_HERSHEY_SIMPLEX, 0.4, (255, 255, 255), 1)
    cv2.putText(im, 'green = traceable share of the bay; pcs = all pieces; cov, /m2, med over the traceable (class 4) cells; +n = pieces from artefact cells; row 0 = south (j=0)', (4, 2 * S + 26), cv2.FONT_HERSHEY_SIMPLEX, 0.35, (255, 255, 255), 1)
    Image.fromarray(im).save(os.path.join(out, 'coverage-bays%s.png' % tag))
    return crops


def dump(pieces, report, counts, extra, hu0, hv0, out, name):
    bin_path = os.path.join(out, name + '.bin')
    u0, v0, nbytes = write_ngvp(pieces, hu0, hv0, bin_path)
    with open(os.path.join(out, name + '.json'), 'w') as f:
        json.dump(dict(board_origin=[u0, v0],
                       frame='NGVP u,v = board = (hu + %.4f, hv + %.4f); ortho px -> hu = hu0 + (px + 0.5) * mm/1000; polygons counter-clockwise in (u, v), convex' % (BOARD_DU, BOARD_DV),
                       colour_lift=COLOUR_LIFT, thresholds=dict(min_eq_mm=MIN_EQ_MM, max_eq_mm=MAX_EQ_MM, min_width_mm=MIN_WIDTH_MM,
                                                                eps_mm=EPS_MM, max_verts=MAX_VERTS, h_maxima_px=H_MAXIMA_PX, neck_ratio=NECK_RATIO),
                       counts=counts, report=report, pieces=pieces, **extra), f)
    print('wrote %s: %d pieces, %d bytes, board origin (u0 %.4f, v0 %.4f)' % (bin_path, len(pieces), nbytes, u0, v0))
    return bin_path


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('--src', default=co.OUT_DEFAULT)
    ap.add_argument('--out', default=co.SCRATCH_DEFAULT)
    ap.add_argument('--tag', default='', help='primary ortho tag (bottom-ortho<tag>.png)')
    ap.add_argument('--second', default=None, help="tag of a second ortho (e.g. -v29) whose traceable cells fill the primary's gaps")
    ap.add_argument('--no-all', action='store_true', help='skip the -all file (class 2 cells traced too)')
    ap.add_argument('--crops', default='', help="overlay crop top-left corners 'hu,hv;hu,hv;hu,hv' (default: the windows with the most traceable cells in three bays)")
    ap.add_argument('--calib', nargs='*', help='reference photographs: print their piece colour statistics and exit')
    ap.add_argument('--split', default=SPLIT, choices=['intensity', 'distance'], help='how bridged neighbours are separated (see split_pieces*)')
    ap.add_argument('--thr-frac', type=float, default=THR_FRAC, help='glass threshold as a share of the local contrast')
    ap.add_argument('--name', default='pieces-atlas', help='output base name (pieces-atlas)')
    args = ap.parse_args()
    if args.calib:
        calib(args.calib)
        return
    t0 = time.time()
    os.makedirs(args.out, exist_ok=True)
    img, meta, cls, cov = load(args.src, args.tag)
    mpp = meta['mm_per_px'] / 1000.0
    hu0, hv0 = meta['hu0'], meta['hv0']
    cell = int(round(co.CELL_M / mpp))
    src_path = os.path.join(args.src, 'bottom-ortho%s.png' % args.tag)
    print('primary %s: %dx%d at %.1f mm/px; split %s, thr_frac %.2f' % (src_path, img.shape[1], img.shape[0], mpp * 1000, args.split, args.thr_frac))
    pieces24, counts, usable24 = trace_source(img, meta, cls, cov, 'primary', keep_classes=(2, 3, 4), split=args.split, thr_frac=args.thr_frac)
    pieces4 = [p for p in pieces24 if p['cell_class'] in (3, 4)]
    usable4 = usable24.copy(); usable4[cls == 2] = 0
    print('\n=== %s (traceable cells + the clean parts of artefact cells)' % args.name)
    rep = summarise(pieces4, cls, cell, mpp, hu0, hv0, (3, 4), usable=usable4)
    method = dict(split=args.split, thr_frac=args.thr_frac, int_h_level=INT_H_LEVEL, int_dip_frac=INT_DIP_FRAC, int_dip_min=INT_DIP_MIN,
                  art_grow_mm=ART_GROW_MM, art_max_share=ART_MAX_SHARE, art_min_solidity=ART_MIN_SOLIDITY)
    bin_path = dump(pieces4, rep, counts, dict(source=src_path, classes_traced=[3, 4], method=method), hu0, hv0, args.out, args.name + args.tag)
    crops = None
    if args.crops:
        crops = []
        for c in args.crops.split(';'):
            hu, hv = map(float, c.split(','))
            crops.append((int((hv - hv0) / mpp // cell), int((hu - hu0) / mpp // cell), int((hu - co.PLATE[0]) // co.PU)))
    otag = args.tag if args.name == 'pieces-atlas' else '-' + args.name.replace('pieces-atlas-', '') + args.tag
    crops = overlays(img, pieces4, cls, cell, mpp, hu0, hv0, args.out, otag, rep, crops)
    if not args.no_all:
        print('\n=== %s-all (smeared cells traced too)' % args.name)
        rep_all = summarise(pieces24, cls, cell, mpp, hu0, hv0, (2, 3, 4), usable=usable24)
        dump(pieces24, rep_all, counts, dict(source=src_path, classes_traced=[2, 3, 4], method=method), hu0, hv0, args.out, args.name + '-all' + args.tag)
    if args.second:
        img2, meta2, cls2, cov2 = load(args.src, args.second)
        assert meta2['hu0'] == hu0 and meta2['hv0'] == hv0 and meta2['mm_per_px'] == meta['mm_per_px']
        print('\n=== second source %s' % args.second)
        p2, counts2, usable2 = trace_source(img2, meta2, cls2, cov2, 'second', keep_classes=(3, 4), split=args.split, thr_frac=args.thr_frac)
        merged = merge_second(pieces4, p2, cls, cls2, mpp, hu0, hv0, img.shape[:2])
        cls_m = cls.copy()
        cls_m[np.isin(cls, [1, 3]) & (cls2 == 4)] = 4
        print('\n=== %s-merged (primary + second-source pieces in cells the primary could not trace)' % args.name)
        usable_m = np.maximum(usable4, np.where(np.isin(cls, [1, 2]) | (usable4 == 0), usable2, 0))
        rep_m = summarise(merged, cls_m, cell, mpp, hu0, hv0, (3, 4), usable=usable_m)
        dump(merged, rep_m, dict(primary=counts, second=counts2),
             dict(source=[src_path, os.path.join(args.src, 'bottom-ortho%s.png' % args.second)], classes_traced=[4], method=method),
             hu0, hv0, args.out, args.name + '-merged' + args.tag)
        overlays(img, merged, cls_m, cell, mpp, hu0, hv0, args.out, otag + '-merged', rep_m, crops)
        np.save(os.path.join(args.out, 'class-merged%s.npy' % args.tag), cls_m)
    print('\ndone in %.1fs' % (time.time() - t0))
    try:
        out = subprocess.run([sys.executable, os.path.join(os.path.dirname(os.path.abspath(__file__)), 'pieces_stats.py'), bin_path],
                             capture_output=True, text=True, timeout=300)
        print(out.stdout[-7000:])
    except Exception as e:
        print('pieces_stats failed:', e)


if __name__ == '__main__':
    main()
