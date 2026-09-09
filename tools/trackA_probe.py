"""Track A resume probe: COLMAP model health for the 62 4K stills, camera spread, cloud extent along
the lattice, and the site chain-of-record (handset + one-bay shift) vs the lattice-fit chains.

python trackA_probe.py
"""
import sys, os, json
import numpy as np
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import trackA_geom as G
from colmap_bin import read_model

MAPPED = "E:/sitecapture-captures/ngv-video/void4k-register/mapped"
SCR = "C:/Users/LLOYDG~1/AppData/Local/Temp/claude/C--Users-Lloyd-Gibbs/046860d0-c13c-4e5d-847c-7ad01cef102a/scratchpad/trackA/"

cams, imgs, pts = read_model(MAPPED, with_points2d=True)
print("cameras:")
for c in cams.values():
    print("  ", c.id, c.model, c.width, c.height, np.array2string(c.params, precision=5, max_line_width=200))
id2xyz = dict(zip(pts["id"].tolist(), pts["xyz"]))
print("points3D", len(pts["id"]), "mean err", pts["err"].mean(), "track_len mean", pts["track_len"].mean())
stills = sorted([im for im in imgs.values() if im.name.startswith("void4k")], key=lambda im: im.name)
walk = [im for im in imgs.values() if not im.name.startswith("void4k")]
print("stills", len(stills), "walk", len(walk), "walk cams", sorted(set(im.camera_id for im in walk)), "still cams", sorted(set(im.camera_id for im in stills)))
# reprojection error per still
rows = []
for im in stills:
    c = cams[im.camera_id]
    cam = G.Cam(c.model, c.width, c.height, c.params, im.R(), im.t)
    ok = im.p3d_ids >= 0
    ids = im.p3d_ids[ok]
    X = np.array([id2xyz[i] for i in ids]) if len(ids) else np.zeros((0, 3))
    if len(X):
        u, v, z = cam.project(X)
        d = np.hypot(u - im.xys[ok, 0], v - im.xys[ok, 1])
        rows.append((os.path.basename(im.name)[:-4], int(ok.sum()), float(np.median(d)), float(np.percentile(d, 90)), int(len(im.xys))))
    else:
        rows.append((os.path.basename(im.name)[:-4], 0, None, None, int(len(im.xys))))
print("per-still: name, n3D, reproj px p50, p90, n2D")
for r in rows:
    print("  ", r)
C = np.array([im.center() for im in stills])
print("still centres void frame: mean", C.mean(0).round(3), "std", C.std(0).round(3), "min", C.min(0).round(3), "max", C.max(0).round(3))
WC = np.array([im.center() for im in walk])
print("walk centres void frame: min", WC.min(0).round(2), "max", WC.max(0).round(2))
# chains
s1 = G.load_sim(SCR + "void-to-hall-trackA-s1f0.json")
d = G.void_to_hall_chain("d")
c = G.void_to_hall_chain("c")
for nm, sim in (("s1f0", s1), ("chain d (handset+shift)", d), ("chain c (handset)", c)):
    s, R, t = sim
    P = G.apply_sim(sim, C)
    hu, hv = G.xz_to_huv(P[:, 0], P[:, 2])
    bi, bj = G.bay_index(hu, hv)
    print(f"{nm}: scale {s:.5f}  spot mean hall {P.mean(0).round(3)}  huv mean ({hu.mean():.3f},{hv.mean():.3f}) hu range {hu.min():.2f}..{hu.max():.2f} hv {hv.min():.2f}..{hv.max():.2f}  bays i {sorted(set(bi.tolist()))} j {sorted(set(bj.tolist()))}")
