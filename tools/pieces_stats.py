# 2026-09-09: the traced canopy panes, counted and sized, so the ceiling can be pixel mapped.
# Reads tools/pieces.bin the way index.html does and reports what a per-pane backlight would cost.
import sys, struct, numpy as np
p = sys.argv[1] if len(sys.argv) > 1 else 'tools/pieces.bin'
b = open(p, 'rb').read()
assert b[:4] == b'NGVP'
n, u0, v0 = struct.unpack_from('<Iff', b, 4)
unit = struct.unpack_from('<H', b, 16)[0]
o = 18
us, vs, ar, cs, ks = [], [], [], [], []
for i in range(n):
    r, g, bb, k = b[o], b[o+1], b[o+2], b[o+3]; o += 4
    pts = []
    for j in range(k):
        a, c = struct.unpack_from('<2H', b, o); o += 4
        pts.append((u0 + a/unit, v0 + c/unit))
    if k < 3: continue
    A = cu = cv = 0.0
    for j in range(k):
        x1, y1 = pts[j]; x2, y2 = pts[(j+1) % k]
        w = x1*y2 - x2*y1; A += w; cu += (x1+x2)*w; cv += (y1+y2)*w
    if abs(A) < 2e-6: continue
    A *= 0.5; cu /= 6*A; cv /= 6*A
    us.append(cu); vs.append(cv); ar.append(abs(A)); cs.append((r, g, bb)); ks.append(k)
us = np.array(us); vs = np.array(vs); ar = np.array(ar); cs = np.array(cs)
eq = 2*np.sqrt(ar/np.pi)*1000
mx = cs.max(1)*1.0; mn = cs.min(1)*1.0
ch = (mx-mn)/np.maximum(mx, 1)
side = 1
while side*side < len(us): side *= 2
print('file holds', n, 'panes;', len(us), 'usable')
print('board u', round(us.min(), 2), 'to', round(us.max(), 2), ' v', round(vs.min(), 2), 'to', round(vs.max(), 2))
print('area m2  median', round(float(np.median(ar)), 4), ' total', round(float(ar.sum()), 1))
print('width mm median', int(np.median(eq)), ' p5', int(np.percentile(eq, 5)), ' p95', int(np.percentile(eq, 95)))
print('vertices median', int(np.median(ks)), ' max', max(ks))
print('chroma median', round(float(np.median(ch)), 2), ' clear share', round(100*float((ch < 0.06).mean()), 1), '%')
print('pixel map texture', side, 'x', side)
print('RGBW channels', 4*len(us), ' universes', round(4*len(us)/512.0, 1))
