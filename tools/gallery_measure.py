import argparse, json, math, os, re, sys
import cv2
import numpy as np
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import underside_geom as U
O = np.array([-54.907447, -1.43545, 3.040286], float)
HU = np.array([0.975681, 0, 0.219196], float)
HD = np.array([0.219196, 0, -0.975681], float)
OUT0 = "E:/sitecapture-captures/ngv-site/agent-ref-walls/shots/pose"
def idx(name):
    m = re.search(r"_(\d+)$", name)
    return int(m.group(1)) if m else 0
def kdist(cam):
    p = np.asarray(cam.params, float)
    fx, fy, cx, cy = p[:4]
    rest = list(p[4:]) + [0, 0, 0, 0]
    return np.array([[fx, 0, cx], [0, fy, cy], [0, 0, 1]], float), np.asarray(rest[:4], float)
def project(R, C, K, dist, X):
    Xc = X @ R.T - (R @ C)
    z = Xc[:, 2]
    with np.errstate(divide="ignore", invalid="ignore"):
        x, y = Xc[:, 0] / z, Xc[:, 1] / z
    k1, k2, p1, p2 = dist
    r2 = x * x + y * y
    rad = 1 + k1 * r2 + k2 * r2 * r2
    xd = x * rad + 2 * p1 * x * y + p2 * (r2 + 2 * x * x)
    yd = y * rad + p1 * (r2 + 2 * y * y) + 2 * p2 * x * y
    return K[0, 0] * xd + K[0, 2], K[1, 1] * yd + K[1, 2], z
def hall(P):
    q = P - O
    return np.stack([q @ HU, q @ HD, q[:, 1]], 1)
def load_frames(cname, chain, wanted):
    cams = U.load_class(cname)
    out = {}
    for name, (cam, path) in cams.items():
        out[name] = dict(frame=name, R=np.asarray(cam.R, float), C=cam.center, cam=cam, path=path)
    if chain:
        recs = json.load(open(chain))
        cname0 = recs[0].get("cname", cname)
        cams0 = U.load_class(cname0)
        base = cams0[recs[0]["frame"]][0] if recs[0]["frame"] in cams0 else next(iter(cams0.values()))[0]
        spec = U.CLASSES[cname0]
        imgroot = spec.get("frames", spec["img"])
        for r in recs:
            f = r["frame"]
            out[f] = dict(frame=f, R=np.asarray(r["R"], float), C=np.asarray(r["C"], float),
                          cam=base, path=os.path.join(imgroot, f + ".png"))
    if wanted:
        keep = set(wanted.split(","))
        out = {k: v for k, v in out.items() if k in keep}
    return [out[k] for k in sorted(out, key=idx)]
def features(rec, sift):
    im = cv2.imread(rec["path"], cv2.IMREAD_GRAYSCALE)
    if im is None:
        return None, None
    small = cv2.resize(im, None, fx=0.5, fy=0.5, interpolation=cv2.INTER_AREA)
    kp, des = sift.detectAndCompute(small, None)
    if des is None:
        return np.empty((0, 2), np.float32), None
    return np.float32([k.pt for k in kp]) * 2.0, des
def cross_matches(d1, d2):
    if d1 is None or d2 is None:
        return []
    bf = cv2.BFMatcher()
    def good(a, b):
        ms = bf.knnMatch(a, b, k=2)
        return {m.queryIdx: m.trainIdx for m, n in ms if m.distance < 0.75 * n.distance}
    ab, ba = good(d1, d2), good(d2, d1)
    return [(i, j) for i, j in ab.items() if ba.get(j) == i]
