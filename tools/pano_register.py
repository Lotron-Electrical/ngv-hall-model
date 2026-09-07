"""Register the NGV Zoomify panorama BUIL000804 (the whole Gandel Hall ceiling, rectified, ~1.75 mm/px)
onto the shared 4 mm huv grid as a source tile for tools/ceiling_trace2.py.

How the registration was decided (2026-09-08, see PLAN-20260907-ceiling.md):
- 15 vertical and 5 horizontal member lines were detected in the panorama (scratchpad pano_grid.json,
  dark-run centres, thick/thin alternating). Their pitch is one half-bay, so the 7 x 2 bay plate is
  in view, with thick lines at the plate ends.
- Which line is which was settled by NCC of the blurred Lab panorama against the bake ortho
  (trackB/bottom-ortho-v29.png) under 4 symmetries x 5 offsets: flipLR with a +PU/2 offset scores
  0.63; every other combination 0.38 or less (id/flipUD 0.38, rot180 0.51, unshifted <= 0.09).
  So the panorama's x runs EAST -> WEST, its y SOUTH -> NORTH, the THIN vertical lines are the six
  column lines, the THICK ones the ridges, and the plate ENDS ON THE VERTEX PHASE: a half coffer
  at each end (the hips meet on the end line, see pano_ends.jpg). The bake ortho, drawn on the
  ridge-ended 7-bay assumption, is dark for its first half bay and stops half a bay short of the
  east end; the 2026-08-31 note in index.html ("the GLB hall is ~3.4 m short of the real one")
  is the same half bay.
- Horizontally the plate is as modelled: south and north edges on the ridge phase, the thick mid
  line the central ridge, the thin lines the two vertex rows.
Mapping: piecewise-linear through the member lines (the panorama's pitch drifts 2181 -> 2037 px),
each line placed on its NEW-lattice hu / hv. Output: tile.png (RGB), mask.png, gsd.npy, meta.json
in sources/pano/, lattice 'new'.
"""
import json, os, sys, argparse
import numpy as np, cv2
from PIL import Image
Image.MAX_IMAGE_PIXELS = None

PANO = 'E:/sitecapture-captures/ngv-site/agent-ref-ceiling/online/ngv_zoomify_BUIL000804_full.jpg'
OUT = 'E:/sitecapture-captures/ngv-site/agent-ref-ceiling/sources/pano'
GRID = dict(hu0=-56.635125, hv0=0.15882, mm=4.0)
NEW = dict(PU=7.36, PV=7.50, HU0=-45.321133, HV0=11.294317)   # funnel-vertex phase (index.html CANOPY)
# panorama member lines (px, dark-run width) from the detection pass
V = [(235, 470), (2415, 326), (4528, 80), (6627, 362), (8714, 92), (10772, 251), (12822, 141), (14904, 306),
     (16976, 104), (19019, 244), (21046, 113), (23095, 304), (25138, 77), (27174, 298), (29318, 513)]
H = [(71, 142), (2040, 92), (4098, 314), (6167, 96), (8176, 191)]

def main():
    global OUT
    ap = argparse.ArgumentParser()
    ap.add_argument('--mm', type=float, default=4.0, help="grid pitch of the output tile (4 = the shared grid; 2 keeps the panorama's own 1.8 mm)")
    ap.add_argument('--out', default=OUT)
    args = ap.parse_args()
    GRID['mm'] = args.mm
    OUT = args.out
    PU, PV = NEW['PU'], NEW['PV']
    # x line k (east -> west): hu = east wall - k * PU/2, east wall = vertex + 6 PU ... the vertex phase
    hu_e = NEW['HU0'] + 6 * PU            # -1.161 east wall (vertex phase)
    hu_lines = [hu_e - k * PU / 2 for k in range(15)]   # descending with x
    hv_s = NEW['HV0'] - PV - PV / 2         # south edge (ridge phase) 0.044
    hv_lines = [hv_s + k * PV / 2 for k in range(5)]
    xs = np.array([v[0] for v in V], float); ys = np.array([h[0] for h in H], float)
    mm = GRID['mm']
    c0 = int(np.floor((hu_lines[-1] - GRID['hu0']) * 1000 / mm)); c1 = int(np.ceil((hu_lines[0] - GRID['hu0']) * 1000 / mm))
    r0 = int(np.floor((hv_lines[0] - GRID['hv0']) * 1000 / mm)); r1 = int(np.ceil((hv_lines[-1] - GRID['hv0']) * 1000 / mm))
    W, Hn = c1 - c0, r1 - r0
    hu = GRID['hu0'] + (np.arange(c0, c1) + 0.5) * mm / 1000
    hv = GRID['hv0'] + (np.arange(r0, r1) + 0.5) * mm / 1000
    # interp needs ascending xp: hu_lines descend, so reverse both
    mx = np.interp(hu, hu_lines[::-1], xs[::-1]).astype(np.float32)
    my = np.interp(hv, hv_lines, ys).astype(np.float32)
    pano = cv2.imread(PANO, cv2.IMREAD_COLOR)
    print('pano', pano.shape, 'tile', W, Hn, 'origin px', c0, r0, flush=True)
    MX = np.repeat(mx[None, :], Hn, 0); MY = np.repeat(my[:, None], W, 1)
    tile = cv2.remap(pano, MX, MY, cv2.INTER_AREA, borderMode=cv2.BORDER_CONSTANT)
    inside = (MX >= xs[0] - 10) & (MX <= xs[-1] + 10) & (MY >= ys[0] - 10) & (MY <= ys[-1] + 10)
    # source pixel size on the plate (mm per pano px) from the local line spacing
    dx = np.gradient(mx) * 0 + 1.0
    dhu = np.abs(np.gradient(hu) / np.gradient(mx)) * 1000   # mm per pano px along u
    dhv = np.abs(np.gradient(hv) / np.gradient(my)) * 1000
    gsd = (np.sqrt(np.outer(dhv, dhu)) / 1000).astype(np.float32)   # metres per pano px, as photo_register writes it
    gsd[~inside] = 0
    os.makedirs(OUT, exist_ok=True)
    cv2.imwrite(OUT + '/tile.png', tile)
    cv2.imwrite(OUT + '/mask.png', (inside * 255).astype(np.uint8))
    np.save(OUT + '/gsd.npy', gsd)
    prev = cv2.resize(tile, (W // 8, Hn // 8), interpolation=cv2.INTER_AREA)
    cv2.imwrite(OUT + '/preview.jpg', prev, [cv2.IMWRITE_JPEG_QUALITY, 85])
    meta = dict(name="pano", px0=c0, py0=r0, source='NGV Zoomify BUIL000804 (restitched from public tiles, (c) NGV)', pano=PANO,
                grid=GRID, origin_px=[c0, r0], size_px=[W, Hn], lattice='new', side='under',
                hu_lines=hu_lines, hv_lines=hv_lines, pano_x=xs.tolist(), pano_y=ys.tolist(),
                orientation='pano x east->west, pano y south->north (flipLR vs the bake, ncc 0.63)',
                plate_ends='vertex phase in u (half coffer at each wall), ridge phase in v',
                gsd_mm=[float(gsd[inside].min()), float(np.median(gsd[inside])), float(gsd[inside].max())],
                registration='piecewise-linear through 15 x 5 member lines; ncc vs bake 0.63 (flipLR, +PU/2)')
    json.dump(meta, open(OUT + '/meta.json', 'w'), indent=1)
    print('gsd mm', meta['gsd_mm'])

if __name__ == '__main__':
    main()
