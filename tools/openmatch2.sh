#!/usr/bin/env bash
# 2026-09-09: the opening/wall brightness test, real against sim, done properly.
#  - the sim is rendered from each walk frame's own camera, with the 2026 show install's rig and
#    tapestries hidden: they stand in the hall in the sim and not in the walk capture, and they would
#    otherwise black out the openings and cover the stone control band behind them;
#  - the real side is measured through the photograph's camera (tools/opening_stats.py),
#  - the sim side through the SIM's camera (tools/sim_openings.py), which is exact.
S=E:/sitecapture-captures/ngv-site/agent-ref-walls/shots/openmatch
export HIDE=rig-chord,rig-braces,rig-profiles,rig-pars,rig-envelope,tapestry-north-1,tapestry-north-2,tapestry-south-1,tapestry-south-2
python -c "import os; os.makedirs('$S', exist_ok=True)"
for pair in "w1_000044 6" "w1_000043 6" "w1_000274 2" "w1_000034 6" "w1_000275 2" "w1_000384 3" "w1_000448 5" "w1_000009 7" "w1_000379 4" "w2_000243 7" "w1_000437 5" "w1_000394 3"; do
  set -- $pair
  FR=$1; OI=$2
  POSE=$(python tools/opening_stats.py pose walk "$FR")
  CDP_PORT=${CDP_PORT:-9334} python tools/with_server.py node tools/pose-shot.mjs "$S/$FR-sim.jpg" $POSE 13 60 >/dev/null 2>&1
  echo "== $FR opening $OI"
  python tools/opening_stats.py cmp walk "$FR" "$OI" "$S/$FR-sim.jpg" | grep -E "^real |^wallR|opening/wall"
  python tools/sim_openings.py "$S/$FR-sim.jpg" $POSE "$OI" | grep -E "^open |^wall |ratio"
done
