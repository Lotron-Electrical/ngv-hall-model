#!/usr/bin/env bash
# 2026-09-09: every jamb re-read with the FIXED-POINT finder and the constant window, across every capture
# that can see the north wall, including b7s (clip 154940) which stands on the south upper gallery and is
# the first capture to look at this wall from the far side of the hall and from above.
cd "C:/Users/Lloyd Gibbs/Claude Projects/ngv-hall-model"
D=E:/sitecapture-captures/ngv-site/agent-ref-walls/walljson
for c in walk night day4k b1 b3 b7s; do
  WALL_JSON="$D/$c.json" python -u tools/wall_edges.py "$c" 25 >/dev/null 2>&1
  echo "$c done"
done
