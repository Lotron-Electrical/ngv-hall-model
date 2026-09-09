# 2026-09-10: CHOOSE THE FRAMES PER SURFACE, FROM THE SURFACE'S OWN BOX, BEFORE ANY PICTURE IS OPENED.
#
# WHY THIS EXISTS. tools/surface_match.py scored ten frames that tools/render_match.py had chosen for how
# much north-wall OPENING they showed, and the balcony surfaces returned ZERO readable pixels in every one
# of them: gallery-fascia, gallery-rail, gallery-floor, gallery-parapet, end-wall, all of them nothing.
# That is not the scorer failing, it is the frame set aimed at the wrong thing. A frame set chosen to show
# openings shows openings.
#
# SO THE TARGET PICKS THE FRAME. Each mesh gave up its own world bounding box in the browser
# (surface_match.mjs bounds), one box PER PART because gallery-fascia is two meshes forty metres apart.
# Every posed camera in the archive is asked how much of each box it frames, with all eight corners
# required inside the picture, and each surface keeps the frames that show it largest. No picture is opened
# to decide any of this, and the rule is the same for a surface that turns out well as for one that does
# not.
#
# ONE PER CAPTURE PER SURFACE, so a clip that happens to dwell on a fascia cannot answer for it alone, and
# a cap on the total so this stays a run rather than a render farm.
#   python tools/surface_pick.py
import io
import json
import os
import re
import sys

import numpy as np

sys.path.insert(0, 'tools')
import underside_geom as U

O = np.array([-54.907447, -1.43545, 3.040286])
HU = np.array([0.975681, 0, 0.219196])
HD = np.array([0.219196, 0, -0.975681])
WANT = re.compile('gallery|corridor|rail|fascia|parapet|upstand|downstand|soffit|reveal|jamb|opening|'
                  'end-wall|end-ground|wall-grille|wall-north|wall-south', re.I)
CLASSES = ('walk', 'night', 'day4k', 'b1', 'b3', 'b4', 'b5', 'b6s', 'b7s')
PERCAP = 1          # one frame per capture per surface
PERSURF = 3         # and at most this many frames for any one surface
MINCOVER = 0.010    # a box smaller than this much of the picture cannot be read and is not chosen
CAP = 30            # the whole render list


def corners_of(bx):
    mn, mx = bx['min'], bx['max']
    pts = []
    for a in (mn[0], mx[0]):
        for b in (mn[1], mx[1]):
            for c in (mn[2], mx[2]):
                pts.append(O + a * HU + b * HD + np.array([0.0, c, 0.0]))
    return np.asarray(pts)


def cover(cam, pts):
    x, y, z = cam.project(pts)
    if not np.all(z > 0.5):
        return 0.0
    mx, my = 0.02 * cam.w, 0.02 * cam.h
    if x.min() < mx or x.max() > cam.w - mx or y.min() < my or y.max() > cam.h - my:
        return 0.0
    return float((x.max() - x.min()) * (y.max() - y.min()) / (cam.w * cam.h))


def pose(cam):
    C = cam.center
    q = C - O
    f = cam.R.T @ np.array([0, 0, 1.0])
    fu, fd, fh = float(f @ HU), float(f @ HD), float(f[1])
    horiz = float(np.hypot(fu, fd))
    p = np.asarray(cam.params, float)
    x0, y0, _ = cam.project(np.asarray([C + f * 10]))
    x1, y1, _ = cam.project(np.asarray([C + f * 10 + np.array([0, 1.0, 0])]))
    du, dv = float(x1[0] - x0[0]), float(y1[0] - y0[0])
    n = float(np.hypot(du, dv))
    dsq = float(np.hypot(cam.w, cam.h))
    return dict(u=float(q @ HU), d=float(q @ HD), h=float(q[1]), fu=fu / horiz, fd=fd / horiz,
                pitch=float(np.degrees(np.arcsin(fh))), w=int(cam.w), hgt=int(cam.h),
                vfov=float(2 * np.degrees(np.arctan(cam.h / 2.0 / p[1]))),
                sqvfov=float(2 * np.degrees(np.arctan(dsq / 2.0 / p[1]))), sqside=dsq / float(cam.h),
                fx=float(p[0]), fy=float(p[1]), ppx=float(p[2]) - cam.w / 2.0,
                ppy=float(p[3]) - cam.h / 2.0, upx=du / n, upy=dv / n,
                roll=float(np.degrees(np.arctan2(du / n, -dv / n))), params=[float(v) for v in p])


