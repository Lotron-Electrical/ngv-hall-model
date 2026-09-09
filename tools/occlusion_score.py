# 2026-09-09: WHY THE LONGEST CLIP WOULD NOT REGISTER, and how to pick the frames that will.
# Clip 153148 (b6) is 2,666 frames, the longest in the archive, and the only part ever registered accepted
# 5 of 171. Looking at the raw frames says why in one glance: for most of the clip a SECOND PHONE is held
# up in shot, with a hand around it, and between them they cover a large part of the picture. Those pixels
# carry no hall features, they move independently of the camera, and their edges are strong, so they both
# starve the matcher and give it wrong correspondences.
# Nothing is wrong with the footage; the frames where the phone is out of shot or small are perfectly good.
# So score every frame by how much of it the hand and phone occupy, and offer the clean ones to the
# register instead of an arbitrary window. Two cheap cues on a 1/8-scale read, no model, no learning:
#   SKIN     a fraction of pixels inside a loose skin-tone envelope in YCrCb, which is what a hand is.
#   SCREEN   a bright, low-saturation blob far brighter than the frame's own median, which is what a lit
#            phone screen is in a dim hall. Only blobs of a plausible size count, so the stained glass and
#            the daylit floor do not read as screens.
# The score is the fraction of the frame those two cover together. Low is clean.
#   python tools/occlusion_score.py <clip dir> [out.csv]
import sys, os, csv
import numpy as np
import cv2

clip = sys.argv[1]
out = sys.argv[2] if len(sys.argv) > 2 else None
src = 'E:/sitecapture-captures/ngv-video/balcony2/%s/images' % clip
names = sorted(n for n in os.listdir(src) if n.lower().endswith('.png'))
print('%s: %d frames' % (clip, len(names)))

rows = []
for i, n in enumerate(names):
    im = cv2.imread(os.path.join(src, n), cv2.IMREAD_REDUCED_COLOR_8)
    if im is None: continue
    ycc = cv2.cvtColor(im, cv2.COLOR_BGR2YCrCb)
    cr, cb = ycc[:, :, 1].astype(np.int16), ycc[:, :, 2].astype(np.int16)
    y = ycc[:, :, 0].astype(np.int16)
    skin = np.logical_and.reduce([cr > 133, cr < 180, cb > 77, cb < 128, y > 40])
    hsv = cv2.cvtColor(im, cv2.COLOR_BGR2HSV)
    v, s = hsv[:, :, 2].astype(np.int16), hsv[:, :, 1].astype(np.int16)
    med = int(np.median(v))
    bright = np.logical_and(v > med + 60, s < 90).astype(np.uint8)
    # a phone screen is one compact blob, not the whole daylit half of the picture
    nlab, lab, stats, _ = cv2.connectedComponentsWithStats(bright, 8)
    px = im.shape[0] * im.shape[1]
    screen = np.zeros_like(bright)
    for k in range(1, nlab):
        a = stats[k, cv2.CC_STAT_AREA]
        if 0.01 * px < a < 0.30 * px:
            w, h = stats[k, cv2.CC_STAT_WIDTH], stats[k, cv2.CC_STAT_HEIGHT]
            if 0.25 < (w / max(h, 1)) < 4.0:
                screen[lab == k] = 1
    occ = float(np.logical_or(skin, screen > 0).mean())
    sharp = float(cv2.Laplacian(cv2.cvtColor(im, cv2.COLOR_BGR2GRAY), cv2.CV_32F).var())
    rows.append((n, occ, float(skin.mean()), float((screen > 0).mean()), sharp))
    if i % 400 == 0: print('  %d/%d' % (i, len(names)), flush=True)

occ = np.array([r[1] for r in rows])
print('occlusion: median %.3f  p10 %.3f  p90 %.3f  worst %.3f' % (np.median(occ), np.percentile(occ, 10), np.percentile(occ, 90), occ.max()))
for thr in (0.02, 0.05, 0.10, 0.20):
    print('  under %.0f%% of the frame occluded: %4d frames' % (thr * 100, int((occ <= thr).sum())))
if out:
    with open(out, 'w', newline='') as fh:
        w = csv.writer(fh); w.writerow(['name', 'occluded', 'skin', 'screen', 'sharpness'])
        for r in rows: w.writerow([r[0], '%.4f' % r[1], '%.4f' % r[2], '%.4f' % r[3], '%.1f' % r[4]])
    print('wrote', out)
