"""Track B diagnostics 2: quality-threshold montage and PNG-vs-v29 registration check.

  python tools/trackB_diag2.py montage     -> scratch/trackB/diag/quality-montage.jpg (cells by nsharp bin)
  python tools/trackB_diag2.py register    -> per-cell phase-correlation shift between the two bakes
"""
import json
import os
import sys

import cv2
import numpy as np
from PIL import Image

Image.MAX_IMAGE_PIXELS = None
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import ceiling_ortho as co

OUT = co.OUT_DEFAULT
SCR = os.path.join(co.SCRATCH_DEFAULT, 'diag')


def load(tag=''):
    img = np.asarray(Image.open(os.path.join(OUT, 'bottom-ortho%s.png' % tag)).convert('RGB'))
    q = np.load(os.path.join(OUT, 'quality%s.npy' % tag))   # nsharp, lapvar, std, mean, cov, dark, class
    m = json.load(open(os.path.join(OUT, 'bottom-meta%s.json' % tag)))
    return img, q, m


def montage(tag=''):
    img, q, m = load(tag)
    nsharp, std, dark, cls = q[0], q[2], q[5], q[6]
    cell = int(round(co.CELL_M / (m['mm_per_px'] / 1000)))
    bins = [(0, 0.5), (0.5, 1.0), (1.0, 1.5), (1.5, 2.5), (2.5, 4.0), (4.0, 99)]
    rng = np.random.default_rng(3)
    rows = []
    for lo, hi in bins:
        ys, xs = np.where((nsharp >= lo) & (nsharp < hi) & (cls > 0) & (std >= 22) & (dark > 0.08) & (dark < 0.92))
        pick = rng.choice(len(ys), size=min(6, len(ys)), replace=False) if len(ys) else []
        tiles = []
        for k in pick:
            cy, cx = ys[k], xs[k]
            y0 = max(0, (cy * cell) - cell // 2); x0 = max(0, (cx * cell) - cell // 2)
            t = img[y0:y0 + 2 * cell, x0:x0 + 2 * cell]
            t = cv2.resize(t, (400, 400), interpolation=cv2.INTER_CUBIC).copy()
            cv2.rectangle(t, (100, 100), (300, 300), (255, 255, 0), 1)
            cv2.putText(t, 'ns %.2f std %.0f dk %.2f' % (nsharp[cy, cx], std[cy, cx], dark[cy, cx]), (6, 18),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 255), 2)
            tiles.append(t)
        while len(tiles) < 6:
            tiles.append(np.zeros((400, 400, 3), np.uint8))
        row = np.concatenate(tiles, axis=1)
        cv2.putText(row, 'nsharp %.1f..%.1f' % (lo, hi), (6, 390), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 255), 2)
        rows.append(row)
    mon = np.concatenate(rows, axis=0)
    mon = cv2.resize(mon, (2000, int(mon.shape[0] * 2000 / mon.shape[1])), interpolation=cv2.INTER_AREA)
    Image.fromarray(mon).save(os.path.join(SCR, 'quality-montage%s.jpg' % tag), quality=90)
    # also a histogram of nsharp over the glass-like cells
    v = nsharp[(cls > 0) & (std >= 22) & (dark > 0.08) & (dark < 0.92)]
    print('glass-like cells %d; nsharp percentiles 10/25/50/75/90: %s' % (v.size, np.percentile(v, [10, 25, 50, 75, 90]).round(2)))


