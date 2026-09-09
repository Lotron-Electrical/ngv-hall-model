# 2026-09-09: THE ROOM BEHIND THE BRICK WALL, MEASURED BY TRIANGULATING ITS OWN LAMP.
#
# Every attempt on this room so far has tried to read a SURFACE through a 1.2 m slot from 15 m away, and
# the surfaces lose: the walk frames see an opening 100 to 150 px wide with under 20 grey levels of signal
# inside it. A lamp is the opposite kind of target. It is a bright point against a dark room, it survives
# any exposure, and a point triangulates from two rays with no edge finder, no search window and therefore
# no follow gain at all. The corridor ceiling 11.4 was ORIGINALLY INFERRED from a lamp; this measures the
# lamp instead of inferring from it.
#
# WHAT IS ASSUMED AND WHAT IS NOT. The drawn opening rectangle is used only to decide which part of each
# picture to look in, so that a light in the hall cannot be mistaken for a light in the room; the position
# that comes out is whatever the rays say and is free to land anywhere, including outside the drawn room.
# A blob is kept only if it is brighter than the opening's own interior by a wide margin, and a point is
# reported only if rays from cameras standing at least a metre apart agree on it, which is the condition
# the balcony soffit could not meet.
#   python tools/corridor_lamp.py [opening]
import sys

import cv2
import numpy as np

sys.path.insert(0, 'tools')
import underside_geom as U  # noqa: E402

O = np.array([-54.907447, -1.43545, 3.040286])
HU = np.array([0.975681, 0, 0.219196])
HD = np.array([0.219196, 0, -0.975681])
DN = -0.090
SILL, HEAD = 8.99, 11.35
OPENINGS = [[4.098, 5.310], [7.697, 8.911], [10.707, 11.920],
        [15.227, 16.440], [18.917, 20.130], [22.565, 23.778],
        [26.213, 27.426], [29.963, 31.175], [33.642, 34.853],
        [37.177, 38.383], [40.906, 42.118], [44.526, 45.739]]
CLASSES = ('walk', 'night', 'day4k', 'b1', 'b3', 'b5', 'b7s', 'b6g', 'b1p', 'b3p', 'b5p', 'b7sp', 'b6gp')


def aperture(cam, u0, u1):
    """the drawn opening rectangle projected into this picture, or None"""
    corners = np.array([O + uu * HU + DN * HD + np.array([0, vv, 0])
                        for uu, vv in ((u0, SILL), (u1, SILL), (u1, HEAD), (u0, HEAD))])
    x, y, z = cam.project(corners)
    if np.any(z <= 0.3):
        return None
    return np.stack([x, y], 1)


def rays_for(cam, img, u0, u1):
    """bright blobs inside the drawn aperture of one opening, as world rays from the camera centre"""
    q = aperture(cam, u0, u1)
    if q is None or q.min() < -50 or q[:, 0].max() > cam.w + 50 or q[:, 1].max() > cam.h + 50:
        return []
    if q[:, 0].max() - q[:, 0].min() < 25 or q[:, 1].max() - q[:, 1].min() < 25:
        return []                                   # too small on the sensor to hold a blob
    mask = np.zeros(img.shape[:2], np.uint8)
    cv2.fillConvexPoly(mask, np.round(q).astype(np.int32), 255)
    mask = cv2.erode(mask, np.ones((5, 5), np.uint8))
    if int(mask.sum()) // 255 < 200:
        return []
    vals = img[mask > 0].astype(np.float32)
    thr = float(vals.mean() + 5.0 * vals.std())
    if thr > 250 or float(vals.max()) < thr:
        return []
    hot = np.logical_and(img.astype(np.float32) > thr, mask > 0).astype(np.uint8)
    n, lab, stats, cent = cv2.connectedComponentsWithStats(hot, 8)
    fx, fy, ux, uy = cam.params[0], cam.params[1], cam.params[2], cam.params[3]
    K = np.array([[fx, 0, ux], [0, fy, uy], [0, 0, 1]], float)
    dist = np.array(cam.params[4:8], float) if cam.model == 'OPENCV' else np.zeros(4)
    out = []
    for k in range(1, n):
        area = int(stats[k, cv2.CC_STAT_AREA])
        if area < 4 or area > 4000:
            continue
        cx, cy = float(cent[k, 0]), float(cent[k, 1])
        un = cv2.undistortPoints(np.array([[[cx, cy]]], np.float64), K, dist.reshape(1, -1))[0, 0]
        v = cam.R.T @ np.array([float(un[0]), float(un[1]), 1.0])
        out.append((cam.center.copy(), v / np.linalg.norm(v), area, float(img[int(cy), int(cx)])))
    return out


def closest_point(bundle):
    """the point minimising the summed squared distance to a bundle of rays"""
    A = np.zeros((3, 3))
    b = np.zeros(3)
    for C, v, _a, _b in bundle:
        M = np.eye(3) - np.outer(v, v)
        A += M
        b += M @ C
    return np.linalg.solve(A, b)


