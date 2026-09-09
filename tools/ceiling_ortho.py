"""Bottom ortho of the NGV Great Hall canopy from the bake atlas (track B, goal 1).

Unwraps the baked ceiling-glass atlas (photo projection) into an orthographic plan view of the
canopy in the huv plate frame at a fixed mm/px, using the full-res GLB's ceiling-glass
primitive (xyz + uv) so every triangle is rasterised with its own uv interpolation.

Frame chain
    GLB world (x, y, z; y up; metres)
      hu = x*0.975681 + z*0.219196
      hv = x*(-0.219196) + z*0.975681
    ortho pixel (col px, row py), pixel centres:
      hu = hu0 + (px + 0.5) * mm/1000
      hv = hv0 + (py + 0.5) * mm/1000
    so row 0 is the SOUTH edge of the plate (hv0), column 0 the WEST end (hu0), hv grows down
    the image, hu grows to the right. (This is the view from the floor looking up with east on
    the right: a straight-up photo has south at the top when east is on the right.)
    atlas texel (u, v) from the GLB uv (glTF convention, v=0 is the top row of the PNG):
      atlas_x = u * atlas_w - 0.5,  atlas_y = v * atlas_h - 0.5   (bilinear)
    Optional 2D affine correction (fitted here from the dark joint lines, see --fit):
      the atlas is sampled at (hu + du, hv + dv), du/dv = affine(hu, hv), so the joint
      lines of the bake land on the measured lattice.

Outputs (in --out):
    bottom-ortho.png       RGB, width x height, 5 mm/px by default
    bottom-meta.json       {hu0, hv0, mm_per_px, width, height, ...frame chain, fit, coverage}
    bottom-preview.jpg     <= 2000 px wide
    coverage.png           1 = atlas covers this pixel (inside the ceiling-glass mesh)
    quality.png            per-cell (0.5 m) sharpness map, colour coded, grid overlaid
    quality.npy / quality.json   per-cell scores and the share above the threshold
    align-bays.json        per-bay joint-line offsets, before and after the correction

Usage
    python tools/ceiling_ortho.py [--glb GLB] [--atlas PNG|embedded] [--out DIR] [--mm 5]
                                  [--fit affine|translate|none] [--scratch DIR]
"""
import argparse
import io
import json
import math
import os
import struct
import sys
import time

import cv2
import numpy as np
from PIL import Image

Image.MAX_IMAGE_PIXELS = None

# ----------------------------------------------------------------------------- constants
GLB_DEFAULT = ('E:/sitecapture-captures/ngv-site/clean-hall-20260831-v29/textured-v29/'
               'clean-hall-textured-blender.glb')
ATLAS_DEFAULT = 'E:/sitecapture-captures/ngv-site/agent-ref-ceiling/atlas/ceiling-glass.png'
OUT_DEFAULT = 'E:/sitecapture-captures/ngv-site/agent-ref-ceiling/trackB'
SCRATCH_DEFAULT = ('C:/Users/LLOYDG~1/AppData/Local/Temp/claude/C--Users-Lloyd-Gibbs/'
                   '046860d0-c13c-4e5d-847c-7ad01cef102a/scratchpad/trackB')

HU_AXIS = (0.975681, 0.219196)      # hu = x*HU[0] + z*HU[1]
HV_AXIS = (-0.219196, 0.975681)     # hv = x*HV[0] + z*HV[1]
PU, PV = 7.4285, 7.3855             # lattice module (m)
VERT_U0, VERT_V0 = -45.492375, 11.237070   # funnel vertex at hu = VERT_U0 + i*PU, hv = VERT_V0 + j*PV
PLATE = (-56.635125, 0.158820, -4.635625, 14.929820)   # hu0, hv0, hu1, hv1 of the 7x2 bays
NB_U, NB_V = 7, 2
RIDGE_W, JOINT_W = 0.20, 0.12       # steel joint widths (m): bay ridge, other joints
CELL_M = 0.5                        # quality cell


# ----------------------------------------------------------------------------- GLB reader
def read_glb(path):
    with open(path, 'rb') as f:
        magic, ver, length = struct.unpack('<4sII', f.read(12))
        if magic != b'glTF':
            raise SystemExit('not a GLB: ' + path)
        cl, ct = struct.unpack('<II', f.read(8))
        js = json.loads(f.read(cl))
        bl, bt = struct.unpack('<II', f.read(8))
        blob = f.read(bl)
    return js, blob


CTYPE = {5120: np.int8, 5121: np.uint8, 5122: np.int16, 5123: np.uint16, 5125: np.uint32, 5126: np.float32}
NCOMP = {'SCALAR': 1, 'VEC2': 2, 'VEC3': 3, 'VEC4': 4, 'MAT4': 16}


def accessor(js, blob, idx):
    a = js['accessors'][idx]
    bv = js['bufferViews'][a['bufferView']]
    off = bv.get('byteOffset', 0) + a.get('byteOffset', 0)
    n = NCOMP[a['type']]
    dt = np.dtype(CTYPE[a['componentType']])
    cnt = a['count']
    stride = bv.get('byteStride', 0)
    if stride and stride != n * dt.itemsize:
        raw = np.frombuffer(blob, dtype=np.uint8, count=stride * cnt, offset=off)
        raw = np.lib.stride_tricks.as_strided(raw, shape=(cnt, n * dt.itemsize), strides=(stride, 1)).copy()
        return raw.view(dt).reshape(cnt, n)
    return np.frombuffer(blob, dtype=dt, count=cnt * n, offset=off).reshape(cnt, n)


def node_world_matrices(js):
    """mesh index -> list of 4x4 world matrices (glTF column-major)."""
    out = {}

    def local(n):
        if 'matrix' in n:
            return np.array(n['matrix'], dtype=np.float64).reshape(4, 4).T
        m = np.eye(4)
        t = n.get('translation', [0, 0, 0])
        q = n.get('rotation', [0, 0, 0, 1])
        s = n.get('scale', [1, 1, 1])
        x, y, z, w = q
        r = np.array([[1 - 2 * (y * y + z * z), 2 * (x * y - z * w), 2 * (x * z + y * w)],
                      [2 * (x * y + z * w), 1 - 2 * (x * x + z * z), 2 * (y * z - x * w)],
                      [2 * (x * z - y * w), 2 * (y * z + x * w), 1 - 2 * (x * x + y * y)]])
        m[:3, :3] = r * np.array(s)[None, :]
        m[:3, 3] = t
        return m

    def walk(ni, parent):
        n = js['nodes'][ni]
        m = parent @ local(n)
        if 'mesh' in n:
            out.setdefault(n['mesh'], []).append(m)
        for c in n.get('children', []):
            walk(c, m)

    scene = js.get('scenes', [{}])[js.get('scene', 0)]
    for ni in scene.get('nodes', range(len(js['nodes']))):
        walk(ni, np.eye(4))
    return out


