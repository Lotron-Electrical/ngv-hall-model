# 2026-09-09: the south wall measured for the first time.
PLAN = 'E:/sitecapture-captures/ngv-site/agent-ref-walls/PLAN-20260908-walls.md'
entry = """- 2026-09-09, THE SOUTH WALL, MEASURED FOR THE FIRST TIME. Everything done on the north wall had no
  counterpart here, and the stated reason was that the south glazing comes from the scan mesh rather than a
  table, so there were no drawn vertical lines to search for. That is true of the GLAZING and not of the
  WALL. The south face also carries three grilles and two doors, and those are tables in index.html, which
  gives ten vertical edges: tools/south_edges.py measures them with the same fixed-point instrument and
  writes both pooled medians and raw per-frame rows.
  THE FACE, fitted by tools/face_depth.py on those raw rows the identified way (remove each edge's own
  constant, regress the remainder on the along-over-out ratio, the slope is the depth error alone):
    day4k -0.010 (50 rows); night -0.050 (47); walk +0.003 (125)
    pooled -0.010 m, capture range 0.053 m
  dSouth 15.364 STANDS, confirmed to 10 mm over three captures. b3 and b7s see this wall but never square
  enough on for the ratio to vary, so they cannot be fitted. Both wall faces are now measured: north
  -0.003 over six captures, south -0.010 over three.
  THE FEATURES ON IT ARE NOT MEASURED and none is moved. Across the same captures the nine resolved grille
  and door edges pool with a median capture-to-capture spread of 185 mm, 2.4 times their spread inside a
  single capture, and only one (door 2 east, +0.041) is both agreed and settled. Grille 2 reads about
  0.09 m west in the captures that resolve it, but only one capture resolves BOTH of its edges, so it
  cannot be applied as a coherent shift the way the north openings were; a one-edge move would change the
  grille's width instead of its position, which is the mistake the north wall taught.
  So: the south wall is where it is drawn; what stands on it is not.
"""
s = open(PLAN, encoding='utf-8').read()
if 'THE SOUTH WALL, MEASURED FOR THE FIRST TIME' not in s:
    open(PLAN, 'a', encoding='utf-8', newline='\n').write(entry)
print('logged')
