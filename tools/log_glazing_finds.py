# 2026-09-09: logs the south glazing check from the first registered balcony clip (b1) and the queue swap.
PLAN = 'E:/sitecapture-captures/ngv-site/agent-ref-walls/PLAN-20260908-walls.md'
entry = """- 2026-09-09 night, the south glazing against b1 (the first of Lloyd's new balcony clips, 59 frames posed):
  b1_000053 from the north balcony (u 19-20, h 9.2) looks down across the hall onto the glazed bay. Its fin edges
  met with the plane d 15.364 (tools/frame_pixel.py, row 1900): grey fin faces on u 21.65-22.60 and 25.81-26.37,
  dark mullion frames on 22.60-23.03, 25.63-25.81, 26.37-26.76 and 31.58-32.26, a grey face on 32.26-32.69,
  stone from there. The sim (tools/glazing-fins.mjs, the GLB in hall coordinates): fins 0.40 wide on a 3.90 m
  pitch, u 18.12-18.52, 22.02-22.42, 25.92-26.32, 29.83-30.23, 33.73-34.13, d 15.24-17.46 (2.2 m deep, seen
  side-on from the balcony as wide grey bands, which is what the frame shows); mullions 0.12 wide on 20.21,
  24.11, 28.02, 31.92 at d 17.13-17.45. Fin-1 and fin-2 agree with the frame within 0.1-0.2 m (the frame's
  plane is the fins' inner face, 0.12 m off); the geometry stands. What differs is BEYOND the glass: the real
  frames show Federation Court by day (concrete floor, escalators, people, the yellow sculpture), the sim shows
  the day sky tone through the panes (nothing beyond the glass is scanned; the court is a viewer layer of
  Lloyd's partner sculptures). Not a wall item; noted for the court pass (PLAN line 56). Proof pairs
  bal-b1_000053 / 105 / 181 in agent-ref-walls/shots/pose.
- 2026-09-09 night: the register queue swapped so the GALLERY clip b6s runs next (balcony2-register/queue2.sh:
  b6s b4 b5 b7s, one clip at a time on the shared database), the first queue stopped once b3's report landed.
"""
s = open(PLAN, encoding='utf-8').read()
if 'the south glazing against b1 (the first of' not in s:
    open(PLAN, 'a', encoding='utf-8', newline='\n').write(entry)
print('logged')
