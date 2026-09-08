# The tapestries' rectangles read off the wall orthos (4 mm grid, hall frame): the saturated
# block's edges by column and row sums of saturation.   python tools/tapestry_ortho.py
import cv2, numpy as np
R = 'E:/sitecapture-captures/ngv-site/agent-ref-walls/ortho/%s/all/ortho.png'
for wall, boxes in (('north', [(8.20, 14.05), (37.84, 43.31)]), ('south', [(8.52, 13.97), (38.18, 43.52)])):
    im = cv2.imread(R % wall)
    if im is None: print(wall, 'no ortho'); continue
    mm = 4.0; H, W = im.shape[:2]
    S = cv2.cvtColor(im, cv2.COLOR_BGR2HSV)[:, :, 1].astype(float)
    for u0, u1 in boxes:
        x0, x1 = int((u0 - 1.5) * 1000 / mm), int((u1 + 1.5) * 1000 / mm)
        y0, y1 = int((13.0 - 9.5) * 1000 / mm), int((13.0 - 2.5) * 1000 / mm)
        sub = S[y0:y1, x0:x1]; sat = sub > 60
        col = sat.mean(axis=0); row = sat.mean(axis=1)
        def edges(prof, off, scale, flip=False):
            thr = max(0.15, prof.max() * 0.45); idx = np.where(prof > thr)[0]
            if len(idx) == 0: return None
            runs = np.split(idx, np.where(np.diff(idx) > 25)[0] + 1); r = max(runs, key=len)
            a, b = (r[0] + off) * scale, (r[-1] + 1 + off) * scale
            return (13.0 - b, 13.0 - a) if flip else (a, b)
        cu = edges(col, x0, mm / 1000); ch = edges(row, y0, mm / 1000, flip=True)
        print('%s tapestry near u %.1f-%.1f: ortho u %s h %s (col peak %.2f, row peak %.2f)' % (wall, u0, u1,
              '%.2f..%.2f' % cu if cu else '-', '%.2f..%.2f' % ch if ch else '-', col.max(), row.max()))
