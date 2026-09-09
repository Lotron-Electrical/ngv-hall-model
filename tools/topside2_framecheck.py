"""Do the two COLMAP models share the roof-void frame?

The stills are posed in void4k-register/mapped; w2/w4/w5 exist only in rebuild-roofvoid/build/model.
Pooling their cameras is only legitimate if one void->hall similarity serves both. The 532 w1 frames
are in BOTH models, so they are the correspondences: fit a similarity (Umeyama) rebuild -> mapped on
the shared camera centres and report the residual. A residual of a few mm or less means the models
are the same reconstruction and no extra transform is needed; anything larger has to be composed in.

python topside2_framecheck.py [--out json]
"""
import sys, os, json, argparse
import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from colmap_bin import read_model
from trackA_chain import umeyama

MAPPED = "E:/sitecapture-captures/ngv-video/void4k-register/mapped"
REBUILD = "E:/sitecapture-captures/ngv-site/rebuild-roofvoid/build/model"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default=None)
    a = ap.parse_args()
    _, ia, _ = read_model(MAPPED, with_points2d=False)
    _, ib, _ = read_model(REBUILD, with_points2d=False)
    # mapped names the w1 frames '000123.png'; the rebuild model names the same frame 'w1_000123.png'
    A = {im.name[:-4]: im.center() for im in ia.values() if not im.name.startswith("void4k")}
    B = {im.name[3:-4]: im.center() for im in ib.values() if im.name.startswith("w1_")}
    keys = sorted(set(A) & set(B))
    P = np.array([B[k] for k in keys])
    Q = np.array([A[k] for k in keys])
    raw = np.linalg.norm(P - Q, axis=1) * 1000
    s, R, t = umeyama(P, Q)
    res = np.linalg.norm(s * (P @ R.T) + t - Q, axis=1) * 1000
    rot = float(np.degrees(np.arccos(np.clip((np.trace(R) - 1) / 2, -1, 1))))
    out = {
        "shared_w1_frames": len(keys),
        "mapped_only": sorted(set(A) - set(B))[:10],
        "rebuild_only_traverses": sorted({im.name.split("_")[0] for im in ib.values()} - {"w1"}),
        "raw_centre_difference_mm": {"p50": float(np.percentile(raw, 50)), "p95": float(np.percentile(raw, 95)),
                                     "max": float(raw.max())},
        "umeyama_rebuild_to_mapped": {"scale": float(s), "rotation_deg": rot,
                                      "translation_mm": float(np.linalg.norm(t) * 1000)},
        "residual_mm": {"mean": float(res.mean()), "p50": float(np.percentile(res, 50)),
                        "p95": float(np.percentile(res, 95)), "max": float(res.max())},
        "traverse_extent_m": np.ptp(Q, axis=0).round(3).tolist(),
        "verdict": ("same reconstruction, one void->hall similarity serves both"
                    if raw.max() < 1.0 else "models differ, compose the fitted similarity"),
    }
    print(json.dumps(out, indent=1))
    if a.out:
        json.dump(out, open(a.out, "w"), indent=1)
        print("wrote", a.out)


if __name__ == "__main__":
    main()
