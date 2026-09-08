# 2026-09-09: logs the urgent door / Free roam / sign fixes and the gallery measurement tool in AGENTS.md and the PLAN.
import io
PLAN = 'E:/sitecapture-captures/ngv-site/agent-ref-walls/PLAN-20260908-walls.md'
AG = 'AGENTS.md'
entry = """- 2026-09-09 night, urgent (Lloyd, from the phone): the two lit vestibules (north GANDEL HALL doorway u 23.10-29.40,
  south door u 37.962-39.662) read as white cut-outs in the wall. In the real world they are doors, closed for our
  purposes: both are `closed:true` now, one canvas each, a leaf a metre (north 6, south 2), stiles, rails, two
  recessed panels a leaf, a push plate by the meeting stile, tinted by the clock (night 0x4a423b, day 0x7c6c5e,
  tones UNMEASURED: every walk saw these doors open and lit). The GANDEL HALL sign over the north door is gone
  ("that should never have been there"). Free roam showed nothing: ROAM_EYE sat on u 48.3, behind the east end
  face (48.056) built the same day; it starts on u 47.0. Live as 1d54b9e and 583b547; proofs closed-doors2.jpg,
  roam-local.jpg. tools/roam-errors.mjs presses Enter then Free roam on the LIVE page and prints every exception.
- 2026-09-09 night: tools/gallery_measure.py (written by Codex from tools/codex-brief-gallery.md, run here):
  triangulates SIFT matches between posed frame pairs of a class, keeps the points behind the north wall face
  (d < -0.29) and reports the outer wall depth, the floor, the canopy slope (RANSAC h = a + b d) and the vitrine
  front, with d/h and u/d scatter images. Smoke test on b1: 1 gallery point from 102 pairs (b1 never looks
  into the gallery), as expected. Waits on the b6s register (queue: b3 matching now, then b4 b5 b7s b6s).
"""
s = open(PLAN, encoding='utf-8').read()
if 'the two lit vestibules (north GANDEL HALL doorway' not in s:
    open(PLAN, 'a', encoding='utf-8', newline='\n').write(entry)
a = open(AG, encoding='utf-8').read()
old = "u 24.5-27.1, h 2.65-3.0, letters 0.35 tall; built as `WALLF.sign`, a canvas 20 mm proud (2026-09-08)."
new = old + "\n  REMOVED 2026-09-09 (Lloyd: \"that should never have been there\"); and the lit vestibule is a CLOSED panelled\n  door now, as is the south lit door u 37.962-39.662 (`closed:true`, tools/patch_doors2.py): Lloyd, the same night,\n  \"in the real world those are just doors, closed for our purposes\"."
if 'REMOVED 2026-09-09 (Lloyd: "that should never have been there")' not in a:
    assert a.count(old) == 1
    open(AG, 'w', encoding='utf-8', newline='\n').write(a.replace(old, new))
print('logged')