# rotation difference s1f0 vs d
Rd = d[1] @ s1[1].T
ang = np.degrees(np.arccos(np.clip((np.trace(Rd) - 1) / 2, -1, 1)))
print("rotation angle between s1f0 and chain d: %.3f deg; scale ratio %.5f" % (ang, d[0] / s1[0]))
Pd = G.apply_sim(d, C.mean(0)[None]); Ps = G.apply_sim(s1, C.mean(0)[None])
print("spot offset chain d - s1f0 (hall xyz):", (Pd - Ps).round(3), "in huv:", np.round(np.array(G.xz_to_huv((Pd - Ps)[0, 0], (Pd - Ps)[0, 2])), 3))
# view directions of the stills in s1f0 hall frame
print("stills view dirs (s1f0): name, cam huv, height above surface, look elevation deg (neg = down), look azimuth in huv deg (0=+hu, 90=+hv)")
for im, r in zip(stills, rows):
    cam = G.Cam(cams[im.camera_id].model, cams[im.camera_id].width, cams[im.camera_id].height, cams[im.camera_id].params, im.R(), im.t).to_frame(s1)
    z = cam.R.T @ np.array([0, 0, 1.0])
    cc = cam.center
    hu, hv = G.xz_to_huv(cc[0], cc[2])
    zu, zv = G.xz_to_huv(z[0], z[2])
    el = np.degrees(np.arcsin(z[1]))
    az = np.degrees(np.arctan2(zv, zu))
    h = cc[1] - G.surface_y(np.array([hu]), np.array([hv]), 0)[0]
    print(f"  {r[0]} huv ({hu:7.2f},{hv:6.2f}) h {h:5.2f} el {el:6.1f} az {az:7.1f}  n3D {r[1]:5d} reproj p50 {r[2]}")
# cloud extent along hu in lattice-locked s1f0 coords using the fit residual image
z = np.load(SCR + "void_dense_heightmap.npz")
H, N, x0, z0, cell = z["H10"], z["N"], float(z["x0"]), float(z["z0"]), float(z["cell"])
fit = json.load(open(SCR + "lattice_fit.json"))
iz, ix = np.nonzero(N >= 3)
x = x0 + (ix + 0.5) * cell
zz = z0 + (iz + 0.5) * cell
h = H[iz, ix]
th, s, tu, tv = fit["theta_rad"], fit["s"], fit["tu"], fit["tv"]
a, b, cc0 = fit["plane_abc"]
hu = s * (np.cos(th) * x - np.sin(th) * zz) + tu + G.PU  # s1f0 labelling (shift 1)
hv = s * (np.sin(th) * x + np.cos(th) * zz) + tv
m = a * x + b * zz + cc0 + G.relief(hu, hv)
good = np.abs(m - h) < 0.06
print("good cells", good.sum(), "of", len(h))
bins = np.arange(-70, -2, 0.5)
for jlab, (lo, hi) in (("j=0 (south, hv 0.16..7.54)", (0.16, 7.54)), ("j=1 (north, hv 7.54..14.93)", (7.54, 14.93))):
    sel = good & (hv >= lo) & (hv < hi)
    cnt, _ = np.histogram(hu[sel], bins)
    print(jlab, "good cells per 0.5 m of hu (s1f0 labels); plate west end -56.64, east -4.64, crest lines every 7.4285 from -56.64:")
    line = ""
    for c_, e in zip(cnt, bins[:-1]):
        if c_ > 0:
            line += f"{e:.1f}:{c_} "
    print("  " + line)
# deck extent along hu: cells with Hmax - H10 > 0.3 and near the mid crest
Hmax = z["Hmax"][iz, ix]
deck = (np.abs(hv - 7.544) < 0.5) & (Hmax - (a * x + b * zz + cc0 + G.relief(hu, hv)) > 0.35)
cnt, _ = np.histogram(hu[deck], bins)
print("deck-like cells (|hv-7.544|<0.5, Hmax 0.35 m above surface) per 0.5 m of hu:")
print("  " + " ".join(f"{e:.1f}:{c_}" for c_, e in zip(cnt, bins[:-1]) if c_ > 0))