def triangulate(a, b, pairs):
    pts1, pts2 = a["pts"], b["pts"]
    K, dist = kdist(a["cam"])
    ma = np.float32([pts1[i] for i, _ in pairs])
    mb = np.float32([pts2[j] for _, j in pairs])
    ua = cv2.undistortPoints(ma.reshape(-1, 1, 2), K, dist, P=K).reshape(-1, 2)
    ub = cv2.undistortPoints(mb.reshape(-1, 1, 2), K, dist, P=K).reshape(-1, 2)
    Pa = K @ np.hstack([a["R"], -(a["R"] @ a["C"]).reshape(3, 1)])
    Pb = K @ np.hstack([b["R"], -(b["R"] @ b["C"]).reshape(3, 1)])
    Xh = cv2.triangulatePoints(Pa, Pb, ua.T, ub.T).T
    X = Xh[:, :3] / Xh[:, 3:4]
    xa, ya, za = project(a["R"], a["C"], K, dist, X)
    xb, yb, zb = project(b["R"], b["C"], K, dist, X)
    err = np.hypot(xa - ma[:, 0], ya - ma[:, 1]) < 3
    err &= np.hypot(xb - mb[:, 0], yb - mb[:, 1]) < 3
    va = X - a["C"]; vb = X - b["C"]
    va /= np.linalg.norm(va, axis=1, keepdims=True); vb /= np.linalg.norm(vb, axis=1, keepdims=True)
    ang = np.degrees(np.arccos(np.clip(np.sum(va * vb, 1), -1, 1)))
    return X[(za > 0) & (zb > 0) & err & (ang > 1.5)]
def densest(vals, step):
    vals = np.asarray(vals)
    if len(vals) == 0:
        return None
    bins = np.floor(vals / step).astype(int)
    keys, cnt = np.unique(bins, return_counts=True)
    k = keys[np.argmax(cnt)]
    return ((k + 0.5) * step, int(cnt.max()))
def outer_wall(D, H):
    vals = D[(H > 8.5) & (H < 11)]
    if len(vals) == 0:
        return None, None
    bins = np.floor(vals / 0.05).astype(int)
    keys, cnt = np.unique(bins, return_counts=True)
    dense = keys[np.argmax(cnt)]
    strong = keys[cnt >= max(1, math.ceil(0.03 * len(vals)))]
    deep = strong.min() if len(strong) else dense
    return ((deep + 0.5) * 0.05, int(cnt[keys == deep][0]), len(vals)), ((dense + 0.5) * 0.05, int(cnt.max()), len(vals))
def canopy(D, H):
    x, y = D[H > 10], H[H > 10]
    if len(x) < 2:
        return None
    best = None
    rng = np.random.default_rng(1234)
    for _ in range(500):
        i, j = rng.choice(len(x), 2, replace=False)
        if abs(x[i] - x[j]) < 1e-6:
            continue
        b = (y[i] - y[j]) / (x[i] - x[j]); a = y[i] - b * x[i]
        inl = np.abs(y - (a + b * x)) < 0.08
        if best is None or inl.sum() > best[2].sum():
            best = (a, b, inl)
    if best is None:
        return None
    a, b, inl = best
    A = np.stack([np.ones(inl.sum()), x[inl]], 1)
    a, b = np.linalg.lstsq(A, y[inl], rcond=None)[0]
    return float(a), float(b), int(inl.sum())
def draw_dh(path, UDH, fit, ow, vit):
    W, H = 620, 740
    img = np.full((H, W, 3), 255, np.uint8)
    def xy(d, h): return int((d + 6) * 100 + 10), int((14 - h) * 100 + 20)
    for d, h in UDH[:, 1:3]:
        x, y = xy(d, h)
        if 0 <= x < W and 0 <= y < H: img[y, x] = (0, 0, 0)
    for d, col, lab in [(-0.09, (0, 0, 255), "hall"), (ow, (255, 0, 0), "outer"), (vit, (0, 160, 0), "vitrine")]:
        if d is None: continue
        x, _ = xy(d, 7); cv2.line(img, (x, 20), (x, 720), col, 1); cv2.putText(img, lab, (x + 3, 35), 0, 0.45, col, 1)
    if fit:
        a, b, _ = fit
        pts = [xy(d, a + b * d) for d in np.linspace(-6, 0, 80)]
        cv2.polylines(img, [np.asarray(pts, np.int32)], False, (0, 0, 200), 1)
    cv2.imwrite(path, img)
def draw_ud(path, UDH):
    W, H = 2100, 260
    img = np.full((H, W, 3), 255, np.uint8)
    for u, d, _ in UDH:
        x, y = int(u * 40 + 10), int((-d) * 40 + 10)
        if 0 <= x < W and 0 <= y < H: img[y, x] = (0, 0, 0)
    cv2.imwrite(path, img)
