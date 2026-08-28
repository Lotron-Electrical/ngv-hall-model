"""Write runs.json for the page from a sitecapture lighting-design JSON.

The page draws every strip live, so it needs only the run polylines (model frame, metres) and
each run's outward normal. Nothing else from the design file is carried: this is a visualisation.

    python tools/export_runs.py E:/sitecapture-captures/ngv-site/lighting-design-20260828-between-fins.json
"""
import json, re, sys
from pathlib import Path
src = Path(sys.argv[1]); d = json.loads(src.read_text())
runs = []
for r in d["runs"]:
    m = re.match(r"col-(\w+)-(\d+)$", r["id"]); col, gap = m.group(1), int(m.group(2))
    runs.append({"column": col, "gap": gap,
                 "points": [[round(v, 4) for v in p] for p in r["points_model"]],
                 "normal": [round(v, 4) for v in r["surface_normals"][0]]})
cols = sorted({r["column"] for r in runs}, key=lambda c: (c[0], int(c[1:])))
out = {"schema": "ngv-hall-site.runs/1", "source": src.name, "unit": "m", "frame": "model (same as model.glb)",
       "columns": cols, "gaps_per_column": 8, "runs": runs}
Path(__file__).resolve().parent.parent.joinpath("runs.json").write_text(json.dumps(out, separators=(",", ":")))
print(len(runs), "runs,", len(cols), "columns")
