#!/usr/bin/env bash
# 2026-09-09: the sill and head measured from every capture that can see the north wall, one lease.
cd "C:/Users/Lloyd Gibbs/Claude Projects/ngv-hall-model"
D=E:/sitecapture-captures/ngv-site/agent-ref-walls/openjson
for c in walk night day4k b1 b3; do
  echo "================ $c"
  OPEN_JSON="$D/$c.json" python -u tools/open_levels.py "$c" 30
done
