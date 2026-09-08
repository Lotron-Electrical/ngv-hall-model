#!/usr/bin/env bash
cd "C:/Users/Lloyd Gibbs/Claude Projects/ngv-hall-model"
J=E:/sitecapture-captures/ngv-site/agent-ref-walls/southjson
R=E:/sitecapture-captures/ngv-site/agent-ref-walls/southraw
for c in walk night day4k b3 b7s; do
  echo "======== $c"
  SOUTH_JSON="$J/$c.json" SOUTH_RAW="$R/$c.csv" python -u tools/south_edges.py "$c" 25
done
