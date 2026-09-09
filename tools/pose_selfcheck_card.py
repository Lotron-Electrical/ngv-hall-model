# 2026-09-09: THE POSE SELF-CHECK AS ONE PHONE-SIZED CARD.
#
# The table tools/pose_selfcheck.py prints is the single most useful number in the archive for judging any
# other number, so it should be readable without a terminal. One row per clip, the median distance by which
# its own matched rays miss each other in the near field, and the line that says what that buys.
#   python tools/pose_selfcheck_card.py
import os

import cv2
import numpy as np

OUT = 'E:/sitecapture-captures/ngv-site/agent-ref-walls/shots/pose'
ROWS = [('b1', 0.061, 'stands in north opening 5'),
        ('b1p', 0.068, 'the same clip, pan-chained'),
        ('b3', 0.099, 'walks the east top gallery'),
        ('b3p', 0.123, 'the same walk, pan-chained'),
        ('b4', 0.067, 'stands in north opening 11'),
        ('b5', 0.066, 'stands in north opening 6'),
        ('b5p', 0.069, 'the same, pan-chained'),
        ('b7sp', 0.109, 'both end decks, pan-chained'),
        ('b7s', 0.173, 'both end decks, accepted'),
        ('b6g', 0.179, 'six frames, 7 to 9 inliers'),
        ('b6gp', 0.200, 'the same six, pan-chained')]
W, ROW, TOP = 1080, 78, 250
im = np.full((TOP + ROW * len(ROWS) + 190, W, 3), 20, np.uint8)
cv2.putText(im, 'HOW FAR APART EACH CLIP MISSES ITSELF', (54, 74),
            cv2.FONT_HERSHEY_SIMPLEX, 0.82, (240, 240, 240), 2, cv2.LINE_AA)
for i, t in enumerate(['match a clip to its own frames, meet every pair of rays,',
                       'and measure how far apart they pass under 6 m.',
                       'that distance is the pose error, in metres.']):
    cv2.putText(im, t, (54, 126 + i * 38), cv2.FONT_HERSHEY_SIMPLEX, 0.56, (185, 185, 185), 1, cv2.LINE_AA)

SCALE = (W - 470) / 0.22
for i, (name, miss, note) in enumerate(ROWS):
    y = TOP + i * ROW
    col = (110, 240, 130) if miss < 0.10 else ((90, 200, 255) if miss < 0.16 else (90, 120, 255))
    cv2.rectangle(im, (330, y - 26), (330 + int(miss * SCALE), y + 12), col, -1)
    cv2.putText(im, name, (54, y + 6), cv2.FONT_HERSHEY_SIMPLEX, 0.72, (240, 240, 240), 2, cv2.LINE_AA)
    cv2.putText(im, '%.3f m' % miss, (170, y + 6), cv2.FONT_HERSHEY_SIMPLEX, 0.66, col, 2, cv2.LINE_AA)
    cv2.putText(im, note, (344 + int(miss * SCALE), y + 6), cv2.FONT_HERSHEY_SIMPLEX, 0.46,
                (170, 170, 170), 1, cv2.LINE_AA)

y = TOP + ROW * len(ROWS) + 44
for t, col in (('green: good enough to measure a surface a metre away', (110, 240, 130)),
               ('amber: the west parapet result lives here, so it is a', (90, 200, 255)),
               ('       suspicion and not a defect', (90, 200, 255)),
               ('red: nothing should rest on these six frames', (90, 120, 255))):
    cv2.putText(im, t, (54, y), cv2.FONT_HERSHEY_SIMPLEX, 0.55, col, 1, cv2.LINE_AA)
    y += 36
os.makedirs(OUT, exist_ok=True)
dst = os.path.join(OUT, 'pose-selfcheck.jpg')
cv2.imwrite(dst, im, [cv2.IMWRITE_JPEG_QUALITY, 90])
print(dst, im.shape)
