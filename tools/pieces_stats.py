"""Statistics on the canopy pane files (tools/pieces.bin and the cloud-tiled backup).

Format (index.html buildGlassPieces): 'NGVP', u32 count, f32 u0, f32 v0, u16 mm scale,
then per piece: r,g,b,k (u8) and k vertices of u16 u,v (divide by mm, add origin;
hall-frame metres).

Usage: python tools/pieces_stats.py [file ...]
Default: tools/pieces.bin and tools/pieces-cloudtiled-6579.bin.bak, then a diff of the two.
"""
import colorsys
import math
import os
import struct
import sys
from collections import Counter, defaultdict

HERE = os.path.dirname(os.path.abspath(__file__))
PU, PV = 7.36, 7.50                # lattice module (index.html CANOPY.PU / PV, 2026-09-07)
REAL_AREA = 795.0                  # m2, the real Great Hall ceiling
REAL_PANELS = 224                  # triangular panels in the real ceiling


def parse(path):
    with open(path, 'rb') as f:
        buf = f.read()
    if buf[:4] != b'NGVP':
        raise SystemExit(f'{path}: bad magic {buf[:4]!r}')
    n, u0, v0, mm = struct.unpack_from('<IffH', buf, 4)
    o = 18
    pieces = []
    for _ in range(n):
        r, g, b, k = struct.unpack_from('<4B', buf, o)
        o += 4
        vs = struct.unpack_from('<%dH' % (2 * k), buf, o)
        o += 4 * k
        poly = [(u0 + vs[2 * j] / mm, v0 + vs[2 * j + 1] / mm) for j in range(k)]
        pieces.append(((r, g, b), poly))
    return dict(n=n, u0=u0, v0=v0, mm=mm, bytes=len(buf), consumed=o, pieces=pieces)


def shoelace(poly):
    s = 0.0
    for i in range(len(poly)):
        x1, y1 = poly[i]
        x2, y2 = poly[(i + 1) % len(poly)]
        s += x1 * y2 - x2 * y1
    return abs(s) / 2


def bbox(poly):
    us = [p[0] for p in poly]
    vs = [p[1] for p in poly]
    return min(us), min(vs), max(us), max(vs)


def centroid(poly):
    return sum(p[0] for p in poly) / len(poly), sum(p[1] for p in poly) / len(poly)


def pct(xs, q):
    xs = sorted(xs)
    if not xs:
        return float('nan')
    i = min(len(xs) - 1, max(0, int(round(q * (len(xs) - 1)))))
    return xs[i]


def hue_bucket(rgb):
    r, g, b = [c / 255 for c in rgb]
    h, s, v = colorsys.rgb_to_hsv(r, g, b)
    if v < 0.18:
        return 'near-black'
    if s < 0.18:
        return 'grey/white' if v > 0.6 else 'dark grey'
    deg = h * 360
    names = [(15, 'red'), (40, 'orange'), (65, 'yellow'), (95, 'yellow-green'), (160, 'green'),
             (200, 'cyan/teal'), (255, 'blue'), (290, 'violet'), (330, 'magenta/pink'), (361, 'red')]
    for lim, name in names:
        if deg < lim:
            return name
    return 'red'