def register():
    a, qa, m = load('')
    b, qb, _ = load('-v29')
    ga = cv2.cvtColor(a, cv2.COLOR_RGB2GRAY).astype(np.float32)
    gb = cv2.cvtColor(b, cv2.COLOR_RGB2GRAY).astype(np.float32)
    cell = int(round(co.CELL_M / (m['mm_per_px'] / 1000)))
    ca, cb = qa[6], qb[6]
    both = (ca == 2) & (cb == 2)
    ys, xs = np.where(both)
    shifts = []
    win = np.hanning(2 * cell)[:, None] * np.hanning(2 * cell)[None, :]
    for cy, cx in zip(ys, xs):
        y0 = cy * cell - cell // 2; x0 = cx * cell - cell // 2
        if y0 < 0 or x0 < 0 or y0 + 2 * cell > ga.shape[0] or x0 + 2 * cell > ga.shape[1]:
            continue
        ta = ga[y0:y0 + 2 * cell, x0:x0 + 2 * cell]; tb = gb[y0:y0 + 2 * cell, x0:x0 + 2 * cell]
        (dx, dy), resp = cv2.phaseCorrelate(ta * win, tb * win)
        shifts.append((dx, dy, resp, cy, cx))
    s = np.array(shifts)
    d = np.hypot(s[:, 0], s[:, 1]) * m['mm_per_px']
    print('cells traceable in both: %d' % len(s))
    print('shift mm percentiles 50/75/90/95: %s' % np.percentile(d, [50, 75, 90, 95]).round(1))
    print('share within 10 mm: %.2f, within 20 mm: %.2f, response median %.2f' % ((d <= 10).mean(), (d <= 20).mean(), np.median(s[:, 2])))
    hi = s[s[:, 2] > 0.3]
    dh = np.hypot(hi[:, 0], hi[:, 1]) * m['mm_per_px']
    print('confident (resp>0.3) cells %d: shift mm percentiles 50/90: %s' % (len(hi), np.percentile(dh, [50, 90]).round(1) if len(hi) else None))
    print('traceable cells: png %d, v29 %d, either %d, both %d' % ((ca == 2).sum(), (cb == 2).sum(), ((ca == 2) | (cb == 2)).sum(), both.sum()))


if __name__ == '__main__':
    os.makedirs(SCR, exist_ok=True)
    cmd = sys.argv[1] if len(sys.argv) > 1 else 'montage'
    if cmd == 'montage':
        montage(sys.argv[2] if len(sys.argv) > 2 else '')
    elif cmd == 'register':
        register()


def montage_classes(tag='', seed=5, per=7):
    """Random cells of every quality class with their features, to check the thresholds by eye."""
    img, q, m = load(tag)
    L = {k: q[n] for n, k in enumerate(co.Q_LAYERS)}
    cls = L['class']
    cell = int(round(co.CELL_M / (m['mm_per_px'] / 1000)))
    rng = np.random.default_rng(seed)
    rows = []
    for k in (1, 2, 3, 4):
        ys, xs = np.where(cls == k)
        pick = rng.choice(len(ys), size=min(per, len(ys)), replace=False) if len(ys) else []
        tiles = []
        for p in pick:
            cy, cx = ys[p], xs[p]
            y0 = max(0, (cy * cell) - cell // 2); x0 = max(0, (cx * cell) - cell // 2)
            t = img[y0:y0 + 2 * cell, x0:x0 + 2 * cell]
            t = cv2.resize(t, (360, 360), interpolation=cv2.INTER_CUBIC).copy()
            cv2.rectangle(t, (90, 90), (270, 270), (255, 255, 0), 1)
            cv2.putText(t, 'ns %.2f st %.2f bk %.2f' % (L['nsharp'][cy, cx], L['step'][cy, cx], L['black'][cy, cx]), (4, 16),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.45, (255, 255, 255), 2)
            cv2.putText(t, 'pc %.2f bg %.0f sd %.0f' % (L['piece'][cy, cx], L['bg'][cy, cx], L['std'][cy, cx]), (4, 34),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.45, (255, 255, 255), 2)
            tiles.append(t)
        while len(tiles) < per:
            tiles.append(np.zeros((360, 360, 3), np.uint8))
        row = np.concatenate(tiles, axis=1)
        cv2.putText(row, co.CLASS_NAMES[k], (6, 350), cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 255, 255), 2)
        rows.append(row)
    mon = np.concatenate(rows, axis=0)
    mon = cv2.resize(mon, (2000, int(mon.shape[0] * 2000 / mon.shape[1])), interpolation=cv2.INTER_AREA)
    Image.fromarray(mon).save(os.path.join(SCR, 'class-montage%s-%d.jpg' % (tag, seed)), quality=90)


if __name__ == '__main__' and len(sys.argv) > 1 and sys.argv[1] == 'classes':
    montage_classes(sys.argv[2] if len(sys.argv) > 2 else '', int(sys.argv[3]) if len(sys.argv) > 3 else 5)
