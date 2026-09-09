# 2026-09-09 (Lloyd: "I gave some specific video references yesterday that has clips from standing on each
# of the balconies and looking around"). He is right that the balconies were not got properly, and the
# reason is not the footage. Of 940 frames offered across the four clips that were tried, 803 SOLVED A POSE
# and only 102 were accepted. The loss is entirely in the acceptance gate, in three places:
#
#  1. INLIERS >= 30. These clips look at a wall 15-40 m away across a hall whose reconstruction is sparse
#     up there, so a perfectly good balcony pose often carries 12-25 inliers where a floor walk carries
#     hundreds. The threshold was set for floor walks. Measured on the registered frames: b3's median is
#     21 inliers, b6g's is 14, b7s's is 12. A cut of 30 refuses the MEDIAN FRAME of three of the four clips.
#
#  2. THE STANDING BANDS. A frame is refused unless the camera sits 0.8-2.3 m (hall floor) or 8.73-10.23 m
#     (upper deck 8.34). There is NO BAND FOR THE LOWER BALCONY. Its floor is 6.33, so a person standing on
#     it holds a phone near 7.5-8.1 m, which falls between the two bands and is refused by construction.
#     Lloyd filmed from each balcony; every lower-balcony frame was thrown away before it was ever looked at.
#
#  3. THE CONTINUITY RULE, which is the biggest single loss and is wrong in principle here. It refuses a
#     frame when the implied speed from its immediate neighbour exceeds a walking speed. That suits a
#     person walking the floor with every frame tracked. On a balcony the operator STANDS STILL AND PANS,
#     and once some frames are refused the chain jumps between survivors, so ordinary standing motion reads
#     as impossible speed. It killed 83 of b1's 142 otherwise-good frames, 58 percent of them.
#
# This re-gates from the reports alone. Every registered frame already carries its inliers, rms, camera
# height and camera centre, so nothing is re-registered and no COLMAP time is spent. The continuity rule is
# replaced by a proper outlier test: a frame is refused only when its centre sits far from the ROBUST LOCAL
# MEDIAN of the frames around it in time, which tolerates a stationary operator and still catches a wild
# pose. Nothing here loosens rms.
#   python tools/regate.py [reports dir] [min inliers] [--json out.json]
import sys, os, json, glob
import numpy as np

D = sys.argv[1] if len(sys.argv) > 1 else 'E:/sitecapture-captures/ngv-video/balcony2-register/reports'
MININL = int(sys.argv[2]) if len(sys.argv) > 2 and not sys.argv[2].startswith('--') else 15

# where a person can actually stand in this hall, and what that puts the phone at.
# floors: the hall 0, the lower balcony 6.33, the upper balcony and the north gallery 8.34.
# a phone is carried 1.1 to 1.9 m above the feet, which is deliberately generous: the point of the band is
# to refuse a pose floating in mid air, not to second-guess how somebody held their phone.
FLOORS = [('hall floor', 0.0), ('lower balcony', 6.33), ('upper balcony', 8.34)]
LOW, HIGH = 1.10, 1.90
BANDS = [(nm, f + LOW, f + HIGH) for nm, f in FLOORS]

def band_of(h):
    for nm, a, b in BANDS:
        if a <= h <= b: return nm
    return None

WINDOW_S = 2.0        # how far either side in time the local median is taken over
JUMP_M = 1.20         # how far a frame may sit from that median before it is called an outlier
SPEED_MS = 1.60       # plus what an operator could genuinely cover in the time gap

out = {}
for f in sorted(glob.glob(os.path.join(D, '*.json'))):
    r = json.load(open(f))
    if 'prefix' not in r or 'gate' not in r: continue
    g = r['gate']; rms_max = g.get('max_rms', 3.0)
    rows = r.get('frames') or r.get('rows') or []
    if not rows: continue
    fps = r.get('fps') or 30.0
    every = r.get('every') or 2

    def tof(name):
        try: return every * int(name.split('_')[1].split('.')[0]) / fps
        except Exception: return 0.0

    cand = []
    for x in rows:
        if not x.get('registered'): continue
        if x.get('inliers', 0) < MININL: continue
        if x.get('rms', 99) > rms_max: continue
        h = x.get('height_m')
        if h is None: continue
        b = band_of(h)
        if b is None: continue
        c = x.get('centre')
        if not c: continue
        cand.append(dict(name=x['name'], t=tof(x['name']), c=np.array(c, float),
                         h=h, band=b, inl=x.get('inliers', 0), rms=x.get('rms', 0)))
    cand.sort(key=lambda z: z['t'])
    kept = []
    for i, z in enumerate(cand):
        near = [w for w in cand if w is not z and abs(w['t'] - z['t']) <= WINDOW_S]
        if len(near) < 2:
            kept.append(z); continue          # nothing to compare against: keep it, the gate above stands
        med = np.median(np.stack([w['c'] for w in near]), axis=0)
        dt = float(np.median([abs(w['t'] - z['t']) for w in near]))
        if float(np.linalg.norm(z['c'] - med)) <= JUMP_M + SPEED_MS * dt:
            kept.append(z)
    was = sum(1 for x in rows if x.get('accepted'))
    bands = {}
    for z in kept: bands[z['band']] = bands.get(z['band'], 0) + 1
    print('%-5s offered %4d  solved %4d  was accepted %3d  ->  NOW %3d   %s'
          % (r['prefix'], len(rows), sum(1 for x in rows if x.get('registered')), was, len(kept),
             ', '.join('%s %d' % (k, v) for k, v in sorted(bands.items()))))
    if kept:
        hs = sorted(z['h'] for z in kept)
        print('        camera heights %.2f to %.2f m; inliers median %d; rms median %.2f'
              % (hs[0], hs[-1], int(np.median([z['inl'] for z in kept])), float(np.median([z['rms'] for z in kept]))))
    out[r['prefix']] = [z['name'] for z in kept]

print('')
print('TOTAL now %d frames against the %d that were accepted before'
      % (sum(len(v) for v in out.values()), 102))
if '--json' in sys.argv:
    p = sys.argv[sys.argv.index('--json') + 1]
    json.dump(out, open(p, 'w'), indent=1)
    print('wrote', p)
