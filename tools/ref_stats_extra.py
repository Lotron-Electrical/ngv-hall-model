"""Track C step 4: emblem sizes, cross-member mirror test, clear/coloured ratio in other photos,
gridded crops of the whole-ceiling photo for facet polygon picking.

Usage: python tools/ref_stats_extra.py <lf02.jpg> <out_dir> <gh03.jpg> <bc0.jpg> <b0.webp>
"""
import sys, os, json
import numpy as np
import cv2
from PIL import Image

src, out, gh03, bc0, b0 = sys.argv[1:6]
P = json.load(open(os.path.join(out, 'pieces.json')))
pieces = P['pieces']; mm = P['mm_per_px']; px_per_m = P['px_per_m']
img = cv2.imread(src); rgb = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
mask = np.load(os.path.join(out, 'mask.npy'))
H, W = mask.shape
sq = P['squares']
res = {}

# ---------- emblems: square-ring-with-X ----------
# centres read off the overlay by eye (top half), mirrored across the ridge for the bottom half
ridge_y = sq['TL'][3]
top = [(560, 180), (720, 180), (560, 300), (720, 300), (330, 420), (450, 420), (820, 420), (950, 420)]
centres = top + [(x, int(2 * ridge_y - y)) for x, y in top]
emb = []
tiles = []
for (ex, ey) in centres:
    # inner X-square: the 4 triangles near the centre (pieces with centroid within 30 px)
    inner = [p for p in pieces if abs(p['cx'] - ex) < 32 and abs(p['cy'] - ey) < 32]
    ring = [p for p in pieces if abs(p['cx'] - ex) < 75 and abs(p['cy'] - ey) < 75 and p not in inner]
    if not inner:
        continue
    # extent from the piece masks
    lab_box = mask[ey - 40:ey + 40, ex - 40:ex + 40]
    ys, xs = np.where(lab_box > 0)
    # restrict to pixels of the inner pieces: use the union bbox of inner pieces
    x0 = min(p['cx'] - p['rect_w_mm'] / mm / 2 for p in inner); x1 = max(p['cx'] + p['rect_w_mm'] / mm / 2 for p in inner)
    y0 = min(p['cy'] - p['rect_w_mm'] / mm / 2 for p in inner); y1 = max(p['cy'] + p['rect_w_mm'] / mm / 2 for p in inner)
    rx0 = min(p['cx'] for p in ring + inner); rx1 = max(p['cx'] for p in ring + inner)
    ry0 = min(p['cy'] for p in ring + inner); ry1 = max(p['cy'] for p in ring + inner)
    fam_in = [p['med_rgb'] for p in inner]
    emb.append(dict(centre=[ex, ey], n_inner=len(inner), inner_extent_m=[(x1 - x0) / px_per_m, (y1 - y0) / px_per_m],
                    inner_med_rgb=[int(v) for v in np.median(fam_in, axis=0)],
                    n_ring=len(ring), ring_extent_m_centres=[(rx1 - rx0) / px_per_m, (ry1 - ry0) / px_per_m],
                    ring_med_rgb=[int(v) for v in np.median([p['med_rgb'] for p in ring], axis=0)] if ring else None))
    t = img[max(0, ey - 80):ey + 80, max(0, ex - 80):ex + 80]
    if t.shape[0] == 160 and t.shape[1] == 160:
        tiles.append(t)
res['emblems'] = emb
if tiles:
    rows = [np.concatenate(tiles[i:i + 8], axis=1) for i in range(0, len(tiles) - len(tiles) % 8, 8)]
    mont = np.concatenate(rows, axis=0)
    cv2.imwrite(os.path.join(out, 'emblem_montage_x2.jpg'), cv2.resize(mont, None, fx=2, fy=2, interpolation=cv2.INTER_CUBIC), [cv2.IMWRITE_JPEG_QUALITY, 90])
for e in emb:
    print(e)

# ---------- mirror across a cross member (x=169 and y=22 / y=960) using the partial strips ----------
blur = cv2.GaussianBlur(mask.astype(np.float32), (0, 0), 5)
def ncc(a, b):
    a = a - a.mean(); b = b - b.mean()
    return float((a * b).sum() / np.sqrt((a * a).sum() * (b * b).sum() + 1e-9))
def best_ncc(a, b, shift=10):
    best = -1; h, w = a.shape[:2]
    for dy in range(-shift, shift + 1, 2):
        for dx in range(-shift, shift + 1, 2):
            bb = b[shift + dy:shift + dy + h - 2 * shift, shift + dx:shift + dx + w - 2 * shift]
            aa = a[shift:h - shift, shift:w - shift]
            best = max(best, ncc(aa, bb))
    return best
x_cm = int(sq['TL'][0]); y_top = int(sq['TL'][1]); y_bot = int(sq['BL'][3]); x_cm2 = int(sq['TR'][2])
w = x_cm - 12   # strip width available left of the cross member
L = blur[y_top + 20:y_bot - 20, 12:x_cm]          # left of x=169
Rm = blur[y_top + 20:y_bot - 20, x_cm:x_cm + w][:, ::-1]   # right of x=169, mirrored
Rp = blur[y_top + 20:y_bot - 20, x_cm:x_cm + w]
res['cross_member_mirror'] = dict(
    left_strip_vs_mirror_right=best_ncc(L, Rm), left_strip_vs_plain_right=best_ncc(L, Rp), strip_width_px=w,
)
w2 = W - x_cm2 - 12
L2 = blur[y_top + 20:y_bot - 20, x_cm2 - w2:x_cm2][:, ::-1]
R2 = blur[y_top + 20:y_bot - 20, x_cm2:x_cm2 + w2]
res['cross_member_mirror'].update(right_strip_vs_mirror_left=best_ncc(R2, L2),
                                  right_strip_vs_plain_left=best_ncc(R2, blur[y_top + 20:y_bot - 20, x_cm2 - w2:x_cm2]))
