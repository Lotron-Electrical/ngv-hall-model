"""Track C step 6: facet brightness by day (b0), piece look at 4K (balcony b001), colour stats
from the saturated close-ups, rosette scale from the entrance shot.

Usage: python tools/ref_stats_more.py <out_dir> <b0.webp> <b001.jpg> <closeup1> <closeup2> <entrance>
Writes <out_dir>/more.json, facet overlays, look crops.
"""
import sys, os, json
import numpy as np
import cv2
from PIL import Image

out, b0p, balcp, cu1p, cu2p, entp = sys.argv[1:7]
res = {}


def load(p):
    if p.endswith('.webp'):
        return cv2.cvtColor(np.array(Image.open(p).convert('RGB')), cv2.COLOR_RGB2BGR)
    return cv2.imread(p)


# ---------------- facets in b0 (oblique whole-hall shot, camera at the balcony end) ----------------
# polygons picked by eye on the gridded crops (b0_bayA_grid.jpg, b0_bayC_grid.jpg); image coords of b0
bays = {
    'A': dict(vertex=(2720, 480), far=[(2050, 110), (3400, 110)], near=[(2000, 610), (3450, 600)]),
    'C': dict(vertex=(3215, 1210), far=[(2870, 880), (3590, 880)], near=[(2860, 1300), (3600, 1300)]),
}
b0 = load(b0p)
hsv0 = cv2.cvtColor(b0, cv2.COLOR_BGR2HSV)
V0 = hsv0[..., 2]; S0 = hsv0[..., 1]
facet_res = {}
for name, b in bays.items():
    v = b['vertex']; fl, fr = b['far']; nl, nr = b['near']
    polys = {'far': [v, fl, fr], 'near': [v, nl, nr], 'left': [v, nl, fl], 'right': [v, nr, fr]}
    ov = b0.copy()
    fr_ = {}
    for k, P in polys.items():
        m = np.zeros(b0.shape[:2], np.uint8)
        cv2.fillPoly(m, [np.array(P, np.int32)], 1)
        cv2.polylines(ov, [np.array(P, np.int32)], True, (0, 255, 0), 3)
        cv2.putText(ov, k, tuple(np.mean(P, axis=0).astype(int)), cv2.FONT_HERSHEY_SIMPLEX, 1.2, (0, 255, 255), 3)
        mm = m.astype(bool)
        glass = mm & (V0 > 110)
        col = glass & (S0 > 80); clr = glass & (S0 <= 80)
        vg = V0[glass].astype(float)
        fr_[k] = dict(area_px=int(mm.sum()), glass_frac=float(glass.sum() / mm.sum()),
                      glass_V_mean=float(vg.mean()), glass_V_p50=float(np.median(vg)),
                      clipped_frac_of_glass=float((vg >= 250).mean()),
                      coloured_V_p50=float(np.median(V0[col])) if col.sum() else None,
                      clear_V_p50=float(np.median(V0[clr])) if clr.sum() else None,
                      clear_share_of_glass=float(clr.sum() / max(1, glass.sum())),
                      facet_mean_V=float(V0[mm].mean()))
    facet_res[name] = dict(polys={k: [list(map(int, p)) for p in P] for k, P in polys.items()}, facets=fr_)
    x0 = min(p[0] for P in polys.values() for p in P) - 60; x1 = max(p[0] for P in polys.values() for p in P) + 60
    y0 = min(p[1] for P in polys.values() for p in P) - 60; y1 = max(p[1] for P in polys.values() for p in P) + 60
    cv2.imwrite(os.path.join(out, 'b0_facets_%s.jpg' % name), ov[max(0, y0):y1, max(0, x0):x1], [cv2.IMWRITE_JPEG_QUALITY, 85])
    print(name, json.dumps({k: {kk: round(vv, 3) if isinstance(vv, float) else vv for kk, vv in d.items()} for k, d in fr_.items()}))
res['b0_facets'] = facet_res

