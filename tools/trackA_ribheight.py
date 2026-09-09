"""Track A (resume): rib / crest-beam / hub heights above the modelled plate surface, from the dense
void cloud heightmap (Hmax per 5 cm cell) carried through the final chain. Sets RIB_H for the occluder.

python trackA_ribheight.py --sim <chain.json>
"""
import sys, os, argparse
import numpy as np
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import trackA_geom as G
from trackA_ortho import line_dists, DECK_HV

SCR = "C:/Users/LLOYDG~1/AppData/Local/Temp/claude/C--Users-Lloyd-Gibbs/046860d0-c13c-4e5d-847c-7ad01cef102a/scratchpad/trackA/"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--sim", required=True)
    a = ap.parse_args()
    sim = G.load_sim(a.sim)
    z = np.load(SCR + "void_dense_heightmap.npz")
    Hmax, H10, N, x0, z0, cell = z["Hmax"], z["H10"], z["N"], float(z["x0"]), float(z["z0"]), float(z["cell"])
    iz, ix = np.nonzero(N >= 3)
    x = x0 + (ix + 0.5) * cell
    zz = z0 + (iz + 0.5) * cell
    Pm = G.apply_sim(sim, np.stack([x, Hmax[iz, ix], zz], 1))
    Pl = G.apply_sim(sim, np.stack([x, H10[iz, ix], zz], 1))
    hu, hv = G.xz_to_huv(Pm[:, 0], Pm[:, 2])
    ymod = G.surface_y(hu, hv, 0.0)
    hmax = Pm[:, 1] - ymod
    hlow = Pl[:, 1] - ymod
    cross, diag, crest, vert = line_dists(hu, hv)
    inplate = (hu > G.PLATE_HU[0]) & (hu < G.PLATE_HU[1] + G.PU) & (hv > G.PLATE_HV[0]) & (hv < G.PLATE_HV[1]) & (np.abs(hv - DECK_HV) > 0.8)
    bins = np.arange(-0.2, 1.01, 0.05)

    def report(name, m):
        h = hmax[m]
        cnt, _ = np.histogram(h, bins)
        print(f"{name}: cells {m.sum()}  Hmax-model p25/50/75/90 = {np.percentile(h,[25,50,75,90]).round(3)}  H10-model p50 {np.median(hlow[m]):.3f}")
        print("   hist 5 cm bins from -0.20:", cnt.tolist())
    report("rib lines (cross+diag, |d|<0.07, >0.5 m from hub, >0.4 from crest)", inplate & (np.minimum(cross, diag) < 0.07) & (vert > 0.5) & (crest > 0.4))
    report("crest lines (|d|<0.07, >0.5 m from the crest corners)", inplate & (crest < 0.07) & (np.minimum(cross, diag) > 0.3))
    report("hubs (vert < 0.25)", inplate & (vert < 0.25))
    report("open field (>0.35 m from every line)", inplate & (np.minimum(np.minimum(cross, diag), crest) > 0.35) & (vert > 0.5))
    # rib width: fraction of cells with Hmax-model > 0.15 as a function of distance from the rib line
    print("rib profile: distance bin (m) -> share of cells with Hmax-model > 0.15")
    d = np.minimum(cross, diag)
    for lo in np.arange(0, 0.5, 0.05):
        m = inplate & (d >= lo) & (d < lo + 0.05) & (vert > 0.6) & (crest > 0.4)
        if m.sum() > 50:
            print(f"   {lo:.2f}-{lo+0.05:.2f}: {np.mean(hmax[m] > 0.15):.2f}  (n {m.sum()})")
    print("crest profile: distance bin (m) -> share with Hmax-model > 0.15")
    for lo in np.arange(0, 0.6, 0.05):
        m = inplate & (crest >= lo) & (crest < lo + 0.05) & (np.minimum(cross, diag) > 0.4)
        if m.sum() > 50:
            print(f"   {lo:.2f}-{lo+0.05:.2f}: {np.mean(hmax[m] > 0.15):.2f}  (n {m.sum()})")


if __name__ == "__main__":
    main()
