"""Second-stage registration of the NGV panorama tile (sources/pano, from tools/pano_register.py).

The first stage maps the panorama through its 15 x 5 straight member lines, which leaves the steel
INSIDE each 3.68 x 3.75 m sub-square up to ~90 mm off the lattice (the X where the hip crosses the
diamond member sits at radial p50 92 mm, p90 163 mm from the sub-square centre; the hips ~76 mm).
This stage measures, on the registered tile itself, (a) every member node (the 15 x 5 line
crossings, a '+' template on the steel mask) and (b) every sub-square centre X (two crossing
diagonals), then warps the tile piecewise-affinely (four triangles per sub-square, corners +
centre) so those measured points land on their lattice positions. Nothing is invented: the warp
only moves the photograph onto the steel it shows. Output: sources/pano-refined/ (tile, mask,
gsd, meta with the control points and the before / after residuals).
"""
import json, os, sys
import numpy as np, cv2

SRC = 'E:/sitecapture-captures/ngv-site/agent-ref-ceiling/sources/pano'
OUT = 'E:/sitecapture-captures/ngv-site/agent-ref-ceiling/sources/pano-refined' + ('-thin' if '--thin' in sys.argv else '')
GRID = dict(hu0=-56.635125, hv0=0.15882, mm=4.0)
NEW = dict(PU=7.36, PV=7.50, HU0=-45.321133, HV0=11.294317)
STEEL = 12          # max channel at or under this is steel (the panorama's steel is clipped black)
SEARCH = 100        # px each way (400 mm)


def px_of(hu, hv, px0, py0):
    return (hu - GRID['hu0']) * 1000 / GRID['mm'] - px0, (hv - GRID['hv0']) * 1000 / GRID['mm'] - py0


def match(steel, x, y, tpl):
    """best offset (dx, dy) in px of the template around (x, y), and the score"""
    W = tpl.shape[0]; R = SEARCH
    x, y = int(round(x)), int(round(y))
    y0, y1, x0, x1 = y - R - W // 2, y + R + W // 2, x - R - W // 2, x + R + W // 2
    if y0 < 0 or x0 < 0 or y1 > steel.shape[0] or x1 > steel.shape[1]:
        return None
    r = cv2.matchTemplate(steel[y0:y1, x0:x1], tpl, cv2.TM_CCOEFF_NORMED)
    _, mx, _, loc = cv2.minMaxLoc(r)
    return loc[0] - R, loc[1] - R, float(mx)


