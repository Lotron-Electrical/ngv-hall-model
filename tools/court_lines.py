# Step 1 of the courtyard-photo solve: find the long straight lines in reference-photos/courtyard/
# lloyd-01 (the fins' vertical edges, the roof grid), estimate the vertical vanishing point and the
# wall-normal vanishing point, and draw them for checking.   python tools/court_lines.py
import cv2, numpy as np, json
P = 'E:/sitecapture-captures/ngv-site/reference-photos/courtyard/lloyd-01-federation-court-kusama-from-balcony.jpg'
OUT = 'E:/sitecapture-captures/ngv-site/agent-ref-walls/shots/'
im = cv2.imread(P); H, W = im.shape[:2]; g = cv2.cvtColor(im, cv2.COLOR_BGR2GRAY)
ed = cv2.Canny(cv2.GaussianBlur(g, (0, 0), 1.2), 40, 120)
segs = cv2.HoughLinesP(ed, 1, np.pi / 720, 60, minLineLength=70, maxLineGap=6)
segs = segs[:, 0, :] if segs is not None else np.zeros((0, 4))
def ang(s): return np.degrees(np.arctan2(s[3] - s[1], s[2] - s[0]))
vert = [s for s in segs if abs(abs(ang(s)) - 90) < 6 and s[1] < H * 0.62 and s[3] < H * 0.62]
roof = [s for s in segs if (s[1] < H * 0.13 and s[3] < H * 0.13) and 8 < abs(ang(s)) < 82]
def vp(lines):
    # least-squares point closest to all the lines (each line as a*x+b*y+c=0)
    A = []; b = []
    for s in lines:
        x1, y1, x2, y2 = map(float, s); a1, b1 = y2 - y1, x1 - x2; n = np.hypot(a1, b1); a1 /= n; b1 /= n
        A.append([a1, b1]); b.append(a1 * x1 + b1 * y1)
    A = np.array(A); b = np.array(b); sol, *_ = np.linalg.lstsq(A, b, rcond=None)
    res = np.abs(A @ sol - b); return sol, res
Vp, rv = vp(vert); Wp, rw = vp(roof)
# refine: drop the worst 30 % and refit
def refine(lines, sol):
    A = []; b = []
    for s in lines:
        x1, y1, x2, y2 = map(float, s); a1, b1 = y2 - y1, x1 - x2; n = np.hypot(a1, b1); a1 /= n; b1 /= n
        A.append([a1, b1]); b.append(a1 * x1 + b1 * y1)
    A = np.array(A); b = np.array(b); res = np.abs(A @ sol - b); keep = res <= np.percentile(res, 70)
    sol2, *_ = np.linalg.lstsq(A[keep], b[keep], rcond=None); return sol2, [l for l, k in zip(lines, keep) if k]
Vp, vert2 = refine(vert, Vp); Wp, roof2 = refine(roof, Wp)
print('vertical segs', len(vert), '-> V', Vp.round(1), ' roof segs', len(roof), '-> W', Wp.round(1))
c = np.array([W / 2, H / 2]); f2 = -np.dot(Vp - c, Wp - c); print('f^2 =', round(f2), ' f =', np.sqrt(f2).round(1) if f2 > 0 else 'NEGATIVE (VPs not orthogonal)', ' image', W, 'x', H)
vis = im.copy()
for s in vert2: cv2.line(vis, (s[0], s[1]), (s[2], s[3]), (0, 255, 255), 2)
for s in roof2: cv2.line(vis, (s[0], s[1]), (s[2], s[3]), (255, 0, 255), 2)
cv2.imwrite(OUT + 'court-lines.jpg', vis, [cv2.IMWRITE_JPEG_QUALITY, 85])
json.dump({'V': Vp.tolist(), 'W': Wp.tolist(), 'f2': float(f2), 'W_img': W, 'H_img': H, 'vert': [list(map(int, s)) for s in vert2], 'roof': [list(map(int, s)) for s in roof2]}, open(OUT + 'court-lines.json', 'w'), indent=1)