hb = H - y_bot - 6
B = blur[y_bot:y_bot + hb, 12:W - 12]; Am = blur[y_bot - hb:y_bot, 12:W - 12][::-1, :]; Ap = blur[y_bot - hb:y_bot, 12:W - 12]
res['cross_member_mirror'].update(bottom_strip_vs_mirror_above=best_ncc(B, Am, shift=6), bottom_strip_vs_plain_above=best_ncc(B, Ap, shift=6), bottom_strip_h_px=hb)
print(res['cross_member_mirror'])
strip = np.concatenate([rgb[y_top + 20:y_bot - 20, 12:x_cm], rgb[y_top + 20:y_bot - 20, x_cm:x_cm + w][:, ::-1]], axis=1)
cv2.imwrite(os.path.join(out, 'symmetry_crossmember_left_vs_mirrorright.jpg'), cv2.cvtColor(strip, cv2.COLOR_RGB2BGR), [cv2.IMWRITE_JPEG_QUALITY, 88])

# ---------- clear vs coloured brightness in other photos ----------
def clear_vs_colour(path, region, thr=110, min_area=25, name=''):
    im = cv2.imread(path) if not path.endswith('.webp') else cv2.cvtColor(np.array(Image.open(path).convert('RGB')), cv2.COLOR_RGB2BGR)
    x0, y0, x1, y1 = region
    im = im[y0:y1, x0:x1]
    hsv = cv2.cvtColor(im, cv2.COLOR_BGR2HSV)
    Vv = hsv[..., 2]
    m = (Vv > thr).astype(np.uint8)
    m = cv2.morphologyEx(m, cv2.MORPH_OPEN, np.ones((3, 3), np.uint8))
    n, lab, st, ce = cv2.connectedComponentsWithStats(m, connectivity=4)
    dt = cv2.distanceTransform(m, cv2.DIST_L2, 3)
    vals_clear, vals_col, sats, clip_clear = [], [], [], []
    for i in range(1, n):
        if st[i, cv2.CC_STAT_AREA] < min_area:
            continue
        comp = (lab == i) & (dt >= 1.5)
        if comp.sum() < 5:
            comp = lab == i
        px = im[comp]
        med = np.median(px, axis=0)
        hm = cv2.cvtColor(np.uint8([[med]]), cv2.COLOR_BGR2HSV)[0, 0]
        s = hm[1] / 255.0; v = hm[2] / 255.0
        if s < 0.25 and v > 0.78:
            vals_clear.append(v); clip_clear.append(float((px.max(axis=1) >= 250).mean()))
        else:
            vals_col.append(v); sats.append(s)
    vc = np.array(vals_clear); vk = np.array(vals_col)
    def lin(v):
        return np.where(v <= 0.04045, v / 12.92, ((v + 0.055) / 1.055) ** 2.4)
    r = dict(n_clear=len(vc), n_coloured=len(vk), clear_V_p50=float(np.median(vc)) if len(vc) else None,
             coloured_V_p10_p50_p90=[float(np.percentile(vk, q)) for q in (10, 50, 90)] if len(vk) else None,
             coloured_S_p50=float(np.median(sats)) if sats else None,
             clear_hard_clipped_frac=float(np.mean(np.array(clip_clear) > 0.5)) if clip_clear else None,
             ratio_srgb_clear_over_coloured_p50=float(np.median(vc) / np.median(vk)) if len(vc) and len(vk) else None,
             ratio_linear_clear_over_coloured_p50=float(lin(np.median(vc)) / lin(np.median(vk))) if len(vc) and len(vk) else None,
             region=region, thr=thr)
    print(name, r)
    return r
res['clear_vs_coloured'] = dict(
    lf02=clear_vs_colour(src, (0, 0, W, H), name='lf02'),
    gh03=clear_vs_colour(gh03, (200, 0, 1536, 1300), name='gh03'),
    bc0=clear_vs_colour(bc0, (0, 0, 1600, 900), name='bc0'),
    b0=clear_vs_colour(b0, (0, 0, 4199, 2400), min_area=40, name='b0'),
)

# ---------- gridded crops of b0 for facet polygon picking ----------
b0im = np.array(Image.open(b0).convert('RGB'))
for name, (x0, y0, x1, y1) in dict(A=(2100, 200, 3500, 1200), B=(600, 100, 2100, 1100), C=(2800, 900, 4199, 1800)).items():
    c = b0im[y0:y1, x0:x1].copy()
    for gx in range(0, c.shape[1], 100):
        cv2.line(c, (gx, 0), (gx, c.shape[0]), (0, 255, 0), 1)
        cv2.putText(c, str(x0 + gx), (gx + 2, 14), cv2.FONT_HERSHEY_SIMPLEX, 0.4, (0, 255, 0), 1)
    for gy in range(0, c.shape[0], 100):
        cv2.line(c, (0, gy), (c.shape[1], gy), (0, 255, 0), 1)
        cv2.putText(c, str(y0 + gy), (2, gy + 12), cv2.FONT_HERSHEY_SIMPLEX, 0.4, (0, 255, 0), 1)
    cv2.imwrite(os.path.join(out, f'b0_grid_{name}.jpg'), cv2.cvtColor(c, cv2.COLOR_RGB2BGR), [cv2.IMWRITE_JPEG_QUALITY, 88])

json.dump(res, open(os.path.join(out, 'extra.json'), 'w'), indent=1)
