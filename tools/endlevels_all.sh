#!/usr/bin/env bash
# 2026-09-09: every end level re-read with the FIXED-POINT finder. The b7s numbers came from the new code
# and the rest of the leveljson was written by the old single-look finder, and pooling two instruments
# together is not a measurement. This rebuilds the whole set with one instrument.
cd "C:/Users/Lloyd Gibbs/Claude Projects/ngv-hall-model"
D=E:/sitecapture-captures/ngv-site/agent-ref-walls/leveljson
for c in walk night day4k b1 b3 b6g b7s; do
  for e in west east; do
    LEVEL_JSON="$D/$c-$e.json" python -u tools/end_levels.py "$c" "$e" 25 >/dev/null 2>&1
  done
  echo "$c done"
done
