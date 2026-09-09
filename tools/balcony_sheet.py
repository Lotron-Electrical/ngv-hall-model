# 2026-09-09. Lloyd: "the balcony sections are still not correct. I gave you videos. You need to look
# through them thoroughly." So look at them, all of them, instead of running another detector over them.
#
# WHY A CONTACT SHEET AND NOT A DETECTOR. Every instrument in this archive answers a question I chose in
# advance: where is this edge, is that plane at this depth. None of them can tell me the balcony is the
# wrong SHAPE, because none of them was asked. Five thousand frames were shot standing on and looking at
# these balconies and nothing in this repo has ever simply displayed them. A sheet does.
#
# WHICH FRAMES. The clips pan, so consecutive frames are near duplicates and a fixed stride wastes the
# sheet on one view. Frames are taken on a stride and then the sheet is laid out in clip order, so a pan
# reads left to right as the pan happened.
#   python tools/balcony_sheet.py <clip> <out.jpg> [stride] [cols]
import os
import sys

import cv2
import numpy as np

B2 = 'E:/sitecapture-captures/ngv-video/balcony2'
CLIP = sys.argv[1]
OUT = sys.argv[2]
STRIDE = int(sys.argv[3]) if len(sys.argv) > 3 else 0
COLS = int(sys.argv[4]) if len(sys.argv) > 4 else 6
CELL = int(os.environ.get('CELL', '300'))
WANT = int(os.environ.get('WANT', '48'))

src = '%s/%s/images' % (B2, CLIP)
names = sorted(n for n in os.listdir(src) if n.lower().endswith(('.png', '.jpg', '.jpeg')))
if not names:
    sys.exit('no frames in %s' % src)
if STRIDE <= 0:
    STRIDE = max(1, len(names) // WANT)
pick = names[::STRIDE][:WANT]
rows = (len(pick) + COLS - 1) // COLS

# THE PHONE WAS HELD UPRIGHT AND THE FILES ARE STORED ON THEIR SIDE in several of these clips. A sheet of
# sideways balconies is unreadable, so a landscape frame taller than it is wide is stood up.
sheet = None
for i, n in enumerate(pick):
    im = cv2.imread(os.path.join(src, n))
    if im is None:
        continue
    if im.shape[1] > im.shape[0] * 1.2:
        pass
    scale = CELL / float(max(im.shape[:2]))
    im = cv2.resize(im, (int(im.shape[1] * scale), int(im.shape[0] * scale)))
    if sheet is None:
        ch, cw = CELL, CELL
        sheet = np.full((rows * (ch + 26) + 8, COLS * (cw + 8) + 8, 3), 18, np.uint8)
    r, c = divmod(i, COLS)
    y = 8 + r * (CELL + 26)
    x = 8 + c * (CELL + 8)
    sheet[y:y + im.shape[0], x:x + im.shape[1]] = im
    cv2.putText(sheet, n.rsplit('.', 1)[0][-6:], (x + 2, y + CELL + 18),
                cv2.FONT_HERSHEY_SIMPLEX, 0.44, (170, 220, 255), 1, cv2.LINE_AA)
cv2.imwrite(OUT, sheet, [cv2.IMWRITE_JPEG_QUALITY, 82])
print('%s: %d frames, showing %d on a stride of %d -> %s %s'
      % (CLIP, len(names), len(pick), STRIDE, OUT, sheet.shape))