def ceiling_glass_mesh(js, blob, material_name='ceiling-glass'):
    """Return (tri_xyz (T,3,3) world, tri_uv (T,3,2), material dict)."""
    mats = node_world_matrices(js)
    for mi, mesh in enumerate(js['meshes']):
        for pr in mesh['primitives']:
            if 'material' not in pr:
                continue
            mat = js['materials'][pr['material']]
            if mat.get('name') != material_name:
                continue
            pos = accessor(js, blob, pr['attributes']['POSITION']).astype(np.float64)
            uv = accessor(js, blob, pr['attributes']['TEXCOORD_0']).astype(np.float64)
            if 'indices' in pr:
                idx = accessor(js, blob, pr['indices']).reshape(-1).astype(np.int64)
            else:
                idx = np.arange(len(pos))
            mode = pr.get('mode', 4)
            if mode != 4:
                raise SystemExit('ceiling-glass primitive is not a triangle list (mode %d)' % mode)
            for M in mats.get(mi, [np.eye(4)]):
                p = (M[:3, :3] @ pos.T).T + M[:3, 3]
                tri = p[idx].reshape(-1, 3, 3)
                tuv = uv[idx].reshape(-1, 3, 2)
                return tri, tuv, mat
    raise SystemExit('no primitive with material ' + material_name)


def embedded_image(js, blob, mat):
    ti = mat['pbrMetallicRoughness']['baseColorTexture']['index']
    img = js['images'][js['textures'][ti]['source']]
    bv = js['bufferViews'][img['bufferView']]
    off = bv.get('byteOffset', 0)
    data = blob[off:off + bv['byteLength']]
    return np.asarray(Image.open(io.BytesIO(data)).convert('RGB'))


# ----------------------------------------------------------------------------- frame helpers
def to_huv(xyz):
    x, z = xyz[..., 0], xyz[..., 2]
    return x * HU_AXIS[0] + z * HU_AXIS[1], x * HV_AXIS[0] + z * HV_AXIS[1]


def bay_vertex(i, j):
    """funnel vertex (hu, hv) of bay i (0..6 from the west) j (0 south, 1 north)."""
    return VERT_U0 + (i - 1) * PU, VERT_V0 + (j - 1) * PV


def bay_rect(i, j):
    cu, cv = bay_vertex(i, j)
    return cu - PU / 2, cv - PV / 2, cu + PU / 2, cv + PV / 2


# ----------------------------------------------------------------------------- rasteriser
def rasterise_ids(tri_hu, tri_hv, hu0, hv0, mpp, W, H):
    """Triangle id per ortho pixel (int32, -1 = none) by scan-converting every triangle."""
    ids = np.full((H, W), -1, np.int32)
    SH = 4
    for t in range(len(tri_hu)):
        px = (tri_hu[t] - hu0) / mpp
        py = (tri_hv[t] - hv0) / mpp
        pts = np.stack([px, py], axis=1)
        if pts[:, 0].max() < 0 or pts[:, 1].max() < 0 or pts[:, 0].min() > W or pts[:, 1].min() > H:
            continue
        cv2.fillConvexPoly(ids, np.round(pts * (1 << SH)).astype(np.int32), int(t), lineType=cv2.LINE_8, shift=SH)
    return ids


def uv_at(tri_hu, tri_hv, tri_uv, ids, hu, hv):
    """Barycentric uv interpolation of the triangle `ids` at plan positions (hu, hv)."""
    t = ids
    ok = t >= 0
    tt = np.where(ok, t, 0)
    a_u, b_u, c_u = tri_hu[tt, 0], tri_hu[tt, 1], tri_hu[tt, 2]
    a_v, b_v, c_v = tri_hv[tt, 0], tri_hv[tt, 1], tri_hv[tt, 2]
    det = (b_u - a_u) * (c_v - a_v) - (c_u - a_u) * (b_v - a_v)
    det = np.where(np.abs(det) < 1e-12, 1e-12, det)
    wa = ((b_u - hu) * (c_v - hv) - (c_u - hu) * (b_v - hv)) / det   # area opposite A
    wb = ((c_u - hu) * (a_v - hv) - (a_u - hu) * (c_v - hv)) / det   # area opposite B
    wc = 1.0 - wa - wb
    u = wa * tri_uv[tt, 0, 0] + wb * tri_uv[tt, 1, 0] + wc * tri_uv[tt, 2, 0]
    v = wa * tri_uv[tt, 0, 1] + wb * tri_uv[tt, 1, 1] + wc * tri_uv[tt, 2, 1]
    return u, v, ok


def fill_seams(ids, max_px=2):
    """Assign the nearest triangle id to unassigned pixels within max_px of an assigned one."""
    from scipy import ndimage as ndi
    empty = ids < 0
    if not empty.any():
        return ids
    dist, (iy, ix) = ndi.distance_transform_edt(empty, return_indices=True)
    near = empty & (dist <= max_px)
    out = ids.copy()
    out[near] = ids[iy[near], ix[near]]
    return out


# ----------------------------------------------------------------------------- joint mask
def joint_lines(i, j):
    """(p0, p1, width) segments of every steel joint of bay (i, j) in huv metres."""
    u0, v0, u1, v1 = bay_rect(i, j)
    cu, cv = bay_vertex(i, j)
    segs = []
    # bay ridge beams (the crest ring)
    for a, b in (((u0, v0), (u1, v0)), ((u1, v0), (u1, v1)), ((u1, v1), (u0, v1)), ((u0, v1), (u0, v0))):
        segs.append((a, b, RIDGE_W))
    # the + cross at half bay, through the vertex
    segs.append(((cu, v0), (cu, v1), JOINT_W))
    segs.append(((u0, cv), (u1, cv), JOINT_W))
    # the main X through the vertex
    segs.append(((u0, v0), (u1, v1), JOINT_W))
    segs.append(((u0, v1), (u1, v0), JOINT_W))
    # the diamond joining the edge midpoints
    segs.append(((cu, v0), (u1, cv), JOINT_W))
    segs.append(((u1, cv), (cu, v1), JOINT_W))
    segs.append(((cu, v1), (u0, cv), JOINT_W))
    segs.append(((u0, cv), (cu, v0), JOINT_W))
    return segs


def draw_segments(img, segs, hu0, hv0, mpp, value=255, min_px=1):
    for (a, b, w) in segs:
        p0 = (int(round((a[0] - hu0) / mpp)), int(round((a[1] - hv0) / mpp)))
        p1 = (int(round((b[0] - hu0) / mpp)), int(round((b[1] - hv0) / mpp)))
        th = max(min_px, int(round(w / mpp)))
        cv2.line(img, p0, p1, value, th, lineType=cv2.LINE_8)
    return img


