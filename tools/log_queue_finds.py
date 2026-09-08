# 2026-09-09: logs the register queue lesson (a script edited while bash runs it) and queue4.
PLAN = 'E:/sitecapture-captures/ngv-site/agent-ref-walls/PLAN-20260908-walls.md'
entry = """- 2026-09-09 late: the register queues went wrong twice and the lesson is worth a line. A queue's bash loop
  outlives TaskStop (the stop reaches the grep on its pipe; the loop and its colmap children run on), so
  "stopping" queue2 left its b6s run going, and editing queue3.sh while bash was reading it garbled the lines
  bash ran next (a lift line executed from mid-way, "Is a directory"; b4, b5 and b7s launched on top of each
  other and locked the database). NEVER edit a running shell script; NEVER trust a stop to end its children:
  watch the logs go quiet instead. queue4.sh does exactly that (nothing in work/ touched for 4 minutes), then
  registers every clip without a report, b6s with its own calibration, the 4K clips frozen. Whatever the
  crossed loops leave behind (a b4 or b7s report from the frozen camera is fine; they are 4K) queue4 skips.
"""
s = open(PLAN, encoding='utf-8').read()
if 'the register queues went wrong twice' not in s:
    open(PLAN, 'a', encoding='utf-8', newline='\n').write(entry)
print('logged')
