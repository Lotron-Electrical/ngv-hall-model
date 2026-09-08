# AGENTS.md: the end stack after the 2014 photograph and the floor frames (string patch, 2026-09-08).
p = 'AGENTS.md'
s = open(p, encoding='utf-8').read()
a = s.index('- END GALLERIES (`ENDW`, rebuilt 2026-09-08')
b = s.index("- THE GALLERIES' HEAD (2026-09-08")
new = '''- THE ENDS (ENDW, rebuilt a second time on 2026-09-08, Lloyd: "it's a balcony", "you aren't looking
  through enough"). Read across every source this time: the 2014 photograph of the east end
  (reference-photos/south-glazing/drawings/great-hall-ngv-2014.jpg, 4732 px; the far end profiled row
  by row and scaled on the top balcony, floor 8.34 and the 4K cameras' own height), the posed floor
  frames of both ends with BOTH face hypotheses drawn in (tools/end_overlay2.py class frame side
  4.194,0.344: the end assemblies' corners fall on the plane 3.85 m in front of the plate line
  on both ends, so the face stays on u 4.194 / 48.056 and the day4k cameras stood on its
  parapet), the 4K west frames, endwalls.json and the 1968 plans (agent-ref-ceiling/online/
  ngv_*_floor_plan_1968_BUIL0054*.jpg: the first-floor plan's balconies are 0.46 of a column pitch
  deep on both ends, 3.9 m, the depth built). The stack, ONE plane per end:
    h 0-4.2   a stone ground wall with doors (east: double doors d 5.7-8.0 and a porthole door
              9.8-11.1, the 2014 photograph; west: a porthole door 11.5-12.7 and the lit doorway
              12.9-14.6, w1_000028 and endwalls.json's lit opening), +-0.3 in d
    4.4-6.33  a dark perforated apron under the lower balcony (the 2014 band h 4.39-6.14)
    6.33      the lower balcony floor, a glass balustrade to 7.22 (endwalls.json: 6.33 and the
              7.2 rail on the face)
    8.08-8.34 the top balcony's fascia; 8.34-9.41 a SOLID dark parapet (the 2014 band 8.33-9.43;
              the 4K frames show the people on it from the chest up)
    10.0      the lit soffit, and stone from there to the top, on the face plane
  The 3.99 "floor" of the previous build was the ground's soffit line (endwalls.json's face-plane
  edges 3.80 / 3.91, the 2014 dark strip to 4.17), never a balcony: gone. Back walls on the plate
  line. The scan's closures (u -4.65, 49.06) are the lobbies' back walls, hidden behind the ground
  walls and discarded in the shader above h 4.0 (ENDW.cut). Unmeasured: the apron's exact top
  (taken as the floor), the doors' heights (2.4, the 2014 scale), the west top doorway's width.
'''
s = s[:a] + new + s[b:]
open(p, 'w', encoding='utf-8', newline='\n').write(s)
q = 'E:/sitecapture-captures/ngv-site/agent-ref-walls/PLAN-20260908-walls.md'
t = open(q, encoding='utf-8').read()
t += ('- 2026-09-08 18:30 ends rebuilt on the 2014 photograph + both-hypothesis overlays + 1968 plans (patch_ends5.py):\n'
      '  one plane per end on 4.194/48.056; ground wall with doors, apron 4.4-6.33, floor 6.33 + glass rail, fascia,\n'
      '  floor 8.34 + solid parapet 9.41, head 10. The 3.99 tier removed (it was the soffit line). Pose pairs east-day,\n'
      '  west-day, west-4k in shots/pose/. Next: the corridor behind the north wall openings.\n')
open(q, 'w', encoding='utf-8', newline='\n').write(t)
print('ok')