def joint_mask_full(hu0, hv0, mpp, W, H, widen=0.0):
    m = np.zeros((H, W), np.uint8)
    for i in range(NB_U):
        for j in range(NB_V):
            segs = [(a, b, w + widen) for (a, b, w) in joint_lines(i, j)]
            draw_segments(m, segs, hu0, hv0, mpp)
    return m


# ----------------------------------------------------------------------------- alignment
def darkness_image(rgb, mpp_src, mpp_work=0.025):
    """Downsample to mpp_work and return (gray, darkness) where darkness = local mean - gray, >= 0."""
    f = mpp_work / mpp_src
    g = cv2.cvtColor(rgb, cv2.COLOR_RGB2GRAY).astype(np.float32)
    gs = cv2.resize(g, (max(1, int(round(g.shape[1] / f))), max(1, int(round(g.shape[0] / f)))),
                    interpolation=cv2.INTER_AREA)
    k = int(round(0.6 / mpp_work)) | 1
    loc = cv2.blur(gs, (k, k))
    d = np.clip(loc - gs, 0, None)
    return gs, d


def wide_dark(rgb, mpp, mpp_work=0.025, width_m=0.125, length_m=0.3, axis='u'):
    """Darkness that survives a min filter shaped like a joint line: width_m across the line and
    length_m along it (axis 'u' = lines of constant hu, i.e. vertical in the ortho; 'v' = horizontal).
    The steel joints (0.12 / 0.20 m wide, metres long) stay; the 30-60 mm concrete gaps between
    pieces and the diagonal joints (not continuous along the axis) vanish."""
    gs, D = darkness_image(rgb, mpp, mpp_work)
    w = max(3, int(round(width_m / mpp_work)) | 1)
    l = max(3, int(round(length_m / mpp_work)) | 1)
    k = np.ones((l, w), np.uint8) if axis == 'u' else np.ones((w, l), np.uint8)
    return gs, cv2.erode(D, k)


def _ncc_shift(seg, tpl, search_px):
    """Normalised cross-correlation of a 1D template against a 1D segment over integer shifts
    -search..search; returns (best shift with a parabolic sub-sample, ncc, second-best ncc)."""
    shifts = np.arange(-search_px, search_px + 1)
    a_ = seg - seg.mean()
    na = np.sqrt((a_ ** 2).sum()) + 1e-9
    cc = np.empty(shifts.size, np.float64)
    for n, s in enumerate(shifts):
        t = np.roll(tpl, int(s))
        b_ = t - t.mean()
        cc[n] = (a_ * b_).sum() / (na * (np.sqrt((b_ ** 2).sum()) + 1e-9))
    k = int(cc.argmax())
    sub = 0.0
    if 0 < k < cc.size - 1:
        den = cc[k - 1] - 2 * cc[k] + cc[k + 1]
        if abs(den) > 1e-9:
            sub = float(np.clip(0.5 * (cc[k - 1] - cc[k + 1]) / den, -1, 1))
    cc2 = cc.copy()
    lo, hi = max(0, k - int(0.4 * search_px)), min(cc.size, k + int(0.4 * search_px) + 1)
    cc2[lo:hi] = -9
    return float(shifts[k] + sub), float(cc[k]), float(cc2.max()) if (cc2 > -9).any() else -1.0


def _band_template(n, origin, mw, bands, blur=1.5):
    tpl = np.zeros(n, np.float32)
    for centre, w in bands:
        a = int(round((centre - w / 2 - origin) / mw)); b = int(round((centre + w / 2 - origin) / mw))
        tpl[max(0, a):max(0, min(n, b))] = 1
    return cv2.GaussianBlur(tpl[None, :], (0, 0), blur)[0]


def measure_bay_offsets(rgb, hu0, hv0, mpp, cov, search_m=0.7, mpp_work=0.025):
    """Per bay: where do the dark joint lines sit relative to the lattice (du, dv in m)?
    Method: the wide-dark image is projected onto hu inside the bay's hv band (shrunk 0.4 m so the
    horizontal ridges do not enter) and correlated with the comb [ridge, cross, ridge] of the bay
    at shifts within +-search_m; the same along hv. ncc is the peak normalised correlation and
    ncc2 the best peak elsewhere (distinctiveness)."""
    gs, Eu = wide_dark(rgb, mpp, mpp_work, axis='u')
    _, Ev = wide_dark(rgb, mpp, mpp_work, axis='v')
    covs = cv2.resize(cov.astype(np.uint8), (Eu.shape[1], Eu.shape[0]), interpolation=cv2.INTER_AREA)
    Eu = Eu * (covs > 0); Ev = Ev * (covs > 0)
    mw = mpp_work
    s = int(round(search_m / mw))
    out = []
    for i in range(NB_U):
        for j in range(NB_V):
            u0, v0, u1, v1 = bay_rect(i, j)
            cu, cv_ = (u0 + u1) / 2, (v0 + v1) / 2
            E = Eu
            share = float((covs[max(0, int((v0 - hv0) / mw)):int((v1 - hv0) / mw), max(0, int((u0 - hu0) / mw)):int((u1 - hu0) / mw)] > 0).mean())
            # --- du from the hu profile
            r0, r1 = int((v0 + 0.4 - hv0) / mw), int((v1 - 0.4 - hv0) / mw)
            prof = E[max(0, r0):max(0, r1)].mean(axis=0) if r1 > r0 else np.zeros(E.shape[1], np.float32)
            c0, c1 = int((u0 - 1.0 - hu0) / mw), int((u1 + 1.0 - hu0) / mw)
            seg = np.zeros(c1 - c0, np.float32)
            a0, a1 = max(0, c0), min(prof.size, c1)
            if a1 > a0:
                seg[a0 - c0:a1 - c0] = prof[a0:a1]
            tpl = _band_template(seg.size, hu0 + c0 * mw, mw, ((u0, RIDGE_W), (cu, JOINT_W), (u1, RIDGE_W)))
            du, nu, nu2 = _ncc_shift(seg, tpl, s)
            # --- dv from the hv profile
            E = Ev
            c0, c1 = int((u0 + 0.4 - hu0) / mw), int((u1 - 0.4 - hu0) / mw)
            prof = E[:, max(0, c0):max(0, c1)].mean(axis=1) if c1 > c0 else np.zeros(E.shape[0], np.float32)
            r0, r1 = int((v0 - 1.0 - hv0) / mw), int((v1 + 1.0 - hv0) / mw)
            seg = np.zeros(r1 - r0, np.float32)
            a0, a1 = max(0, r0), min(prof.size, r1)
            if a1 > a0:
                seg[a0 - r0:a1 - r0] = prof[a0:a1]
            tpl = _band_template(seg.size, hv0 + r0 * mw, mw, ((v0, RIDGE_W), (cv_, JOINT_W), (v1, RIDGE_W)))
            dv, nv, nv2 = _ncc_shift(seg, tpl, s)
            out.append(dict(i=i, j=j, du=du * mw, dv=dv * mw, ncc_u=nu, ncc2_u=nu2, ncc_v=nv, ncc2_v=nv2,
                            ncc=min(nu, nv), cov_share=share, hu_c=float(cu), hv_c=float(cv_)))
    return out


