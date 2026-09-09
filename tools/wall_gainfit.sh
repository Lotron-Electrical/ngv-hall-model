#!/usr/bin/env bash
# 2026-09-09: every north jamb read against three tables slid along the wall, so the follow gain is fitted
# rather than assumed. Reasoning in tools/wall_gainfit.py.
cd "C:/Users/Lloyd Gibbs/Claude Projects/ngv-hall-model"
D=E:/sitecapture-captures/ngv-site/agent-ref-walls/walljson
for c in walk night day4k b1 b3 b7s b1p b5p; do
  for td in "m -0.10" "z 0.0" "p 0.10"; do
    set -- $td
    WALL_JSON="$D/gain-$1-$c.json" OPEN_SHIFT="$2" python -u tools/wall_edges.py "$c" 40 >/dev/null 2>&1
  done
  echo "$c read"
done
python -u tools/wall_gainfit.py
