# 2026-09-09: write the re-gated frame sets out as COLMAP models, so the MEASUREMENTS can judge whether the
# re-gate was right. tools/regate.py lifts the four balcony clips from 102 accepted frames to 296 by fixing
# three faults in the acceptance gate, but a looser gate that admits bad poses is worse than a tight one
# that admits few. The honest test is not to look at the poses, it is to re-run the balcony levels through
# them and see whether the pooled numbers TIGHTEN or SCATTER. Junk poses scatter.
# Nothing is re-registered: reg-<prefix> already holds every solved frame, so this only subsets it.
#   python tools/regate_export.py [reports dir]
import sys, os, json, shutil, glob
import pycolmap

WS = 'E:/sitecapture-captures/ngv-video/balcony2-register'
D = sys.argv[1] if len(sys.argv) > 1 else WS + '/reports'
sel = json.load(open(os.environ.get('REGATE_JSON', WS + '/regated.json')))

for prefix, names in sorted(sel.items()):
    src = os.path.join(WS, 'work', 'reg-' + prefix)
    if not os.path.isdir(src):
        print('%-5s no reg model' % prefix); continue
    keep = set(names)
    rec = pycolmap.Reconstruction(src)
    drop = [iid for iid, im in rec.images.items() if im.name not in keep]
    for iid in drop:
        try: rec.deregister_frame(rec.images[iid].frame_id)
        except Exception: pass
    dst = os.path.join(WS, 'work', 'model-%s-regated' % prefix)
    os.makedirs(dst, exist_ok=True)
    rec.write(dst)
    # the colour frames the measuring tools read, named exactly as the model names them
    isrc = os.path.join(WS, 'images-colour')
    idst = os.path.join(WS, 'images-colour-%s-regated' % prefix)
    os.makedirs(idst, exist_ok=True)
    n = 0
    for nm in keep:
        a = os.path.join(isrc, nm)
        b = os.path.join(idst, nm)
        if os.path.exists(b): n += 1; continue
        if os.path.exists(a):
            shutil.copyfile(a, b); n += 1
    print('%-5s wrote %d images to the model, %d colour frames in place' % (prefix, rec.num_reg_images(), n))
