"""Register one photograph of the canopy to the plate and render it onto the 4 mm ortho grid.

A photograph from the hall floor, a balcony or the internet has no pose. What it does have is the
steel: every funnel vertex, crest node and edge midpoint of the lattice is a point whose hall
position is known to the centimetre (tools/trackA_geom.py: the lattice phase, the vertex plane and
the relief). Mark six or more of those in the photo and the camera can be solved (one view, square
pixels, principal point at the frame centre, no distortion unless asked), after which every pixel of
the plate is projected into the photo through the same surface and the photo becomes an ortho tile
on the same grid as the topside and underside renders: 4 mm/px, hu0 -56.635125, hv0 0.15882, row 0
south, col 0 west. Nothing is drawn that the camera did not see: the mask is the projected footprint
inside the frame at under 75 degrees incidence, and the gsd map (metres per photo pixel on the glass)
says how much to trust each pixel when the tiles are fused.

    python tools/photo_register.py --photo lf02.jpg --points lf02.points.json --name lf02 [--side under]
        [--slab -0.04] [--out E:/.../agent-ref-ceiling/sources] [--k1] [--margin-m 0.5]

points json: {"note": "...", "points": [{"px": 636.5, "py": 493.75, "i": 0, "j": 0, "du": 0.5, "dv": -0.5}, ...]}
  (i, j) index a funnel vertex of the OLD lattice (trackA_geom HU0/HV0, PU/PV); (du, dv) are module
  fractions from it: (0,0) the vertex, (+-0.5, +-0.5) a crest node, (+-0.5, 0) / (0, +-0.5) an edge midpoint.
  Which lattice the photo is on is decided BEFORE this (tools/ceiling_locate.py); this tool only trusts
  the points it is given, and prints the reprojection residual so a wrong placement shows as pixels.
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
import trackA_geom as G

GRID = dict(hu0=-56.635125, hv0=0.15882, mm=4.0)
OUT_DEFAULT = 'E:/sitecapture-captures/ngv-site/agent-ref-ceiling/sources'
FLOOR_Y = -1.435          # the hall floor in the GLB frame (GAME-PLAN.md)


def lattice_xyz(pt, slab):
    hu = G.HU0 + (pt['i'] + pt['du']) * G.PU
    hv = G.HV0 + (pt['j'] + pt['dv']) * G.PV
    return G.surface_xyz(np.array([hu]), np.array([hv]), slab=slab)[0], (hu, hv)


def solve_camera(obj, img, w, h, k1=False, side='under'):
    """Solve the camera by a sweep over the focal length: at each f (square pixels, principal point at
    the frame centre) PnP gives the pose, and the f with the smallest reprojection wins, subject to the
    camera being on the side of the plate the photo was taken from. A one-view calibrateCamera on
    nine near-coplanar lattice points collapses to a degenerate telephoto camera (it did: f -26,000
    px, camera 195 m under the floor); the sweep cannot, because f is never a free unknown in the
    linear step."""
    best = None; curve = []
    obj32 = obj.astype(np.float32); img32 = img.astype(np.float32)
    for f in np.geomspace(0.35 * max(w, h), 5.0 * max(w, h), 120):
        K = np.array([[f, 0, w / 2], [0, f, h / 2], [0, 0, 1]], float)
        # a near-planar target under weak perspective has TWO poses that fit (the Necker pair, the
        # camera reflected through the plate); ask for every candidate and keep the ones on our side
        cands = []
        for flag in (cv2.SOLVEPNP_IPPE, cv2.SOLVEPNP_SQPNP, cv2.SOLVEPNP_EPNP):
            try:
                n, rvecs, tvecs, _ = cv2.solvePnPGeneric(obj32, img32, K, None, flags=flag)
            except cv2.error:
                continue
            cands += list(zip(rvecs, tvecs))
        for rvec, tvec in cands:
            try:
                rvec, tvec = cv2.solvePnPRefineLM(obj32, img32, K, None, rvec, tvec)
            except cv2.error:
                pass
            R, _ = cv2.Rodrigues(rvec); t = tvec.ravel()
            C = -R.T @ t
            plate_y = float(G.surface_y(*G.xz_to_huv(C[0], C[2]), slab=0.0))
            # the camera was in the hall (floor -1.44 m, a balcony or a lift at most a few metres up)
            # or in the roof void above the plate; a solution outside that band is the weak-perspective
            # runaway (f -> infinity, camera -> infinity) and is refused, whatever its residual
            if side == 'under' and not (FLOOR_Y - 0.5 < C[1] < plate_y - 1.5):
                continue
            if side == 'top' and not (plate_y + 0.3 < C[1] < plate_y + 6.0):
                continue
            u, v, z = project(K, np.zeros(1), R, t, obj)
            if (z <= 0).any():
                continue
            rms = float(np.sqrt(np.mean((u - img[:, 0]) ** 2 + (v - img[:, 1]) ** 2)))
            curve.append((float(f), rms, float(C[1])))
            if best is None or rms < best[0]:
                best = (rms, K, R, t)
    if best is None:
        raise SystemExit('no camera on the %s side fits these points' % side)
    rms, K, R, t = best
    curve.sort()
    print('  f sweep (f px, rms px, camera y):', ' '.join(f'{f:.0f}/{r:.1f}/{y:.1f}' for f, r, y in curve[::max(1, len(curve) // 12)]))
    dist = np.zeros(1)
    if k1:
        # one radial term, refined with the pose by calibrateCamera from the sweep's own start
        flags = (cv2.CALIB_USE_INTRINSIC_GUESS | cv2.CALIB_FIX_PRINCIPAL_POINT | cv2.CALIB_FIX_ASPECT_RATIO |
                 cv2.CALIB_ZERO_TANGENT_DIST | cv2.CALIB_FIX_K2 | cv2.CALIB_FIX_K3)
        rms2, K2, d2, rv, tv = cv2.calibrateCamera([obj32], [img32], (w, h), K.copy(), None, flags=flags)
        if rms2 < rms and K2[0, 0] > 0:
            R, _ = cv2.Rodrigues(rv[0]); t = tv[0].ravel(); K = K2; dist = d2.ravel()[:1]; rms = rms2
    return K, dist, R, t, rms


def project(K, dist, R, t, X):
    Xc = X @ R.T + t
    z = Xc[:, 2]
    with np.errstate(divide='ignore', invalid='ignore'):
        xn, yn = Xc[:, 0] / z, Xc[:, 1] / z
    k1 = dist[0] if len(dist) else 0.0
    r2 = xn * xn + yn * yn
    rad = 1 + k1 * r2
    u = K[0, 0] * xn * rad + K[0, 2]
    v = K[1, 1] * yn * rad + K[1, 2]
    return u, v, z


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('--photo', required=True)
    ap.add_argument('--points', required=True)
    ap.add_argument('--name', required=True)
    ap.add_argument('--side', default='under', choices=['under', 'top'])
    ap.add_argument('--slab', type=float, default=None, help='glass face height above the plate lattice surface (m); default -0.04 under, 0.02 top')
    ap.add_argument('--out', default=OUT_DEFAULT)
    ap.add_argument('--k1', action='store_true', help='solve one radial distortion term too (needs 10+ well spread points)')
    ap.add_argument('--margin-m', type=float, default=0.6, help='render this far beyond the marked points')
    ap.add_argument('--max-inc', type=float, default=75.0)
    args = ap.parse_args()
    slab = args.slab if args.slab is not None else (-0.04 if args.side == 'under' else 0.02)

    photo = np.array(Image.open(args.photo).convert('RGB'))
    h, w = photo.shape[:2]
    spec = json.load(open(args.points))
    pts = spec['points']
    obj = []; img = []; huv = []
    for p in pts:
        X, uv = lattice_xyz(p, slab)
        obj.append(X); img.append([p['px'], p['py']]); huv.append(uv)
    obj = np.array(obj); img = np.array(img); huv = np.array(huv)
    K, dist, R, t, rms = solve_camera(obj, img, w, h, args.k1, args.side)
    u, v, z = project(K, dist, R, t, obj)
    res = np.hypot(u - img[:, 0], v - img[:, 1])
    C = -R.T @ t
    print(f'{args.name}: f {K[0,0]:.1f} px (fov {2*np.degrees(np.arctan(w/2/K[0,0])):.1f} deg across), k1 {dist[0] if len(dist) else 0:.4f}')
    print(f'  camera at hall xyz {C.round(2)}; huv {np.round(G.xz_to_huv(C[0], C[2]), 2)}; height {C[1]:.2f} m')
    print(f'  reprojection: rms {rms:.2f} px, max {res.max():.2f} px over {len(pts)} points')
    for p, r in zip(pts, res):
        if r > 3 * max(rms, 1):
            print(f'  suspect point px ({p["px"]},{p["py"]}) residual {r:.1f} px')

    # the tile: the marked points' huv box plus a margin, on the 4 mm grid
    mm = GRID['mm']
    hu_lo, hu_hi = huv[:, 0].min() - args.margin_m, huv[:, 0].max() + args.margin_m
    hv_lo, hv_hi = huv[:, 1].min() - args.margin_m, huv[:, 1].max() + args.margin_m
    px0 = int(np.floor((hu_lo - GRID['hu0']) * 1000 / mm)); px1 = int(np.ceil((hu_hi - GRID['hu0']) * 1000 / mm))
    py0 = int(np.floor((hv_lo - GRID['hv0']) * 1000 / mm)); py1 = int(np.ceil((hv_hi - GRID['hv0']) * 1000 / mm))
    W, H = px1 - px0, py1 - py0
    hu = GRID['hu0'] + (np.arange(px0, px1) + 0.5) * mm / 1000
    hv = GRID['hv0'] + (np.arange(py0, py1) + 0.5) * mm / 1000
    HU, HV = np.meshgrid(hu, hv)
    X = G.surface_xyz(HU.ravel(), HV.ravel(), slab=slab)
    u, v, z = project(K, dist, R, t, X)
    # incidence against the facet normal: the surface gradient is cheap from the relief's own shape
    eps = 0.01
    yu = (G.surface_y(HU.ravel() + eps, HV.ravel(), slab) - G.surface_y(HU.ravel() - eps, HV.ravel(), slab)) / (2 * eps)
    yv = (G.surface_y(HU.ravel(), HV.ravel() + eps, slab) - G.surface_y(HU.ravel(), HV.ravel() - eps, slab)) / (2 * eps)
    # normal in hall xyz: huv axes -> xz
    nu = np.stack([G.CU * np.ones_like(yu), np.zeros_like(yu), G.SU * np.ones_like(yu)], -1)   # d/dhu direction
    nv = np.stack([-G.SU * np.ones_like(yv), np.zeros_like(yv), G.CU * np.ones_like(yv)], -1)
    tu = nu + np.stack([np.zeros_like(yu), yu, np.zeros_like(yu)], -1)
    tv = nv + np.stack([np.zeros_like(yv), yv, np.zeros_like(yv)], -1)
    n = np.cross(tu, tv); n /= np.linalg.norm(n, axis=1, keepdims=True)
    if args.side == 'under':
        n = -n * np.sign(n[:, 1:2]) ; n[:, 1] = -np.abs(n[:, 1])     # pointing down into the hall
    else:
        n = n * np.sign(n[:, 1:2])
    ray = X - C; ray /= np.linalg.norm(ray, axis=1, keepdims=True)
    cosi = np.clip((-ray * n).sum(1), 0, 1)
    ok = (z > 0) & (u >= 0) & (u < w - 1) & (v >= 0) & (v < h - 1) & (cosi > np.cos(np.radians(args.max_inc)))
    gsd = np.where(ok, z / K[0, 0] / np.maximum(cosi, 1e-3), np.inf).reshape(H, W)
    mx = u.reshape(H, W).astype(np.float32); my = v.reshape(H, W).astype(np.float32)
    tile = cv2.remap(photo, mx, my, cv2.INTER_LINEAR, borderMode=cv2.BORDER_CONSTANT, borderValue=0)
    mask = ok.reshape(H, W)
    tile[~mask] = 0
    od = os.path.join(args.out, args.name); os.makedirs(od, exist_ok=True)
    Image.fromarray(tile).save(os.path.join(od, 'tile.png'))
    Image.fromarray((mask * 255).astype(np.uint8)).save(os.path.join(od, 'mask.png'))
    np.save(os.path.join(od, 'gsd.npy'), gsd.astype(np.float32))
    meta = dict(name=args.name, photo=os.path.abspath(args.photo), side=args.side, slab=slab, grid=GRID,
                px0=px0, py0=py0, width=W, height=H, hu_lo=float(hu[0] - mm / 2000), hv_lo=float(hv[0] - mm / 2000),
                camera=dict(K=K.tolist(), dist=dist.tolist(), R=R.tolist(), t=t.tolist(), centre=C.tolist(), fov_deg=float(2 * np.degrees(np.arctan(w / 2 / K[0, 0])))),
                reprojection=dict(rms=float(rms), max=float(res.max()), n=len(pts), residuals=res.round(2).tolist()),
                coverage=float(mask.mean()), gsd_mm=dict(p10=float(np.percentile(gsd[mask], 10) * 1000) if mask.any() else None,
                                                        p50=float(np.percentile(gsd[mask], 50) * 1000) if mask.any() else None,
                                                        p90=float(np.percentile(gsd[mask], 90) * 1000) if mask.any() else None),
                points=pts, note=spec.get('note', ''))
    json.dump(meta, open(os.path.join(od, 'meta.json'), 'w'), indent=1)
    # a preview with the lattice drawn back onto the tile, so misregistration is visible
    prev = tile.copy()
    for p in pts:
        X1, (phu, phv) = lattice_xyz(p, slab)
        x = int((phu - GRID['hu0']) * 1000 / mm) - px0; y = int((phv - GRID['hv0']) * 1000 / mm) - px0 * 0 - py0
        cv2.circle(prev, (x, y), 12, (255, 0, 255), 2)
    s = min(1.0, 1600 / W)
    cv2.imwrite(os.path.join(od, 'preview.jpg'), cv2.resize(prev[..., ::-1], (int(W * s), int(H * s)), interpolation=cv2.INTER_AREA), [cv2.IMWRITE_JPEG_QUALITY, 85])
    print(f'  tile {W}x{H} at px0 {px0} py0 {py0}; coverage {mask.mean():.2f}; gsd p50 {meta["gsd_mm"]["p50"]} mm; wrote {od}')


if __name__ == '__main__':
    main()
