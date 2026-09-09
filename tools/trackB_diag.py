"""Track B diagnostics: lattice overlay crops of bottom-ortho.png and joint-line phase profiles.

Usage: python tools/trackB_diag.py [--ortho PATH] [--tag ''] [--out DIR]
Writes to the scratch folder: bay-overlay-<i>,<j>.jpg (one bay at ~1500 px with the lattice joints
drawn), profile-u.png / profile-v.png (darkness projected onto hu / hv with the lattice comb) and
prints the measured joint-line phase offsets.
"""
import argparse
import json
import os
import sys

import cv2
import numpy as np
from PIL import Image

Image.MAX_IMAGE_PIXELS = None
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import ceiling_ortho as co

SCR = co.SCRATCH_DEFAULT


def load(ortho, meta):
    img = np.asarray(Image.open(ortho).convert('RGB'))
    m = json.load(open(meta))
    return img, m


def bay_overlay(img, m, i, j, out, size=1500, margin=0.5):
    mpp = m['mm_per_px'] / 1000.0
    u0, v0, u1, v1 = co.bay_rect(i, j)
    x0 = int((u0 - margin - m['hu0']) / mpp); x1 = int((u1 + margin - m['hu0']) / mpp)
    y0 = int((v0 - margin - m['hv0']) / mpp); y1 = int((v1 + margin - m['hv0']) / mpp)
    x0c, y0c = max(0, x0), max(0, y0)
    crop = img[y0c:min(img.shape[0], y1), x0c:min(img.shape[1], x1)].copy()
    segs = co.joint_lines(i, j)
    ov = crop.copy()
    for (a, b, w) in segs:
        p0 = (int(round((a[0] - m['hu0']) / mpp)) - x0c, int(round((a[1] - m['hv0']) / mpp)) - y0c)
        p1 = (int(round((b[0] - m['hu0']) / mpp)) - x0c, int(round((b[1] - m['hv0']) / mpp)) - y0c)
        cv2.line(ov, p0, p1, (0, 255, 255), 2)
    # 0.5 m ticks along the top edge
    for k in range(0, 20):
        x = int(round((u0 + 0.5 * k - m['hu0']) / mpp)) - x0c
        if 0 <= x < ov.shape[1]:
            cv2.line(ov, (x, 0), (x, 12 if k % 2 else 24), (255, 255, 0), 2)
    s = size / max(ov.shape[:2])
    ov = cv2.resize(ov, (int(ov.shape[1] * s), int(ov.shape[0] * s)), interpolation=cv2.INTER_AREA)
    cv2.putText(ov, 'bay %d,%d  hu %.2f..%.2f hv %.2f..%.2f  (%.1f mm/px shown)' % (i, j, u0, u1, v0, v1, mpp * 1000 / s),
                (10, ov.shape[0] - 12), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 255), 2)
    Image.fromarray(ov).save(out, quality=90)


def crop_1to1(img, m, hu, hv, w_m, out, scale=1):
    mpp = m['mm_per_px'] / 1000.0
    x0 = int((hu - m['hu0']) / mpp); y0 = int((hv - m['hv0']) / mpp)
    n = int(w_m / mpp)
    c = img[y0:y0 + n, x0:x0 + n]
    if scale != 1:
        c = cv2.resize(c, (c.shape[1] * scale, c.shape[0] * scale), interpolation=cv2.INTER_CUBIC)
    c = c.copy()
    # 100 mm scale bar
    bar = int(0.1 / mpp * scale)
    cv2.rectangle(c, (10, c.shape[0] - 20), (10 + bar, c.shape[0] - 12), (255, 255, 255), -1)
    cv2.putText(c, '100 mm  hu %.2f hv %.2f' % (hu, hv), (10, c.shape[0] - 26), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 255), 1)
    Image.fromarray(c).save(out, quality=92)


def wide_dark(img, mpp, mpp_work=0.025, width_m=0.09):
    """Darkness (local mean - grey) surviving a min-filter of width_m: only joints / big dark areas."""
    gs, D = co.darkness_image(img, mpp, mpp_work)
    k = int(round(width_m / mpp_work)) | 1
    # a joint is dark across its whole width: erode the darkness with a k x k box
    E = cv2.erode(D, np.ones((k, k), np.uint8))
    return gs, D, E