def analyse(path, label):
    d = parse(path)
    pcs = d['pieces']
    print(f'\n===== {label}: {path}')
    print(f'bytes {d["bytes"]} (consumed {d["consumed"]}), pieces {d["n"]}, origin u0={d["u0"]:.4f} v0={d["v0"]:.4f}, scale {d["mm"]} /m')
    ks = Counter(len(p) for _, p in pcs)
    nv = sum(ks[k] * k for k in ks)
    print(f'vertices total {nv}, mean {nv / max(1, len(pcs)):.2f} per piece')
    print('vertex-count histogram: ' + ', '.join(f'{k}:{ks[k]}' for k in sorted(ks)))
    areas = [shoelace(p) for _, p in pcs]
    tot = sum(areas)
    zero = sum(1 for a in areas if a < 1e-6)
    print(f'area m2: total {tot:.2f}, mean {tot / len(areas):.5f}, median {pct(areas, .5):.5f}, '
          f'p10 {pct(areas, .1):.5f}, p90 {pct(areas, .9):.5f}, min {min(areas):.6f}, max {max(areas):.4f}, degenerate(<1e-6) {zero}')
    eq = [2 * math.sqrt(a / math.pi) for a in areas]   # equivalent-circle diameter
    print(f'equivalent diameter mm: median {pct(eq, .5) * 1000:.0f}, p10 {pct(eq, .1) * 1000:.0f}, p90 {pct(eq, .9) * 1000:.0f}, mean {sum(eq) / len(eq) * 1000:.0f}')
    bands = [(0, .05), (.05, .1), (.1, .15), (.15, .25), (.25, .4), (.4, 9)]
    bc = Counter()
    for e in eq:
        for lo, hi in bands:
            if lo <= e < hi:
                bc[(lo, hi)] += 1
                break
    print('equivalent-diameter bands (count, %): ' + ', '.join(
        f'{lo * 1000:.0f}-{hi * 1000:.0f}mm {bc[(lo, hi)]} ({100 * bc[(lo, hi)] / len(eq):.1f}%)' for lo, hi in bands))
    bbs = [bbox(p) for _, p in pcs]
    U0 = min(b[0] for b in bbs); V0 = min(b[1] for b in bbs); U1 = max(b[2] for b in bbs); V1 = max(b[3] for b in bbs)
    print(f'bounding box u [{U0:.3f}, {U1:.3f}] ({U1 - U0:.3f} m)  v [{V0:.3f}, {V1:.3f}] ({V1 - V0:.3f} m)  box area {(U1 - U0) * (V1 - V0):.1f} m2')
    print(f'covered / bbox = {100 * tot / ((U1 - U0) * (V1 - V0)):.1f}%   pieces per m2 of bbox = {len(pcs) / ((U1 - U0) * (V1 - V0)):.1f}')
    # per-bay bins
    bays = defaultdict(lambda: [0, 0.0])
    for (_, p), a in zip(pcs, areas):
        cu, cv = centroid(p)
        key = (math.floor(cu / PU), math.floor(cv / PV))
        bays[key][0] += 1
        bays[key][1] += a
    print(f'bays (bin = floor(u/{PU}), floor(v/{PV}); cell {PU * PV:.2f} m2): {len(bays)} occupied')
    print(f'{"bayU":>5} {"bayV":>5} {"pieces":>7} {"area m2":>8} {"cover%":>7} {"mean piece mm":>14}')
    for key in sorted(bays):
        n, a = bays[key]
        print(f'{key[0]:>5} {key[1]:>5} {n:>7} {a:>8.2f} {100 * a / (PU * PV):>7.1f} {2 * math.sqrt(a / n / math.pi) * 1000:>14.0f}')
    # colour histogram by hue bucket, weighted by area
    hb = defaultdict(lambda: [0, 0.0, [0, 0, 0]])
    for (rgb, _), a in zip(pcs, areas):
        h = hue_bucket(rgb)
        hb[h][0] += 1
        hb[h][1] += a
        for i in range(3):
            hb[h][2][i] += rgb[i] * a
    print('colour buckets (by area): ')
    for h, (n, a, acc) in sorted(hb.items(), key=lambda kv: -kv[1][1]):
        mean = tuple(int(c / max(a, 1e-9)) for c in acc)
        print(f'  {h:<13} {100 * a / tot:>5.1f}%  {n:>5} pcs  mean rgb {mean}')
    distinct = len(set(rgb for rgb, _ in pcs))
    print(f'distinct rgb values: {distinct}')
    return dict(d, areas=areas, bays=bays, tot=tot, bbox=(U0, V0, U1, V1), eq=eq)


def index_by_centroid(d, cell):
    ix = defaultdict(list)
    for i, (rgb, p) in enumerate(d['pieces']):
        cu, cv = centroid(p)
        ix[(rgb, round(cu / cell), round(cv / cell))].append(i)
    return ix


