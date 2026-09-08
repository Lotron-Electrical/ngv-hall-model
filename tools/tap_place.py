# Put the four tapestries where the orthophotos measure them (tools/tap_id.py NCC boxes, 16 mm/px):
# rewrite the corners in tools/tapestries.json in the hall frame, keeping each one's d.
import json, numpy as np
O = np.array([-54.907447, -1.43545, 3.040286]); HU = np.array([0.975681, 0, 0.219196]); HD = np.array([0.219196, 0, -0.975681])
boxes = {'north-1': (8.20, 14.05, 3.35, 8.34), 'north-2': (37.84, 43.31, 3.35, 8.31), 'south-1': (8.52, 13.97, 3.67, 8.63), 'south-2': (38.18, 43.52, 3.50, 8.50)}
p = 'tools/tapestries.json'; doc = json.load(open(p, encoding='utf-8'))
for t in doc['tapestries']:
    c = np.array(t['corners']); q = c - O; dd = float(np.mean(q @ HD)); us = q @ HU; hs = q[:, 1]
    u0, u1, h0, h1 = boxes[t['position']]
    # keep the corner order: each old corner maps to the nearest new corner by (u, h) rank
    new = []
    for i in range(4):
        uu = u0 if us[i] < np.mean(us) else u1; hh_ = h0 if hs[i] < np.mean(hs) else h1
        new.append((O + uu * HU + dd * HD + np.array([0, hh_, 0])).round(4).tolist())
    print(t['position'], 'u %.2f-%.2f h %.2f-%.2f -> u %.2f-%.2f h %.2f-%.2f d %.3f' % (us.min(), us.max(), hs.min(), hs.max(), u0, u1, h0, h1, dd))
    t['corners'] = new
    t['placement'] = 'ortho NCC 2026-09-08 (agent-ref-walls, tools/tap_id.py): box u %.2f-%.2f h %.2f-%.2f, +-0.05 m' % (u0, u1, h0, h1)
json.dump(doc, open(p, 'w', encoding='utf-8'), indent=1)
print('written', p)
