# 2026-09-09: clear one frame prefix out of a COLMAP relocalisation database, so a register that was
# killed part way through its matching can be run again. Without this the second run dies on
# "SQLite error: constraint failed" when matches_importer re-inserts pairs the first run already wrote.
# Only rows belonging to that prefix are touched; every other class in the workspace is left alone.
#   python tools/db_clear_prefix.py <workspace> <prefix>
import sys, sqlite3
from pathlib import Path
ws, prefix = sys.argv[1], sys.argv[2]
db = Path(ws) / 'work' / 'database.db'
if not db.exists(): raise SystemExit('no database at ' + str(db))
con = sqlite3.connect(str(db))
ids = [i for (i,) in con.execute("SELECT image_id FROM images WHERE name LIKE ?", (prefix + '_%',))]
print('%s: %d images in the database' % (prefix, len(ids)))
if not ids: raise SystemExit(0)
S = set(ids); M = 2147483647
def touches(pair_id): return (pair_id // M) in S or (pair_id % M) in S
for table in ('two_view_geometries', 'matches'):
    try: rows = [r for (r,) in con.execute('SELECT pair_id FROM %s' % table)]
    except sqlite3.OperationalError: print('  no table', table); continue
    hit = [r for r in rows if touches(r)]
    con.executemany('DELETE FROM %s WHERE pair_id = ?' % table, [(r,) for r in hit])
    print('  %-20s deleted %d of %d rows' % (table, len(hit), len(rows)))
for table in ('keypoints', 'descriptors'):
    try: con.executemany('DELETE FROM %s WHERE image_id = ?' % table, [(i,) for i in ids])
    except sqlite3.OperationalError: print('  no table', table); continue
    print('  %-20s cleared for %d images' % (table, len(ids)))
con.executemany('DELETE FROM images WHERE image_id = ?', [(i,) for i in ids])
print('  images               removed %d rows' % len(ids))
con.commit(); con.close(); print('done; the register can run fresh now')
