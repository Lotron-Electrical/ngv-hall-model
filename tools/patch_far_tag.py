# 2026-09-09: give the far-edge collector and its fitter a TAG, so one ladder's rays cannot overwrite
# another's.
#
# tools/west_far.py writes <end>-far-rays.npy and tools/far_edge_range.py reads it. That was fine while
# there was one edge to find. There are now two on the same face at the same end: the balcony front top,
# already measured on 9.799 west and 9.865 east from a ladder spanning 8.20 to 10.00, and BELOW it the top
# of the solid upstand, which is a different edge with the same polarity and needs its own narrower ladder
# so the fan cannot reach the front. Two experiments, two files.
import io

a = 'tools/west_far.py'
s = io.open(a, encoding='utf-8').read()
if 'TAG' not in s:
    s = s.replace("END = os.environ.get('END', 'west')",
                  "END = os.environ.get('END', 'west')\n"
                  "# TAG separates one ladder's rays from another's on the same face, see "
                  "tools/patch_far_tag.py\nTAG = os.environ.get('TAG', '')")
    s = s.replace("np.save(os.path.join(OUT, END + '-far-rays.npy'), R)",
                  "np.save(os.path.join(OUT, '%s%s-far-rays.npy' % (END, TAG)), R)")
    io.open(a, 'w', encoding='utf-8', newline='\n').write(s)
    print('west_far.py tagged')
else:
    print('west_far.py already tagged')

b = 'tools/far_edge_range.py'
s = io.open(b, encoding='utf-8').read()
if 'TAG' not in s:
    s = s.replace("ends = os.environ.get('RAYS', 'west east').split()",
                  "ends = os.environ.get('RAYS', 'west east').split()\n"
                  "TAG = os.environ.get('TAG', '')\n"
                  "# HLO/HHI keep the RANSAC window on the same band the ladder was walked over, so a fit\n"
                  "# for the upstand cannot wander up onto the front edge already measured above it.\n"
                  "HLO = float(os.environ.get('HLO', '8.0'))\n"
                  "HHI = float(os.environ.get('HHI', '12.0'))")
    s = s.replace("        if not (uf - 3.0 < c[0] < uf + 3.0 and 8.0 < c[1] < 12.0):",
                  "        if not (uf - 3.0 < c[0] < uf + 3.0 and HLO < c[1] < HHI):")
    s = s.replace("    src = os.path.join(OUT, end + '-far-rays.npy')",
                  "    src = os.path.join(OUT, '%s%s-far-rays.npy' % (end, TAG))")
    io.open(b, 'w', encoding='utf-8', newline='\n').write(s)
    print('far_edge_range.py tagged')
else:
    print('far_edge_range.py already tagged')
