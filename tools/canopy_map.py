"""The canopy's colour as the walls see it: tools/canopy-colour.png from tools/pieces.bin.

Daylight reaches the stone through the coloured slabs, so the light on a wall carries the mix of
the panes above it: a bay heavy in reds throws a warmer light than one heavy in blues. This
rasterises every traced pane (tools/pieces.bin, NGVP: each piece a polygon in hall metres with
the photograph's own colour) into a 2 m grid over the hall (26 x 8 cells, u 0..52 by d 0..16),
area-weighted mean colour per cell, then divides by the plate's area mean so the map is the
RELATIVE tint only (mean white). The absolute cast of daylight through the glass is already in
the stone albedo, which was matched to a daylight photograph (WALL_TINT, tools/stone.jpg), so
multiplying it in again would count it twice. Cells with no traced pane take the plate mean.

The file's frame: vertices are millimetres from the lattice origin; the provenance file gives
the plate's extent in hu (-52.681..-1.161) and hv (0.044..15.044); the hall frame is
u = hu + 53.04 (the real west wall, hu -52.68, is u 0.34) and d = hv - 0.044.

usage: python tools/canopy_map.py            (writes tools/canopy-colour.png and prints the stats)
"""
import json, struct, sys
import numpy as np
from PIL import Image, ImageDraw

HERE = __file__.rsplit('/', 1)[0] if '/' in __file__ else __file__.rsplit('\\', 1)[0]
BIN = HERE + '/pieces.bin'; PROV = HERE + '/pieces-provenance.json'; OUT = HERE + '/canopy-colour.png'
CELL = 2.0; NU, ND = 26, 8; SUB = 40           # 26 x 8 cells of 2 m, rasterised at 50 mm

def s2l(c):
    c = c / 255.0
    return np.where(c <= 0.04045, c / 12.92, ((c + 0.055) / 1.055) ** 2.4)

def l2s(c):
    return np.where(c <= 0.0031308, c * 12.92, 1.055 * c ** (1 / 2.4) - 0.055)

b = open(BIN, 'rb').read()
assert b[:4] == b'NGVP'
n, u0, v0, mm = struct.unpack('<IffH', b[4:18])
o = 18; pieces = []
for _ in range(n):
    r, g, bb, k = struct.unpack('<4B', b[o:o + 4]); o += 4
    pts = [struct.unpack('<HH', b[o + 4 * j:o + 4 * j + 4]) for j in range(k)]; o += 4 * k
    pieces.append(((r, g, bb), [(p[0] / mm, p[1] / mm) for p in pts]))
prov = json.load(open(PROV))
allu = [p[0] for _, pts in pieces for p in pts]; allv = [p[1] for _, pts in pieces for p in pts]
fu0, fu1, fv0, fv1 = min(allu), max(allu), min(allv), max(allv)
HU0, HU1, HV0, HV1 = -52.681, -1.161, 0.044, 15.044    # the provenance file's plate extent
# file units -> hall (u, d): the file's vertex range spans the plate
def hall(pu, pv):
    hu = HU0 + (pu - fu0) / (fu1 - fu0) * (HU1 - HU0); hv = HV0 + (pv - fv0) / (fv1 - fv0) * (HV1 - HV0)
    return hu + 53.04, hv - 0.044

W, H = NU * SUB, ND * SUB
acc = np.zeros((H, W, 3)); cnt = np.zeros((H, W))
im = Image.new('RGB', (W, H), (0, 0, 0)); msk = Image.new('L', (W, H), 0)
d_im = ImageDraw.Draw(im); d_msk = ImageDraw.Draw(msk)
for col, pts in pieces:
    poly = [(u / CELL * SUB, d / CELL * SUB) for u, d in (hall(*p) for p in pts)]
    d_im.polygon(poly, fill=col); d_msk.polygon(poly, fill=255)
lin = s2l(np.asarray(im).astype(float)); m = (np.asarray(msk) > 0).astype(float)
cells = np.zeros((ND, NU, 3)); cov = np.zeros((ND, NU))
for j in range(ND):
    for i in range(NU):
        blk = lin[j * SUB:(j + 1) * SUB, i * SUB:(i + 1) * SUB]; mb = m[j * SUB:(j + 1) * SUB, i * SUB:(i + 1) * SUB]
        cov[j, i] = mb.mean()
        cells[j, i] = (blk * mb[..., None]).sum((0, 1)) / max(mb.sum(), 1)
mean = (cells * cov[..., None]).sum((0, 1)) / cov.sum()
rel = np.where(cov[..., None] > 0.02, cells / mean, 1.0)
# a wall point takes light from a wide patch of canopy, so the tint it sees is the panes averaged
# over many metres: blur the cell grid with a 2-cell (4 m) Gaussian, coverage-weighted, and keep
# the result within 0.7..1.3 of the plate mean (the extremes are single thin cells)
from scipy.ndimage import gaussian_filter
w = np.clip(cov, 0.02, None)
rel = np.stack([gaussian_filter(rel[..., k] * w, 2.0, mode='nearest') / gaussian_filter(w, 2.0, mode='nearest') for k in range(3)], -1)
rel = np.clip(rel, 0.7, 1.3); rel = rel / (rel * cov[..., None]).sum((0, 1)) * cov.sum()
rel = np.clip(rel, 0, 2.0) / 2.0                        # stored as sRGB 0..1 = relative 0..2
Image.fromarray((l2s(rel) * 255 + 0.5).astype('uint8')).save(OUT)
print(f'{n} pieces, file range u {fu0:.3f}..{fu1:.3f} v {fv0:.3f}..{fv1:.3f}')
print(f'plate mean transmission colour (linear) {mean.round(4)}, chroma {(mean / mean.sum()).round(3)}')
print(f'coverage {cov.mean():.2f}; relative tint range r {rel[...,0].min()*2:.2f}..{rel[...,0].max()*2:.2f} g {rel[...,1].min()*2:.2f}..{rel[...,1].max()*2:.2f} b {rel[...,2].min()*2:.2f}..{rel[...,2].max()*2:.2f}')
print('wrote', OUT)
