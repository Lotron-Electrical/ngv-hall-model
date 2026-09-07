"""Which bay is this photograph of? Locate a rectified ceiling photograph on the plate.

A straight-up photograph of the canopy shows one crest node with its four sub-squares round it, but
nothing in the frame says WHICH of the twelve interior crest nodes it is, or which way up. The bake
ortho (trackB/bottom-ortho-v29.png) is blurry but it is real and it covers the whole plate, and the
glass palette is regional (reference-stats: lf02's area is pastel blue / lilac / amber, the close-ups'
area red / magenta), so a blurred colour layout is a fingerprint. This matches the rectified photo
against every candidate placement (crest node x the four in-plane symmetries that keep the ridges on
the ridges) by normalised cross-correlation of the Gaussian-blurred Lab channels, and prints the
ranking with the margin between first and second. A margin under ~0.05 means the placement is NOT
determined and the photo must not be registered by this alone.

The photograph is rectified from its own steel: the caller passes the pixel positions of the members
(the three vertical and three horizontal lines through the frame, centre px) and their huv meaning;
a linear fit px -> metres per axis is enough at the 20 mm/px this works at (perspective in a
straight-up shot of a 0.86 m relief is a few percent at the corners and the blur eats it).

    python tools/ceiling_locate.py --photo <jpg> --xs 169,636.5,1109 --ys 22,493.75,960 \
        --xm -3.7035,0,3.7035 --ym -3.7035,0,3.7035 [--sigma-mm 100] [--mpp 20]

xm/ym are the member positions in metres relative to the centre node (0 = the crest node itself).
"""
import argparse
import json
import os

import cv2
import numpy as np
from PIL import Image

Image.MAX_IMAGE_PIXELS = None
TRACKB = 'E:/sitecapture-captures/ngv-site/agent-ref-ceiling/trackB'


def load_ortho(tag='-v29'):
    meta = json.load(open(f'{TRACKB}/bottom-meta{tag}.json'))
    img = np.array(Image.open(f'{TRACKB}/bottom-ortho{tag}.png').convert('RGB'))
    return img, meta


def candidate_nodes(meta, centre):
    """The places a photo's central crossing can be on the OLD lattice the ortho is drawn on.
    centre='vertex': the twelve funnel vertices (column heads, the + cross of wide members meets
    there); centre='crest': the six interior crest nodes on the mid ridge (the corners shared by four
    bays). The reading of lf02 changed on 2026-09-08: its heavy members are the cross members through
    a vertex (the relief perspective a crest-centred reading predicts, 37 px of tilt on the light
    lines, is not in the photo), so vertex is the default."""
    lat = meta['lattice']
    PU, PV = lat['PU'], lat['PV']
    hu_c0 = -52.920875
    hv_c0 = 3.851570
    nodes = []
    if centre == 'crest':
        for i in range(6):
            nodes.append((f'crest{i}', hu_c0 + (i + 0.5) * PU, hv_c0 + 0.5 * PV))
    else:
        for i in range(7):
            for j in range(2):
                nodes.append((f'V{i}{"S" if j == 0 else "N"}', hu_c0 + i * PU, hv_c0 + j * PV))
    return nodes, PU, PV


def rectify(photo, xs, ys, xm, ym, mpp_mm):
    """Resample the photo onto a metric raster centred on the node: (u, v) metres -> pixel by the
    linear fits x = a*u + b, y = c*v + d from the member positions."""
    a, b = np.polyfit(xm, xs, 1)
    c, d = np.polyfit(ym, ys, 1)
    h, w = photo.shape[:2]
    # the metric window the photo covers
    u0, u1 = (0 - b) / a, (w - b) / a
    v0, v1 = (0 - d) / c, (h - d) / c
    u_lo, u_hi = min(u0, u1), max(u0, u1)
    v_lo, v_hi = min(v0, v1), max(v0, v1)
    W = int((u_hi - u_lo) * 1000 / mpp_mm)
    H = int((v_hi - v_lo) * 1000 / mpp_mm)
    uu = u_lo + (np.arange(W) + 0.5) * mpp_mm / 1000
    vv = v_lo + (np.arange(H) + 0.5) * mpp_mm / 1000
    mx = (a * uu + b).astype(np.float32)[None, :].repeat(H, 0)
    my = (c * vv + d).astype(np.float32)[:, None].repeat(W, 1)
    out = cv2.remap(photo, mx, my, cv2.INTER_AREA, borderMode=cv2.BORDER_CONSTANT, borderValue=0)
    valid = cv2.remap(np.full((h, w), 255, np.uint8), mx, my, cv2.INTER_NEAREST, borderMode=cv2.BORDER_CONSTANT, borderValue=0) > 0
    return out, valid, (u_lo, v_lo)


def lab_blur(img, sigma_px):
    lab = cv2.cvtColor(img, cv2.COLOR_RGB2LAB).astype(np.float32)
    return np.stack([cv2.GaussianBlur(lab[..., k], (0, 0), sigma_px) for k in range(3)], -1)