# ---------------- piece look from the 4K balcony still (b001, top strip) ----------------
bl = load(balcp)[0:1100, 400:2160]
hsv = cv2.cvtColor(bl, cv2.COLOR_BGR2HSV); V = hsv[..., 2]; S = hsv[..., 1]
rgb = cv2.cvtColor(bl, cv2.COLOR_BGR2RGB).astype(np.float32)
Lum = 0.2126 * rgb[..., 0] + 0.7152 * rgb[..., 1] + 0.0722 * rgb[..., 2]
mask = (V > 70).astype(np.uint8)
mask = cv2.morphologyEx(mask, cv2.MORPH_OPEN, np.ones((5, 5), np.uint8))
n, lab, st, ce = cv2.connectedComponentsWithStats(mask, connectivity=4)
dt = cv2.distanceTransform(mask, cv2.DIST_L2, 5)
dt_out = cv2.distanceTransform(1 - mask, cv2.DIST_L2, 5)
rows = []
ov = bl.copy()
for i in range(1, n):
    x, y, w, h, a = st[i]
    if a < 1500 or x <= 2 or y <= 2 or x + w >= bl.shape[1] - 2 or y + h >= bl.shape[0] - 2:
        continue
    comp = lab == i
    d = dt[comp]; l = Lum[comp]
    px = rgb[comp]
    core = d >= 8
    if core.sum() < 200:
        continue
    clipped = float((px.max(axis=1) >= 250).mean())
    med = np.median(px[core], axis=0)
    hs = cv2.cvtColor(np.uint8([[med]]), cv2.COLOR_RGB2HSV)[0, 0]
    interior = l[core]
    prof = {}
    for r in range(1, 9):
        m = (d >= r) & (d < r + 1)
        prof[r] = float(l[m].mean() / interior.mean()) if m.sum() > 5 else None
    eqd = 2 * np.sqrt(a / np.pi)
    rows.append(dict(id=int(i), area_px=int(a), eqd_px=float(eqd), clipped_frac=clipped,
                     med_rgb=[int(v) for v in med], sat=float(hs[1]) / 255, val=float(hs[2]) / 255,
                     rim_profile_rel=prof, interior_cv=float(interior.std() / interior.mean()),
                     interior_p10_p90_rel=[float(np.percentile(interior, q) / interior.mean()) for q in (10, 90)]))
    colr = (0, 255, 0) if clipped < 0.1 else (0, 0, 255)
    cv2.rectangle(ov, (x, y), (x + w, y + h), colr, 2)
    cv2.putText(ov, str(i), (x, y - 3), cv2.FONT_HERSHEY_SIMPLEX, 0.5, colr, 1)
cv2.imwrite(os.path.join(out, 'balc_b001_pieces_overlay.jpg'), cv2.resize(ov, None, fx=0.75, fy=0.75), [cv2.IMWRITE_JPEG_QUALITY, 85])
ok = [r for r in rows if r['clipped_frac'] < 0.1 and r['sat'] > 0.25]
print('balcony pieces', len(rows), 'unclipped coloured', len(ok))


def agg(key, rs, q=(25, 50, 75)):
    return [float(np.percentile([r[key] for r in rs], x)) for x in q]


rim = {}
for r_ in range(1, 9):
    vals = [r['rim_profile_rel'][r_] for r in ok if r['rim_profile_rel'][r_] is not None]
    rim[r_] = [float(np.percentile(vals, q)) for q in (25, 50, 75)] if vals else None
far = (dt_out >= 6) & (dt_out < 40)
mat = np.median(rgb[far], axis=0)
mat_p = [float(np.percentile(Lum[far], q)) for q in (10, 50, 90)]
look = dict(n_pieces=len(rows), n_unclipped_coloured=len(ok),
            eqd_px_p10_p50_p90=agg('eqd_px', rows, (10, 50, 90)),
            rim_profile_rel_by_px_p25_p50_p75=rim,
            interior_cv_p10_p50_p90=agg('interior_cv', ok, (10, 50, 90)),
            interior_p10_rel_p50=float(np.median([r['interior_p10_p90_rel'][0] for r in ok])),
            interior_p90_rel_p50=float(np.median([r['interior_p10_p90_rel'][1] for r in ok])),
            matrix_med_rgb=[float(v) for v in mat], matrix_lum_p10_p50_p90=mat_p,
            sat_of_unclipped_coloured_p10_p50_p90=agg('sat', ok, (10, 50, 90)))
print(json.dumps(look, indent=1))
res['balcony_b001_look'] = look
ok_sorted = sorted(ok, key=lambda r: -r['area_px'])[:6]
tiles = []
for r in ok_sorted:
    x, y, w, h, a = st[r['id']]
    t = bl[max(0, y - 10):y + h + 10, max(0, x - 10):x + w + 10]
    tiles.append(cv2.resize(t, (260, 260)))
if tiles:
    cv2.imwrite(os.path.join(out, 'balc_b001_piece_tiles.jpg'), np.concatenate(tiles, axis=1), [cv2.IMWRITE_JPEG_QUALITY, 90])


# ---------------- colour stats from the saturated close-ups ----------------
def family(h, s, v):
    if s < 0.25 and v > 0.78: return 'clear'
    if s < 0.55 and (h >= 330 or h < 25): return 'pink'
    if h >= 345 or h < 12: return 'red'
    if h < 32: return 'orange'
    if h < 48: return 'amber'
    if h < 72: return 'yellow'
    if h < 165: return 'green'
    if h < 200: return 'cyan'
    if h < 262: return 'blue'
    if h < 292: return 'violet'
    return 'magenta'


