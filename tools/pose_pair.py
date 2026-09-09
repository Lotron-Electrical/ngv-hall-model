# 2026-09-10: THE PHOTOGRAPH AND THE SIM, THROUGH THE SAME LENS, SIDE BY SIDE.
#
# Lloyd's words on 2026-09-09 were "the balcony sections are still not correct", and he was looking at a
# picture when he said it. Everything since has been detectors, and a detector answers only the question it
# was set. The one instrument that answers HIS question is a pair: his frame on the left, the sim rendered
# from that frame's own solved camera on the right, at the same field of view and the same pixel size. A
# difference in shape shows up without anyone having to guess in advance which number is wrong.
#
# WHAT MAKES THE PAIR HONEST. The pose is not chosen, it is read out of the registration for that exact
# frame: position in hall coordinates, forward direction, pitch and vertical field of view. The sim is
# rendered at the frame's own stored width and height, so a feature that lands on pixel row 900 in one
# lands on row 900 in the other if the model is right. Every piece of the game's interface is hidden by
# walking the DOM rather than by a selector list, so nothing added later leaks into the picture.
#
# WHAT IT CANNOT DO. A pair shows disagreement; it does not measure it, and it cannot separate a geometry
# error from a lighting or material error. It is a way of deciding what to measure next, which is the step
# this model kept skipping.
#   python tools/pose_pair.py <out dir> <class> <frame> [<class> <frame> ...]
# It writes poses.json and the photo halves; the renderer runs separately and the pairs are composed by
# tools/pose_pair.py --compose <out dir>.
import json
import os
import sys

import cv2
import numpy as np

sys.path.insert(0, 'tools')
import underside_geom as U

O = np.array([-54.907447, -1.43545, 3.040286])
HU = np.array([0.975681, 0, 0.219196])
HD = np.array([0.219196, 0, -0.975681])
LONG = 1000


def turn_of(cam):
    """how a stored frame must be turned so world up points up, decided by the camera not by the clip"""
    C = cam.center
    a = cam.project(np.asarray([C + cam.R.T @ np.array([0, 0, 4.0])]))
    b = cam.project(np.asarray([C + cam.R.T @ np.array([0, 0, 4.0]) + np.array([0, 1.0, 0])]))
    dx, dy = float(b[0][0] - a[0][0]), float(b[1][0] - a[1][0])
    if abs(dx) > abs(dy):
        return 'cw' if dx < 0 else 'ccw'
    return 'none' if dy < 0 else 'flip'


def upright(im, cam):
    t = turn_of(cam)
    if t == 'cw':
        return cv2.rotate(im, cv2.ROTATE_90_CLOCKWISE)
    if t == 'ccw':
        return cv2.rotate(im, cv2.ROTATE_90_COUNTERCLOCKWISE)
    if t == 'flip':
        return cv2.rotate(im, cv2.ROTATE_180)
    return im


if sys.argv[1] == '--compose':
    outdir = sys.argv[2]
    jobs = json.load(open(os.path.join(outdir, 'poses.json'), encoding='utf-8'))
    for j in jobs:
        ph = cv2.imread(j['photo_up'])
        si = cv2.imread(j['out'])
        if ph is None or si is None:
            print('missing half for %s' % j['tag'])
            continue
        # THE SIM HALF IS NOT TURNED. It is rendered by a camera that is already the right way up; the
        # first version rotated it with the photo and laid the hall on its side. What has to match is the
        # RENDER SHAPE, so a frame whose world-up runs along the stored image column axis is rendered
        # width by height swapped, with the vertical field of view taken over the upright height.
        s = float(LONG) / max(ph.shape[:2])
        ph = cv2.resize(ph, None, fx=s, fy=s)
        si = cv2.resize(si, (ph.shape[1], ph.shape[0]))
        pad = np.zeros((ph.shape[0], 12, 3), np.uint8)
        pad[:] = (40, 40, 40)
        both = np.hstack([ph, pad, si])
        cv2.putText(both, 'PHOTO  %s %s' % (j['cls'], j['frame']), (10, 26),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.7, (60, 255, 60), 2, cv2.LINE_AA)
        cv2.putText(both, 'SIM, same camera', (ph.shape[1] + 22, 26),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.7, (60, 200, 255), 2, cv2.LINE_AA)
        cv2.putText(both, 'u %.1f  d %.1f  h %.2f  vfov %.0f' % (j['u'], j['d'], j['h_eye'], j['vfov']),
                    (10, both.shape[0] - 12), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 220, 255), 2, cv2.LINE_AA)
        dst = os.path.join(outdir, 'pair-%s.jpg' % j['tag'])
        cv2.imwrite(dst, both, [cv2.IMWRITE_JPEG_QUALITY, 92])
        print(dst)
    sys.exit(0)

outdir = sys.argv[1]
args = sys.argv[2:]
jobs = []
for i in range(0, len(args), 2):
    cls, frame = args[i], args[i + 1]
    cam, ip = U.load_class(cls)[frame]
    q = cam.center - O
    f = cam.R.T @ np.array([0, 0, 1.0])
    fu, fd, fh = float(f @ HU), float(f @ HD), float(f[1])
    horiz = float(np.hypot(fu, fd))
    pitch = float(np.degrees(np.arcsin(fh)))
    x0, y0, _ = cam.project(np.asarray([cam.center + f * 10]))
    x1, y1, _ = cam.project(np.asarray([cam.center + f * 10 + (cam.R.T @ np.array([1.0, 0, 0])) * 1]))
    fx = float(np.hypot(x1[0] - x0[0], y1[0] - y0[0])) * 10
    # THREE takes a VERTICAL fov over the render's height, and these frames are stored rotated, so the
    # render is made at the frame's own stored width and height and the fov taken over that height.
    turn = turn_of(cam)
    rw, rh = (int(cam.h), int(cam.w)) if turn in ('cw', 'ccw') else (int(cam.w), int(cam.h))
    vfov = float(2 * np.degrees(np.arctan(rh / 2 / fx)))
    tag = '%s-%s' % (cls, frame)
    im = cv2.imread(ip)
    up = os.path.join(outdir, 'photo-%s.jpg' % tag)
    cv2.imwrite(up, upright(im, cam), [cv2.IMWRITE_JPEG_QUALITY, 92])
    jobs.append({'tag': tag, 'cls': cls, 'frame': frame, 'out': os.path.join(outdir, 'sim-%s.jpg' % tag),
                 'photo_up': up, 'w': rw, 'h': rh, 'turn': turn, 'vfov': vfov,
                 'u': float(q @ HU), 'd': float(q @ HD), 'h_eye': float(q[1]),
                 'fu': fu / horiz, 'fd': fd / horiz, 'pitch': pitch})
    print('%-18s u %6.2f d %6.2f h %5.2f  pitch %+5.1f  vfov %.1f  render %dx%d  turn %s'
          % (tag, q @ HU, q @ HD, q[1], pitch, vfov, rw, rh, turn))
json.dump(jobs, open(os.path.join(outdir, 'poses.json'), 'w'), indent=1)
print('wrote %s' % os.path.join(outdir, 'poses.json'))
