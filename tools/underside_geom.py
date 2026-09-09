"""Underside orthophoto: geometry, posed-camera sources and the from-below occluders.

WHY A NEW GEOMETRY MODULE instead of using trackA_geom's lattice directly: trackA_geom still
carries the 2026-08-31 recon module (PU 7.4285 / PV 7.3855, phase HU0/HV0). That module was
re-measured on 2026-09-06 and is ~1 % large; the sim now draws 7.36 x 7.50 with the phase
LEAST-SQUARES FITTED to the GLB's own twelve column shaft tops (index.html, buildCanopy).
Over the 52 m plate a 1 % pitch error walks the crest lines 0.48 m out of place, which at
4 mm/px is 120 px of misregistration -- far more than anything else in this pipeline. So the
lattice here is recomputed FROM model.glb exactly the way index.html does it, and cached.
Cameras, projection and the huv axes still come from trackA_geom (unchanged, imported).

Frames
  hall : GLB world of model.glb (y up, metres). The certified COLMAP model
         (day4k-register/model, 1501 images) and the day4k registration are both in it.
  huv  : plate frame, hu = x*CU + z*SU, hv = -x*SU + z*CU  (trackA_geom.xz_to_huv)

Raster convention: identical to trackB/bottom-meta-v29.json so a later fusion is pixel-aligned.
  col 0 = HU0_RASTER (west), row 0 = HV0_RASTER (south), hv grows downward,
  pixel centre hu = hu0 + (px + 0.5) * mm / 1000.
"""
import os
import sys
import json
import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import trackA_geom as G  # noqa: E402  (huv axes, Cam/projection, sim helpers)

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
GLB = os.path.join(REPO, "model.glb")
SITE = "E:/sitecapture-captures/ngv-site/"
OUT_ROOT = SITE + "agent-ref-ceiling/underside/"

# --- raster (bottom-meta-v29 origin and mm/px; the east extent matches track A's sheet so the
#     topside and the underside are the same picture size) -----------------------------------
HU0_RASTER, HV0_RASTER = -56.635125, 0.158820
MM_DEFAULT = 4.0
W_DEFAULT, H_DEFAULT = 14857, 3693

# --- canopy, as index.html draws it (CANOPY block) -------------------------------------------
PU, PV = 7.36, 7.50
RELIEF, DIP, RIBH = 0.860, 0.030, 0.225
CAP_INSET = 0.05
PROUD = 0.006      # index.html buildGlassPieces: the pane face sits 6 mm below the plate face

# --- steel as SEEN FROM BELOW (reference/reference-stats.json rib_widths_mm_as_seen_from_below).
#     These are soffit widths measured on the lf02 straight-up photograph, so they are exactly
#     what hides a pixel from a camera on the floor. Half-widths in metres.
RIDGE_HALF = 0.477 / 2
CROSS_HALF = 0.231 / 2
HIP_HALF = 0.247 / 2
DIAG_HALF = 0.276 / 2
RIB_DEPTH = 0.30           # how far the members hang below the glass face
HUB_HALF, HUB_DEPTH = 0.31, 0.30     # the 0.62 m square column-head node, 300 mm deep
HUB_ARM_R, HUB_ARM_DEPTH = 0.56, 0.18  # the eight arms, 1.1 m across the node

# --- the permanent house lighting rig (index.html RIG). It is 4.7 m under the glass along the
#     north wall, so it streaks the north bays of every floor camera. EVENT.N.origin in huv.
RIG_HV = 12.8018            # north wall hv 15.0018 less RIG.d 2.2
RIG_Y = -1.43545 + 9.0      # carpet + RIG.y
RIG_HALF_HV = 0.35          # 300 mm truss plus the fixtures hanging off it
RIG_HALF_Y = 0.60
RIG_HU = (-51.906, -6.906)  # EVENT origin hu -52.9058 plus RIG.u0 1.0 .. RIG.u1 46.0


