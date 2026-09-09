"""Track C step 3: derived statistics + mirror-symmetry test from pieces.json / mask.npy.

Usage: python tools/ref_stats_derive.py <lf02.jpg> <out_dir>
Writes <out_dir>/derived.json, symmetry_*.jpg
"""
import sys, os, json
import numpy as np
import cv2

src, out = sys.argv[1], sys.argv[2]
P = json.load(open(os.path.join(out, 'pieces.json')))
pieces = P['pieces']
mm = P['mm_per_px']; px_per_m = P['px_per_m']
img = cv2.imread(src); rgb = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
mask = np.load(os.path.join(out, 'mask.npy'))
H, W = mask.shape
sq = P['squares']

def pct(a, q):
    return [float(np.percentile(a, x)) for x in q]

# ---------- sizes ----------
area_m2 = np.array([p['area_px'] for p in pieces]) / px_per_m ** 2
eqd = np.array([p['eq_diam_mm'] for p in pieces])
asp = np.array([p['aspect'] for p in pieces])
wid = np.array([p['rect_w_mm'] for p in pieces]); hei = np.array([p['rect_h_mm'] for p in pieces])
shapes = [p['shape'] for p in pieces]
field_area_m2 = sum(c['area_px'] - c['rib_px'] for c in P['coverage'].values()) / px_per_m ** 2
plan_area_m2 = sum(c['area_px'] for c in P['coverage'].values()) / px_per_m ** 2
sizes = dict(
    n_pieces=len(pieces), plan_area_m2=plan_area_m2, field_area_m2_excl_ribs_p50=field_area_m2,
    pieces_per_m2_plan=len(pieces) / plan_area_m2, pieces_per_m2_field=len(pieces) / field_area_m2,
    eq_diam_mm_p10_p50_p90=pct(eqd, [10, 50, 90]), eq_diam_mm_mean=float(eqd.mean()),
    eq_diam_mm_area_weighted_p10_p50_p90=[float(v) for v in np.interp([0.1, 0.5, 0.9], np.cumsum(area_m2[np.argsort(eqd)]) / area_m2.sum(), np.sort(eqd))],
    minrect_long_mm_p10_p50_p90=pct(wid, [10, 50, 90]), minrect_short_mm_p10_p50_p90=pct(hei, [10, 50, 90]),
    aspect_p10_p50_p90=pct(asp, [10, 50, 90]),
    shape_share_count={s: shapes.count(s) / len(shapes) for s in ('rect', 'tri', 'irregular')},
    shape_share_area={s: float(area_m2[[i for i, x in enumerate(shapes) if x == s]].sum() / area_m2.sum()) for s in ('rect', 'tri', 'irregular')},
    area_mm2_p10_p50_p90=pct(area_m2 * 1e6, [10, 50, 90]),
)
print(json.dumps(sizes, indent=1))

# ---------- colour ----------
hue = np.array([p['hue'] for p in pieces]); sat = np.array([p['sat'] for p in pieces]); val = np.array([p['val'] for p in pieces])
clear = (sat < 0.25) & (val > 0.78)
def family(h, s, v):
    if s < 0.25 and v > 0.78:
        return 'clear'
    if s < 0.55 and (h >= 330 or h < 25):
        return 'pink'
    if h >= 345 or h < 12: return 'red'
    if h < 32: return 'orange'
    if h < 48: return 'amber'
    if h < 72: return 'yellow'
    if h < 165: return 'green'
    if h < 200: return 'cyan'
    if h < 262: return 'blue'
    if h < 292: return 'violet'
    return 'magenta'
fam = [family(h, s, v) for h, s, v in zip(hue, sat, val)]
fams = ['red', 'orange', 'amber', 'yellow', 'green', 'cyan', 'blue', 'violet', 'magenta', 'pink', 'clear']
buckets = {}
tot = area_m2.sum()
for k in range(12):
    lo, hi = 30 * k - 15, 30 * k + 15
    m = (~clear) & (((hue - 30 * k + 180) % 360 - 180) >= -15) & (((hue - 30 * k + 180) % 360 - 180) < 15)
    buckets[f'{(30*k)%360:03d}'] = dict(centre_deg=30 * k % 360, area_frac=float(area_m2[m].sum() / tot), count=int(m.sum()))
