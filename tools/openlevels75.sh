#!/usr/bin/env bash
cd "C:/Users/Lloyd Gibbs/Claude Projects/ngv-hall-model"
D=E:/sitecapture-captures/ngv-site/agent-ref-walls/openjson
export MAXANG=75
for c in walk night day4k b1 b3; do
  echo "================ $c"
  OPEN_JSON="$D/$c.json" python -u tools/open_levels.py "$c" 30
done
