# 2026-09-09: WHERE was clip 153148 shot? Five independent attempts to read the room from those frames all
# returned no number and disagreed about whether the camera stands inside the room behind the north wall or
# on the hall side of it, and the whole 13.55 ceiling rests on that answer. The register accepted 6 of 171
# frames; this prints where those six cameras stand and which way they look, in the hall's own frame.
#   python tools/b6g_where.py [model dir]
import sys, numpy as np, pycolmap
MODEL = sys.argv[1] if len(sys.argv) > 1 else 'E:/sitecapture-captures/ngv-video/balcony2-register/work/model-b6g-accepted'
O = np.array([-54.907447, -1.43545, 3.040286]); HU = np.array([0.975681, 0, 0.219196]); HD = np.array([0.219196, 0, -0.975681])
rec = pycolmap.Reconstruction(MODEL)
print('%d images, %d points' % (rec.num_images(), rec.num_points3D()))
print('%-18s %8s %8s %8s   %s' % ('frame', 'u', 'd', 'h', 'looking'))
us, ds, hs = [], [], []
for iid, im in sorted(rec.images.items(), key=lambda kv: kv[1].name):
    T = im.cam_from_world() if callable(im.cam_from_world) else im.cam_from_world
    R = T.rotation.matrix(); t = np.asarray(T.translation)
    C = -R.T @ t                                   # the camera centre in world
    f = R.T @ np.array([0, 0, 1.0])                # where it looks
    q = C - O
    u, d, h = float(q @ HU), float(q @ HD), float(q[1])
    fu, fd, fh = float(f @ HU), float(f @ HD), float(f[1])
    us.append(u); ds.append(d); hs.append(h)
    print('%-18s %8.2f %8.2f %8.2f   u %+.2f d %+.2f up %+.2f' % (im.name, u, d, h, fu, fd, fh))
if us:
    print('spread: u %.2f..%.2f   d %.2f..%.2f   h %.2f..%.2f' % (min(us), max(us), min(ds), max(ds), min(hs), max(hs)))
    print('the north wall inner face is d -0.09; the room behind it runs d -0.99 to -2.99 as built;')
    print('the hall floor is h 0, the upper balcony deck 8.34, the openings h 8.99-11.35.')
    inside = sum(1 for d in ds if d < -0.09)
    print('cameras with d < -0.09 (behind the north wall): %d of %d' % (inside, len(ds)))
