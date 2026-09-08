#!/usr/bin/env bash
# 2026-09-09: the same opening/wall brightness test as tools/opening_bright.py, but on the SIM rendered
# from each frame's own camera, so the two numbers are comparable. The show rig is hidden: it stands in
# the hall in the sim and not in the walk capture, and it would otherwise black out the openings behind it.
export HIDE=rig-envelope,rig-truss,rig-tower,rig-light
for pair in "w1_000044 6" "w1_000043 6" "w1_000274 2" "w1_000034 6" "w1_000275 2" "w1_000384 3" "w1_000448 5" "w1_000009 7"; do
  set -- $pair
  echo "== $1 opening $2"
  bash tools/openmatch.sh walk "$1" "$2" 13 60 2>&1 | grep -E "opening/wall|^sim |^real " || echo "  (render failed)"
done
