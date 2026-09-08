# Identify the four tapestries on the wall orthophotos by NCC against the candidate images at their true size.
import cv2, numpy as np
A = 'E:/sitecapture-captures/ngv-site/agent-ref-walls/'
S = cv2.imread(A + 'ortho/south/all/ortho.png'); N = cv2.imread(A + 'ortho/north/all/ortho.png')
def box(im, u0, u1, h0, h1):
    x0, x1 = int(u0 / 0.004), int(u1 / 0.004); y0, y1 = int((13 - h1) / 0.004), int((13 - h0) / 0.004); return im[y0:y1, x0:x1]
crops = {'south-A': (S, 6.5, 15.0, 2.4, 9.4), 'south-B': (S, 36.0, 44.5, 2.4, 9.4), 'north-A': (N, 6.5, 15.5, 2.4, 9.4), 'north-B': (N, 35.5, 44.5, 2.4, 9.4)}
names = ['abstract-sequence', 'evolving-forms', 'organic-form', 'piano-movement']
cands = {n: cv2.imread('tools/tapestry-%s.jpg' % n) for n in names}
sizes = {'abstract-sequence': (5.87, 4.993), 'evolving-forms': (5.356, 5.01), 'organic-form': (5.46, 4.968), 'piano-movement': (5.482, 4.967)}
MM = 0.016
for k, (im, u0, u1, h0, h1) in crops.items():
    c = box(im, u0, u1, h0, h1); cs = cv2.resize(c, None, fx=0.25, fy=0.25)
    g = cv2.GaussianBlur(cv2.cvtColor(cs, cv2.COLOR_BGR2GRAY).astype(np.float32), (0, 0), 2)
    out = []
    for n, ci in cands.items():
        w, h = sizes[n]
        best = (-1, None)
        for scale in (0.92, 1.0, 1.08):
            t = cv2.resize(ci, (int(w * scale / MM), int(h * scale / MM)))
            tg = cv2.GaussianBlur(cv2.cvtColor(t, cv2.COLOR_BGR2GRAY).astype(np.float32), (0, 0), 2)
            for flip in (False, True):
                tt = tg[:, ::-1] if flip else tg
                if tt.shape[0] >= g.shape[0] or tt.shape[1] >= g.shape[1]: continue
                r = cv2.matchTemplate(g, tt, cv2.TM_CCOEFF_NORMED); _, mx, _, loc = cv2.minMaxLoc(r)
                if mx > best[0]: best = (mx, (loc, flip, tt.shape, scale))
        out.append((round(float(best[0]), 3), n, best[1]))
    out.sort(reverse=True)
    b = out[0]; loc, flip, shape, scale = b[2]; u = u0 + loc[0] * MM; hy = h1 - (loc[1] + shape[0]) * MM
    print(k, [(o[0], o[1]) for o in out], ' best box u %.2f-%.2f h %.2f-%.2f flip=%s scale=%.2f' % (u, u + shape[1] * MM, hy, hy + shape[0] * MM, flip, scale))
    cv2.imwrite(A + 'shots/tap-%s-wide.jpg' % k, cs, [cv2.IMWRITE_JPEG_QUALITY, 85])
