# A contact sheet of a balcony2 clip: every Nth extracted frame, 8 a row, frame index on each, for a real review.
#   python tools/balcony2_sheet.py <clip> <every> [start] [end]     e.g. b6 30
import sys, os
from PIL import Image, ImageDraw
ROOT = 'E:/sitecapture-captures/ngv-video/balcony2'; S = 'E:/sitecapture-captures/ngv-site/agent-ref-walls/shots/pose/'
t, every = sys.argv[1], int(sys.argv[2]); a = int(sys.argv[3]) if len(sys.argv) > 3 else 0; b = int(sys.argv[4]) if len(sys.argv) > 4 else 10**9
d = '%s/%s/images' % (ROOT, t); fs = [f for f in sorted(os.listdir(d)) if a <= int(f.split('_')[1][:6]) <= b][::every]
W, H, cols = 216, 384, 8; rows = (len(fs) + cols - 1) // cols
o = Image.new('RGB', (cols * W, rows * H), (20, 20, 20)); dr = ImageDraw.Draw(o)
for i, f in enumerate(fs):
    x, y = (i % cols) * W, (i // cols) * H
    o.paste(Image.open(d + '/' + f).resize((W, H)), (x, y)); dr.rectangle([x, y, x + 70, y + 16], fill=(0, 0, 0)); dr.text((x + 3, y + 2), f.split('_')[1][:6], fill=(255, 255, 0))
out = S + '%s-sheet-%d-%d.jpg' % (t, a, min(b, 10**6)); o.save(out, quality=80); print(out, len(fs), 'frames', o.size)
