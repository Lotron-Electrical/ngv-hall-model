# A strip of frames from one balcony2 clip over a frame range, to read a stretch of it.
#   python tools/balcony2_strip.py <tag> <first> <last> <count> <out_name>
import sys
from PIL import Image
ROOT = 'E:/sitecapture-captures/ngv-video/balcony2'; S = 'E:/sitecapture-captures/ngv-site/agent-ref-walls/shots/pose/'
t, a, b, n, out = sys.argv[1], int(sys.argv[2]), int(sys.argv[3]), int(sys.argv[4]), sys.argv[5]
picks = [a + int(i * (b - a) / max(n - 1, 1)) for i in range(n)]
cols = min(n, 8); rows = (n + cols - 1) // cols
o = Image.new('RGB', (cols * 216, rows * 384))
for i, k in enumerate(picks):
    o.paste(Image.open('%s/%s/images/%s_%06d.png' % (ROOT, t, t, k)).resize((216, 384)), ((i % cols) * 216, (i // cols) * 384))
o.save(S + out + '.jpg', quality=85); print(out, picks)
