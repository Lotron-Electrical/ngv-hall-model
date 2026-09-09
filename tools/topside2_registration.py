"""Collect the registration evidence for the topside2 ortho into one file, and cut the crops that
let a reader check it by eye.

It reads what the individual measurements wrote (diamond fit before and after the candidate
correction, the three-way ridge check, the frame-space rib fit, the cloud hub check, the track B
cross-registration) and states the verdict each supports, including where a measurement is too noisy
to support anything. Nothing here re-measures; this is the assembly step.

Why "after" needs no re-render. The renderer samples the surface at corr(lattice huv) for each pixel,
so a feature physically at huv_f lands at the pixel corr^-1(huv_f): applying the correction to the
LATTICE LINE at measurement time and applying it to the SAMPLING at render time move the measured
residual by exactly the same amount. The re-rendered image would differ only in second order, where
the correction changes which frame wins a facet.

python topside2_registration.py <render dir> [--crops 4]
"""
import sys, os, json, argparse
import numpy as np
import cv2

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import trackA_geom as G
from trackA_assemble2 import lattice_overlay


def load(d, name):
    p = os.path.join(d, name)
    return json.load(open(p)) if os.path.exists(p) else None


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("dir")
    ap.add_argument("--crops", type=int, default=4)
    ap.add_argument("--crop-px", type=int, default=1200)
    a = ap.parse_args()
    d = a.dir
    args = json.load(open(os.path.join(d, "render-args.json")))
    mm, hu0, hv0 = args["mm"], args["hu0"], args["hv0"]
    before = load(d, "diamond-fit-before.json")
    after = load(d, "diamond-fit-after.json")
    ridge = load(d, "ridge-check.json")
    ribs = load(d, "rib-fit-before.json")
    memb = load(d, "member-fit-before.json")
    cross = load(d, "crossreg-trackB.json")
    joint = load(d, "joint-check.json")

    # ---- crops centred on the best covered lattice vertices, lattice drawn on top
    rgb = cv2.cvtColor(cv2.imread(os.path.join(d, "topside-ortho.png"), cv2.IMREAD_COLOR), cv2.COLOR_BGR2RGB)
    obs = cv2.imread(os.path.join(d, "topside-observed.png"), cv2.IMREAD_GRAYSCALE) > 127
    H, W = obs.shape
    S = a.crop_px
    cands = []
    for i in range(-2, 7):
        for j in (-1, 0):
            vu, vv = G.HU0 + i * G.PU, G.HV0 + j * G.PV
            x = int((vu - hu0) * 1000 / mm) - S // 2
            y = int((vv - hv0) * 1000 / mm) - S // 2
            if x < 0 or y < 0 or x + S > W or y + S > H:
                continue
            bi = int(np.floor((vu - (G.HU0 - G.PU / 2)) / G.PU)) + 1
            bj = int(np.floor((vv - (G.HV0 - G.PV / 2)) / G.PV)) + 1
            cands.append((float(obs[y:y + S, x:x + S].mean()), x, y, bi, bj, vu, vv))
    cands.sort(reverse=True)
    pv = os.path.join(d, "preview")
    os.makedirs(pv, exist_ok=True)
    crops = []
    for k, (f, x, y, bi, bj, vu, vv) in enumerate(cands[:a.crops]):
        crop = rgb[y:y + S, x:x + S].copy()
        ov = lattice_overlay(crop.copy(), x, y, mm, hu0, hv0, args["hu1"], args["hv1"], thick=2)
        nm = "registration-vertex-%d_%d" % (bi, bj)
        cv2.imwrite(os.path.join(pv, nm + ".jpg"), cv2.cvtColor(crop, cv2.COLOR_RGB2BGR),
                    [cv2.IMWRITE_JPEG_QUALITY, 93])
        cv2.imwrite(os.path.join(pv, nm + "-lattice.jpg"), cv2.cvtColor(ov, cv2.COLOR_RGB2BGR),
                    [cv2.IMWRITE_JPEG_QUALITY, 93])
        crops.append({"file": "preview/" + nm + "-lattice.jpg", "vertex_bay": [bi, bj],
                      "vertex_huv": [round(vu, 3), round(vv, 3)], "px": [x, y], "size_px": S,
                      "observed_frac": round(f, 3)})
        print("crop %-22s vertex bay %d,%d huv %8.2f,%6.2f  observed %.1f%%"
              % (nm, bi, bj, vu, vv, f * 100))

    verdict = {
        "question": "is the topside2 ortho registered to the lattice of trackA_geom, per bay?",
        "answer": "yes for the ridge line, to a median 14 mm and a worst bay 75 mm; the diamond "
                  "members scatter far more than that but not coherently, so no rigid correction is "
                  "supported and none was applied",
        "correction_applied": None,
        "why_no_correction": [
            "the candidate similarity fitted to the diamond offsets is tiny (scale 0.99934, "
            "0.26 deg, tu +42 mm, tv -30 mm) and removes almost none of the spread: the fit's own "
            "residual rms goes 268 -> 261 mm",
            "applying it would move the plate -30 mm in hv, which makes the ridge line WORSE: the "
            "ridge is the one feature three independent sources agree on (cloud, this ortho's deck "
            "gap, the track B bake), all within 0.21 m of the lattice and a median under 45 mm",
            "the frame-space rib fit, which would have covered the cut-out member classes, returns "
            "per-bay residuals larger than the shifts it reports, so it is not evidence either way",
        ],
    }
    out = {
        "render_dir": d, "lattice": {"PU": G.PU, "PV": G.PV, "HU0": G.HU0, "HV0": G.HV0,
                                     "source": "trackA_geom.py"},
        "verdict": verdict,
        "measurements": {
            "ridge_line_three_ways": ridge["summary"] if ridge else None,
            "diamond_members_before": before["summary"] if before else None,
            "diamond_members_after_candidate_correction": after["summary"] if after else None,
            "candidate_correction": before["similarity"] if before else None,
            "diamond_per_bay_before": before["per_bay"] if before else None,
            "diamond_per_bay_after": after["per_bay"] if after else None,
            "frame_space_rib_fit": {"summary": ribs["summary"], "per_bay": ribs["per_bay"],
                                    "usable": False,
                                    "why": "the per-bay residual rms (200-700 mm) exceeds the shifts "
                                           "it reports, so the texture-minimum detector is latching "
                                           "onto slabs and shadows, not members"} if ribs else None,
            "hub_nodes_bay_slide": memb["hub_summary"] if memb else None,
            "hub_nodes_detail": memb["hubs"] if memb else None,
            "trackB_cross_registration": {"whole_plate": cross["whole_plate"],
                                          "per_bay": cross["per_bay"],
                                          "reading": "no alignment at any shift within 0.7 m "
                                                     "(peak ncc 0.03-0.09). The ridge check shows "
                                                     "this is not a translation error: it is that "
                                                     "the blurred bake and the topside matrix share "
                                                     "no correlatable fine pattern"} if cross else None,
            "joint_lines_pipeline_check": joint["summary"] if joint else None,
        },
        "crops": crops,
    }
    p = os.path.join(d, "registration-check.json")
    json.dump(out, open(p, "w"), indent=1)
    print(json.dumps(out["measurements"]["ridge_line_three_ways"], indent=1))
    print("wrote", p)


if __name__ == "__main__":
    main()