def main():
    box = json.loads(io.open('render-match/bounds.json', encoding='utf-8').read())
    targets = []
    for nm, e in sorted(box.items()):
        if not WANT.search(nm) or e.get('baked'):
            continue
        for k, part in enumerate(e['parts']):
            targets.append((nm, k, part))
    print('%d parts over %d named surfaces are the targets' % (len(targets), len({t[0] for t in targets})))

    cams = {}
    for cn in CLASSES:
        try:
            fr = U.load_class(cn)
        except Exception as exc:
            print('   %-6s could not be loaded: %s' % (cn, str(exc)[:60]))
            continue
        keep = {}
        for k, (cam, ip) in fr.items():
            q = cam.center - O
            cu, cd = float(q @ HU), float(q @ HD)
            if not (-1.0 < cu < 53.0) or not (-1.5 < cd < 16.5):
                continue
            pp = np.asarray(cam.params, float)
            if abs(pp[2] - cam.w / 2.0) > 0.25 * cam.w or abs(pp[3] - cam.h / 2.0) > 0.25 * cam.h:
                continue
            keep[k] = (cam, ip)
        cams[cn] = keep
        print('   %-6s %d posed frames stand inside the building with a sane lens' % (cn, len(keep)))

    best = {}
    for nm, k, part in targets:
        pts = corners_of(part)
        for cn, fr in cams.items():
            top = None
            for fk, (cam, ip) in fr.items():
                c = cover(cam, pts)
                if c >= MINCOVER and (top is None or c > top[0]):
                    top = (c, cn, fk, ip, cam)
            if top:
                best.setdefault(nm, []).append(top)

    if not best:
        sys.exit('   NOT ONE SURFACE IS FRAMED WHOLE BY ANY POSED CAMERA. Nothing to render.')

    # THE CAP IS SPENT ROUND BY ROUND, NOT SURFACE BY SURFACE, and the first version of this got it wrong
    # in a way worth recording. Spending it in order of size gave the big surfaces three frames each and
    # left the corridor with none, which is exactly the part of the goal that most needs looking at. Every
    # surface now gets its FIRST frame before any surface gets its second.
    picks, seen, chosen = [], {}, {}
    order = sorted(best.items(), key=lambda t: -max(x[0] for x in t[1]))
    for nm, rows in order:
        rows.sort(key=lambda t: -t[0])
        taken, caps = [], set()
        for c, cn, fk, ip, cam in rows:
            if cn in caps or len(taken) >= PERSURF:
                continue
            caps.add(cn)
            taken.append((c, cn, fk, ip, cam))
        best[nm] = taken
        chosen[nm] = []
    for r in range(PERSURF):
        for nm, taken in order:
            taken = best[nm]
            if r >= len(taken):
                continue
            c, cn, fk, ip, cam = taken[r]
            key = cn + '/' + fk
            if key in seen:
                if nm not in seen[key]['wants']:
                    seen[key]['wants'].append(nm)
                chosen[nm].append(fk + ' (already)')
                continue
            if len(picks) >= CAP:
                chosen[nm].append(fk + ' (over the cap)')
                continue
            p = pose(cam)
            p.update(dict(cls=cn, frame=fk, photo=ip, cover=c, wants=[nm], group='surface'))
            picks.append(p)
            seen[key] = p
            chosen[nm].append(fk)
    print('')
    print('   surface                  captures that frame it whole   best cover  chosen')
    for nm, rows in order:
        print('   %-24s %-30s %.3f       %s'
              % (nm[:24], ', '.join(sorted({t[1] for t in rows}))[:30],
                 max(t[0] for t in rows), ', '.join(chosen[nm])))

    io.open('render-match.json', 'w', encoding='utf-8', newline='').write(json.dumps(picks, indent=1))
    print('')
    print('   %d frames chosen over %d captures, covering %d of the %d surfaces.'
          % (len(picks), len({p['cls'] for p in picks}), len({w for p in picks for w in p['wants']}),
             len(best)))
    miss = [nm for nm in {t[0] for t in targets} if nm not in best]
    if miss:
        print('   AND %d SURFACES ARE FRAMED WHOLE BY NO POSED CAMERA IN THE ARCHIVE, so this run cannot'
              % len(miss))
        print('   say anything about them either way: %s' % ', '.join(sorted(miss)))
    print('   wrote render-match.json; now run node tools/surface_match.mjs then surface_match.py')


if __name__ == '__main__':
    main()
