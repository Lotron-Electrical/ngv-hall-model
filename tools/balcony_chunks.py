# 2026-09-09. Lloyd: "4/5 had some frames of when I'm standing on the balcony and looking along it."
# A view ALONG a balcony is the only view in this archive that shows its SECTION: the parapet in the near
# field with the deck at its foot, the soffit overhead, the back wall behind. Every measurement taken so
# far has been of the balcony's FACE, seen from the hall floor forty metres away, and a face cannot tell
# you how deep a parapet is or how high the ceiling over the deck stands.
#
# So cut every clip into contact sheets dense enough that a run of a few seconds cannot fall between two
# samples, and go through all of them. 5,300 frames at a whole-clip stride walks past exactly the runs
# that matter, which is what happened on the first pass.
#   python tools/balcony_chunks.py <outdir>
import os
import sys

import cv2
import numpy as np

B2 = 'E:/sitecapture-captures/ngv-video/balcony2'
OUTDIR = sys.argv[1]
CELL = 300
PER = 48
COLS = 8
# stride per clip: the two long room-scan clips are sampled coarser, the short balcony clips at every
# other frame, because those are the ones Lloyd names
STRIDES = {'b1': 2, 'b3': 2, 'b4': 2, 'b5': 2, 'b6': 8, 'b7': 4}

os.makedirs(OUTDIR, exist_ok=True)
manifest = []
for clip, stride in sorted(STRIDES.items()):
    src = '%s/%s/images' % (B2, clip)
    if not os.path.isdir(src):
        continue
    names = sorted(n for n in os.listdir(src) if n.lower().endswith(('.png', '.jpg', '.jpeg')))
    pick = names[::stride]
    for ci in range(0, len(pick), PER):
        chunk = pick[ci:ci + PER]
        rows = (len(chunk) + COLS - 1) // COLS
        sheet = np.full((rows * (CELL + 24) + 8, COLS * (CELL + 8) + 8, 3), 18, np.uint8)
        for i, n in enumerate(chunk):
            im = cv2.imread(os.path.join(src, n))
            if im is None:
                continue
            s = CELL / float(max(im.shape[:2]))
            im = cv2.resize(im, (int(im.shape[1] * s), int(im.shape[0] * s)))
            r, c = divmod(i, COLS)
            y, x = 8 + r * (CELL + 24), 8 + c * (CELL + 8)
            sheet[y:y + im.shape[0], x:x + im.shape[1]] = im
            cv2.putText(sheet, n.rsplit('.', 1)[0], (x + 2, y + CELL + 17),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.46, (170, 220, 255), 1, cv2.LINE_AA)
        out = os.path.join(OUTDIR, 'sheet-%s-%02d.jpg' % (clip, ci // PER))
        cv2.imwrite(out, sheet, [cv2.IMWRITE_JPEG_QUALITY, 84])
        manifest.append((out, clip, chunk[0], chunk[-1], len(chunk)))
        print('%s  %s..%s  %d frames' % (out, chunk[0], chunk[-1], len(chunk)))
print('')
print('%d sheets over %d clips' % (len(manifest), len(STRIDES)))
