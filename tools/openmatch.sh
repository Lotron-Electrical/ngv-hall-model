#!/usr/bin/env bash
# 2026-09-09: render the sim from a posed frame's own camera and compare the pixels inside one north
# opening against the real ones. Usage: bash tools/openmatch.sh <class> <frame> <opening> <hour> <house%>
set -e
CLS=$1; FR=$2; OI=$3; HR=$4; HS=$5
S=E:/sitecapture-captures/ngv-site/agent-ref-walls/shots/openmatch
python -c "import os; os.makedirs('$S', exist_ok=True)"
POSE=$(python tools/opening_stats.py pose "$CLS" "$FR")
echo "$FR pose: $POSE"
CDP_PORT=${CDP_PORT:-9334} python tools/with_server.py node tools/pose-shot.mjs "$S/$FR-sim.jpg" $POSE "$HR" "$HS" 2>&1 | grep -E "^shot|Error" || true
python tools/opening_stats.py cmp "$CLS" "$FR" "$OI" "$S/$FR-sim.jpg" "$S/$FR-o$OI-pair.jpg"
