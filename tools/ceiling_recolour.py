"""Recolour the traced panes from the scan bake, our own daylight capture of the real ceiling.

WHY (Lloyd, 2026-09-08: the 2 mm trace "looks correct. However it is missing the colour vibrancy
of the bake (which was a real world scan)"). Every pane's SHAPE is traced from the NGV panorama
(1.8 mm/px), but its COLOUR was the panorama's too: one photograph, one exposure, muted. The bake
(trackB/bottom-ortho-v29.png, 5 mm/px, the certified scan's texture unwrapped on the OLD lattice)
is the hall's own glass in daylight, so it is the witness of colour, as the panorama is the
witness of shape. Nothing is invented: a pane takes the MEDIAN of the bake's pixels inside its own
outline where the bake is legible there, and says so in the provenance.

Where the bake is not legible (its dark west bays, its smeared patches, panes too small to hold
six bake pixels) the pane keeps the panorama's colour passed through ONE global colour fit, a 3x3
matrix + offset in linear RGB, least-squares from the panes that DID get a bake colour (thousands
of pairs, panorama colour -> bake colour). That is a calibration of the photograph's exposure to
the scan's, not a colour laid by hand, and the provenance says "pano+fit" for those panes.

Legible: the bake's luminance box-filtered over 0.3 m is above LEGIBLE (the unlit west bays sit
under it everywhere), the coverage mask is set for every pixel of the pane, and the pane holds at
least MIN_PX bake pixels 6 mm in from its edge.

    python tools/ceiling_recolour.py --in tools/pieces.bin --prov tools/pieces-provenance.json \
        --out-dir <dir> [--name pieces]

Frames: pieces.bin is board metres (uu = hu + 58.3053, vv = hv + 0.4556) on the NEW lattice;
the bake is OLD-lattice metres (tools/ceiling_assemble.py OLD/NEW, remap inverted here).
"""
import argparse
import json
import os
import struct
import sys

import numpy as np
from PIL import Image
from shapely.geometry import Polygon
from shapely import contains_xy

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from ceiling_assemble import OLD, NEW, BOARD_DU, BOARD_DV, write_ngvp  # noqa: E402

Image.MAX_IMAGE_PIXELS = None
TRACKB = 'E:/sitecapture-captures/ngv-site/agent-ref-ceiling/trackB/'
BAKE, COVER, META = TRACKB + 'bottom-ortho-v29.png', TRACKB + 'coverage-v29.png', TRACKB + 'bottom-meta-v29.json'
LEGIBLE = 22.0      # 8-bit luminance, box 0.3 m: the unlit west bays measure under it, glass over
MIN_PX = 6
ERODE = 0.006


def read_ngvp(path):
    b = open(path, 'rb').read()
    n, u0, v0, mm = struct.unpack_from('<IffH', b, 4)
    o, out = 18, []
    for _ in range(n):
        r, g, bb, k = struct.unpack_from('<4B', b, o); o += 4
        pts = [(u0 + struct.unpack_from('<H', b, o + 4 * j)[0] / mm, v0 + struct.unpack_from('<H', b, o + 2 + 4 * j)[0] / mm) for j in range(k)]; o += 4 * k
        out.append(dict(colour=[r, g, bb], pts=pts))
    return out


def new_to_old(hu, hv):
    return (OLD['hu0'] + (np.asarray(hu, float) - NEW['hu0']) * (OLD['PU'] / NEW['PU']),
            OLD['hv0'] + (np.asarray(hv, float) - NEW['hv0']) * (OLD['PV'] / NEW['PV']))


def srgb_to_lin(c):
    c = np.asarray(c, float) / 255.0
    return np.where(c <= 0.04045, c / 12.92, ((c + 0.055) / 1.055) ** 2.4)