def raster_meta(mm=MM_DEFAULT, width=W_DEFAULT, height=H_DEFAULT):
    return {"hu0": HU0_RASTER, "hv0": HV0_RASTER, "mm_per_px": mm, "width": width, "height": height,
            "hu1": HU0_RASTER + width * mm / 1000.0, "hv1": HV0_RASTER + height * mm / 1000.0,
            "pixel_centre": "hu = hu0 + (px + 0.5) * mm_per_px / 1000; hv = hv0 + (py + 0.5) * mm_per_px / 1000",
            "orientation": "row 0 = south edge (hv0), col 0 = west end (hu0); hv grows downward, hu rightward",
            "huv_from_world": {"hu": "x*0.975681 + z*0.219196", "hv": "x*(-0.219196) + z*0.975681"}}


# ------------------------------------------------------------------ lattice, read off the GLB
def _fit_phase(vals, P):
    """index.html fitPhase: the modular mean of vals at period P (four sweeps is plenty)."""
    o = float(vals[0])
    for _ in range(4):
        o = float(np.mean([v - P * round((v - o) / P) for v in vals]))
    return o


def lattice(cache=None):
    """The canopy lattice the sim draws, measured off model.glb: phase, leaning vertex plane and
    the ridge-snapped plate rect. Cached as json because loading the GLB costs a few seconds."""
    if cache and os.path.exists(cache):
        return json.load(open(cache))
    import trimesh
    scene = trimesh.load(GLB, process=False)
    heads, glass, void = [], None, None
    for node in scene.graph.nodes_geometry:
        T, gname = scene.graph[node]
        g = scene.geometry[gname]
        name = (getattr(getattr(g.visual, "material", None), "name", "") or "").lower()
        V = trimesh.transform_points(g.vertices, T)
        if "column" in name:
            lo, hi = V.min(0), V.max(0)
            hu, hv = G.xz_to_huv((lo[0] + hi[0]) / 2, (lo[2] + hi[2]) / 2)
            heads.append({"hu": float(hu), "hv": float(hv), "top": float(hi[1]),
                          "box": [lo.tolist(), hi.tolist()], "name": name})
        elif name == "ceiling-glass":
            glass = V
        elif name == "flat-ceiling-void":
            void = V
    if len(heads) < 6 or glass is None:
        raise RuntimeError("model.glb: expected 12 column primitives and a ceiling-glass mesh")
    hus = [h["hu"] for h in heads]
    hvs = [h["hv"] for h in heads]
    ys = [h["top"] - CAP_INSET for h in heads]
    ou, ov = _fit_phase(hus, PU), _fit_phase(hvs, PV)
    A = np.stack([np.ones(len(heads)), hus, hvs], 1)
    plane = np.linalg.lstsq(A, np.array(ys), rcond=None)[0]
    gu, gv = G.xz_to_huv(glass[:, 0], glass[:, 2])
    wu, wv = (G.xz_to_huv(void[:, 0], void[:, 2]) if void is not None
              else (np.array([gu.min() - 0.7, gu.max() + 0.7]), np.array([gv.min() - 0.7, gv.max() + 0.7])))

    def ridge(x, P, o):
        return o + P * (round((x - o) / P - 0.5) + 0.5)
    su0 = ridge(gu.min(), PU, ou)
    su0 = su0 + PU if su0 < wu.min() - 0.02 else su0
    su1 = ridge(gu.max(), PU, ou)
    su1 = su1 - PU if su1 > wu.max() + 0.02 else su1
    sv0 = ridge(gv.min(), PV, ov)
    sv0 = sv0 + PV if sv0 < wv.min() - 0.02 else sv0
    sv1 = ridge(gv.max(), PV, ov)
    sv1 = sv1 - PV if sv1 > wv.max() + 0.02 else sv1
    out = {"source": "model.glb column heads + ceiling-glass footprint, index.html buildCanopy",
           "PU": PU, "PV": PV, "RELIEF": RELIEF, "DIP": DIP, "RIBH": RIBH,
           "phase_hu": ou, "phase_hv": ov, "plane": [float(p) for p in plane],
           "plate": [su0, su1, sv0, sv1], "bays": [int(round((su1 - su0) / PU)), int(round((sv1 - sv0) / PV))],
           "heads": heads}
    if cache:
        os.makedirs(os.path.dirname(cache), exist_ok=True)
        json.dump(out, open(cache, "w"), indent=1)
    return out


