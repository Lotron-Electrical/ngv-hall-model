#!/usr/bin/env bash
# 2026-09-09: chain every balcony clip's pans onto its site-solved anchors. Two hops only: the hold-out
# test in tools/pan_poses.py measures 0.2 deg of rotation error within two hops and 4 deg by five, so two
# is where the evidence stops, not a round number.
cd "C:/Users/Lloyd Gibbs/Claude Projects/ngv-hall-model"
for c in b5 b1 b3 b7s b6g; do
  echo "########## $c"
  python -u tools/pan_poses.py "$c" --max-hops 2
done