def measure_lines(rgb, hu0, hv0, mpp, cov, search_m=0.6, mpp_work=0.025):
    """Every straight joint line of the lattice on its own: the 8 vertical ridges + 7 vertical crosses
    (per bay row) and the 3 horizontal ridges + 2 horizontal crosses (per bay column). Returns the
    measured position of each (a scale check: does the atlas module match PU / PV?)."""
    gs, Eu = wide_dark(rgb, mpp, mpp_work, axis='u')
    _, Ev = wide_dark(rgb, mpp, mpp_work, axis='v')
    mw = mpp_work
    s = int(round(search_m / mw))
    out = []
    plate_u0, plate_v0 = PLATE[0], PLATE[1]
    E = Eu
    for j in range(NB_V):
        _, v0, _, v1 = bay_rect(0, j)
        r0, r1 = int((v0 + 0.4 - hv0) / mw), int((v1 - 0.4 - hv0) / mw)
        prof = E[max(0, r0):max(0, r1)].mean(axis=0)
        for k2 in range(0, 2 * NB_U + 1):
            hu = plate_u0 + k2 * PU / 2
            w = RIDGE_W if k2 % 2 == 0 else JOINT_W
            c0, c1 = int((hu - 1.2 - hu0) / mw), int((hu + 1.2 - hu0) / mw)
            seg = np.zeros(c1 - c0, np.float32)
            a0, a1 = max(0, c0), min(prof.size, c1)
            if a1 > a0:
                seg[a0 - c0:a1 - c0] = prof[a0:a1]
            tpl = _band_template(seg.size, hu0 + c0 * mw, mw, ((hu, w),))
            d, n, n2 = _ncc_shift(seg, tpl, s)
            out.append(dict(axis='u', line=k2 / 2, row=j, kind='ridge' if k2 % 2 == 0 else 'cross',
                            expected=hu, measured=hu + d * mw, offset=d * mw, ncc=n, ncc2=n2))
    E = Ev
    for i in range(NB_U):
        u0, _, u1, _ = bay_rect(i, 0)
        c0, c1 = int((u0 + 0.4 - hu0) / mw), int((u1 - 0.4 - hu0) / mw)
        prof = E[:, max(0, c0):max(0, c1)].mean(axis=1)
        for k2 in range(0, 2 * NB_V + 1):
            hv = plate_v0 + k2 * PV / 2
            w = RIDGE_W if k2 % 2 == 0 else JOINT_W
            r0, r1 = int((hv - 1.2 - hv0) / mw), int((hv + 1.2 - hv0) / mw)
            seg = np.zeros(r1 - r0, np.float32)
            a0, a1 = max(0, r0), min(prof.size, r1)
            if a1 > a0:
                seg[a0 - r0:a1 - r0] = prof[a0:a1]
            tpl = _band_template(seg.size, hv0 + r0 * mw, mw, ((hv, w),))
            d, n, n2 = _ncc_shift(seg, tpl, s)
            out.append(dict(axis='v', line=k2 / 2, col=i, kind='ridge' if k2 % 2 == 0 else 'cross',
                            expected=hv, measured=hv + d * mw, offset=d * mw, ncc=n, ncc2=n2))
    return out


RELIABLE_NCC = 0.35


def reliable(m, axis=None):
    """A bay measurement is trusted when its comb correlation is clear (see RELIABLE_NCC)."""
    if m['cov_share'] < 0.6:
        return False
    if axis == 'u':
        return m['ncc_u'] >= RELIABLE_NCC
    if axis == 'v':
        return m['ncc_v'] >= RELIABLE_NCC
    return m['ncc_u'] >= RELIABLE_NCC and m['ncc_v'] >= RELIABLE_NCC


def fit_offset_field(meas, kind='affine'):
    """Fit du = c0 + c1*hu + c2*hv (and dv likewise) to the reliable per-bay measurements, each axis
    from its own reliable set, weighted by ncc. Falls back to a translation with < 4 bays."""
    use_u = [m for m in meas if reliable(m, 'u')]
    use_v = [m for m in meas if reliable(m, 'v')]
    if not use_u or not use_v:
        return None, use_u + use_v

    def solve(use, key, nkey):
        hu = np.array([m['hu_c'] for m in use]); hv = np.array([m['hv_c'] for m in use])
        d = np.array([m[key] for m in use]); w = np.array([m[nkey] for m in use])
        if kind == 'affine' and len(use) >= 4 and (hu.max() - hu.min()) > PU and (hv.max() - hv.min()) > 1:
            A = np.column_stack([np.ones_like(hu), hu, hv]) * w[:, None]
            c, *_ = np.linalg.lstsq(A, d * w, rcond=None)
            return c.tolist(), 'affine'
        if kind == 'affine' and len(use) >= 3 and (hu.max() - hu.min()) > PU:
            A = np.column_stack([np.ones_like(hu), hu]) * w[:, None]
            c, *_ = np.linalg.lstsq(A, d * w, rcond=None)
            return [float(c[0]), float(c[1]), 0.0], 'affine-u-only'
        return [float(np.average(d, weights=w)), 0.0, 0.0], 'translate'

    cu, ku = solve(use_u, 'du', 'ncc_u')
    cv_, kv = solve(use_v, 'dv', 'ncc_v')
    return dict(kind=kind, du=cu, dv=cv_, du_fit=ku, dv_fit=kv, n_u=len(use_u), n_v=len(use_v)), use_u + use_v


def local_grid_coords(hu, hv):
    """Continuous bay-grid coordinates (fi, fj) of a point: 0 at the centre of bay 0, 6 at bay 6."""
    fi = (hu - (PLATE[0] + PU / 2)) / PU
    fj = (hv - (PLATE[1] + PV / 2)) / PV
    return np.clip(fi, 0, NB_U - 1), np.clip(fj, 0, NB_V - 1)


def bilinear_grid(grid, fi, fj):
    """Bilinear interpolation of a (NB_V, NB_U) grid at continuous (fi, fj), clamped at the edges."""
    g = np.asarray(grid, np.float64)
    i0 = np.clip(np.floor(fi).astype(int), 0, NB_U - 2); j0 = np.clip(np.floor(fj).astype(int), 0, NB_V - 2)
    t = np.clip(fi - i0, 0, 1); u = np.clip(fj - j0, 0, 1)
    return ((1 - t) * (1 - u) * g[j0, i0] + t * (1 - u) * g[j0, i0 + 1] +
            (1 - t) * u * g[j0 + 1, i0] + t * u * g[j0 + 1, i0 + 1])


