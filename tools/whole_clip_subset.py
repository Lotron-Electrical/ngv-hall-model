# 2026-09-09 (Lloyd: the clips are "from standing on each of the balconies and looking around").
# The two long clips have barely been touched, and the reason is that the subsets taken from them were
# WINDOWS, not samples. b6g is frames 1000-1340 of clip 153148, a 340-frame window out of 2,666, and it
# found the east balcony because that is where the operator happened to be during those twelve seconds.
# b7s is a 306-frame subset of clip 154940's 1,224. Everything outside those windows has never been offered
# to the register at all, and that is where the LOWER balconies will be: the re-gate found not one frame in
# the whole archive standing on the lower deck (6.33), yet Lloyd filmed from each balcony.
# So sample the WHOLE clip evenly instead of cutting a window out of it. Same number of frames and the same
# matching cost, but every part of the walk gets a chance to register.
#   python tools/whole_clip_subset.py <src clip dir> <dst prefix> <keep every Nth>
import sys, os, shutil

src, dstpref, every = sys.argv[1], sys.argv[2], int(sys.argv[3])
B2 = 'E:/sitecapture-captures/ngv-video/balcony2'
sdir = os.path.join(B2, src, 'images')
ddir = os.path.join(B2, dstpref, 'images')
os.makedirs(ddir, exist_ok=True)
names = sorted(n for n in os.listdir(sdir) if n.lower().endswith('.png'))
print('%s: %d frames, taking every %d' % (src, len(names), every))
n = 0
for i, nm in enumerate(names):
    if i % every: continue
    idx = nm.rsplit('.', 1)[0].split('_')[1]
    out = '%s_%s.png' % (dstpref, idx)
    b = os.path.join(ddir, out)
    if not os.path.exists(b):
        shutil.copyfile(os.path.join(sdir, nm), b)
    n += 1
print('%s: %d frames spanning the whole clip, %s .. %s' % (dstpref, n, names[0], names[-1]))
