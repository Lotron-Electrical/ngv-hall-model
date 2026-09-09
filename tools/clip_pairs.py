# 2026-09-09: THE MISSING HALF OF THE MATCHING. Lloyd: "those frames are me looking at the hall. but there
# should be more frames when I look around the actual balcony area."
#
# register_day4k.py matches every clip frame against the SITE keyframes and against nothing else. The site
# reconstruction is the hall: floor, long walls, ceiling. It carries almost no surface on the balconies
# themselves. So the moment the operator turns to face the parapet, the deck, the back wall or an opening,
# the frame has nearly nothing to match, and it either fails outright or solves on a handful of points and
# is refused for low inliers. Measured on the reports: b5 median 15 inliers on its solved frames against a
# gate of 30, b7s median 12, b3 median 21. The clip is not short of information, it is short of PAIRS.
#
# A frame that looks at the balcony has thousands of correspondences with the frame before it. Those pairs
# were never computed. This writes them.
#
# WHAT IS AND IS NOT CLAIMED HERE. Intra-clip pairs alone do not reconstruct the balcony: on a balcony the
# operator stands still and pans, so there is no baseline and nothing can be triangulated from the clip by
# itself. That is exactly why an earlier solo reconstruction of one clip broke into eight fragments with
# focal estimates from 1300 to 2421 px, which the register's own docstring records as "a rotation, not a
# reconstruction". What these pairs DO give is the relative ROTATION between neighbouring frames, which is
# the best conditioned thing in photogrammetry and is all a standing pan actually changes. The pose of a
# frame that looks at the balcony is then its neighbour's centre with its own rotation.
#
# The pairs are a short sliding window plus a few long reaches. The window carries the pan. The long reaches
# close the loop when the operator sweeps back across the same view, which is what stops a chain of small
# rotations accumulating drift over a look.
#
#   python tools/clip_pairs.py <prefix> [out.txt]
import sqlite3
import sys

DB = 'E:/sitecapture-captures/ngv-video/balcony2-register/work/database.db'
NEAR = 8            # every pair within this many frames: the pan itself
FAR = [12, 18, 26, 40]   # sparse long reaches, taken every FAR_EVERY frames: loop closure across a sweep
FAR_EVERY = 3

prefix = sys.argv[1]
out = sys.argv[2] if len(sys.argv) > 2 else None

con = sqlite3.connect(DB)
rows = con.execute('SELECT name FROM images ORDER BY name').fetchall()
con.close()
names = sorted(r[0] for r in rows if r[0].startswith(prefix) and r[0][len(prefix)] == '_')
print(prefix, 'has', len(names), 'frames in the database')
if not names:
    raise SystemExit('no frames with that prefix')

pairs = []
n = len(names)
for i in range(n):
    for k in range(1, NEAR + 1):
        if i + k < n:
            pairs.append((names[i], names[i + k]))
    if i % FAR_EVERY == 0:
        for k in FAR:
            if i + k < n:
                pairs.append((names[i], names[i + k]))
print('writing', len(pairs), 'pairs')
if out:
    fh = open(out, 'w', encoding='utf-8', newline='\n')
    for a, b in pairs:
        print(a, b, file=fh)
    fh.close()
    print('wrote', out)
