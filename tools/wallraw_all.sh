#!/usr/bin/env bash
cd "C:/Users/Lloyd Gibbs/Claude Projects/ngv-hall-model"
D=E:/sitecapture-captures/ngv-site/agent-ref-walls/wallraw
for c in walk night day4k b1 b3 b7s; do
  WALL_RAW="$D/$c.csv" python -u tools/wall_edges.py "$c" 25 >/dev/null 2>&1
  echo "$c done"
done