def dist_to(P, C, v):
    w = P - C
    return float(np.linalg.norm(w - (w @ v) * v))


def main():
    which = int(sys.argv[1]) if len(sys.argv) > 1 else None
    todo = [which - 1] if which else range(len(OPENINGS))
    seen = set()
    cams = {}
    for cls in CLASSES:
        try:
            fr = U.load_class(cls)
        except Exception:
            continue
        for f, v in fr.items():
            if f not in seen:
                seen.add(f)
                cams[f] = (cls, v[0], v[1])
    print(len(cams), 'distinct posed frames offered to the search')

    for oi in todo:
        u0, u1 = OPENINGS[oi]
        rays = []
        for f, (cls, cam, ip) in cams.items():
            qc = cam.center - O
            if float(qc @ HD) < 0.5:
                continue                                # must be out in the hall looking at this wall
            if abs(float(qc @ HU) - 0.5 * (u0 + u1)) > 22.0:
                continue
            q = aperture(cam, u0, u1)
            if q is None or q[:, 0].min() < 0 or q[:, 0].max() > cam.w or q[:, 1].min() < 0 or q[:, 1].max() > cam.h:
                continue
            img = cv2.imread(ip, cv2.IMREAD_GRAYSCALE)
            if img is None:
                continue
            for r in rays_for(cam, cv2.GaussianBlur(img, (3, 3), 0), u0, u1):
                rays.append((f,) + r)
        if len(rays) < 4:
            continue
        cs = np.array([r[1] for r in rays])
        base = float(np.linalg.norm(cs.max(0) - cs.min(0)))
        best = None
        for i in range(len(rays)):
            for j in range(i + 1, len(rays)):
                if np.linalg.norm(rays[i][1] - rays[j][1]) < 1.0:
                    continue
                P = closest_point([rays[i][1:], rays[j][1:]])
                inl = [r for r in rays if dist_to(P, r[1], r[2]) < 0.12]
                if best is None or len(inl) > len(best[1]):
                    best = (P, inl)
        if best is None or len(best[1]) < 4:
            print('opening %2d: %3d blobs from %2d frames, baseline %.1f m, no consistent point'
                  % (oi + 1, len(rays), len(set(r[0] for r in rays)), base))
            continue
        P = closest_point([r[1:] for r in best[1]])
        for _ in range(3):
            inl = [r for r in rays if dist_to(P, r[1], r[2]) < 0.12]
            if len(inl) < 4:
                break
            P = closest_point([r[1:] for r in inl])
        inl = [r for r in rays if dist_to(P, r[1], r[2]) < 0.12]
        qq = P - O
        pu, pd, ph = float(qq @ HU), float(qq @ HD), float(P[1] - O[1])
        cin = np.array([r[1] for r in inl])
        spread = float(np.linalg.norm(cin.max(0) - cin.min(0)))
        rms = float(np.sqrt(np.mean([dist_to(P, r[1], r[2]) ** 2 for r in inl])))
        print('opening %2d: %3d blobs from %2d frames; a point on u %.3f d %.3f h %.3f'
              % (oi + 1, len(rays), len(set(r[0] for r in rays)), pu, pd, ph))
        print('            %d rays agree within %.3f m rms, from cameras %.1f m apart'
              % (len(inl), rms, spread))
        print('            it sits %.3f m behind the wall face, the room is drawn 2.000 m deep'
              % (DN - pd))
        if 'draw' in sys.argv:
            # THE DRAWING BACK, which is the step that refuted three earlier instruments in this project and
            # is therefore not optional. The triangulated point is projected into the frames that voted for
            # it, beside the aperture it was found through.
            import os
            outd = 'E:/sitecapture-captures/ngv-site/agent-ref-walls/shots/corridor'
            os.makedirs(outd, exist_ok=True)
            for r in inl[:3]:
                cls, cam, ip = cams[r[0]]
                im = cv2.imread(ip)
                ap = aperture(cam, u0, u1)
                cv2.polylines(im, [np.round(ap).astype(np.int32)], True, (255, 120, 0), 3)
                px, py, pz = cam.project(np.asarray([P]))
                cv2.circle(im, (int(px[0]), int(py[0])), 22, (0, 255, 255), 4)
                cv2.putText(im, 'd %.2f h %.2f' % (pd, ph), (int(px[0]) + 30, int(py[0])),
                            cv2.FONT_HERSHEY_SIMPLEX, 1.0, (0, 255, 255), 3, cv2.LINE_AA)
                k = 1400.0 / im.shape[0]
                cv2.imwrite(os.path.join(outd, 'op%02d-%s.jpg' % (oi + 1, r[0])),
                            cv2.resize(im, (int(im.shape[1] * k), 1400)), [cv2.IMWRITE_JPEG_QUALITY, 86])
            print('            drawn back into', min(3, len(inl)), 'of its own frames')


if __name__ == '__main__':
    main()
