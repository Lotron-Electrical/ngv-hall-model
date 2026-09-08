# AGENTS.md: the end galleries, the tapestries and the inscription after 2026-09-08 (string patch).
p = 'AGENTS.md'
s = open(p, encoding='utf-8').read()
a = s.index('- END GALLERIES (`ENDW`).'); b = s.index('- PROOF. `tools/wall-check.mjs')
new = '''- END GALLERIES (`ENDW`, rebuilt 2026-09-08, Lloyd: "get the ends of the hall correct"). They PROJECT
  into the hall, they are not a recess: the 138 day4k frames were all shot from the east gallery
  standing 3.9 m in front of the plate end (u 48.0, h 9.7), the 1968 ground plan (BUIL005490, 27.1
  mm/px off the column pitch) puts the hall's end walls 3.7 m past the outer columns, and the 4K view
  of the west end shows the stack: a lit ground lobby, three open floors with dark fascias and dark
  glass balustrades, lit ceilings, a stone wall with double doors behind the top one. Floors on the
  measured h 3.99 / 6.33 / 8.34 (endwalls.json), face u 4.05 / 48.2, back wall on the plate end
  (0.344 / 51.906, the face-plane edge h 9.96-10.04). The scan's closures, u -4.65 and 49.06, are
  the real ground-level walls (the lobby's back, the kitchen wall) and are KEPT below the first
  fascia (the shader cut is h > 3.54 only). Unmeasured, taken as: fascia 0.45, balustrade 1.1,
  ceilings 0.45 under the floor above; the east's tiers repeat the west's (its frames stand 13 m out).
- TAPESTRIES (2026-09-08): all four identified by NCC on the 4 mm orthos against the collection
  images at true size (tools/tap_id.py): south-A Organic form 0.545, south-B Evolving forms 0.394,
  north-A Abstract sequence 0.339 (mirrored, as the north wall reads in u), north-B Piano movement
  0.446; each next candidate under 0.26. Placed on the NCC boxes (tools/tap_place.py writes
  tools/tapestries.json): the south pair had sat 0.3 m low / 0.3 m west.
- THE INSCRIPTION is gone (Lloyd, 2026-09-08: "I didn't want that there").
'''
s = s[:a] + new + s[b:]
open(p, 'w', encoding='utf-8', newline='\n').write(s)
print('agents ok')
