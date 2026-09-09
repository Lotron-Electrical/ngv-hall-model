"""Track A step 2a: top-surface heightmap of the roof void's dense cloud in the VOID frame.

Input : rebuild-roofvoid/topside-extended-20260821.ply (void register frame, y ~ up, metres)
Output: <scratch>/trackA/void_dense_heightmap.npz  {H10, H50, Hmax, N, x0, z0, cell}
        <scratch>/trackA/void_dense_heightmap.png   (H10 shaded)
H10/H50 = 10th/50th percentile of y per cell (the glass surface sits under the beams/deck, so the
low percentile is the plate top), Hmax = max (deck/beams), N = count.

python trackA_heightmap.py [cell_m=0.05]
"""
import sys, os
import numpy as np
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from trackA_ply import read_ply

PLY = "E:/sitecapture-captures/ngv-site/rebuild-roofvoid/topside-extended-20260821.ply"
SCR = "C:/Users/LLOYDG~1/AppData/Local/Temp/claude/C--Users-Lloyd-Gibbs/046860d0-c13c-4e5d-847c-7ad01cef102a/scratchpad/trackA/"


def main():
    cell = float(sys.argv[1]) if len(sys.argv) > 1 else 0.05
    mm, dt = read_ply(PLY)
    x = np.asarray(mm["x"], np.float64)
    y = np.asarray(mm["y"], np.float64)
    z = np.asarray(mm["z"], np.float64)
    print("points", len(x))
    print("x range", x.min(), x.max(), "y range", y.min(), y.max(), "z range", z.min(), z.max())
    # y histogram (coarse) to see the glass band and the deck
    hist, edges = np.histogram(y, bins=np.arange(-4, 2.01, 0.1))
    for h, e in zip(hist, edges[:-1]):
        if h > 20000:
            print(f"  y {e:6.2f}..{e+0.1:6.2f}  {h:9d}")
    # keep a generous band around the glass + deck; drop the roof structure high above
    keep = (y > -3.5) & (y < 0.5)
    x, y, z = x[keep], y[keep], z[keep]
    x0, z0 = np.floor(x.min()), np.floor(z.min())
    nx = int(np.ceil((x.max() - x0) / cell)) + 1
    nz = int(np.ceil((z.max() - z0) / cell)) + 1
    ix = ((x - x0) / cell).astype(np.int64)
    iz = ((z - z0) / cell).astype(np.int64)
    key = iz * nx + ix
    order = np.argsort(key, kind="stable")
    key, ys = key[order], y[order]
    uniq, start, cnt = np.unique(key, return_index=True, return_counts=True)
    H10 = np.full(nz * nx, np.nan)
    H50 = np.full(nz * nx, np.nan)
    Hmax = np.full(nz * nx, np.nan)
    N = np.zeros(nz * nx, np.int32)
    # percentile per group without a python loop per cell: sort y within groups
    # (groups are contiguous after the stable sort by key; sort y inside each group)
    ys_sorted = np.empty_like(ys)
    # lexsort by (y, key) gives groups contiguous and y ascending within them
    o2 = np.lexsort((ys, key))
    ys_sorted = ys[o2]
    idx10 = start + np.minimum(cnt - 1, (0.10 * cnt).astype(np.int64))
    idx50 = start + np.minimum(cnt - 1, (0.50 * cnt).astype(np.int64))
    idxmx = start + cnt - 1
    H10[uniq] = ys_sorted[idx10]
    H50[uniq] = ys_sorted[idx50]
    Hmax[uniq] = ys_sorted[idxmx]
    N[uniq] = cnt
    H10, H50, Hmax, N = (a.reshape(nz, nx) for a in (H10, H50, Hmax, N))
    np.savez_compressed(SCR + "void_dense_heightmap.npz", H10=H10, H50=H50, Hmax=Hmax, N=N, x0=x0, z0=z0, cell=cell)
    print("grid", nx, "x", nz, "cells; filled", int((N > 0).sum()))
    # png of H10
    from PIL import Image
    v = H10.copy()
    lo, hi = np.nanpercentile(v, 2), np.nanpercentile(v, 98)
    img = np.where(np.isnan(v), 0, np.clip((v - lo) / (hi - lo), 0, 1) * 255).astype(np.uint8)
    Image.fromarray(img).save(SCR + "void_dense_heightmap.png")
    print("H10 range shown", lo, hi, "->", SCR + "void_dense_heightmap.png")


if __name__ == "__main__":
    main()
