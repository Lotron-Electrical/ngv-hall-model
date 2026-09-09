# 2026-09-09. The contact sheets show what these clips are OF: the operator standing on a balcony aiming
# at the hall and the ceiling. The frames that show the balcony's own section are the few seconds at each
# end of a pan, and a whole-clip stride walks straight past them. This pulls one run of consecutive frames
# out of one clip at a size where a parapet, a deck and a soffit can actually be told apart.
#   python tools/balcony_look.py <clip> <first> <last> <step> <out.jpg> [cols]
import os
import sys

import cv2
import numpy as np

B2 = 'E:/sitecapture-captures/ngv-video/balcony2'
CLIP, A, B, STEP, OUT = sys.argv[1], int(sys.argv[2]), int(sys.argv[3]), int(sys.argv[4]), sys.argv[5]
COLS = int(sys.argv[6]) if len(sys.argv) > 6 else 4
CELL = int(os.environ.get('CELL', '460'))

src = '%s/%s/images' % (B2, CLIP)
names = sorted(n for n in os.listdir(src) if n.lower().endswith(('.png', '.jpg', '.jpeg')))


def num(n):
    return int(''.join(ch for ch in n.rsplit('.', 1)[0] if ch.isdigit())[-6:])


pick = [n for n in names if A <= num(n) <= B][::STEP]
rows = (len(pick) + COLS - 1) // COLS
sheet = None
for i, n in enumerate(pick):
    im = cv2.imread(os.path.join(src, n))
    if im is None:
        continue
    scale = CELL / float(max(im.shape[:2]))
    im = cv2.resize(im, (int(im.shape[1] * scale), int(im.shape[0] * scale)))
    if sheet is None:
        sheet = np.full((rows * (CELL + 24) + 8, COLS * (CELL + 8) + 8, 3), 18, np.uint8)
    r, c = divmod(i, COLS)
    y, x = 8 + r * (CELL + 24), 8 + c * (CELL + 8)
    sheet[y:y + im.shape[0], x:x + im.shape[1]] = im
    cv2.putText(sheet, '%s %06d' % (CLIP, num(n)), (x + 2, y + CELL + 17),
                cv2.FONT_HERSHEY_SIMPLEX, 0.5, (170, 220, 255), 1, cv2.LINE_AA)
cv2.imwrite(OUT, sheet, [cv2.IMWRITE_JPEG_QUALITY, 86])
print('%s %d..%d step %d: %d frames -> %s %s' % (CLIP, A, B, STEP, len(pick), OUT, sheet.shape))