fams = ['red', 'orange', 'amber', 'yellow', 'green', 'cyan', 'blue', 'violet', 'magenta', 'pink', 'clear']


def colour_stats(img, name, thr=90, min_area=30):
    hsv = cv2.cvtColor(img, cv2.COLOR_BGR2HSV); V = hsv[..., 2]
    m = (V > thr).astype(np.uint8)
    m = cv2.morphologyEx(m, cv2.MORPH_OPEN, np.ones((3, 3), np.uint8))
    n, lab, st, ce = cv2.connectedComponentsWithStats(m, connectivity=4)
    dt = cv2.distanceTransform(m, cv2.DIST_L2, 3)
    rgb = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
    H, Sx, Vx, A, F, M = [], [], [], [], [], []
    for i in range(1, n):
        a = st[i, cv2.CC_STAT_AREA]
        if a < min_area:
            continue
        comp = (lab == i) & (dt >= 1.5)
        if comp.sum() < 5:
            comp = lab == i
        med = np.median(rgb[comp], axis=0)
        hs = cv2.cvtColor(np.uint8([[med]]), cv2.COLOR_RGB2HSV)[0, 0]
        h, s, v = hs[0] * 2.0, hs[1] / 255.0, hs[2] / 255.0
        H.append(h); Sx.append(s); Vx.append(v); A.append(a); F.append(family(h, s, v)); M.append(med)
    H, Sx, Vx, A, M = map(np.array, (H, Sx, Vx, A, M)); F = np.array(F)
    tot = A.sum()
    clear = F == 'clear'
    buckets = {}
    for k in range(12):
        dh = ((H - 30 * k + 180) % 360) - 180
        mm = (~clear) & (dh >= -15) & (dh < 15)
        buckets['%03d' % ((30 * k) % 360)] = dict(centre_deg=30 * k % 360, area_frac=float(A[mm].sum() / tot), count=int(mm.sum()))
    buckets['clear'] = dict(area_frac=float(A[clear].sum() / tot), count=int(clear.sum()))
    famstats = {}
    for f in fams:
        idx = F == f
        if idx.sum() == 0:
            famstats[f] = dict(count=0); continue
        famstats[f] = dict(count=int(idx.sum()), area_frac=float(A[idx].sum() / tot),
                           median_srgb=[int(v) for v in np.median(M[idx], axis=0)],
                           sat_p10_p50_p90=[float(np.percentile(Sx[idx], q)) for q in (10, 50, 90)],
                           val_p10_p50_p90=[float(np.percentile(Vx[idx], q)) for q in (10, 50, 90)],
                           hue_p50=float(np.median(H[idx])))
    r = dict(n_pieces=int(len(A)), hue_buckets_30deg=buckets, families=famstats,
             coloured_sat_p10_p50_p90=[float(np.percentile(Sx[~clear], q)) for q in (10, 50, 90)],
             coloured_val_p10_p50_p90=[float(np.percentile(Vx[~clear], q)) for q in (10, 50, 90)],
             clear_area_frac=float(A[clear].sum() / tot), clear_count_frac=float(clear.mean()), thr=thr)
    print(name, 'n', r['n_pieces'], 'clear area', round(r['clear_area_frac'], 3), 'sat p50', round(r['coloured_sat_p10_p50_p90'][1], 3),
          {k: round(v['area_frac'], 3) for k, v in buckets.items()})
    return r


res['closeup_colour'] = dict(closeup1_10f13e18=colour_stats(load(cu1p), 'cu1'),
                             closeup2_06984bd9=colour_stats(load(cu2p), 'cu2'),
                             entrance_3de491c9=colour_stats(load(entp)[150:600, :], 'entrance', min_area=12))

# ---------------- rosette scale from the entrance shot ----------------
ent = load(entp)
V = cv2.cvtColor(ent, cv2.COLOR_BGR2HSV)[..., 2].astype(np.float32)
band = 1.0 - V[250:520, :] / 255.0
prof = band.mean(axis=0)
prof = cv2.GaussianBlur(prof[None], (0, 0), 2)[0]
pk = [i for i in range(3, len(prof) - 3) if prof[i] == prof[i - 3:i + 4].max() and prof[i] > prof.mean() + 0.5 * prof.std()]
res['entrance_rosette'] = dict(dark_column_peaks_x=pk, note='rosette ring picked by eye on entrance_centre_x2.jpg')
print('entrance dark column peaks', pk)
json.dump(res, open(os.path.join(out, 'more.json'), 'w'), indent=1)