class Surface:
    """The underside of the canopy: the inverted-pyramid lattice of index.html, offset DOWN.

    slab is the drop below the plate face in metres (PROUD = the pane face). Everything the
    renderer needs about the sheet -- xyz, normal, rib distances, bay index -- comes from here.
    """

    def __init__(self, lat, slab=PROUD):
        self.PU, self.PV = lat["PU"], lat["PV"]
        self.ou, self.ov = lat["phase_hu"], lat["phase_hv"]
        self.plane = np.asarray(lat["plane"], float)
        self.su0, self.su1, self.sv0, self.sv1 = lat["plate"]
        self.slab = slab
        self.a = self.PU / 2 - lat["RIBH"]
        self.b = self.PV / 2 - lat["RIBH"]
        self.relief, self.dip, self.ribh = lat["RELIEF"], lat["DIP"], lat["RIBH"]

    def cell_local(self, hu, hv):
        """(du, dv) in the cell centred on the nearest funnel vertex."""
        du = ((hu - self.ou + self.PU / 2) % self.PU) - self.PU / 2
        dv = ((hv - self.ov + self.PV / 2) % self.PV) - self.PV / 2
        return du, dv

    def plane_at(self, hu, hv):
        return self.plane[0] + self.plane[1] * hu + self.plane[2] * hv

    def rel(self, hu, hv):
        """index.html coffRelief: 0 at the vertex, RELIEF on the crest square, RELIEF-DIP at the border."""
        du, dv = self.cell_local(hu, hv)
        t = np.maximum(np.abs(du) / self.a, np.abs(dv) / self.b)
        over = np.minimum(np.maximum(np.abs(du) - self.a, np.abs(dv) - self.b) / self.ribh, 1.0)
        return np.where(t <= 1, self.relief * t, self.relief - self.dip * over)

    def y(self, hu, hv):
        return self.plane_at(hu, hv) + self.rel(hu, hv) - self.slab

    def xyz_n(self, hu, hv):
        """hall xyz of the underside and its unit normal, pointing DOWN into the hall."""
        y = self.y(hu, hv)
        x, z = G.huv_to_xz(hu, hv)
        P = np.stack([x, y, z], 1)
        e = 0.01
        dyu = (self.y(hu + e, hv) - self.y(hu - e, hv)) / (2 * e)
        dyv = (self.y(hu, hv + e) - self.y(hu, hv - e)) / (2 * e)
        dydx = dyu * G.CU - dyv * G.SU
        dydz = dyu * G.SU + dyv * G.CU
        n = np.stack([dydx, -np.ones_like(dydx), dydz], 1)   # down-facing
        n /= np.linalg.norm(n, axis=1, keepdims=True)
        return P, n

    def in_plate(self, hu, hv, eps=1e-6):
        return (hu >= self.su0 - eps) & (hu < self.su1 + eps) & (hv >= self.sv0 - eps) & (hv < self.sv1 + eps)

    def bay(self, hu, hv):
        """bay (i 0..6 west->east, j 0 south / 1 north)."""
        bi = np.floor((hu - self.su0) / self.PU).astype(int)
        bj = np.floor((hv - self.sv0) / self.PV).astype(int)
        return bi, bj

    def rib_dists(self, hu, hv):
        """metres to the nearest ridge beam, cross member, main hip and edge-midpoint diagonal."""
        du, dv = self.cell_local(hu, hv)
        A, B = self.PU / 2, self.PV / 2
        ridge = np.minimum(A - np.abs(du), B - np.abs(dv))
        cross = np.minimum(np.abs(du), np.abs(dv))
        # the two vertex-to-corner lines du/A = +/- dv/B
        k = np.hypot(1.0 / A, 1.0 / B)
        hip = np.minimum(np.abs(du / A - dv / B), np.abs(du / A + dv / B)) / k
        # the diamond through the four edge midpoints: |du|/A + |dv|/B = 1
        diag = np.abs(np.abs(du) / A + np.abs(dv) / B - 1.0) / k
        return ridge, cross, hip, diag

    def steel_code(self, hu, hv):
        """Which member's soffit the pixel itself is: 0 glass, 1 ridge, 2 cross, 3 hip, 4 diamond,
        5 hub node. Used to exempt a member from occluding ITSELF (see occluded_from_below)."""
        ridge, cross, hip, diag = self.rib_dists(hu, hv)
        du, dv = self.cell_local(hu, hv)
        c = np.zeros(np.shape(hu), np.uint8)
        c = np.where(diag < DIAG_HALF, 4, c)
        c = np.where(hip < HIP_HALF, 3, c)
        c = np.where(cross < CROSS_HALF, 2, c)
        c = np.where(ridge < RIDGE_HALF, 1, c)
        c = np.where(np.maximum(np.abs(du), np.abs(dv)) < HUB_HALF, 5, c)
        return c.astype(np.uint8)

    def on_steel(self, hu, hv):
        """True where the pixel itself is painted steel, not glass (the members' own soffit)."""
        return self.steel_code(hu, hv) > 0