def lin_to_srgb(c):
    c = np.clip(np.asarray(c, float), 0, 1)
    return np.where(c <= 0.0031308, c * 12.92, 1.055 * c ** (1 / 2.4) - 0.055) * 255.0


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--in', dest='inp', default='tools/pieces.bin')
    ap.add_argument('--prov', default='tools/pieces-provenance.json')
    ap.add_argument('--out-dir', required=True)
    ap.add_argument('--name', default='pieces')
    ap.add_argument('--legible', type=float, default=LEGIBLE)
    a = ap.parse_args()
    os.makedirs(a.out_dir, exist_ok=True)

    meta = json.load(open(META)); mm = meta['mm_per_px']; hu0, hv0 = meta['hu0'], meta['hv0']
    bake = np.array(Image.open(BAKE).convert('RGB'))
    cover = np.array(Image.open(COVER)) > 0
    H, W = cover.shape
    # legibility: luminance box-filtered over 0.3 m (integral image)
    lum = bake.astype(np.float32) @ np.array([0.299, 0.587, 0.114], np.float32)
    r = int(round(0.15 / (mm / 1000)))
    ii = np.pad(lum, ((1, 0), (1, 0))).cumsum(0).cumsum(1)
    yy, xx = np.mgrid[0:H, 0:W]
    y0 = np.clip(yy - r, 0, H); y1 = np.clip(yy + r + 1, 0, H); x0 = np.clip(xx - r, 0, W); x1 = np.clip(xx + r + 1, 0, W)
    box = (ii[y1, x1] - ii[y0, x1] - ii[y1, x0] + ii[y0, x0]) / ((y1 - y0) * (x1 - x0))
    legible = (box > a.legible) & cover
    del ii, yy, xx, y0, y1, x0, x1
    print(f'bake {W}x{H} at {mm} mm; legible {legible.mean():.3f} of the raster (threshold {a.legible})')

    pieces = read_ngvp(a.inp)
    prov = json.load(open(a.prov))
    assert len(prov['pieces']) == len(pieces), 'provenance is not index-aligned'
    pairs, pano_col, bake_col, why = [], [], [], {'bake': 0, 'dark': 0, 'small': 0, 'uncovered': 0}
    for i, pc in enumerate(pieces):
        hu = [p[0] - BOARD_DU for p in pc['pts']]; hv = [p[1] - BOARD_DV for p in pc['pts']]
        pc['poly'] = Polygon(list(zip(hu, hv)))       # NEW hall metres, what write_ngvp writes
        ou, ov = new_to_old(hu, hv)
        poly = Polygon(list(zip(ou, ov)))
        if not poly.is_valid:
            poly = poly.buffer(0)
        inner = poly.buffer(-ERODE)
        if inner.is_empty:
            inner = poly
        minx, miny, maxx, maxy = poly.bounds
        px0 = int((minx - hu0) * 1000 / mm); px1 = int((maxx - hu0) * 1000 / mm) + 1
        py0 = int((miny - hv0) * 1000 / mm); py1 = int((maxy - hv0) * 1000 / mm) + 1
        px0, py0 = max(px0, 0), max(py0, 0); px1, py1 = min(px1, W), min(py1, H)
        bake_col.append(None)
        if px1 <= px0 or py1 <= py0:
            why['uncovered'] += 1; continue
        gy, gx = np.mgrid[py0:py1, px0:px1]
        chu = hu0 + (gx + 0.5) * mm / 1000; chv = hv0 + (gy + 0.5) * mm / 1000
        ins = contains_xy(inner, chu.ravel(), chv.ravel()).reshape(gx.shape)
        if ins.sum() < MIN_PX:
            why['small'] += 1; continue
        if not cover[py0:py1, px0:px1][ins].all():
            why['uncovered'] += 1; continue
        if not legible[py0:py1, px0:px1][ins].all():
            why['dark'] += 1; continue
        col = np.median(bake[py0:py1, px0:px1][ins], axis=0)
        bake_col[i] = [int(round(v)) for v in col]
        pairs.append((pc['colour'], bake_col[i])); why['bake'] += 1
    print('colour sources:', why)

    # the global fit, panorama -> bake, linear RGB, 3x3 + offset, least squares on the bake pairs
    P = srgb_to_lin([p for p, _ in pairs]); B = srgb_to_lin([b for _, b in pairs])
    A = np.hstack([P, np.ones((len(P), 1))])
    M, *_ = np.linalg.lstsq(A, B, rcond=None)
    fitted = A @ M
    resid = np.sqrt(((fitted - B) ** 2).sum(1))
    print(f'fit on {len(pairs)} pairs: matrix\n{np.round(M.T, 3)}\n residual (linear) median {np.median(resid):.3f}, p90 {np.percentile(resid, 90):.3f}')
    sat = lambda c: (c.max(1) - c.min(1)) / np.maximum(c.max(1), 1e-3)
    print(f' saturation: panorama median {np.median(sat(P)):.3f}, bake {np.median(sat(B)):.3f}, fitted {np.median(sat(np.clip(fitted, 0, 1))):.3f}')
    print(f' luminance (linear): panorama {np.median(P.mean(1)):.3f}, bake {np.median(B.mean(1)):.3f}')

    n_fit = 0
    for i, pc in enumerate(pieces):
        pr = prov['pieces'][i]
        pr['colour_pano'] = list(pc['colour'])
        if bake_col[i] is not None:
            pc['colour'] = bake_col[i]; pr['colour_source'] = 'bake-v29'
        else:
            lin = np.append(srgb_to_lin(pc['colour']), 1.0) @ M
            pc['colour'] = [int(round(v)) for v in lin_to_srgb(lin)]; pr['colour_source'] = 'pano+fit'; n_fit += 1
    prov['colour'] = dict(note='pane colours: the median of the scan bake (trackB/bottom-ortho-v29.png, our own daylight capture, 5 mm) inside the pane outline eroded 6 mm where the bake is legible there (box 0.3 m luminance over %.0f, covered, >= %d px); elsewhere the panorama colour through one global 3x3+offset fit in linear RGB from the bake-coloured panes' % (a.legible, MIN_PX),
                          counts=why, fit_pairs=len(pairs), fit_matrix=M.T.round(5).tolist(), fit_resid_median=float(np.median(resid)),
                          fit_resid_p90=float(np.percentile(resid, 90)), n_fit=n_fit)
    write_ngvp(pieces, os.path.join(a.out_dir, a.name + '.bin'))
    json.dump(prov, open(os.path.join(a.out_dir, a.name + '-provenance.json'), 'w'), indent=None)
    print('wrote', os.path.join(a.out_dir, a.name + '.bin'), len(pieces), 'pieces')


if __name__ == '__main__':
    main()