def apply_field(field, hu, hv):
    """Sample position of the atlas for the lattice position (hu, hv): the affine part plus, when
    present, the per-bay residual grid interpolated bilinearly between bay centres."""
    if field is None:
        return hu, hv
    cu, cv_ = field['du'], field['dv']
    su = hu + cu[0] + cu[1] * hu + cu[2] * hv
    sv = hv + cv_[0] + cv_[1] * hu + cv_[2] * hv
    if field.get('local_du') is not None:
        fi, fj = local_grid_coords(hu, hv)
        su = su + bilinear_grid(field['local_du'], fi, fj)
        sv = sv + bilinear_grid(field['local_dv'], fi, fj)
    return su, sv


def add_local_residuals(field, meas):
    """Per-bay residual offsets (after the affine) as a (NB_V, NB_U) grid each for du and dv;
    unreliable bays get 0 (the affine alone)."""
    gu = np.zeros((NB_V, NB_U)); gv = np.zeros((NB_V, NB_U))
    for m in meas:
        if reliable(m, 'u'):
            gu[m['j'], m['i']] = m['du']
        if reliable(m, 'v'):
            gv[m['j'], m['i']] = m['dv']
    out = dict(field)
    out['local_du'] = (np.asarray(field.get('local_du', np.zeros_like(gu))) + gu).tolist()
    out['local_dv'] = (np.asarray(field.get('local_dv', np.zeros_like(gv))) + gv).tolist()
    return out


# ----------------------------------------------------------------------------- quality
CLASS_NAMES = {0: 'no data', 1: 'not glass / flat', 2: 'smeared', 3: 'artefact', 4: 'traceable'}
Q_LAYERS = ['nsharp', 'std', 'mean', 'cov', 'piece', 'bg', 'step', 'black', 'chroma', 'class']


def quality_map(rgb, cov, mpp, cell_m=CELL_M):
    """Per-cell features of the ortho (see classify_cells for how they are read):
      nsharp  Laplacian energy / contrast at 10 mm/px: low = smeared streaks, no edges
      step    share of strong edges that are sharper than the bake's own blur (a 1-px step): the
              seams of mis-projected patches, cut-outs, rims. Real glass edges in this bake are
              12-15 mm wide (20-80 % rise) so they survive a 6 mm blur nearly unchanged
      black   share of near-black texels (< 15): missing texture, never the concrete matrix
      bg      30th percentile of grey: the matrix level (glass cells 40-110, walls > 130)
      piece   share of texels standing out from the matrix (grey > bg + 35 or chroma > 28)
      chroma  mean chroma (max(rgb) - min(rgb)) of the piece texels
    """
    g = cv2.cvtColor(rgb, cv2.COLOR_RGB2GRAY).astype(np.float32)
    chroma = (rgb.max(axis=2).astype(np.float32) - rgb.min(axis=2).astype(np.float32))
    n = int(round(cell_m / mpp))
    H, W = g.shape
    bh, bw = H // n, W // n

    def blocks(a):
        return a[:bh * n, :bw * n].reshape(bh, n, bw, n)

    mean = blocks(g).mean(axis=(1, 3))
    std = blocks(g).std(axis=(1, 3))
    covshare = blocks(cov.astype(np.float32)).mean(axis=(1, 3))
    bg = np.percentile(blocks(g), 30, axis=(1, 3))
    bg_full = np.repeat(np.repeat(bg, n, axis=0), n, axis=1)
    piece_px = np.zeros((H, W), np.float32)
    piece_px[:bh * n, :bw * n] = ((g[:bh * n, :bw * n] > bg_full + 35) | (chroma[:bh * n, :bw * n] > 28)).astype(np.float32)
    piece = blocks(piece_px).mean(axis=(1, 3))
    chroma_sum = blocks(chroma * piece_px).sum(axis=(1, 3))
    chroma_mean = chroma_sum / np.maximum(1, blocks(piece_px).sum(axis=(1, 3)))
    black = blocks((g < 15).astype(np.float32)).mean(axis=(1, 3))
    # step edges: gradient before / after a small blur
    gx = cv2.Sobel(g, cv2.CV_32F, 1, 0, ksize=3) / 8; gy = cv2.Sobel(g, cv2.CV_32F, 0, 1, ksize=3) / 8
    g0 = np.hypot(gx, gy)
    gb = cv2.GaussianBlur(g, (0, 0), 1.2)
    gx = cv2.Sobel(gb, cv2.CV_32F, 1, 0, ksize=3) / 8; gy = cv2.Sobel(gb, cv2.CV_32F, 0, 1, ksize=3) / 8
    g1 = np.hypot(gx, gy)
    edge = (g0 > 14).astype(np.float32)
    stepy = (edge * (g0 > 2.0 * (g1 + 1.0))).astype(np.float32)
    step = blocks(stepy).sum(axis=(1, 3)) / np.maximum(20, blocks(edge).sum(axis=(1, 3)))
    # sharpness at 10 mm/px (near the texel size) as before
    f = 0.010 / mpp
    gs = cv2.resize(g, (int(round(W / f)), int(round(H / f))), interpolation=cv2.INTER_AREA)
    lap = cv2.Laplacian(gs, cv2.CV_32F, ksize=3)
    n2 = int(round(cell_m / 0.010))
    lapvar = lap[:bh * n2, :bw * n2].reshape(bh, n2, bw, n2).var(axis=(1, 3))
    std2 = gs[:bh * n2, :bw * n2].reshape(bh, n2, bw, n2).std(axis=(1, 3))
    nsharp = lapvar / (std2 ** 2 + 25.0)
    return dict(nsharp=nsharp, std=std, mean=mean, cov=covshare, piece=piece, bg=bg, step=step, black=black,
                chroma=chroma_mean, cell_px=n)


THR = dict(nsharp=0.5, nsharp_max=4.0, step=0.05, black=0.02, bg_max=145.0, piece_min=0.06, piece_max=0.80, std_min=15.0)


def classify_cells(q, thr=None):
    """0 no data, 1 not glass / flat, 2 smeared, 3 artefact (seams, cut-outs), 4 traceable."""
    t = dict(THR); t.update(thr or {})
    cls = np.zeros(q['std'].shape, np.uint8)
    has = q['cov'] > 0.5
    cls[has] = 1
    glass = has & (q['std'] >= t['std_min']) & (q['piece'] >= t['piece_min']) & (q['piece'] <= t['piece_max']) & (q['bg'] <= t['bg_max'])
    cls[glass] = 4
    cls[glass & (q['nsharp'] < t['nsharp'])] = 2
    cls[glass & (q['nsharp'] >= t['nsharp']) & ((q['step'] > t['step']) | (q['black'] > t['black']) | (q['nsharp'] > t['nsharp_max']))] = 3
    return cls


