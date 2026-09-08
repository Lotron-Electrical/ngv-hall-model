# A thinned frame set of a long balcony2 clip for the register (SIFT on a 4K frame costs about 7 s): every Nth
# extracted frame, plus every Mth inside a dense range. Files keep their frame numbers (the register reads the
# clock from the index) under the tag with an s appended.
#   python tools/balcony2_subset.py <tag> <step> [<dense_first> <dense_last> <dense_step>]
import sys, os, shutil
ROOT = 'E:/sitecapture-captures/ngv-video/balcony2'
t, step = sys.argv[1], int(sys.argv[2]); dense = [int(x) for x in sys.argv[3:6]] if len(sys.argv) > 5 else None
src = '%s/%s/images' % (ROOT, t); dst = '%s/%ss/images' % (ROOT, t); os.makedirs(dst, exist_ok=True)
names = sorted(os.listdir(src)); keep = []
for i, n in enumerate(names):
    if i % step == 0 or (dense and dense[0] <= i <= dense[1] and (i - dense[0]) % dense[2] == 0): keep.append(n)
for n in keep:
    o = os.path.join(dst, n.replace(t + '_', t + 's_'))
    if not os.path.exists(o): shutil.copy2(os.path.join(src, n), o)
print(t + 's', len(keep), 'of', len(names))