# --------------------------------------------------------------- distortion domain guard
def distortion_ok(cam, P):
    """True where the OPENCV distortion model is still single-valued for this point.

    THE BUG THIS FIXES, in the plainest terms: the radial polynomial 1 + k1*r^2 + k2*r^4 is only
    meant for rays inside the lens's field of view. Past a certain angle it turns over and goes
    negative, which FOLDS a ray pointing 70 deg off the optical axis back onto a pixel near the
    middle of the frame. cam.inside() then happily accepts it. On these frames that painted whole
    fans of the sheet with a smear of whatever was near the frame centre -- a wall, a step, the
    glass seen edge-on -- at a healthy-looking gsd, because the distance and the incidence to the
    sheet were both perfectly reasonable. Every plate pixel outside the real field of view is now
    rejected, at both ends: rad must stay positive, and the mapping r -> r*rad must still be
    increasing (1 + 3*k1*r^2 + 5*k2*r^4 > 0). For the cameras here the limit falls at 57-58 deg
    off axis and the frame corners sit at 40 deg, so nothing real is lost.
    """
    if cam.model != "OPENCV":
        Xc = P @ cam.R.T + cam.t
        return Xc[:, 2] > 0
    Xc = P @ cam.R.T + cam.t
    z = Xc[:, 2]
    with np.errstate(divide="ignore", invalid="ignore"):
        xn = Xc[:, 0] / z
        yn = Xc[:, 1] / z
    k1, k2 = cam.params[4], cam.params[5]
    r2 = xn * xn + yn * yn
    rad = 1 + k1 * r2 + k2 * r2 * r2
    drad = 1 + 3 * k1 * r2 + 5 * k2 * r2 * r2
    return (z > 0) & np.isfinite(r2) & (rad > 0.2) & (drad > 0)


# ------------------------------------------------------------------------------- occluders
def occluded_from_below(surf, P, centre, columns, steel_code=None):
    """True where the ray from the sheet point P DOWN to the camera centre is blocked.

    Everything that hides underside glass hangs below the sheet: the members' own depth (they
    are ~0.3 m deep, so a member 2 m away in plan still eats the view at 80 deg), the column-head
    hub nodes, the house lighting truss along the north wall, and the twelve columns.
    """
    d = centre[None, :] - P
    dist = np.linalg.norm(d, axis=1)
    d = d / dist[:, None]
    drop = np.maximum(-d[:, 1], 0.02)          # the ray descends; guard the near-horizontal case
    occ = np.zeros(len(P), bool)
    for t in (0.05, 0.11, 0.17, 0.23, 0.30):   # sample the members' depth band
        s = t / drop
        Q = P + d * s[:, None]
        qu, qv = G.xz_to_huv(Q[:, 0], Q[:, 2])
        ridge, cross, hip, diag = surf.rib_dists(qu, qv)
        du, dv = surf.cell_local(qu, qv)
        parts = [ridge < RIDGE_HALF, cross < CROSS_HALF, hip < HIP_HALF, diag < DIAG_HALF,
                 (np.maximum(np.abs(du), np.abs(dv)) < HUB_HALF) & (t <= HUB_DEPTH)
                 | (np.hypot(du, dv) < HUB_ARM_R) & (t <= HUB_ARM_DEPTH)]
        # A pixel that IS a member's soffit would occlude ITSELF here, punching the steel out of the
        # picture and leaving nothing to check the registration against. Exempt only the member the
        # pixel sits on: at 75 deg and 0.3 m of depth the ray travels 1.1 m sideways, which cannot
        # reach the next line of the same family (they are 7.4 m apart), so nothing real is missed.
        for k, hit in enumerate(parts):
            if steel_code is not None:
                hit = hit & (steel_code != k + 1)
            occ |= hit
    # the lighting truss, as one box in (hu, hv, y): an exact slab test, not sampled, because the
    # bar is only 300 mm thick and a sampled ray walks straight through it
    Phuv = np.stack([*G.xz_to_huv(P[:, 0], P[:, 2]), P[:, 1]], 1)
    dhuv = np.stack([*G.xz_to_huv(d[:, 0], d[:, 2]), d[:, 1]], 1)
    occ |= _slab_hit(Phuv, dhuv, dist,
                     np.array([RIG_HU[0], RIG_HV - RIG_HALF_HV, RIG_Y - RIG_HALF_Y]),
                     np.array([RIG_HU[1], RIG_HV + RIG_HALF_HV, RIG_Y + RIG_HALF_Y]))
    # the twelve columns: a ray to a floor camera at the far end of the hall can graze one
    for lo, hi in columns:
        occ |= _slab_hit(P, d, dist, lo, hi)
    return occ