def plus_tpl(wv, wh):
    """a node: the member along v (width wv px) crossing the member along u (width wh px)"""
    W = 300
    plus = np.zeros((W, W), np.float32)
    cv2.line(plus, (0, W // 2), (W, W // 2), 1.0, wh); cv2.line(plus, (W // 2, 0), (W // 2, W), 1.0, wv)
    return plus - plus.mean()


THIN = '--thin' in sys.argv      # one 40 px + for every node instead of the members' own widths
EDGES = '--edges' in sys.argv    # also the member offsets at the sub-square edge midpoints (tried 2026-09-08: 62 of
                                 # 130 measurable, and the hips did not improve, 34 vs 32 mm median; off by default)


def node_widths(a, b):
    # lines along u: a even = column / wall lines (thin, ~160 mm), a odd = ridges (~450 mm with flanks)
    # lines along v: b odd = vertex rows (thin), b even = the edges and the mid ridge (wide)
    if THIN:
        return 40, 40
    return (40 if a % 2 == 0 else 110), (40 if b % 2 == 1 else 110)


def templates():
    PU, PV = NEW['PU'], NEW['PV']
    W = 300
    plus = plus_tpl(40, 40)
    ex = np.zeros((W, W), np.float32)
    for s in (1, -1):
        cv2.line(ex, (0, W // 2 - s * int(W / 2 * PV / PU)), (W, W // 2 + s * int(W / 2 * PV / PU)), 1.0, 40)
    return plus - plus.mean(), ex - ex.mean()


def band_offset(steel, x, y, nx, ny, width_px):
    """perpendicular offset (px) of the dark member centre at (x, y); (nx, ny) is the unit normal.
    Profile +-100 px across the member. The member is a dark run; where the glass stops on one
    side (the black wedges beside the members) only its far edge is seen, and the centre is that
    edge plus half the member's width. A run open at both ends says nothing."""
    R = 100
    ks = np.arange(-R, R + 1, dtype=np.float32)
    xs = (x + nx * ks).astype(np.float32); ys = (y + ny * ks).astype(np.float32)
    if xs.min() < 0 or ys.min() < 0 or xs.max() >= steel.shape[1] - 1 or ys.max() >= steel.shape[0] - 1:
        return None
    prof = cv2.remap(steel, xs[None, :], ys[None, :], cv2.INTER_LINEAR)[0]
    dark = prof > 0.5
    runs = []; k = 0
    while k < len(dark):
        if dark[k]:
            j = k
            while j < len(dark) and dark[j]:
                j += 1
            runs.append((k - R, j - R)); k = j
        else:
            k += 1
    cands = []
    for r0, r1 in runs:
        open0, open1 = r0 <= -R, r1 >= R + 1
        if open0 and open1:
            continue
        if not open0 and not open1:
            w = r1 - r0
            if 0.5 * width_px <= w <= 1.8 * width_px:
                cands.append((r0 + r1) / 2)
        elif open0:
            cands.append(r1 - width_px / 2)          # only the far (positive) edge is seen
        else:
            cands.append(r0 + width_px / 2)
    if not cands:
        return None
    c = min(cands, key=abs)
    return c if abs(c) <= 60 else None


def edge_width(a, b, along_u):
    # an edge along u lies on a v-line index b; an edge along v lies on a u-line index a
    if along_u:
        return 40 if b % 2 == 1 else 110
    return 40 if a % 2 == 0 else 110


def measure(steel, nodes, centres, plus, ex):
    for (a, b), p in nodes.items():
        p['m'] = match(steel, p['x'], p['y'], plus_tpl(*node_widths(a, b)))
    for p in centres.values():
        p['m'] = match(steel, p['x'], p['y'], ex)


def main():
    meta = json.load(open(SRC + '/meta.json')); px0, py0 = meta['px0'], meta['py0']
    tile = cv2.imread(SRC + '/tile.png'); mask = cv2.imread(SRC + '/mask.png', 0)
    gsd = np.load(SRC + '/gsd.npy')
    steel = (tile.max(axis=2) <= STEEL).astype(np.float32)
    plus, ex = templates()
    PU, PV = NEW['PU'], NEW['PV']
    hu_w = NEW['HU0'] - PU                                      # the west wall (vertex phase)
    hv_s = NEW['HV0'] - PV - PV / 2                             # south edge (ridge phase)
    nodes = {}
    for a in range(15):
        for b in range(5):
            hu = hu_w + a * PU / 2; hv = hv_s + b * PV / 2
            x, y = px_of(hu, hv, px0, py0)
            nodes[(a, b)] = dict(hu=hu, hv=hv, x=x, y=y, m=None)
    centres = {}
    for a in range(14):
        for b in range(4):
            hu = hu_w + (a + 0.5) * PU / 2; hv = hv_s + (b + 0.5) * PV / 2
            x, y = px_of(hu, hv, px0, py0)
            centres[(a, b)] = dict(hu=hu, hv=hv, x=x, y=y, m=None)
    measure(steel, nodes, centres, plus, ex)
    NT, CT = 0.25, 0.3
    # edge midpoints: 14 x 5 edges along u and 15 x 4 along v; the member's offset across itself
    edges = {}
    for a in range(14):
        for b in range(5):
            hu = hu_w + (a + 0.5) * PU / 2; hv = hv_s + b * PV / 2
            x, y = px_of(hu, hv, px0, py0)
            off = band_offset(steel, x, y, 0.0, 1.0, edge_width(a, b, True)) if EDGES else None
            edges[('u', a, b)] = dict(hu=hu, hv=hv, x=x, y=y, dx=0.0, dy=off if off is not None else 0.0, ok=off is not None)
    for a in range(15):
        for b in range(4):
            hu = hu_w + a * PU / 2; hv = hv_s + (b + 0.5) * PV / 2
            x, y = px_of(hu, hv, px0, py0)
            off = band_offset(steel, x, y, 1.0, 0.0, edge_width(a, b, False)) if EDGES else None
            edges[('v', a, b)] = dict(hu=hu, hv=hv, x=x, y=y, dx=off if off is not None else 0.0, dy=0.0, ok=off is not None)
    print('edge midpoints measured', sum(e['ok'] for e in edges.values()), 'of', len(edges))

    def take(p, thr):
        if p['m'] is None or p['m'][2] < thr:
            return p['x'], p['y'], False
        return p['x'] + p['m'][0], p['y'] + p['m'][1], True
    src, dst, used = [], [], 0
    for p in nodes.values():
        sx, sy, ok = take(p, NT); src.append((sx, sy)); dst.append((p['x'], p['y'])); used += ok
    for p in centres.values():
        sx, sy, ok = take(p, CT); src.append((sx, sy)); dst.append((p['x'], p['y'])); used += ok
    for e in edges.values():
        src.append((e['x'] + e['dx'], e['y'] + e['dy'])); dst.append((e['x'], e['y'])); used += e['ok']
    src = np.array(src, np.float32); dst = np.array(dst, np.float32)
    print(f'control points {len(src)}, measured {used}')
    off = src - dst; r = np.hypot(off[:, 0], off[:, 1]) * GRID['mm']; r = r[r > 0]
    print('before: radial offset of the measured steel from the lattice, p50 %.0f p90 %.0f mm' % (np.median(r), np.percentile(r, 90)))
    # piecewise-affine warp: 4 triangles per sub-square (corners + centre), lattice px -> photo px
    H, W = mask.shape
    mapx = np.full((H, W), -1, np.float32); mapy = np.full((H, W), -1, np.float32)
    idx_node = lambda a, b: a * 5 + b
    idx_c = lambda a, b: 75 + a * 4 + b
    idx_eu = lambda a, b: 131 + a * 5 + b            # edge along u at (a + 0.5, b)
    idx_ev = lambda a, b: 131 + 70 + a * 4 + b       # edge along v at (a, b + 0.5)
    for a in range(14):
        for b in range(4):
            c = idx_c(a, b)
            ring = [idx_node(a, b), idx_eu(a, b), idx_node(a + 1, b), idx_ev(a + 1, b), idx_node(a + 1, b + 1),
                    idx_eu(a, b + 1), idx_node(a, b + 1), idx_ev(a, b)]
            for t in range(8):
                tri = [ring[t], ring[(t + 1) % 8], c]
                D = dst[tri]; S = src[tri]
                A = cv2.getAffineTransform(D, S)
                x0, y0 = np.floor(D.min(0)).astype(int); x1, y1 = np.ceil(D.max(0)).astype(int)
                x0, y0 = max(x0, 0), max(y0, 0); x1, y1 = min(x1, W - 1), min(y1, H - 1)
                if x1 <= x0 or y1 <= y0:
                    continue
                yy, xx = np.mgrid[y0:y1 + 1, x0:x1 + 1]
                poly = np.zeros((y1 - y0 + 1, x1 - x0 + 1), np.uint8)
                cv2.fillConvexPoly(poly, np.round(D - [x0, y0]).astype(np.int32), 1)
                sel = poly > 0
                sub_x = mapx[y0:y1 + 1, x0:x1 + 1]; sub_y = mapy[y0:y1 + 1, x0:x1 + 1]
                sub_x[sel] = (A[0, 0] * xx + A[0, 1] * yy + A[0, 2])[sel]
                sub_y[sel] = (A[1, 0] * xx + A[1, 1] * yy + A[1, 2])[sel]
    covered = mapx >= 0
    out = cv2.remap(tile, mapx, mapy, cv2.INTER_LINEAR, borderMode=cv2.BORDER_CONSTANT)
    omask = cv2.remap(mask, mapx, mapy, cv2.INTER_NEAREST, borderMode=cv2.BORDER_CONSTANT)
    ogsd = cv2.remap(gsd, mapx, mapy, cv2.INTER_NEAREST, borderMode=cv2.BORDER_CONSTANT)
    omask[~covered] = 0; ogsd[~covered] = 0
    os.makedirs(OUT, exist_ok=True)
    cv2.imwrite(OUT + '/tile.png', out); cv2.imwrite(OUT + '/mask.png', omask); np.save(OUT + '/gsd.npy', ogsd)
    # residual after: re-measure on the warped tile
    steel2 = (out.max(axis=2) <= STEEL).astype(np.float32)
    n2 = {k: dict(v, m=None) for k, v in nodes.items()}; c2 = {k: dict(v, m=None) for k, v in centres.items()}
    measure(steel2, n2, c2, plus, ex)
    r2 = [np.hypot(p['m'][0], p['m'][1]) * GRID['mm'] for p in n2.values() if p['m'] and p['m'][2] >= NT]
    r2 += [np.hypot(p['m'][0], p['m'][1]) * GRID['mm'] for p in c2.values() if p['m'] and p['m'][2] >= CT]
    r2 = np.array(r2)
    print('after: p50 %.0f p90 %.0f mm over %d re-measured points' % (np.median(r2), np.percentile(r2, 90), len(r2)))
    meta2 = dict(meta, name='pano-refined', source_tile=SRC,
                 refinement=dict(control_points=int(len(src)), measured=int(used), before_p50_mm=float(np.median(r)), before_p90_mm=float(np.percentile(r, 90)),
                                 after_p50_mm=float(np.median(r2)), after_p90_mm=float(np.percentile(r2, 90)),
                                 edges_measured=int(sum(e['ok'] for e in edges.values())),
                                 method='piecewise affine, 8 triangles per sub-square; nodes by a + template, edge midpoints by the member profile across itself, centres by an X template on the black steel'),
                 registration=meta['registration'] + '; then piecewise-affine on 75 nodes + 56 X centres measured on the steel (tools/pano_refine.py)')
    json.dump(meta2, open(OUT + '/meta.json', 'w'), indent=1)
    json.dump(dict(nodes=[dict(a=k[0], b=k[1], hu=p['hu'], hv=p['hv'], m=p['m']) for k, p in nodes.items()],
                   centres=[dict(a=k[0], b=k[1], hu=p['hu'], hv=p['hv'], m=p['m']) for k, p in centres.items()]),
              open(OUT + '/control-points.json', 'w'), indent=0)


if __name__ == '__main__':
    main()