buckets['clear'] = dict(area_frac=float(area_m2[clear].sum() / tot), count=int(clear.sum()))
fam_stats = {}
def srgb_to_lin(c):
    c = np.asarray(c, np.float64) / 255.0
    return np.where(c <= 0.04045, c / 12.92, ((c + 0.055) / 1.055) ** 2.4)
for f in fams:
    idx = [i for i, x in enumerate(fam) if x == f]
    if not idx:
        fam_stats[f] = dict(count=0); continue
    meds = np.array([pieces[i]['med_rgb'] for i in idx], np.float64)
    w = area_m2[idx]
    med = np.median(meds, axis=0)
    fam_stats[f] = dict(count=len(idx), area_frac=float(w.sum() / tot), median_srgb=[int(v) for v in med],
                        median_linear=[float(v) for v in srgb_to_lin(med)],
                        sat_p10_p50_p90=pct(sat[idx], [10, 50, 90]), val_p10_p50_p90=pct(val[idx], [10, 50, 90]),
                        clipped_frac_mean=float(np.mean([pieces[i]['clipped_frac'] for i in idx])))
coloured = ~clear
colour = dict(hue_buckets_30deg=buckets, families=fam_stats,
              coloured_sat_p10_p50_p90=pct(sat[coloured], [10, 50, 90]),
              coloured_val_p10_p50_p90=pct(val[coloured], [10, 50, 90]),
              clear_area_frac=float(area_m2[clear].sum() / tot), clear_count_frac=float(clear.mean()),
              clear_hard_clipped_frac=float(np.mean([p['clipped_frac'] > 0.5 for p, c in zip(pieces, clear) if c])))
# transmission estimate: linear sRGB / exposure gain k. k chosen so the brightest coloured family channel = 0.62
lin_max = max(max(fam_stats[f]['median_linear']) for f in fams if f not in ('clear', 'pink') and fam_stats[f].get('count', 0) > 2)
k = lin_max / 0.62
trans = {}
for f in fams:
    if fam_stats[f].get('count', 0) == 0:
        continue
    if f == 'clear':
        trans[f] = [0.85, 0.85, 0.85]
    else:
        trans[f] = [float(min(0.9, v / k)) for v in fam_stats[f]['median_linear']]
colour['transmission_estimate'] = dict(exposure_gain_k=float(k), values=trans,
    method='per-family median piece sRGB -> linear (sRGB EOTF), divided by k; k set so the brightest coloured '
           'channel (yellow/amber) = 0.62, a typical 25 mm pot-glass peak transmission; clear fixed at 0.85 because '
           'it is clipped in the photo. Absolute level uncertain by ~x1.5; hue ratios between channels are the measured part.')
print(json.dumps(colour['families'], indent=1))
print('k', k, trans)

# ---------- piece look ----------
ok = [p for p in pieces if p['interior_mean'] and p['clipped_frac'] < 0.2 and p['area_px'] > 150 and p['edge_prof']['1'] and p['edge_prof']['2'] and p['edge_prof']['3']]
r1 = np.array([p['edge_prof']['1'] / p['interior_mean'] for p in ok])
r2 = np.array([p['edge_prof']['2'] / p['interior_mean'] for p in ok])
r3 = np.array([p['edge_prof']['3'] / p['interior_mean'] for p in ok])
cv = np.array([p['interior_std'] / p['interior_mean'] for p in ok])
look = dict(n_unclipped_pieces=len(ok),
            edge_lum_ratio_d1px_p25_p50_p75=pct(r1, [25, 50, 75]), edge_lum_ratio_d2px=pct(r2, [25, 50, 75]),
            edge_lum_ratio_d3px=pct(r3, [25, 50, 75]), pixel_mm=mm,
            interior_cv_p10_p50_p90=pct(cv, [10, 50, 90]),
            matrix_field_rgb=P['matrix_field_rgb'], matrix_rib_rgb=P['matrix_rib_rgb'],
            matrix_lum_p10_50_90=P['matrix_field_lum_p10_50_90'])
print(json.dumps(look, indent=1))