def quality_png(q, cls, hu0, hv0, mpp, W, H):
    """Class map with the bay grid, at the cell scale x 4 for legibility.
    black = no data, purple = not glass / flat, red = smeared, orange = artefact, green = traceable."""
    bh, bw = cls.shape
    S = 4
    img = np.zeros((bh, bw, 3), np.uint8)
    img[cls == 1] = (90, 40, 120)
    img[cls == 2] = (220, 30, 30)
    img[cls == 3] = (240, 150, 20)
    img[cls == 4] = (40, 220, 40)
    img = cv2.resize(img, (bw * S, bh * S), interpolation=cv2.INTER_NEAREST)
    cell = q['cell_px']
    for i in range(NB_U):
        for j in range(NB_V):
            u0, v0, u1, v1 = bay_rect(i, j)
            p0 = (int((u0 - hu0) / mpp / cell * S), int((v0 - hv0) / mpp / cell * S))
            p1 = (int((u1 - hu0) / mpp / cell * S), int((v1 - hv0) / mpp / cell * S))
            cv2.rectangle(img, p0, p1, (255, 255, 255), 1)
            cv2.putText(img, '%d,%d' % (i, j), (p0[0] + 4, p0[1] + 14), cv2.FONT_HERSHEY_SIMPLEX, 0.4, (255, 255, 255), 1)
    return img


def quality_report(cls, hu0, hv0, mpp, cell):
    per_bay = []
    for i in range(NB_U):
        for j in range(NB_V):
            u0, v0, u1, v1 = bay_rect(i, j)
            c0, c1 = int((u0 - hu0) / mpp / cell), int(math.ceil((u1 - hu0) / mpp / cell))
            r0, r1 = int((v0 - hv0) / mpp / cell), int(math.ceil((v1 - hv0) / mpp / cell))
            sub = cls[r0:r1, c0:c1]
            d = dict(i=i, j=j, cells=int(sub.size))
            for k, name in CLASS_NAMES.items():
                d[name.split(' ')[0] if k != 1 else 'not_glass'] = int((sub == k).sum())
            d['traceable_share'] = float((sub == 4).mean()) if sub.size else 0.0
            per_bay.append(d)
    return per_bay