def match(a, b, tol=0.004):
    """For each piece of a: index of the piece of b with the same rgb and a centroid within tol
    (metres), else None. The files carry different origins, so exact bytes never match; a piece
    re-quantised to 1 mm under a new origin moves under 1 mm."""
    ixb = index_by_centroid(b, tol)
    out = []
    for rgb, p in a['pieces']:
        cu, cv = centroid(p)
        k0, k1 = round(cu / tol), round(cv / tol)
        found = None
        for du in (-1, 0, 1):
            for dv in (-1, 0, 1):
                for j in ixb.get((rgb, k0 + du, k1 + dv), []):
                    cb = centroid(b['pieces'][j][1])
                    if abs(cb[0] - cu) <= tol and abs(cb[1] - cv) <= tol:
                        found = j
                        break
                if found is not None:
                    break
            if found is not None:
                break
        out.append(found)
    return out


def bay_name(k, lettered):
    if lettered:
        letter = chr(65 + k[0]) if 0 <= k[0] < 26 else str(k[0])
        return letter + ('N' if k[1] == 0 else 'S' if k[1] == 1 else str(k[1]))
    return f'({k[0]},{k[1]})'


def group_stats(name, grp, phase_u, phase_v):
    ar = [shoelace(p) for _, p in grp]
    eq = [2 * math.sqrt(x / math.pi) for x in ar]
    ks = Counter(len(p) for _, p in grp)
    bb = [bbox(p) for _, p in grp]
    U0 = min(x[0] for x in bb); V0 = min(x[1] for x in bb); U1 = max(x[2] for x in bb); V1 = max(x[3] for x in bb)
    print(f'  {name}: {len(grp)} pcs, area {sum(ar):.2f} m2, median piece {pct(ar, .5):.5f} m2 '
          f'(eq diam med {pct(eq, .5) * 1000:.0f} mm, p10 {pct(eq, .1) * 1000:.0f}, p90 {pct(eq, .9) * 1000:.0f}), '
          f'tri/quad {ks[3]}/{ks[4]}, bbox u[{U0:.2f},{U1:.2f}] v[{V0:.2f},{V1:.2f}]')
    bays = defaultdict(lambda: [0, 0.0])
    for (_, p), x in zip(grp, ar):
        cu, cv = centroid(p)
        k = (math.floor((cu - phase_u) / PU), math.floor((cv - phase_v) / PV))
        bays[k][0] += 1
        bays[k][1] += x
    print('    per bay (lettered A.. from the bbox min, N/S = v row): ' + '; '.join(
        f'{bay_name(k, True)} {bays[k][0]}pcs {bays[k][1]:.1f}m2 {bays[k][0] / bays[k][1]:.0f}/m2' for k in sorted(bays)))
    return ar