def _slab_hit(O, D, tmax, lo, hi):
    """Ray/AABB: does the segment O + s*D, 0 < s < tmax, enter the box? (vectorised over rows)"""
    t0 = np.zeros(len(O))
    t1 = np.asarray(tmax, float).copy()
    with np.errstate(divide="ignore", invalid="ignore"):
        for k in range(3):
            inv = 1.0 / D[:, k]
            a = (lo[k] - O[:, k]) * inv
            b = (hi[k] - O[:, k]) * inv
            t0 = np.maximum(t0, np.minimum(a, b))
            t1 = np.minimum(t1, np.maximum(a, b))
    return np.nan_to_num(t1 - t0, nan=-1.0) > 0.02   # 20 mm of chord: ignore a pure graze


# --------------------------------------------------------------------------------- sources
CERT_MODEL = "E:/sitecapture-captures/ngv-video/day4k-register/model"
CERT_IMG = "E:/sitecapture-captures/ngv-site/rebuild-site-images-colour-certified/"
D4_MODEL = "E:/sitecapture-captures/ngv-video/day4k-register/work/model-d4-accepted"
D4_IMG = "E:/sitecapture-captures/ngv-video/day4k-register/images-colour-d4-accepted/"

# Which certified walk prefix is which capture (SCANS.md registered counts pin them uniquely):
#   w1 = 155626 20260809 day floor walk (627)   w2 = 160433 20260809 day floor walk (162)
#   w5 = 191702 20260817 night floor scan (72)  w6 = 191831 20260817 night floor scan (27)
# r* prefixes are in the same model but have NO exported colour frame, so they cannot be sampled.
CLASSES = {
    "day4k": {"prefixes": None, "model": D4_MODEL, "img": D4_IMG, "factor": 1.0,
              "note": "4K balcony video, 138 accepted frames, east balcony, daylight"},
    "night": {"prefixes": ("w5", "w6"), "model": CERT_MODEL, "img": CERT_IMG, "factor": 1.0,
              "note": "20260817 night hall-floor scans 191702 + 191831, certified model"},
    "walk": {"prefixes": ("w1", "w2"), "model": CERT_MODEL, "img": CERT_IMG, "factor": 1.0,
             "note": "20260809 day hall-floor walks 155626 + 160433, certified model"},
}
# the 2026-09-09 balcony and gallery clips (Lloyd's Drive folder, balcony2/map.txt): registered one clip at a
# time in balcony2-register with the day4k camera frozen; "frames" is the full extracted set (every 2nd frame),
# "img" the accepted ones. b6s / b7s are thinned sets of the two long clips (balcony2_subset.py).
B2 = "E:/sitecapture-captures/ngv-video/balcony2"
# b6g is the tight gallery set from clip 153148 (frames 1000-1340, every 2nd). Only 6 of its 171 frames
# registered, all refused elsewhere for 7-9 inliers, but those six settle the question the clip was cut
# for: they stand on the EAST UPPER BALCONY (u 49.1-49.4, d 13.4-13.7, h 9.6-9.8, looking west), not
# behind the north wall. tools/b6g_where.py prints them.
# THE RE-GATED SETS WERE WITHDRAWN THE SAME DAY THEY WERE ADDED (2026-09-09), and the reason is worth
# keeping. The DIAGNOSIS behind them is right: the acceptance gate that produced the "-accepted" models was
# written for floor walks and threw away two thirds of Lloyd's balcony footage for reasons unrelated to pose
# quality (an inlier cut of 30 that refuses the median frame of three of four clips, no standing band for
# the lower balcony, and a walking-speed continuity chain applied to an operator standing still and
# panning). That is all confirmed and is now fixed inside register_day4k.py itself.
# The EXPORT was wrong. tools/regate_export.py built the wider sets by subsetting work/reg-<prefix>, and
# reg-<prefix> is the register's raw output, not the refined model. Measured: the strict 25 b3 frames read
# from model-b3-accepted match their own report to 45 mm, while the same frames read from reg-b3 disagree by
# a median of 0.295 m and a maximum of 10.90 m, and the re-gated model built from it carried camera heights
# from -5.62 to 12.68 m, which is below the floor and above the roof. Every measurement taken through those
# models is void, including the ones that appeared to overturn the east parapet.
# The right way is to widen the gate in the registrar and re-run its final stage with --skip-match, so the
# extra frames go through the same refinement the accepted ones did. register_day4k.py now takes
# --standing-floors and --pan-tolerant for exactly that.
for _t in ("b1", "b3", "b4", "b5", "b6s", "b7s", "b6g"):
    CLASSES[_t] = {"prefixes": None, "model": B2 + "-register/work/model-%s-accepted" % _t,
                   "img": B2 + "-register/images-colour-%s-accepted/" % _t, "frames": B2 + "/%s/images/" % _t,
                   "factor": 1.0, "note": "20260809 4K balcony/gallery clip %s, registered 2026-09-09" % _t}