# ----------------------------------------------------------------------------- main
def quality_only(args):
    tag = args.tag
    img = np.asarray(Image.open(os.path.join(args.out, 'bottom-ortho%s.png' % tag)).convert('RGB'))
    cov = cv2.imread(os.path.join(args.out, 'coverage%s.png' % tag), cv2.IMREAD_GRAYSCALE) > 0
    meta = json.load(open(os.path.join(args.out, 'bottom-meta%s.json' % tag)))
    hu0, hv0, mpp = meta['hu0'], meta['hv0'], meta['mm_per_px'] / 1000.0
    H, W = img.shape[:2]
    q = quality_map(img, cov, mpp)
    cls = classify_cells(q)
    has = cls > 0
    share_ok = float((cls == 4).sum() / max(1, has.sum()))
    print('quality: %d cells with data; %s' % (has.sum(), ', '.join('%s %d' % (CLASS_NAMES[k], (cls == k).sum()) for k in range(1, 5))))
    print('  traceable share of cells with data: %.1f%%  (thresholds %s)' % (100 * share_ok, json.dumps(THR)))
    per_bay = quality_report(cls, hu0, hv0, mpp, q['cell_px'])
    for d in per_bay:
        print('  bay %d,%d: %d cells: not-glass %d, smeared %d, artefact %d, traceable %d (%.0f%%)' % (
            d['i'], d['j'], d['cells'], d['not_glass'], d['smeared'], d['artefact'], d['traceable'], 100 * d['traceable_share']))
    qp = quality_png(q, cls, hu0, hv0, mpp, W, H)
    cv2.imwrite(os.path.join(args.out, 'quality%s.png' % tag), cv2.cvtColor(qp, cv2.COLOR_RGB2BGR))
    np.save(os.path.join(args.out, 'quality%s.npy' % tag), np.stack([q[k] for k in Q_LAYERS[:-1]] + [cls.astype(np.float32)]))
    Image.fromarray(cv2.resize(qp, (2000, int(round(qp.shape[0] * 2000 / qp.shape[1]))), interpolation=cv2.INTER_NEAREST)).save(
        os.path.join(args.scratch, 'quality-preview%s.jpg' % tag), quality=88)
    meta['quality'] = dict(cell_m=CELL_M, thresholds=THR, cells_with_data=int(has.sum()), traceable_share=share_ok,
                           counts={CLASS_NAMES[k]: int((cls == k).sum()) for k in range(5)}, per_bay=per_bay,
                           layers='quality.npy layers: ' + ', '.join(Q_LAYERS), classes=CLASS_NAMES)
    with open(os.path.join(args.out, 'bottom-meta%s.json' % tag), 'w') as f:
        json.dump(meta, f, indent=1)
    print('quality rewritten for', tag or 'primary')


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('--glb', default=GLB_DEFAULT)
    ap.add_argument('--atlas', default=ATLAS_DEFAULT, help="PNG path, or 'embedded' for the GLB's own texture")
    ap.add_argument('--out', default=OUT_DEFAULT)
    ap.add_argument('--scratch', default=SCRATCH_DEFAULT)
    ap.add_argument('--mm', type=float, default=5.0)
    ap.add_argument('--fit', default='local', choices=['local', 'affine', 'translate', 'none'],
                    help='local = affine + per-bay residual grid (bilinear between bay centres)')
    ap.add_argument('--quality-only', action='store_true', help='reuse the ortho already in --out, redo only the quality map')
    ap.add_argument('--tag', default='', help='suffix for the output names (e.g. -v29)')
    args = ap.parse_args()
    os.makedirs(args.out, exist_ok=True); os.makedirs(args.scratch, exist_ok=True)
    t0 = time.time()
    if args.quality_only:
        return quality_only(args)
    js, blob = read_glb(args.glb)
    tri, tuv, mat = ceiling_glass_mesh(js, blob)
    if args.atlas == 'embedded':
        atlas = embedded_image(js, blob, mat)
        atlas_src = args.glb + '#' + js['images'][js['textures'][mat['pbrMetallicRoughness']['baseColorTexture']['index']]['source']].get('name', '')
    else:
        atlas = np.asarray(Image.open(args.atlas).convert('RGB'))
        atlas_src = args.atlas
    AH, AW = atlas.shape[:2]
    print('glb %s: ceiling-glass %d triangles; atlas %s %dx%d' % (args.glb, len(tri), atlas_src, AW, AH))
    tri_hu, tri_hv = to_huv(tri)
    # uv vs huv: report the global affine and its residual (a diagnostic; the raster uses the mesh)
    P = np.column_stack([tri_hu.ravel(), tri_hv.ravel(), np.ones(tri_hu.size)])
    aff = {}
    for k, lab in ((0, 'u'), (1, 'v')):
        c, *_ = np.linalg.lstsq(P, tuv[..., k].ravel(), rcond=None)
        err = np.abs(P @ c - tuv[..., k].ravel()).max()
        aff[lab] = dict(coef_hu_hv_1=c.tolist(), max_abs_err=float(err))
    print('uv(huv) affine:', json.dumps(aff))
    mm_per_texel = [1000.0 / (abs(aff['u']['coef_hu_hv_1'][0]) * AW), 1000.0 / (abs(aff['v']['coef_hu_hv_1'][1]) * AH)]

    mpp = args.mm / 1000.0
    hu0, hv0, hu1, hv1 = PLATE
    W = int(math.ceil((hu1 - hu0) / mpp - 1e-6))
    H = int(math.ceil((hv1 - hv0) / mpp - 1e-6))
    print('ortho %dx%d at %.1f mm/px, hu0 %.6f hv0 %.6f' % (W, H, args.mm, hu0, hv0))

    # 1. triangle ids on the raw grid
    ids = rasterise_ids(tri_hu, tri_hv, hu0, hv0, mpp, W, H)
    ids = fill_seams(ids, 2)
    def render(field, check=False):
        """Row-chunked: sample position -> triangle -> barycentric uv -> bilinear atlas."""
        img = np.zeros((H, W, 3), np.uint8)
        inside = np.zeros((H, W), bool)
        worst = 0.0
        CH = 192
        for y0 in range(0, H, CH):
            y1 = min(H, y0 + CH)
            yy, xx = np.mgrid[y0:y1, 0:W]
            hu = hu0 + (xx + 0.5) * mpp
            hv = hv0 + (yy + 0.5) * mpp
            hus, hvs = apply_field(field, hu, hv)
            # triangle of the sampled position (nearest raw pixel; uv is continuous across facets)
            sx = np.clip(np.round((hus - hu0) / mpp - 0.5).astype(np.int32), 0, W - 1)
            sy = np.clip(np.round((hvs - hv0) / mpp - 0.5).astype(np.int32), 0, H - 1)
            tid = ids[sy, sx]
            outside = (hus < hu0) | (hus > hu1) | (hvs < hv0) | (hvs > hv1)
            tid = np.where(outside, -1, tid)
            u, v, ok = uv_at(tri_hu, tri_hv, tuv, tid, hus, hvs)
            if check:
                cu_, cv_ = aff['u']['coef_hu_hv_1'], aff['v']['coef_hu_hv_1']
                eu = np.abs(u - (cu_[0] * hus + cu_[1] * hvs + cu_[2]))[ok]
                ev = np.abs(v - (cv_[0] * hus + cv_[1] * hvs + cv_[2]))[ok]
                if eu.size:
                    worst = max(worst, float(eu.max()), float(ev.max()))
            mapx = (u * AW - 0.5).astype(np.float32)
            mapy = (v * AH - 0.5).astype(np.float32)
            chunk = cv2.remap(atlas, mapx, mapy, cv2.INTER_LINEAR, borderMode=cv2.BORDER_CONSTANT, borderValue=(0, 0, 0))
            ins = ok & (u >= 0) & (u <= 1) & (v >= 0) & (v <= 1)
            chunk[~ins] = 0
            img[y0:y1] = chunk
            inside[y0:y1] = ins
        if check:
            print('mesh-uv vs global affine: max |uv err| %.2e (= %.2f texels)' % (worst, worst * max(AW, AH)))
        return img, inside

    raw, cov_raw = render(None, check=True)
    print('raw render %.1fs, coverage %.3f' % (time.time() - t0, cov_raw.mean()))
    def show(meas, label):
        for m in meas:
            print('  bay %d,%d %s: du %+.3f (ncc %.2f/%.2f%s) dv %+.3f (ncc %.2f/%.2f%s) cov %.2f' % (
                m['i'], m['j'], label, m['du'], m['ncc_u'], m['ncc2_u'], '' if reliable(m, 'u') else ' x',
                m['dv'], m['ncc_v'], m['ncc2_v'], '' if reliable(m, 'v') else ' x', m['cov_share']))

    def residual(meas):
        ru = np.array([m['du'] for m in meas if reliable(m, 'u')])
        rv = np.array([m['dv'] for m in meas if reliable(m, 'v')])
        if ru.size == 0 or rv.size == 0:
            return None
        return dict(n_u=int(ru.size), n_v=int(rv.size), rms_u=float(np.sqrt((ru ** 2).mean())),
                    rms_v=float(np.sqrt((rv ** 2).mean())), max_u=float(np.abs(ru).max()), max_v=float(np.abs(rv).max()),
                    mean_u=float(ru.mean()), mean_v=float(rv.mean()))

    def show_lines(lines, label):
        for ax in 'uv':
            L = [l for l in lines if l['axis'] == ax]
            # slope of measured vs expected over the reliable lines: the atlas module relative to PU / PV
            ok = [l for l in L if l['ncc'] >= 0.5 and (l['ncc'] - l['ncc2']) >= 0.1]
            if len(ok) >= 3:
                e = np.array([l['expected'] for l in ok]); mmeas = np.array([l['measured'] for l in ok])
                b, a = np.polyfit(e, mmeas, 1)
                print('  lines %s %s: %d/%d reliable, measured = %.5f * lattice %+.3f  (scale %+.2f%%)' % (
                    ax, label, len(ok), len(L), b, a, (b - 1) * 100))
            for l in L:
                key = 'row' if ax == 'u' else 'col'
                print('    %s %s %4.1f %s %d: off %+.3f ncc %.2f/%.2f%s' % (
                    ax, l['kind'], l['line'], key, l[key], l['offset'], l['ncc'], l['ncc2'],
                    '' if (l['ncc'] >= 0.5 and (l['ncc'] - l['ncc2']) >= 0.1) else ' x'))

    meas_raw = measure_bay_offsets(raw, hu0, hv0, mpp, cov_raw)
    show(meas_raw, 'raw')
    lines_raw = measure_lines(raw, hu0, hv0, mpp, cov_raw)
    show_lines(lines_raw, 'raw')
    res_raw = residual(meas_raw)
    print('raw residual', json.dumps(res_raw))
    field = None
    used = []
    if args.fit != 'none':
        field, used = fit_offset_field(meas_raw, 'affine' if args.fit == 'local' else args.fit)
        print('fit', args.fit, json.dumps(field), 'bays used', sorted(set((m['i'], m['j']) for m in used)))
    img, cov = (raw, cov_raw) if field is None else render(field)
    meas_cor = measure_bay_offsets(img, hu0, hv0, mpp, cov)
    show(meas_cor, 'affine')
    res_aff = residual(meas_cor)
    print('residual after the affine', json.dumps(res_aff))
    lines_cor = None
    if field is not None and args.fit == 'local':
        for it in range(2):
            field = add_local_residuals(field, meas_cor)
            img, cov = render(field)
            meas_cor = measure_bay_offsets(img, hu0, hv0, mpp, cov)
            show(meas_cor, 'local%d' % (it + 1))
            print('residual after local pass %d' % (it + 1), json.dumps(residual(meas_cor)))
    lines_cor = measure_lines(img, hu0, hv0, mpp, cov)
    show_lines(lines_cor, 'cor')
    res_cor = residual(meas_cor)
    print('residual after correction', json.dumps(res_cor))
    rms = res_cor

    # 2. quality
    q = quality_map(img, cov, mpp)
    cls = classify_cells(q)
    has = cls > 0
    share_ok = float((cls == 4).sum() / max(1, has.sum()))
    print('quality: %d cells with data; %s' % (has.sum(), ', '.join('%s %d' % (CLASS_NAMES[k], (cls == k).sum()) for k in range(1, 5))))
    print('  traceable share of cells with data: %.1f%%  (thresholds %s)' % (100 * share_ok, json.dumps(THR)))
    cell = q['cell_px']
    per_bay = quality_report(cls, hu0, hv0, mpp, cell)
    for d in per_bay:
        print('  bay %d,%d: %d cells: not-glass %d, smeared %d, artefact %d, traceable %d (%.0f%%)' % (
            d['i'], d['j'], d['cells'], d['not_glass'], d['smeared'], d['artefact'], d['traceable'], 100 * d['traceable_share']))

    # 3. write
    tag = args.tag
    ortho_path = os.path.join(args.out, 'bottom-ortho%s.png' % tag)
    Image.fromarray(img).save(ortho_path, compress_level=6)
    cv2.imwrite(os.path.join(args.out, 'coverage%s.png' % tag), (cov.astype(np.uint8) * 255))
    qp = quality_png(q, cls, hu0, hv0, mpp, W, H)
    cv2.imwrite(os.path.join(args.out, 'quality%s.png' % tag), cv2.cvtColor(qp, cv2.COLOR_RGB2BGR))
    np.save(os.path.join(args.out, 'quality%s.npy' % tag), np.stack([q[k] for k in Q_LAYERS[:-1]] + [cls.astype(np.float32)]))
    pv = cv2.resize(img, (2000, int(round(H * 2000 / W))), interpolation=cv2.INTER_AREA)
    Image.fromarray(pv).save(os.path.join(args.scratch, 'bottom-preview%s.jpg' % tag), quality=88)
    Image.fromarray(pv).save(os.path.join(args.out, 'bottom-preview%s.jpg' % tag), quality=88)
    Image.fromarray(cv2.resize(qp, (2000, int(round(qp.shape[0] * 2000 / qp.shape[1]))), interpolation=cv2.INTER_NEAREST)).save(
        os.path.join(args.scratch, 'quality-preview%s.jpg' % tag), quality=88)
    meta = dict(
        hu0=hu0, hv0=hv0, mm_per_px=args.mm, width=W, height=H,
        hu1=hu0 + W * mpp, hv1=hv0 + H * mpp,
        pixel_centre='hu = hu0 + (px + 0.5) * mm_per_px / 1000; hv = hv0 + (py + 0.5) * mm_per_px / 1000',
        orientation='row 0 = south edge (hv0), col 0 = west end (hu0); hv grows downward, hu rightward',
        huv_from_world=dict(hu='x*0.975681 + z*0.219196', hv='x*(-0.219196) + z*0.975681'),
        board_from_huv=dict(uu='hu + 58.3053', vv='hv + 0.4556'),
        lattice=dict(PU=PU, PV=PV, vertex_hu='-45.492375 + i*PU', vertex_hv='11.237070 + j*PV',
                     bay_vertex='bay (i 0..6 west->east, j 0 south / 1 north): hu = -52.920875 + i*PU, hv = 3.851570 + j*PV'),
        glb=args.glb, atlas=atlas_src, atlas_size=[AW, AH], mm_per_texel=mm_per_texel,
        uv_affine_of_huv=aff, glTF_v_convention='atlas_y = v * atlas_h (v = 0 is the top row)',
        correction=dict(kind=args.fit, field=field,
                        meaning='atlas sampled at (hu + du, hv + dv): du = c0 + c1*hu + c2*hv (field.du, same for dv with field.dv) plus, for kind=local, the residual grid field.local_du / local_dv (rows j=0..1, cols i=0..6, metres, at the bay centres hu = PLATE0 + (i+0.5)*PU, hv = PLATE1 + (j+0.5)*PV) interpolated bilinearly and clamped at the edges; fitted so the dark joint lines of the bake land on the lattice',
                        residual_after_affine=res_aff,
                        bays_used=sorted(set((m['i'], m['j']) for m in used)),
                        reliable_ncc=RELIABLE_NCC,
                        method='wide-dark (local mean - grey, min-filtered 75 mm) projected onto hu / hv per bay, correlated with the comb [ridge 0.20 m, cross 0.12 m, ridge] within +-0.7 m'),
        bay_offsets_raw=meas_raw, bay_offsets_after=meas_cor, residual_raw_m=res_raw, residual_after_m=res_cor,
        joint_lines_raw=lines_raw, joint_lines_after=lines_cor,
        coverage_share=float(cov.mean()),
        quality=dict(cell_m=CELL_M, thresholds=THR, cells_with_data=int(has.sum()), traceable_share=share_ok,
                     counts={CLASS_NAMES[k]: int((cls == k).sum()) for k in range(5)}, per_bay=per_bay,
                     layers='quality.npy layers: ' + ', '.join(Q_LAYERS), classes=CLASS_NAMES),
        seconds=time.time() - t0)
    with open(os.path.join(args.out, 'bottom-meta%s.json' % tag), 'w') as f:
        json.dump(meta, f, indent=1)
    with open(os.path.join(args.out, 'align-bays%s.json' % tag), 'w') as f:
        json.dump(dict(raw=meas_raw, after=meas_cor, field=field, lines_raw=lines_raw, lines_after=lines_cor,
                       residual_raw=res_raw, residual_after=res_cor), f, indent=1)
    print('wrote', ortho_path, 'in %.1fs' % (time.time() - t0))


if __name__ == '__main__':
    main()