def profiles(img, m, out_prefix):
    mpp = m['mm_per_px'] / 1000.0
    mw = 0.025
    gs, D, E = wide_dark(img, mpp, mw)
    hu0, hv0 = m['hu0'], m['hv0']
    res = {}
    # --- hu profile per bay row j (mean of E over the bay's hv range), folded by PU across the 7 bays
    for j in range(co.NB_V):
        _, v0, _, v1 = co.bay_rect(0, j)
        r0, r1 = int((v0 + 0.4 - hv0) / mw), int((v1 - 0.4 - hv0) / mw)
        prof = E[r0:r1].mean(axis=0)
        hu = hu0 + (np.arange(prof.size) + 0.5) * mw
        phase = ((hu - co.PLATE[0]) % co.PU)
        bins = np.linspace(0, co.PU, 298)
        idx = np.clip(np.digitize(phase, bins) - 1, 0, 296)
        fold = np.bincount(idx, prof, 297) / np.maximum(1, np.bincount(idx, None, 297))
        res['fold_u_j%d' % j] = fold.tolist()
        # per bay i: correlate with a comb (ridge at 0 and PU, cross at PU/2)
        for i in range(co.NB_U):
            u0, _, u1, _ = co.bay_rect(i, j)
            c0, c1 = int((u0 - 1.0 - hu0) / mw), int((u1 + 1.0 - hu0) / mw)
            c0c = max(0, c0); c1c = min(prof.size, c1)
            seg = np.zeros(c1 - c0, np.float32); seg[c0c - c0:c1c - c0] = prof[c0c:c1c]
            tpl = np.zeros_like(seg)
            for uu, w in ((u0, co.RIDGE_W), (u1, co.RIDGE_W), ((u0 + u1) / 2, co.JOINT_W)):
                a = int(round((uu - w / 2 - (u0 - 1.0)) / mw)); b = int(round((uu + w / 2 - (u0 - 1.0)) / mw))
                tpl[max(0, a):max(0, b)] = 1
            tpl = cv2.GaussianBlur(tpl[None, :], (0, 0), 1.5)[0]
            best, bo = -9, 0
            shifts = np.arange(-int(0.7 / mw), int(0.7 / mw) + 1)
            cc = []
            for s in shifts:
                t = np.roll(tpl, s)
                a_ = seg - seg.mean(); b_ = t - t.mean()
                v = float((a_ * b_).sum() / (np.sqrt((a_ ** 2).sum() * (b_ ** 2).sum()) + 1e-9))
                cc.append(v)
            cc = np.array(cc); k = int(cc.argmax())
            res['bay_u_%d_%d' % (i, j)] = dict(du=float(shifts[k] * mw), ncc=float(cc[k]))
    # --- hv profile per bay column i
    for i in range(co.NB_U):
        u0, _, u1, _ = co.bay_rect(i, 0)
        c0, c1 = int((u0 + 0.4 - hu0) / mw), int((u1 - 0.4 - hu0) / mw)
        prof = E[:, c0:c1].mean(axis=1)
        for j in range(co.NB_V):
            _, v0, _, v1 = co.bay_rect(i, j)
            r0, r1 = int((v0 - 1.0 - hv0) / mw), int((v1 + 1.0 - hv0) / mw)
            r0c = max(0, r0); r1c = min(prof.size, r1)
            seg = np.zeros(r1 - r0, np.float32); seg[r0c - r0:r1c - r0] = prof[r0c:r1c]
            tpl = np.zeros_like(seg)
            for vv, w in ((v0, co.RIDGE_W), (v1, co.RIDGE_W), ((v0 + v1) / 2, co.JOINT_W)):
                a = int(round((vv - w / 2 - (v0 - 1.0)) / mw)); b = int(round((vv + w / 2 - (v0 - 1.0)) / mw))
                tpl[max(0, a):max(0, b)] = 1
            tpl = cv2.GaussianBlur(tpl[None, :], (0, 0), 1.5)[0]
            shifts = np.arange(-int(0.7 / mw), int(0.7 / mw) + 1)
            cc = []
            for s in shifts:
                t = np.roll(tpl, s)
                a_ = seg - seg.mean(); b_ = t - t.mean()
                cc.append(float((a_ * b_).sum() / (np.sqrt((a_ ** 2).sum() * (b_ ** 2).sum()) + 1e-9)))
            cc = np.array(cc); k = int(cc.argmax())
            res['bay_v_%d_%d' % (i, j)] = dict(dv=float(shifts[k] * mw), ncc=float(cc[k]))
    # plot the folded u profiles and the full v profile
    Hp = 200
    for j in range(co.NB_V):
        f = np.array(res['fold_u_j%d' % j]); f = f / (f.max() + 1e-9)
        pl = np.zeros((Hp, f.size * 3, 3), np.uint8)
        for x in range(f.size):
            cv2.line(pl, (x * 3, Hp - 1), (x * 3, Hp - 1 - int(f[x] * (Hp - 20))), (0, 200, 0), 3)
        for ph, col in ((0, (0, 255, 255)), (co.PU / 2, (255, 0, 255)), (co.PU, (0, 255, 255))):
            x = int(ph / co.PU * (f.size - 1)) * 3
            cv2.line(pl, (x, 0), (x, Hp), col, 1)
        cv2.putText(pl, 'fold u, bay row j=%d: yellow = ridge phase (lattice), magenta = cross' % j, (5, 15), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 255), 1)
        Image.fromarray(pl).save(out_prefix + 'fold-u-j%d.png' % j)
    # E image with the lattice drawn, downsampled to 2000 wide
    Ei = np.clip(E / (np.percentile(E, 99.5) + 1e-6) * 255, 0, 255).astype(np.uint8)
    Ei = cv2.cvtColor(Ei, cv2.COLOR_GRAY2RGB)
    for i in range(co.NB_U):
        for j in range(co.NB_V):
            for (a, b, w) in co.joint_lines(i, j):
                p0 = (int(round((a[0] - hu0) / mw)), int(round((a[1] - hv0) / mw)))
                p1 = (int(round((b[0] - hu0) / mw)), int(round((b[1] - hv0) / mw)))
                cv2.line(Ei, p0, p1, (255, 0, 0), 1)
    Ei = cv2.resize(Ei, (2000, int(Ei.shape[0] * 2000 / Ei.shape[1])), interpolation=cv2.INTER_AREA)
    Image.fromarray(Ei).save(out_prefix + 'widedark-lattice.jpg', quality=88)
    return res


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--ortho', default=os.path.join(co.OUT_DEFAULT, 'bottom-ortho.png'))
    ap.add_argument('--meta', default=os.path.join(co.OUT_DEFAULT, 'bottom-meta.json'))
    ap.add_argument('--out', default=os.path.join(SCR, 'diag'))
    ap.add_argument('--bays', default='1,0 2,0 5,1 3,1')
    ap.add_argument('--crops', default='')
    args = ap.parse_args()
    os.makedirs(args.out, exist_ok=True)
    img, m = load(args.ortho, args.meta)
    for b in args.bays.split():
        i, j = map(int, b.split(','))
        bay_overlay(img, m, i, j, os.path.join(args.out, 'bay-overlay-%d,%d.jpg' % (i, j)))
    for c in args.crops.split():
        hu, hv, w = map(float, c.split(','))
        crop_1to1(img, m, hu, hv, w, os.path.join(args.out, 'crop-%.1f_%.1f.jpg' % (hu, hv)), scale=2)
    res = profiles(img, m, os.path.join(args.out, ''))
    for j in range(co.NB_V):
        for i in range(co.NB_U):
            a = res['bay_u_%d_%d' % (i, j)]; b = res['bay_v_%d_%d' % (i, j)]
            print('bay %d,%d: du %+.3f (ncc %.2f)  dv %+.3f (ncc %.2f)' % (i, j, a['du'], a['ncc'], b['dv'], b['ncc']))
    json.dump(res, open(os.path.join(args.out, 'profiles.json'), 'w'))


if __name__ == '__main__':
    main()