# THE PAN CLASSES, 2026-09-09, and how they differ from the withdrawn re-gated ones above. Lloyd: "those
# frames are me looking at the hall. but they should be more frames when I look around the actual balcony
# area." He is right: the accepted sets are the frames aimed DOWN THE HALL, because the site model those
# frames were solved against is the hall and carries almost no surface on the balconies, so a frame turned
# toward the parapet has nothing to match. tools/pan_poses.py builds the missing poses from the clip's own
# frame-to-frame matches, which tools/clip_selfmatch.py added.
# WHAT MAKES THESE LEGITIMATE WHERE THE RE-GATED SETS WERE NOT. The re-gated models subsetted work/reg-*,
# the register's RAW output, and inherited its unrefined poses. These are anchored on model-<t>-accepted,
# the SAME refined model every accepted measurement already uses, and add only a rotation measured from
# image correspondences plus a position interpolated between two of those refined poses. Nothing raw enters.
# WHAT THEY COST. Every frame carries its own error in pan-quality.json beside the model: the leave-one-out
# position error per clip is 0.024 to 0.100 m and the rotation hold-out is 0.17 to 0.58 deg. That is fine
# for something a few metres away, which is the balcony the operator is standing on, and poor for the far
# end of the hall, which the accepted frames already measure better. Use these for what is NEAR the camera.
for _t in ("b1", "b3", "b5", "b7s", "b6g"):
    CLASSES[_t + "p"] = {"prefixes": None, "model": B2 + "-register/work/model-%s-pan" % _t,
                         "img": B2 + "/%s/images/" % _t, "frames": B2 + "/%s/images/" % _t, "factor": 1.0,
                         "note": "clip %s, anchors from model-%s-accepted plus pan-chained frames" % (_t, _t)}


def load_class(name, plate_y=13.0):
    """{frame: (Cam, image path)} for one source class, hall frame, cameras below the glass only."""
    from colmap_bin import read_model
    spec = CLASSES[name]
    cams, imgs, _ = read_model(spec["model"], with_points2d=False)
    out = {}
    for im in imgs.values():
        base = os.path.basename(im.name)
        stem = base.rsplit(".", 1)[0]
        if spec["prefixes"] is not None and not stem.split("_")[0] in spec["prefixes"]:
            continue
        c = cams[im.camera_id]
        cam = G.Cam(c.model, c.width, c.height, c.params, im.R(), im.t)
        if cam.center[1] > plate_y:      # a roof-void frame cannot see the underside
            continue
        path = spec["img"] + base
        if not os.path.exists(path):
            continue
        out[stem] = (cam, path)
    return out