def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("cname"); ap.add_argument("--chain"); ap.add_argument("--frames")
    ap.add_argument("--u-range", nargs=2, type=float); ap.add_argument("--out", default=OUT0)
    args = ap.parse_args(); os.makedirs(args.out, exist_ok=True)
    frames = load_frames(args.cname, args.chain, args.frames)
    sift = cv2.SIFT_create(4000); pts = []; pair_count = 0
    # Pair nearby posed frames, match image features, triangulate, then keep only gallery-side points.
    for f in frames:
        f["pts"], f["des"] = features(f, sift)
    for i, a in enumerate(frames):
        for b in frames[i + 1:]:
            if idx(b["frame"]) - idx(a["frame"]) > 6: break
            base = np.linalg.norm(a["C"] - b["C"])
            if not (0.10 <= base <= 2.0): continue
            m = cross_matches(a["des"], b["des"])
            if len(m) < 8: continue
            X = triangulate(a, b, m)
            if len(X): pts.append(X)
            pair_count += 1
    UDH = hall(np.vstack(pts)) if pts else np.empty((0, 3))
    keep = UDH[:, 1] < -0.29 if len(UDH) else np.zeros(0, bool)
    if args.u_range and len(UDH):
        keep &= (UDH[:, 0] >= args.u_range[0]) & (UDH[:, 0] <= args.u_range[1])
    UDH = UDH[keep]; Uv, D, Hh = UDH[:, 0], UDH[:, 1], UDH[:, 2]
    # Measure wall depth, floor height, canopy slope, and vitrine-front depth from the filtered cloud.
    deep, dense = outer_wall(D, Hh); floor = densest(Hh[Hh < 9.0], 0.05); fit = canopy(D, Hh)
    ow = deep[0] if deep else None
    vmask = (Hh > 8.5) & (Hh < 10.5)
    if ow is not None: vmask &= (D >= ow) & (D <= ow + 1.5)
    vit = densest(D[vmask], 0.1); vh = Hh[vmask & (np.abs(D - vit[0]) < 0.05)] if vit else []
    js = dict(class_name=args.cname, gallery_points=int(len(UDH)), frame_pairs_used=pair_count,
              outer_wall_deep=deep, outer_wall_dense=dense, floor=floor, canopy=fit, vitrine=vit)
    json.dump(js, open(os.path.join(args.out, f"gallery-{args.cname}.json"), "w"), indent=1)
    draw_dh(os.path.join(args.out, f"gallery-{args.cname}-dh.png"), UDH, fit, ow, vit[0] if vit else None)
    draw_ud(os.path.join(args.out, f"gallery-{args.cname}-ud.png"), UDH)
    print(f"{len(UDH)} gallery points from {pair_count} frame pairs used")
    if len(UDH) < 200: print(f"fewer than 200 gallery points found: {len(UDH)} points")
    if deep: print(f"outer wall deepest strong d {deep[0]:.2f} m from {deep[1]} of {deep[2]} points; densest d {dense[0]:.2f} m from {dense[1]} of {dense[2]} points")
    else: print("outer wall depth: no points in 8.5<h<11 m")
    if floor: print(f"floor h {floor[0]:.2f} m from {floor[1]} points")
    else: print("floor: no points with h<9.0 m")
    if fit:
        hout = fit[0] + fit[1] * ow if ow is not None else float("nan")
        print(f"canopy h = {fit[0]:.3f} m + {fit[1]:.3f}*d from {fit[2]} inliers; h at hall face d=-0.09 m is {fit[0]+fit[1]*-0.09:.2f} m; h at outer wall is {hout:.2f} m")
    else: print("canopy: not enough points above h>10.0 m")
    if vit and len(vh): print(f"vitrine front d {vit[0]:.2f} m from {vit[1]} points; h span {np.min(vh):.2f}-{np.max(vh):.2f} m from {len(vh)} points")
    else: print("vitrines: no points in the outer-wall band")
    print("wrote " + os.path.join(args.out, f"gallery-{args.cname}.json"))
if __name__ == "__main__":
    main()
