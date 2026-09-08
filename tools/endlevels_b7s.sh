#!/usr/bin/env bash
# 2026-09-09: b7s (clip 154940) joins the pooled end-level test. It is the first capture that stands on the
# SOUTH upper gallery at BOTH ends, so it sees each end wall from a place nothing else in the archive does.
cd "C:/Users/Lloyd Gibbs/Claude Projects/ngv-hall-model"
D=E:/sitecapture-captures/ngv-site/agent-ref-walls/leveljson
for e in west east; do
  LEVEL_JSON="$D/b7s-$e.json" python -u tools/end_levels.py b7s "$e" 12 >/dev/null 2>&1
  echo "b7s $e done"
done
