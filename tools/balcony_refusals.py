# 2026-09-09: WHY THE BALCONY CLIPS ONLY EVER KEEP THE FRAMES THAT LOOK DOWN THE HALL.
# Lloyd, on seeing b5's 24 accepted poses: "those frames are me looking at the hall. but they should be
# more frames when I look around the actual balcony area." He is right, and the reports say so themselves:
# b5 offered 287 frames, SOLVED 242 of them, and accepted 24. The loss is not in the solving.
# This prints, per clip, exactly which rule refused each solved frame, and where those cameras stood and
# looked, so the refusals can be read as a pattern rather than a total.
import json
import numpy as np

REPORTS = [
    ('b5', 'E:/sitecapture-captures/ngv-video/balcony2-register/reports/b5.json'),
    ('b1', 'E:/sitecapture-captures/ngv-video/balcony2-register/reports/b1.json'),
    ('b3', 'E:/sitecapture-captures/ngv-video/balcony2-register/reports/b3.json'),
    ('b7s', 'E:/sitecapture-captures/ngv-video/balcony2-register/reports/b7s.json'),
    ('b6g', 'E:/sitecapture-captures/ngv-video/balcony2-register/reports/b6g.json'),
]

for name, path in REPORTS:
    try:
        j = json.load(open(path))
    except Exception as e:
        print(name, 'no report', e)
        continue
    fr = j['frames']
    reg = [f for f in fr if f.get('registered')]
    refused = [f for f in reg if not f.get('accepted')]
    print('=====', name, 'offered', j['offered'], 'solved', j['registered'], 'accepted', j['accepted'])
    tally = {}
    for f in refused:
        w = f.get('why') or 'no reason given'
        tally[w] = tally.get(w, 0) + 1
    for w in sorted(tally, key=lambda k: -tally[k])[:10]:
        print('   refused', tally[w], w)
    hs = np.array([f['height_m'] for f in reg if 'height_m' in f])
    if hs.size:
        qs = [round(float(x), 2) for x in np.percentile(hs, [10, 25, 50, 75, 90])]
        print('   solved camera heights', round(float(hs.min()), 2), 'to', round(float(hs.max()), 2), 'deciles', qs)
    ha = np.array([f['height_m'] for f in reg if f.get('accepted') and 'height_m' in f])
    if ha.size:
        print('   accepted camera heights', round(float(ha.min()), 2), 'to', round(float(ha.max()), 2))
    inl = np.array([f['inliers'] for f in reg if 'inliers' in f], dtype=float)
    if inl.size:
        print('   solved inliers deciles', [int(x) for x in np.percentile(inl, [10, 25, 50, 75, 90])])
    print('')