# ---------- mirror symmetry ----------
vx = sorted(set([sq['TL'][0], sq['TL'][2], sq['TR'][2]])); hy = sorted(set([sq['TL'][1], sq['TL'][3], sq['BL'][3]]))
cx, cy = vx[1], hy[1]
blur = cv2.GaussianBlur(mask.astype(np.float32), (0, 0), 5)
col = cv2.GaussianBlur(rgb.astype(np.float32), (0, 0), 5)
def crop(im, x0, y0, x1, y1):
    return im[int(y0):int(y1), int(x0):int(x1)]
def ncc(a, b):
    a = a - a.mean(); b = b - b.mean()
    return float((a * b).sum() / np.sqrt((a * a).sum() * (b * b).sum() + 1e-9))
def best_ncc(a, b, shift=12):
    """max NCC over small translations of b"""
    best = -1
    h, w = a.shape[:2]
    for dy in range(-shift, shift + 1, 2):
        for dx in range(-shift, shift + 1, 2):
            bb = b[shift + dy:shift + dy + h - 2 * shift, shift + dx:shift + dx + w - 2 * shift]
            aa = a[shift:h - shift, shift:w - shift]
            best = max(best, ncc(aa, bb))
    return best
S = 440  # inner size of the comparison square (avoid the members)
def square(im, k):
    x0, y0, x1, y1 = sq[k]
    return crop(im, x0 + 15, y0 + 15, x0 + 15 + S, y0 + 15 + S)
res = {}
for im_name, im in (('mask', blur), ('colour', col)):
    TL, TR, BL, BR = [square(im, k) for k in ('TL', 'TR', 'BL', 'BR')]
    res[im_name] = dict(
        TL_vs_mirrorLR_TR=best_ncc(TL, TR[:, ::-1]), TL_vs_plain_TR=best_ncc(TL, TR),
        TL_vs_mirrorUD_BL=best_ncc(TL, BL[::-1, :]), TL_vs_plain_BL=best_ncc(TL, BL),
        TL_vs_rot180_BR=best_ncc(TL, BR[::-1, ::-1]), TL_vs_plain_BR=best_ncc(TL, BR),
        TR_vs_mirrorUD_BR=best_ncc(TR, BR[::-1, :]),
        # within a square: transpose about the main diagonal (TL main diag runs corner (x0,y0)->(x1,y1) = matrix transpose)
        TL_vs_transpose_TL=best_ncc(TL, np.swapaxes(TL, 0, 1)),
        TR_vs_antitranspose_TR=best_ncc(TR, np.swapaxes(TR[::-1, ::-1], 0, 1)),
        BL_vs_antitranspose_BL=best_ncc(BL, np.swapaxes(BL[::-1, ::-1], 0, 1)),
        BR_vs_transpose_BR=best_ncc(BR, np.swapaxes(BR, 0, 1)),
        TL_vs_antitranspose_TL_control=best_ncc(TL, np.swapaxes(TL[::-1, ::-1], 0, 1)),
    )
print(json.dumps(res, indent=1))
# visual: TL | mirrored TR | mirrored BL | rot180 BR
TLc, TRc, BLc, BRc = [square(rgb, k) for k in ('TL', 'TR', 'BL', 'BR')]
strip = np.concatenate([TLc, TRc[:, ::-1], BLc[::-1, :], BRc[::-1, ::-1]], axis=1)
cv2.imwrite(os.path.join(out, 'symmetry_TL_mirrorTR_mirrorBL_rot180BR.jpg'), cv2.cvtColor(strip, cv2.COLOR_RGB2BGR), [cv2.IMWRITE_JPEG_QUALITY, 88])
strip2 = np.concatenate([TLc, np.swapaxes(TLc, 0, 1)], axis=1)
cv2.imwrite(os.path.join(out, 'symmetry_TL_vs_transposeTL.jpg'), cv2.cvtColor(strip2, cv2.COLOR_RGB2BGR), [cv2.IMWRITE_JPEG_QUALITY, 88])

json.dump(dict(sizes=sizes, colour=colour, look=look, symmetry=res, family_of_piece=fam),
          open(os.path.join(out, 'derived.json'), 'w'), indent=1)
