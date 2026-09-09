# 2026-09-10: HOW FAR IS THE SCAN FROM EACH SURFACE THE GOAL NAMES, AND IS IT EVEN THERE?
#
# WHY THE SLAB TEST WAS THE WRONG SHAPE. tools/bake_vs_model.py asked, for a fixed slab either side of each
# analytic face, what the scan lying on it says. With the scan correctly identified as the clean-hall
# chunks and nothing else, the answer for almost every surface this goal names was NO POINTS AT ALL, and a
# fixed slab cannot tell the two reasons apart. A surface with the scan half a metre off it is a
# CONTRADICTION between two descriptions of one building. A surface with no scan for three metres around is
# a place NOBODY SCANNED. Those deserve opposite responses, so the search radius has to be free.
#
# THE DECISION RULE, FIXED BEFORE THE NUMBERS ARE OPENED.
#   1. Each analytic triangle is sampled on a barycentric grid, and every sample asks for its nearest scan
#      vertex, with no distance limit.
#   2. THE FLOOR IS THE SCAN'S OWN RESOLUTION, measured here as the median distance from a scan vertex to
#      its nearest neighbour. Nothing can be shown to agree better than the scan's own point spacing, and
#      a claim must not be smaller than its own spread.
#   3. A surface is UNSCANNED where fewer than MINNEAR scan vertices lie within PRESENT metres of its
#      samples. UNSCANNED is not a verdict and is never written as one: the corridor behind the wall was
#      never scanned and must come out this way.
#   4. Otherwise it is TESTED, and it CONTRADICTS the scan when its median nearest distance exceeds both
#      three times the scan's spacing and 100 mm. Anything less is AGREES, to a bound this prints.
#   5. THE CONTROL IS A SURFACE OF THE SAME KIND THAT NOBODY DISPUTES, run through the same machine. If the
#      control contradicts, the two descriptions are not registered and no other row may be read.
#
# WHAT A CONTRADICTION WOULD AND WOULD NOT MEAN. Not automatically that the analytic surface is wrong: the
# scan has its own registration, its own holes and its own noise, and it is a MESH, so a flat wall may be
# described by vertices only along its edges. What it means is that two independent descriptions of this
# building disagree in a place where both claim to speak.
#   python tools/bake_distance.py
import io
import json
import sys

import numpy as np

NEAR = 0.15
PRESENT = 1.0
MINNEAR = 30
BAR = 0.100
GRID = 4          # barycentric samples a side, so ten points a triangle
CONTROL = 'canopy-procedural'


def tri_samples(v):
    """Points spread over a triangle, corners included."""
    out = []
    for i in range(GRID + 1):
        for j in range(GRID + 1 - i):
            a, b = i / float(GRID), j / float(GRID)
            out.append(v[0] + a * (v[1] - v[0]) + b * (v[2] - v[0]))
    return out


class Grid(object):
    """A hash grid, so this needs nothing that is not already installed."""

    def __init__(self, pts, cell):
        self.cell = cell
        self.pts = pts
        self.d = {}
        k = np.floor(pts / cell).astype(np.int32)
        for i in range(len(pts)):
            self.d.setdefault((k[i, 0], k[i, 1], k[i, 2]), []).append(i)

    def near(self, p, rings):
        c = np.floor(p / self.cell).astype(np.int32)
        got = []
        for a in range(-rings, rings + 1):
            for b in range(-rings, rings + 1):
                for e in range(-rings, rings + 1):
                    v = self.d.get((c[0] + a, c[1] + b, c[2] + e))
                    if v:
                        got.extend(v)
        return got

    def nearest(self, p, maxrings=6):
        for r in range(1, maxrings + 1):
            idx = self.near(p, r)
            if idx:
                q = self.pts[idx] - p
                dd = np.sqrt((q * q).sum(1))
                j = int(np.argmin(dd))
                if dd[j] <= r * self.cell or r == maxrings:
                    return float(dd[j]), len(idx)
        return float('inf'), 0