def compare(head, cloud, photo, names):
    """head = the shipped file; cloud = the scan-tiled backup; photo = the 36c0bdc blob
    (photo-found pieces only), may be None."""
    print(f'\n===== provenance of {names[0]} (rgb equal + centroid within 4 mm)')
    hc = match(head, cloud)
    hp = match(head, photo) if photo else [None] * head['n']
    cls = ['photo' if a is not None else ('scan' if b is not None else 'unmatched') for a, b in zip(hp, hc)]
    c = Counter(cls)
    print(f'{names[0]}: {head["n"]} pieces -> photo-found (in {names[2] or "n/a"}) {c["photo"]}, '
          f'scan-tiled (in {names[1]}) {c["scan"]}, unmatched {c["unmatched"]}')
    U0, V0, U1, V1 = head['bbox']
    for cname in ('photo', 'scan', 'unmatched'):
        grp = [head['pieces'][i] for i, x in enumerate(cls) if x == cname]
        if grp:
            group_stats(cname, grp, U0, V0)
    # footprint claims on a 0.5 m grid
    cell = 0.5
    occ_all = defaultdict(float); occ_photo = defaultdict(float); cnt = defaultdict(int)
    for i, (rgb, p) in enumerate(head['pieces']):
        cu, cv = centroid(p)
        k = (math.floor(cu / cell), math.floor(cv / cell))
        a = shoelace(p)
        occ_all[k] += a; cnt[k] += 1
        if cls[i] == 'photo':
            occ_photo[k] += a
    tot_cells = len(occ_all) * cell * cell
    ph_cells = len(occ_photo) * cell * cell
    dil = set()
    for k in occ_photo:
        for du in (-1, 0, 1):
            for dv in (-1, 0, 1):
                dil.add((k[0] + du, k[1] + dv))
    print(f'0.5 m cells holding any piece: {len(occ_all)} = {tot_cells:.1f} m2 (bbox {(U1 - U0) * (V1 - V0):.1f} m2)')
    if c['photo']:
        print(f'  cells holding a photo-found piece: {ph_cells:.1f} m2 = {100 * ph_cells / tot_cells:.1f}% of occupied cells; '
              f'glass fill inside them {100 * sum(occ_photo.values()) / ph_cells:.1f}%, {c["photo"] / ph_cells:.1f} pieces/m2')
        print(f'  photo claim dilated by one 0.5 m cell (the commit: "the half metre round its found pieces"): '
              f'{len(dil) * cell * cell:.1f} m2 = {100 * len(dil) * cell * cell / (58.9 * 15.0):.0f}% of a 58.9 x 15.0 m board')
    sc = [k for k in occ_all if k not in occ_photo]
    sa = sum(occ_all[k] for k in sc)
    print(f'  scan-only cells: {len(sc) * cell * cell:.1f} m2 = {100 * len(sc) / len(occ_all):.1f}% of occupied cells; '
          f'glass fill {100 * sa / max(1e-9, len(sc) * cell * cell):.1f}%, {sum(cnt[k] for k in sc) / max(1e-9, len(sc) * cell * cell):.1f} pieces/m2')
    scan_area = sum(shoelace(p) for i, (rgb, p) in enumerate(head['pieces']) if cls[i] == 'scan')
    print(f'  by count: scan-tiled {100 * c["scan"] / head["n"]:.1f}% of pieces; by glass area: {100 * scan_area / head["tot"]:.1f}%')
    for cname in ('photo', 'scan'):
        sats = [colorsys.rgb_to_hsv(*(ch / 255 for ch in rgb))[1] for i, (rgb, p) in enumerate(head['pieces']) if cls[i] == cname]
        if sats:
            print(f'  {cname} mean HSV saturation {sum(sats) / len(sats):.3f}, median {pct(sats, .5):.3f}')


def main(argv):
    files = argv[1:] or [os.path.join(HERE, 'pieces.bin'), os.path.join(HERE, 'pieces-cloudtiled-6579.bin.bak')]
    # optional third file: the 36c0bdc blob (photo-found pieces only):
    #   git show 36c0bdc:tools/pieces.bin > <scratch>/pieces-36c0bdc-photo3114.bin
    res = [analyse(f, os.path.basename(f)) for f in files]
    print(f'\n===== against the real ceiling: {REAL_AREA} m2, {REAL_PANELS} triangular panels '
          f'({REAL_AREA / REAL_PANELS:.2f} m2 each), pieces 100-250 mm')
    for f, r in zip(files, res):
        n = r['n']; cov = r['tot']
        print(f'  {os.path.basename(f)}: {n} pieces, glass {cov:.1f} m2 = {100 * cov / REAL_AREA:.1f}% of {REAL_AREA} m2, '
              f'{n / REAL_AREA:.1f} pieces per m2 of real ceiling; mean piece {cov / n:.4f} m2 '
              f'({2 * math.sqrt(cov / n / math.pi) * 1000:.0f} mm eq)')
    print(f'  model lattice: {PU} x {PV} m module, 4 facets per bay; the 7x2 plate = 56 facets of {PU * PV / 4:.1f} m2, '
          f'8x2 = 64. Real: {REAL_PANELS} panels = {REAL_PANELS / 16:.0f} per bay, {REAL_PANELS / 64:.1f} per model facet')
    if len(res) >= 2:
        compare(res[0], res[1], res[2] if len(res) >= 3 else None,
                [os.path.basename(f) for f in files] + [None] * (3 - len(files)))


if __name__ == '__main__':
    main(sys.argv)
