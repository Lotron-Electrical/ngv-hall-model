#!/usr/bin/env bash
# 2026-09-09: the gallery parapet top read at three draws at BOTH ends with one instrument, so the follow
# gain is fitted rather than assumed. Reasoning in tools/parapet_fit.py. The p classes are the pan-chained
# ones, which are the only frames in the archive that see this edge from beside it.
cd "C:/Users/Lloyd Gibbs/Claude Projects/ngv-hall-model"
D=E:/sitecapture-captures/ngv-site/agent-ref-walls/leveljson
for e in west east; do
  for c in walk night day4k b1 b3 b6g b7s b1p b3p b5p b7sp b6gp; do
    for td in "a 8.92" "b 9.06" "c 9.20"; do
      set -- $td
      LEVEL_JSON="$D/fit-$1-$c-$e.json" LEVELS_SET="top parapet top=$2" \
        python -u tools/end_levels.py "$c" "$e" 40 >/dev/null 2>&1
    done
  done
  echo "$e read"
done
END=west python -u tools/parapet_fit.py
echo ""
END=east python -u tools/parapet_fit.py
