# 2026-09-09: one table of what the pan chaining actually delivered per clip, and how well it validated.
import json
import os

CLIPS = [
    ('b5', 'E:/sitecapture-captures/ngv-video/balcony2-register/work/model-b5-pan/pan-quality.json'),
    ('b1', 'E:/sitecapture-captures/ngv-video/balcony2-register/work/model-b1-pan/pan-quality.json'),
    ('b3', 'E:/sitecapture-captures/ngv-video/balcony2-register/work/model-b3-pan/pan-quality.json'),
    ('b7s', 'E:/sitecapture-captures/ngv-video/balcony2-register/work/model-b7s-pan/pan-quality.json'),
    ('b6g', 'E:/sitecapture-captures/ngv-video/balcony2-register/work/model-b6g-pan/pan-quality.json'),
]
print('clip  offered anchors  new  total   rot deg   centre m   centre p90')
tot_a, tot_n = 0, 0
for name, path in CLIPS:
    if not os.path.exists(path):
        print(name, 'no output')
        continue
    j = json.load(open(path))
    tot_a += j['anchors']
    tot_n += j['posed']
    print(name.ljust(5), str(j['offered']).rjust(7), str(j['anchors']).rjust(7), str(j['posed']).rjust(5),
          str(j['anchors'] + j['posed']).rjust(6), str(j.get('holdout_still_rot_deg_median')).rjust(9),
          str(j.get('centre_leave_one_out_m_median')).rjust(10), str(j.get('centre_leave_one_out_m_p90')).rjust(11))
print('')
print('anchors', tot_a, 'plus newly posed', tot_n, 'gives', tot_a + tot_n, 'balcony poses against', tot_a, 'before')
