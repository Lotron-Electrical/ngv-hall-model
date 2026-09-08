# Six evenly spaced frames of a balcony2 clip in one strip, to see what the clip covers.
#   python tools/balcony2_montage.py b3 [b4 ...]
import sys, os
from PIL import Image
ROOT = 'E:/sitecapture-captures/ngv-video/balcony2'; S = 'E:/sitecapture-captures/ngv-site/agent-ref-walls/shots/pose/'
for t in sys.argv[1:]:
    d = '%s/%s/images' % (ROOT, t); fs = sorted(os.listdir(d)); n = len(fs)
    picks = [fs[int(i * (n - 1) / 5)] for i in range(6)]
    o = Image.new('RGB', (6 * 270, 480))
    for i, f in enumerate(picks): o.paste(Image.open(d + '/' + f).resize((270, 480)), (i * 270, 0))
    o.save(S + t + '-montage.jpg', quality=85); print(t, n, picks)
