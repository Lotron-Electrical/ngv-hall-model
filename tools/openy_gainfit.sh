#!/usr/bin/env bash
# 2026-09-09: the openings' sill and head read against three shifted draws, so the follow gain is fitted
# rather than assumed. Reasoning in tools/openy_gainfit.py. The shift is small because the search window is
# half a bluestone course; that is a property of the wall, not a choice.
cd "C:/Users/Lloyd Gibbs/Claude Projects/ngv-hall-model"
D=E:/sitecapture-captures/ngv-site/agent-ref-walls/openjson
for c in walk night day4k b1 b3 b7s b1p b5p; do
  for td in "m -0.06" "z 0.0" "p 0.06"; do
    set -- $td
    OPEN_JSON="$D/gain-$1-$c.json" OPENY_SHIFT="$2" python -u tools/open_levels.py "$c" 30 >/dev/null 2>&1
  done
  echo "$c read"
done
python -u tools/openy_gainfit.py
