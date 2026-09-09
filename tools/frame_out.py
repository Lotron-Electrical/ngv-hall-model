# Pull named raw frames out of Lloyd's balcony clips, big enough for a reader to judge, because a 300 px
# thumbnail on a contact sheet can tell you a balcony is in shot and cannot tell you how its parapet is
# built.
#   python tools/frame_out.py <outdir> <clip> <frame> [<frame> ...]
# Frames may be given as bare numbers (214) or names (b4_000214). Writes <outdir>/<clip>_<nnnnnn>.jpg,
# 1100 px on the long side, and prints each path.
import os
import sys

import cv2

B2 = 'E:/sitecapture-captures/ngv-video/balcony2'
LONG = int(os.environ.get('LONG', '1100'))
outdir, clip = sys.argv[1], sys.argv[2]
if not os.path.isdir(outdir):
    os.makedirs(outdir)
src = '%s/%s/images' % (B2, clip)
names = sorted(n for n in os.listdir(src) if n.lower().endswith(('.png', '.jpg', '.jpeg')))
by_num = {}
for n in names:
    digits = ''.join(ch for ch in n.rsplit('.', 1)[0] if ch.isdigit())
    by_num[int(digits[-6:])] = n
for arg in sys.argv[3:]:
    d = ''.join(ch for ch in arg if ch.isdigit())
    if not d:
        print('skip %s' % arg)
        continue
    k = int(d[-6:])
    if k not in by_num:
        near = min(by_num, key=lambda z: abs(z - k))
        print('%s not extracted; nearest is %d' % (arg, near))
        continue
    im = cv2.imread(os.path.join(src, by_num[k]))
    if im is None:
        print('unreadable %s' % by_num[k])
        continue
    s = LONG / float(max(im.shape[:2]))
    if s < 1.0:
        im = cv2.resize(im, (int(im.shape[1] * s), int(im.shape[0] * s)))
    out = os.path.join(outdir, '%s_%06d.jpg' % (clip, k))
    cv2.imwrite(out, im, [cv2.IMWRITE_JPEG_QUALITY, 92])
    print(out)