def main():
    g = json.loads(io.open('render-match/geom.json', encoding='utf-8').read())
    raw = np.asarray(g['scan'], float).reshape(-1, 3)
    # THE SCAN'S VERTICES ARE REPEATED ONCE PER TRIANGLE CORNER, and the first run of this did not notice:
    # it reported the scan's own resolution as 0.000 m, because a vertex's nearest neighbour is its own
    # duplicate. Distinct positions only, or the number that sets the floor for every claim below is a lie.
    scan = np.unique(np.round(raw, 3), axis=0)
    print('THE DECISION RULE, WRITTEN OUT BEFORE THE NUMBERS ARE OPENED.')
    print('   Every analytic triangle is sampled on a barycentric grid and each sample asks for its')
    print('   nearest scan vertex with NO distance limit. The floor is the scan\'s own resolution, measured')
    print('   below as the median spacing between neighbouring scan vertices. A surface is UNSCANNED where')
    print('   fewer than %d scan vertices lie within %.1f m of its samples, which is not a verdict and is'
          % (MINNEAR, PRESENT))
    print('   never written as one. Otherwise it CONTRADICTS the scan only when its median nearest')
    print('   distance beats both three times that spacing and %.0f mm. The control is %s, run'
          % (1000 * BAR, CONTROL))
    print('   through the same machine; if the control contradicts, no other row may be read.')
    print('')
    print('   %d scan vertices, %d of them distinct, spanning u %.2f to %.2f, d %.2f to %.2f, h %.2f to'
          % (len(raw), len(scan), scan[:, 0].min(), scan[:, 0].max(), scan[:, 1].min(), scan[:, 1].max(),
             scan[:, 2].min()))
    print('   %.2f' % scan[:, 2].max())

    grid = Grid(scan, 0.5)
    rs = np.random.RandomState(20260910)
    sample = rs.choice(len(scan), min(3000, len(scan)), replace=False)
    own = []
    for i in sample:
        p = scan[i]
        idx = grid.near(p, 1)
        if len(idx) < 2:
            continue
        q = scan[idx] - p
        dd = np.sqrt((q * q).sum(1))
        dd.sort()
        own.append(float(dd[1]))
    spacing = float(np.median(own)) if own else float('nan')
    print('   THE SCAN\'S OWN RESOLUTION: a vertex sits %.3f m from its nearest neighbour at the median,'
          % spacing)
    print('   over %d sampled vertices. Nothing below can be shown to agree better than that.' % len(own))
    bar = max(3 * spacing, BAR)
    print('   so the bar for a contradiction is %.3f m.' % bar)
    print('')

    rows = []
    for nm, flat in g['tri'].items():
        v = np.asarray(flat, float).reshape(-1, 3, 3)
        pts, area = [], 0.0
        for t in v:
            area += 0.5 * float(np.linalg.norm(np.cross(t[1] - t[0], t[2] - t[0])))
            pts.extend(tri_samples(t))
        pts = np.asarray(pts)
        if len(pts) > 4000:
            pts = pts[rs.choice(len(pts), 4000, replace=False)]
        dists, present = [], []
        rings = int(np.ceil(PRESENT / grid.cell))
        for p in pts:
            d, k = grid.nearest(p)
            dists.append(d)
            idx = grid.near(p, rings)
            if idx:
                q = grid.pts[idx] - p
                present.append(int((np.sqrt((q * q).sum(1)) <= PRESENT).sum()))
            else:
                present.append(0)
        dists = np.asarray(dists)
        near_n = float(np.median(present))
        fin = dists[np.isfinite(dists)]
        q1 = float(np.percentile(fin, 25)) if len(fin) else float('inf')
        rows.append(dict(nm=nm, tris=len(v), area=area, n=len(pts),
                         med=float(np.median(dists)), q1=q1,
                         frac=float((dists <= NEAR).mean()), present=near_n))

    ctrl = [r for r in rows if r['nm'] == CONTROL]
    if not ctrl:
        sys.exit('   THE CONTROL SURFACE IS NOT IN THE DUMP, so nothing may be read.')
    cr = ctrl[0]
    # A CONTROL THAT COMES BACK UNSCANNED DISQUALIFIES THIS RUN EXACTLY AS A CONTROL THAT CONTRADICTS
    # DOES, and the first version of this rule missed that. It only vetoed on a contradicting control, so
    # when the canopy came back UNSCANNED the three rows below were still printed as faults. An instrument
    # that cannot find an 870 square metre canopy is not in a position to adjudicate a wall.
    cbad = cr['present'] < MINNEAR or cr['med'] > bar
    print('   THE CONTROL: %s, %d triangles, %.1f square metres.' % (cr['nm'], cr['tris'], cr['area']))
    print('      scan within %.1f m of a sample: %.0f vertices at the median' % (PRESENT, cr['present']))
    print('      nearest scan vertex: %.3f m at the median, %.3f m at the lower quartile'
          % (cr['med'], cr['q1']))
    if cbad:
        print('')
        print('   THE CONTROL FAILS, so NOTHING BELOW MAY BE READ AS A FAULT and no row is written as one.')
        print('   The scan does not reach a surface of 870 square metres that it certainly overlaps, which')
        print('   means the two descriptions cannot adjudicate each other anywhere. The rows are printed')
        print('   as a record of what was measured and for nothing else.')
    print('')
    print('   surface                  tris   area m2   scan nearby   nearest m   within %.2f   verdict'
          % NEAR)
    rows.sort(key=lambda r: (r['present'] < MINNEAR, -r['med']))
    tested = contra = unscanned = 0
    for r in rows:
        if r['present'] < MINNEAR:
            tag = 'UNSCANNED'
            unscanned += 1
        elif cbad:
            tag = 'not readable'
        elif r['med'] > bar:
            tag = 'CONTRADICTS'
            contra += 1
            tested += 1
        else:
            tag = 'agrees'
            tested += 1
        print('   %-24s %5d  %8.1f   %9.0f   %9.3f   %8.2f   %s'
              % (r['nm'][:24], r['tris'], r['area'], r['present'], r['med'], r['frac'], tag))

    print('')
    if cbad:
        print('   NOTHING IS CONCLUDED ABOUT ANY SURFACE. %d rows had scan near enough to look at and %d'
              % (len(rows) - unscanned, unscanned))
        print('   did not, but the control settles it: this comparison has no purchase on this model.')
    else:
        print('   %d surfaces are TESTED, %d of them CONTRADICT the scan, and %d are UNSCANNED.'
              % (tested, contra, unscanned))
    if unscanned:
        print('   UNSCANNED is the expected and correct answer for the corridor behind the wall, because')
        print('   nobody ever took a camera in there. It is not a fault and none of those rows is being')
        print('   called right or wrong.')
    print('')
    print('   WHAT A CONTRADICTION MEANS AND WHAT IT DOES NOT. Not automatically that the analytic surface')
    print('   is wrong. The scan has its own registration, its own holes and its own noise, and it is a')
    print('   MESH, so a flat wall can be described by vertices only along its edges and a sample in the')
    print('   middle of that wall will report a large distance with nothing wrong anywhere. What it means')
    print('   is that two independent descriptions of this building disagree in a place where both claim')
    print('   to speak, and that is worth more than either agreeing with itself.')


if __name__ == '__main__':
    main()