def ncc(a, b, m):
    a = a[m]; b = b[m]
    a = a - a.mean(); b = b - b.mean()
    den = np.sqrt((a * a).sum() * (b * b).sum())
    return float((a * b).sum() / den) if den > 0 else 0.0


def symmetries():
    # the ridges must land on the ridges: only the dihedral moves that keep the axes are allowed
    return {
        'id': lambda x: x,
        'flipLR': lambda x: x[:, ::-1],
        'flipUD': lambda x: x[::-1, :],
        'rot180': lambda x: x[::-1, ::-1],
    }


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('--photo', required=True)
    ap.add_argument('--xs', required=True); ap.add_argument('--ys', required=True)
    ap.add_argument('--xm', required=True); ap.add_argument('--ym', required=True)
    ap.add_argument('--mpp', type=float, default=20.0, help='mm per pixel of the matching raster')
    ap.add_argument('--sigma-mm', type=float, default=100.0)
    ap.add_argument('--tag', default='-v29')
    ap.add_argument('--out', default='')
    ap.add_argument('--centre', default='vertex', choices=['vertex', 'crest'], help='what the photo is centred on')
    args = ap.parse_args()
    f = lambda s: [float(x) for x in s.split(',')]
    photo = np.array(Image.open(args.photo).convert('RGB'))
    rect, valid, (u_lo, v_lo) = rectify(photo, f(args.xs), f(args.ys), f(args.xm), f(args.ym), args.mpp)
    ortho, meta = load_ortho(args.tag)
    nodes, PU, PV = candidate_nodes(meta, args.centre)
    scale = meta['mm_per_px'] / args.mpp          # ortho px per matching px
    sig = args.sigma_mm / args.mpp
    H, W = rect.shape[:2]
    # erode the valid mask so the blur does not bleed the black border into the match
    valid = cv2.erode(valid.astype(np.uint8), np.ones((int(sig * 2) | 1,) * 2, np.uint8)) > 0
    pr = lab_blur(rect, sig)
    results = []
    for name, op in symmetries().items():
        p = op(pr); m = op(valid)
        for (i, hu, hv) in nodes:   # i is the node's name
            # window of the ortho this raster covers, node at the raster's (0,0) metric origin
            x0 = (hu + u_lo - meta['hu0']) * 1000 / meta['mm_per_px']
            y0 = (hv + v_lo - meta['hv0']) * 1000 / meta['mm_per_px']
            M = np.array([[scale, 0, -x0 * scale], [0, scale, -y0 * scale]], np.float32)   # ortho px -> matching px
            win = cv2.warpAffine(ortho, M, (W, H), flags=cv2.INTER_AREA, borderMode=cv2.BORDER_CONSTANT)
            inside = cv2.warpAffine(np.full(ortho.shape[:2], 255, np.uint8), M, (W, H), flags=cv2.INTER_NEAREST) > 0
            mm = m & inside
            if mm.mean() < 0.3:
                continue
            ob = lab_blur(win, sig)
            s = [ncc(p[..., k], ob[..., k], mm) for k in range(3)]
            score = 0.2 * s[0] + 0.4 * s[1] + 0.4 * s[2]     # chroma carries the fingerprint, not luminance
            results.append(dict(sym=name, node=i, hu=hu, hv=hv, score=score, L=s[0], a=s[1], b=s[2], frac=float(mm.mean())))
    results.sort(key=lambda r: -r['score'])
    for r in results[:8]:
        print(f"{r['score']:.3f}  {r['node']:6s} hu {r['hu']:.2f} hv {r['hv']:.2f} {r['sym']:7s}  L {r['L']:.2f} a {r['a']:.2f} b {r['b']:.2f}  cover {r['frac']:.2f}")
    if len(results) > 1:
        print('margin first-second: %.3f' % (results[0]['score'] - results[1]['score']))
    if args.out:
        os.makedirs(args.out, exist_ok=True)
        best = results[0]
        op = symmetries()[best['sym']]
        p = op(rect)
        x0 = (best['hu'] + u_lo - meta['hu0']) * 1000 / meta['mm_per_px']
        y0 = (best['hv'] + v_lo - meta['hv0']) * 1000 / meta['mm_per_px']
        M = np.array([[scale, 0, -x0 * scale], [0, scale, -y0 * scale]], np.float32)   # ortho px -> matching px
        win = cv2.warpAffine(ortho, M, (W, H), flags=cv2.INTER_AREA)
        pair = np.concatenate([p, win], 0)
        Image.fromarray(pair).save(os.path.join(args.out, 'locate-pair.jpg'), quality=85)
        json.dump(dict(photo=args.photo, results=results[:12], u_lo=u_lo, v_lo=v_lo, mpp=args.mpp),
                  open(os.path.join(args.out, 'locate.json'), 'w'), indent=1)
        print('wrote', args.out)


if __name__ == '__main__':
    main()
