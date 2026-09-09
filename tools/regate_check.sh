#!/usr/bin/env bash
# 2026-09-09: the honest test of the re-gate. Run the SAME level instrument on the strict set and the
# re-gated set of each clip. If the extra frames are good poses the answers agree and the sample grows;
# if they are junk the answers scatter. Nothing else changes between the two runs.
cd "C:/Users/Lloyd Gibbs/Claude Projects/ngv-hall-model"
D=E:/sitecapture-captures/ngv-site/agent-ref-walls/regatecheck
mkdir -p "$D"
for c in b1 b1r b3 b3r b6g b6gr b7s b7sr; do
  for e in west east; do
    LEVEL_JSON="$D/$c-$e.json" python -u tools/end_levels.py "$c" "$e" 60 >/dev/null 2>&1
  done
  echo "$c done"
done
