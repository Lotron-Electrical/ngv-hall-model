"""Orthophoto of one long wall of the NGV Great Hall, rendered straight from the posed frames.

Same method as tools/underside_ortho.py, turned on its side: every raster pixel is a real point on
the wall, projected into every posed camera of the source class, and painted from the ONE camera
that sees it best. Nothing is baked, averaged, inpainted or mirrored; a pixel no camera sees stays
unobserved (mask 0).

  python tools/wall_ortho.py --wall north|south --source walk|night|day4k|all --out <dir>
                             [--mm 4] [--workers 12] [--tile 1024] [--max-inc 75]

Raster (written verbatim into meta.json): col 0 = u 0.0 at the WEST end wall, row 0 = the TOP of
the render at 13.0 m above the carpet, u rightward, height downward.
  u = (px + 0.5) * mm/1000            h = TOP - (py + 0.5) * mm/1000
  world = HALL.origin + u*HALL.u + d*HALL.inRoom + (0, h, 0)
At 4 mm that is 12977 x 3250 px for u 0 .. 51.906 and h 13.0 .. 0.

THE SAMPLING SURFACE is not a bare plane. model.glb's `walls` mesh is planar to well under a
millimetre over ~81 % of each long wall, but the remaining fifth is stone courses standing 150 mm
and 210 mm PROUD of that plane, and the middle 16 m of the south wall is not stone at all but the
glazed screen to the garden, set back behind its fins. A 210 mm depth error at the 75 deg grazing
incidence these floor cameras work at drags the sample 780 mm along the wall, so the surface here
is the GLB's own geometry: the room-facing faces of every mesh within 1.1 m of the fitted plane are
z-buffered into the raster (frontmost wins), giving an exact depth and an exact normal per pixel.
The fitted plane is the fallback only where the GLB has no face at all (openings, the door), and
meta.json records which pixels used which. The same geometry, at 40 mm, is what the self-occlusion
test marches the ray against, so a proud course correctly shadows the recess beside it.

AND THE WHOLE SURFACE IS THEN MOVED, by an offset MEASURED FROM THE FRAMES (tools/wall_depth_check.py,
written to <out>/depth-offset-<wall>.json and applied automatically). The GLB is a decimated blocky
envelope: its faces are exactly planar but they are not exactly where the photographed stone is. Two
independent measurements agree that they are set too far back -- the certified sparse cloud and, more
reliably, a stacked cross-correlation of every patch resampled from two widely separated cameras at a
sweep of depths, which peaks where the two views agree and nowhere else. North +49 mm, south +185 mm.
Left uncorrected, the south error alone drags each sample 320 mm along the wall at 60 deg incidence.
"""
import os
import sys
import json
import time
import argparse
import numpy as np
import cv2

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import underside_geom as U
import underside_ortho as UO
import trackA_geom as G

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
GLB = os.path.join(REPO, "model.glb")

# --- the hall frame (game/world.js HALL), unchanged ------------------------------------------
HALL_O = np.array([-54.907447, -1.43545, 3.040286])
HALL_U = np.array([0.975681, 0.0, 0.219196])
HALL_D = np.array([0.219196, 0.0, -0.975681])
U_WEST, U_EAST = 0.344, 51.906          # index.html ENDW.west / ENDW.east
TOP = 13.0                              # render 0 .. 13 m above the carpet
MM_DEFAULT = 4.0

# the twelve columns (game/world.js COLUMN_FEET), as cylinders: 0.26 m shaft + fins -> 0.40 m
COLUMN_FEET = [[7.71, 3.82], [7.53, 11.41], [14.94, 3.86], [14.88, 11.29], [22.3, 3.86],
               [22.17, 11.33], [29.67, 3.77], [29.96, 11.15], [37.18, 3.84], [36.82, 11.52],
               [44.54, 3.80], [44.23, 11.27]]
COLUMN_R = 0.40

# the permanent house lighting truss (underside_geom RIG_*), in hall (u, d, h)
RIG_U = (1.0, 46.0)
RIG_D = 2.2
RIG_H = 9.0
RIG_HALF_D = 0.35
RIG_HALF_H = 0.60

D_SOUTH = 15.38       # index.html WALLF.dSouth: the far side of the hall
D_MAX = 15.5          # the end-wall raster runs d 0 .. 15.5

# The two end walls are NOT in model.glb. Its `walls` mesh closes the hall at u = -5.393 and
# u = 48.905 -- five metres past the real west wall and three metres short of the real east one
# (index.html ENDW, from the ceiling session's trace of the NGV panorama: the plate ends on the
# vertex phase one bay past the outer columns, u 0.344 and 51.906). index.html cuts both scan
# closures out and builds the real end walls with the gallery the balcony photographs show, so
# THAT is the surface sampled here: the same quads buildEndWalls draws, z-buffered. The plane
# lean with height is measured off the GLB own closures (both give -0.000488 per metre, 6 mm
# over the full height), because a wall built from two numbers carries no lean of its own.
ENDW = {"west": 0.344, "east": 51.906, "top": 13.5,
        "recess": {"d0": 3.9, "d1": 11.5, "y0": 1.8, "y1": 10.0, "depth": 6.0,
                   "tiers": [3.6, 6.4, 9.2], "slab": 0.35}}
END_TILT = -0.000488

# axis: which hall coordinate runs ACROSS the raster (the other one is the wall depth).
# sgn: +1 where the room is at a larger value of the depth coordinate.
# flip: col 0 is at s = smax instead of s = 0, so both end walls read as seen from inside.
WALLS = {
    "north": {"axis": "u", "sgn": +1.0, "band": (-1.30, 0.90), "s0": U_WEST, "s1": U_EAST,
              "smax": U_EAST, "flip": False, "plane": None},
    "south": {"axis": "u", "sgn": -1.0, "band": (14.60, 16.70), "s0": U_WEST, "s1": U_EAST,
              "smax": U_EAST, "flip": False, "plane": None},
    "west":  {"axis": "d", "sgn": +1.0, "band": (-1.20, 1.80), "s0": 0.0, "s1": D_SOUTH,
              "smax": D_MAX, "flip": False, "plane": [ENDW["west"], 0.0, END_TILT]},
    "east":  {"axis": "d", "sgn": -1.0, "band": (50.70, 53.20), "s0": 0.0, "s1": D_SOUTH,
              "smax": D_MAX, "flip": True, "plane": [ENDW["east"], 0.0, END_TILT]},
}


def s_to_px(wall, s, mm):
    w = WALLS[wall]
    v = (w["smax"] - s) if w["flip"] else s
    return v / (mm / 1000.0) - 0.5


def px_to_s(wall, px, mm):
    w = WALLS[wall]
    v = (np.asarray(px) + 0.5) * mm / 1000.0
    return (w["smax"] - v) if w["flip"] else v


def hall_of(wall, s, depth):
    """(u, d) from the wall across coordinate and its depth coordinate."""
    return (s, depth) if WALLS[wall]["axis"] == "u" else (depth, s)


def depth_axis(wall):
    return HALL_D if WALLS[wall]["axis"] == "u" else HALL_U


def across_axis(wall):
    return HALL_U if WALLS[wall]["axis"] == "u" else HALL_D

CELL = 32        # camera-choice cell, px
STRIDE = 4       # the choice pass runs on every 4th pixel (see underside_ortho)
NOCAM = 65535
COARSE_MM = 40.0  # the self-occlusion protrusion map

_S = {}


# ------------------------------------------------------------------ hall frame <-> world
def hall_to_world(u, d, h):
    return (HALL_O[None, :] + np.asarray(u)[:, None] * HALL_U[None, :]
            + np.asarray(d)[:, None] * HALL_D[None, :]
            + np.stack([np.zeros_like(h), np.asarray(h), np.zeros_like(h)], 1))


def world_to_hall(P):
    R = np.asarray(P) - HALL_O
    return R @ HALL_U, R @ HALL_D, R[..., 1]


# ------------------------------------------------------------------ the wall, off model.glb
def _end_wall_tris():
    """index.html buildEndWalls, as quads in (d, h, p): the piers, lintel, base, the 6 m gallery
    recess with its stone reveals, dark back and soffit, and the three tiers as slabs across it.
    p is metres into the wall, so p = 0 is the face and p = -6 the back of the gallery."""
    R = ENDW["recess"]
    T, D = ENDW["top"], D_SOUTH
    d0, d1, y0, y1, dep = R["d0"], R["d1"], R["y0"], R["y1"], R["depth"]
    q = [[(0, 0, 0), (d0, 0, 0), (d0, T, 0), (0, T, 0)],
         [(d1, 0, 0), (D, 0, 0), (D, T, 0), (d1, T, 0)],
         [(d0, y1, 0), (d1, y1, 0), (d1, T, 0), (d0, T, 0)],
         [(d0, 0, 0), (d1, 0, 0), (d1, y0, 0), (d0, y0, 0)],
         [(d0, y0, 0), (d0, y0, -dep), (d0, y1, -dep), (d0, y1, 0)],
         [(d1, y0, 0), (d1, y0, -dep), (d1, y1, -dep), (d1, y1, 0)],
         [(d0, y0, -dep), (d1, y0, -dep), (d1, y1, -dep), (d0, y1, -dep)],
         [(d0, y1, 0), (d1, y1, 0), (d1, y1, -dep), (d0, y1, -dep)],
         [(d0, y0, 0), (d1, y0, 0), (d1, y0, -dep), (d0, y0, -dep)]]
    for y in R["tiers"]:
        yb = y + R["slab"]
        q += [[(d0, yb, 0), (d1, yb, 0), (d1, yb, -dep), (d0, yb, -dep)],
              [(d0, y, 0), (d1, y, 0), (d1, y, -dep), (d0, y, -dep)],
              [(d0, y, 0), (d1, y, 0), (d1, yb, 0), (d0, yb, 0)]]
    tri = []
    for a, b, c, e in q:
        tri += [[a, b, c], [a, c, e]]
    return np.asarray(tri, float)


def _wall_faces(wall):
    """The wall triangles, in (s, h, protrusion).

    Returns (tris_room, tris_all, normals, plane, stats). tris_* are (N, 3, 3) arrays of vertices
    as (s, h, p) where s is the raster across coordinate and p is metres PROUD of the plane,
    towards the room. tris_room is the visible surface; tris_all is what the self-occlusion ray
    marches against, so a glazing fin edge-on still casts its shadow.
    """
    spec = WALLS[wall]
    sgn = spec["sgn"]
    DEP, ACR = depth_axis(wall), across_axis(wall)

    if spec["plane"] is not None:
        # --- an END wall: model.glb has no face here, so the surface is index.html own quads
        q = _end_wall_tris()
        c = spec["plane"]
        s_, h_, p_ = q[:, :, 0], q[:, :, 1], q[:, :, 2]
        dep = c[0] + c[1] * s_ + c[2] * h_ + sgn * p_
        uu, dd = hall_of(wall, s_, dep)
        Wp = (HALL_O[None, None, :] + uu[:, :, None] * HALL_U[None, None, :]
              + dd[:, :, None] * HALL_D[None, None, :]
              + np.stack([np.zeros_like(h_), h_, np.zeros_like(h_)], 2))
        nn = np.cross(Wp[:, 1] - Wp[:, 0], Wp[:, 2] - Wp[:, 0])
        area = np.linalg.norm(nn, axis=1) / 2
        nn = nn / np.maximum(np.linalg.norm(nn, axis=1, keepdims=True), 1e-12)
        tris = np.stack([s_, h_, p_], 2).astype(np.float32)
        plane = {"d = a + b*u + c*h": [float(x) for x in c],
                 "d_at_h0_m": float(c[0]), "tilt_with_height_deg": float(np.degrees(np.arctan(c[2]))),
                 "tilt_along_u_deg": 0.0, "inlier_share_of_area": 1.0, "inlier_rms_mm": 0.0,
                 "quadratic_bow_over_u_mm": 0.0, "samples": 0,
                 "note": "NOT fitted: model.glb has no end wall at this station (its closures are "
                         "at u -5.393 and u 48.905). The plane is index.html ENDW, and the lean "
                         "with height is the one both GLB closures carry, -0.000488 per metre.",
                 "off_plane_bands_m_share": {}}
        stats = {"faces_in_band": len(tris), "room_facing_faces": len(tris),
                 "room_facing_area_m2": round(float(area.sum()), 1),
                 "meshes_in_band_area_m2": {"index.html buildEndWalls quads": round(float(area.sum()), 1)}}
        return tris, tris, nn.astype(np.float32), plane, stats

    import trimesh
    scene = trimesh.load(GLB, process=False)
    blo, bhi = spec["band"]
    V, Fi, mesh_names = [], [], []
    for node in scene.graph.nodes_geometry:
        T, gname = scene.graph[node]
        g = scene.geometry[gname]
        name = (getattr(getattr(g.visual, "material", None), "name", "") or "").lower()
        if "column" in name:
            continue                     # the columns stand in the room, not on the wall
        W = trimesh.transform_points(g.vertices, T)
        Fi.append(np.asarray(g.faces) + sum(len(x) for x in V))
        V.append(W)
        mesh_names.append((name, len(Fi[-1])))
    V = np.concatenate(V)
    Fi = np.concatenate(Fi)
    tri = V[Fi]
    cu, cd, ch = world_to_hall(tri.mean(1))
    nrm = np.cross(tri[:, 1] - tri[:, 0], tri[:, 2] - tri[:, 0])
    area = np.linalg.norm(nrm, axis=1) / 2
    nrm = nrm / np.maximum(np.linalg.norm(nrm, axis=1, keepdims=True), 1e-12)
    inband = (cd > blo) & (cd < bhi) & (cu > -0.5) & (cu < U_EAST + 0.5) & (ch > -0.3) & (ch < TOP + 0.6)

    # --- the fitted plane: an area-weighted robust (Tukey) fit of d = a + b*u + c*h to the
    #     room-facing faces, so the dominant wall face wins and the proud courses fall out as
    #     outliers rather than dragging the plane out between them.
    face = inband & (np.abs(nrm @ HALL_D) > 0.95)
    tf = tri[face]
    n_s = max(int(area[face].sum() / 0.0004), 20000)          # ~1 sample per 2 cm of wall
    rng = np.random.default_rng(7)
    w = area[face] / area[face].sum()
    pick = rng.choice(len(tf), size=min(n_s, 400000), p=w)
    r1, r2 = rng.random(len(pick)), rng.random(len(pick))
    bad = r1 + r2 > 1
    r1[bad], r2[bad] = 1 - r1[bad], 1 - r2[bad]
    S = tf[pick, 0] + r1[:, None] * (tf[pick, 1] - tf[pick, 0]) + r2[:, None] * (tf[pick, 2] - tf[pick, 0])
    su, sd, sh = world_to_hall(S)
    ok = (su > U_WEST) & (su < U_EAST) & (sh > 0.0) & (sh < TOP - 0.2)
    su, sd, sh = su[ok], sd[ok], sh[ok]
    X = np.stack([np.ones(len(su)), su, sh], 1)
    c = np.array([np.median(sd), 0.0, 0.0])
    for _ in range(30):
        r = sd - X @ c
        s = 1.4826 * np.median(np.abs(r - np.median(r))) + 1e-4
        t = np.clip(r / (2.5 * s), -1, 1)
        wt = (1 - t * t) ** 2
        c = np.linalg.lstsq(X * wt[:, None], sd * wt, rcond=None)[0]
    r = sd - X @ c
    inl = np.abs(r) < 0.03
    q = np.polyfit(su[inl], r[inl], 2)
    uu = np.linspace(U_WEST, U_EAST, 200)
    plane = {"d = a + b*u + c*h": [float(c[0]), float(c[1]), float(c[2])],
             "d_at_h0_m": float(c[0]), "tilt_with_height_deg": float(np.degrees(np.arctan(c[2]))),
             "tilt_along_u_deg": float(np.degrees(np.arctan(c[1]))),
             "inlier_share_of_area": float(inl.mean()),
             "inlier_rms_mm": float(1000 * r[inl].std()),
             "quadratic_bow_over_u_mm": float(1000 * np.abs(np.polyval(q, uu) - np.polyval(q, uu).mean()).max()),
             "samples": int(len(su)),
             "note": "robust area-weighted fit to the room-facing faces of model.glb 'walls' in "
                     "the hall frame; the outliers are the proud stone courses, not noise"}
    # the off-plane structure, so the report can name the courses
    hist, edges = np.histogram(r, bins=np.arange(-0.60, 0.62, 0.02))
    plane["off_plane_bands_m_share"] = {("%+.2f" % (edges[i] + 0.01)): round(float(hist[i] / len(r)), 4)
                                        for i in range(len(hist)) if hist[i] / len(r) > 0.01}

    def to_uhp(t):
        a, b, e = world_to_hall(t.reshape(-1, 3))
        p = sgn * (b - (c[0] + c[1] * a + c[2] * e))
        return np.stack([a, e, p], 1).reshape(-1, 3, 3).astype(np.float32)

    # the GLB's winding is not consistent across its meshes, so take any face that stands up
    # across the wall (|n.d| > 0.3) and orient its normal into the room in surface() below
    room = inband & (np.abs(nrm @ HALL_D) > 0.30)
    owner = np.concatenate([np.full(k, i) for i, (_, k) in enumerate(mesh_names)])
    seen = {}
    for i in np.unique(owner[inband]):
        seen[mesh_names[i][0]] = round(float(area[inband & (owner == i)].sum()), 1)
    stats = {"faces_in_band": int(inband.sum()), "room_facing_faces": int(room.sum()),
             "room_facing_area_m2": round(float(area[room].sum()), 1),
             "meshes_in_band_area_m2": dict(sorted(seen.items(), key=lambda kv: -kv[1]))}
    return to_uhp(tri[room]), to_uhp(tri[inband]), nrm[room].astype(np.float32), plane, stats


def wall_geometry(wall, cache):
    """The wall's plane + triangles, cached (loading the GLB costs a few seconds per worker)."""
    if cache and os.path.exists(cache):
        z = np.load(cache, allow_pickle=True)
        return (z["room"], z["all"], z["nrm"], json.loads(str(z["plane"])), json.loads(str(z["stats"])))
    room, alltri, nrm, plane, stats = _wall_faces(wall)
    if cache:
        os.makedirs(os.path.dirname(cache), exist_ok=True)
        np.savez_compressed(cache, room=room, all=alltri, nrm=nrm,
                            plane=json.dumps(plane), stats=json.dumps(stats))
    return room, alltri, nrm, plane, stats


# --------------------------------------------------------------------------- rasterisation
def raster_tris(wall, tris, x0, y0, w, h, mm, fill=-1e9):
    """Z-buffer triangles given as (N,3,3) of (s, h, p) into the raster window.

    Returns (P, IDX): protrusion in metres (fill where nothing covers the pixel) and the winning
    triangle index (-1 where nothing does). FRONTMOST wins, i.e. the largest p.
    """
    P = np.full((h, w), fill, np.float32)
    IDX = np.full((h, w), -1, np.int32)
    if not len(tris):
        return P, IDX
    px = s_to_px(wall, tris[:, :, 0], mm) - x0
    py = (TOP - tris[:, :, 1]) / (mm / 1000.0) - 0.5 - y0
    pz = tris[:, :, 2]
    lo_x = np.floor(px.min(1)).astype(int)
    hi_x = np.ceil(px.max(1)).astype(int)
    lo_y = np.floor(py.min(1)).astype(int)
    hi_y = np.ceil(py.max(1)).astype(int)
    cand = np.nonzero((hi_x >= 0) & (lo_x < w) & (hi_y >= 0) & (lo_y < h))[0]
    for i in cand:
        ax, ay = px[i, 0], py[i, 0]
        bx, by = px[i, 1], py[i, 1]
        cx, cy = px[i, 2], py[i, 2]
        den = (by - cy) * (ax - cx) + (cx - bx) * (ay - cy)
        if abs(den) < 1e-9:
            continue
        xa, xb = max(lo_x[i], 0), min(hi_x[i] + 1, w)
        ya, yb = max(lo_y[i], 0), min(hi_y[i] + 1, h)
        if xa >= xb or ya >= yb:
            continue
        X, Y = np.meshgrid(np.arange(xa, xb), np.arange(ya, yb))
        l1 = ((by - cy) * (X - cx) + (cx - bx) * (Y - cy)) / den
        l2 = ((cy - ay) * (X - cx) + (ax - cx) * (Y - cy)) / den
        l3 = 1.0 - l1 - l2
        e = 1e-6
        inside = (l1 >= -e) & (l2 >= -e) & (l3 >= -e)
        if not inside.any():
            continue
        z = l1 * pz[i, 0] + l2 * pz[i, 1] + l3 * pz[i, 2]
        sub = P[ya:yb, xa:xb]
        take = inside & (z > sub)
        sub[take] = z[take]
        IDX[ya:yb, xa:xb][take] = i
    return P, IDX


def coarse_map(wall, alltri, mm=COARSE_MM):
    """The whole wall frontmost protrusion at 40 mm, for the self-occlusion ray march."""
    w = int(np.ceil(WALLS[wall]["smax"] * 1000.0 / mm))
    h = int(np.ceil(TOP * 1000.0 / mm))
    P, _ = raster_tris(wall, alltri, 0, 0, w, h, mm, fill=-9.0)
    return P


def coarse_lookup(wall, C, s, hgt, mm=COARSE_MM):
    x = np.clip(np.round(s_to_px(wall, s, mm)).astype(np.int32), 0, C.shape[1] - 1)
    y = np.clip(((TOP - hgt) / (mm / 1000.0) - 0.5).astype(np.int32), 0, C.shape[0] - 1)
    return C[y, x]


# ------------------------------------------------------------------------------ occluders
def _occluded(wall, sv, hgt, prot, P, centre, C, sgn, plane, cols, rig):
    """True where the ray from the wall point P to the camera centre is blocked."""
    d = centre[None, :] - P
    dist = np.linalg.norm(d, axis=1)
    d = d / dist[:, None]
    occ = np.zeros(len(P), bool)

    # --- the wall own proud courses (and the fins, and the gallery reveals of an end wall),
    #     marched in the wall own depth map
    du, dd, dh = d @ HALL_U, d @ HALL_D, d[:, 1]
    dacr, ddep = (du, dd) if WALLS[wall]["axis"] == "u" else (dd, du)
    out = sgn * ddep                                    # metres out of the wall per metre of ray
    out = np.where(out > 1e-4, out, 1e-4)
    for t in (0.06, 0.12, 0.20, 0.30, 0.45, 0.9, 1.8, 3.5, 6.0):
        st = t / out
        qp = coarse_lookup(wall, C, sv + dacr * st, hgt + dh * st)
        occ |= (qp > prot + t + 0.02) & (st < dist)

    # --- the twelve columns, as cylinders from the carpet to the canopy
    depv = sgn * prot + plane[0] + plane[1] * sv + plane[2] * hgt
    pu, pd = hall_of(wall, sv, depv)
    ph = hgt
    ou, od = du, dd
    for cu0, cd0 in cols:
        ex, ez = pu - cu0, pd - cd0
        a = np.maximum(ou * ou + od * od, 1e-9)
        b = 2 * (ex * ou + ez * od)
        cc = ex * ex + ez * ez - COLUMN_R * COLUMN_R
        disc = b * b - 4 * a * cc
        hit = disc > 0
        if not hit.any():
            continue
        sq = np.sqrt(np.maximum(disc, 0))
        t0 = (-b - sq) / (2 * a)
        t1 = (-b + sq) / (2 * a)
        seg = hit & (t1 > 0.02) & (t0 < dist - 0.02)
        if not seg.any():
            continue
        ta = np.clip(t0, 0, dist)
        yb = ph + dh * ta
        occ |= seg & (yb > -0.05) & (yb < 12.4)

    # --- the house lighting truss, as one box in (u, d, h)
    if rig:
        O = np.stack([pu, pd, ph], 1)
        D = np.stack([ou, od, dh], 1)
        lo = np.array([RIG_U[0], RIG_D - RIG_HALF_D, RIG_H - RIG_HALF_H])
        hi = np.array([RIG_U[1], RIG_D + RIG_HALF_D, RIG_H + RIG_HALF_H])
        occ |= U._slab_hit(O, D, dist, lo, hi)
    return occ


def visible(wall, cam, sv, hgt, prot, P, n, C, sgn, plane, cols, rig, max_inc_cos, margin=8):
    """indices of P this camera really sees, with pixel uv and gsd (mm/px)."""
    uu, vv, z = cam.project(P)
    ok = cam.inside(uu, vv, z, margin=margin) & U.distortion_ok(cam, P)
    if not ok.any():
        return None
    idx = np.nonzero(ok)[0]
    d = P[idx] - cam.center
    dist = np.linalg.norm(d, axis=1)
    cosi = np.abs(np.einsum("ij,ij->i", d / dist[:, None], n[idx]))
    keep = cosi > max_inc_cos
    idx, dist, cosi = idx[keep], dist[keep], cosi[keep]
    if not len(idx):
        return None
    occ = _occluded(wall, sv[idx], hgt[idx], prot[idx], P[idx], cam.center, C, sgn, plane, cols, rig)
    idx, dist, cosi = idx[~occ], dist[~occ], cosi[~occ]
    if not len(idx):
        return None
    gsd = 1000.0 * dist / cam.params[0] / cosi
    r = np.hypot((uu[idx] - cam.w / 2) / (cam.w / 2), (vv[idx] - cam.h / 2) / (cam.h / 2))
    return idx, uu[idx], vv[idx], gsd.astype(np.float32), (gsd * (1 + 0.30 * r * r)).astype(np.float32)


# ---------------------------------------------------------------------------------- tiles
def surface(wall, tw, th, px0, py0, mm, room, nrm, plane, sgn, doff=0.0):
    """hall xyz, unit normal, protrusion and validity for every pixel of the tile."""
    spec = WALLS[wall]
    DEP = depth_axis(wall)
    PX, PY = np.meshgrid(px0 + np.arange(tw), py0 + np.arange(th))
    sv = px_to_s(wall, PX.ravel(), mm)
    hgt = TOP - (PY.ravel() + 0.5) * mm / 1000.0
    prot, idx = raster_tris(wall, room, px0, py0, tw, th, mm)
    prot, idx = prot.ravel(), idx.ravel()
    onmesh = idx >= 0
    prot = np.where(onmesh, prot, 0.0).astype(np.float64) + doff
    dep = plane[0] + plane[1] * sv + plane[2] * hgt + sgn * prot
    uu, dd = hall_of(wall, sv, dep)
    P = hall_to_world(uu, dd, hgt)
    n = np.tile(-sgn * DEP, (len(sv), 1))
    if onmesh.any():
        n[onmesh] = nrm[idx[onmesh]]
    flip = (n @ DEP) * sgn < 0
    n[flip] *= -1.0                              # every normal points INTO the room
    inwall = (sv >= spec["s0"]) & (sv <= spec["s1"]) & (hgt >= 0.0) & (hgt <= TOP)
    return sv, hgt, prot, P, n, onmesh, inwall


def render_tile(args):
    px0, py0, tw, th = args
    S = _S
    mm, sgn, plane = S["mm"], S["sgn"], S["plane"]
    names, cams, factors = S["names"], S["cams"], S["factors"]
    mic, C, cols, rig = S["max_inc_cos"], S["coarse"], S["cols"], S["rig"]
    wall = S["wall"]
    sv, hgt, prot, P, n, onmesh, inwall = surface(wall, tw, th, px0, py0, mm, S["room"], S["nrm"],
                                                 plane, sgn, S["doff"])
    npx = len(sv)
    rgb = np.zeros((npx, 3), np.uint8)
    camid = np.full(npx, NOCAM, np.uint16)
    gsdm = np.zeros(npx, np.float32)
    blank = (px0, py0, rgb.reshape(th, tw, 3), camid.reshape(th, tw), gsdm.reshape(th, tw),
             onmesh.reshape(th, tw), inwall.reshape(th, tw))
    if not inwall.any():
        return blank

    # --- pass 1: every camera, on a stride grid, to pick one camera per cell
    ncx = (tw + CELL - 1) // CELL
    ncy = (th + CELL - 1) // CELL
    ncell = ncx * ncy
    sy, sx = np.meshgrid(np.arange(0, th, STRIDE), np.arange(0, tw, STRIDE), indexing="ij")
    sub = sy.ravel() * tw + sx.ravel()
    sub = sub[inwall[sub]]
    if not len(sub):
        return blank
    cell_of = ((sub // tw) // CELL) * ncx + ((sub % tw) // CELL)
    Ps, ns = P[sub], n[sub]
    us, hs, ps = sv[sub], hgt[sub], prot[sub]
    probe = np.linspace(0, len(sub) - 1, min(400, len(sub))).astype(int)
    csum, ccnt = {}, {}
    obs_sub = np.zeros(len(sub), bool)
    side = S["side"]
    for ci, name in enumerate(names):
        if not side[ci]:
            continue          # the camera stands behind this wall; it can never see its face
        cam = cams[name]
        a, b, z = cam.project(Ps[probe])
        if not cam.inside(a, b, z, margin=-cam.w // 3).any():
            continue
        res = visible(wall, cam, us, hs, ps, Ps, ns, C, sgn, plane, cols, rig, mic)
        if res is None:
            continue
        idx, _, _, _, score = res
        score = score * factors[ci]
        obs_sub[idx] = True
        csum[ci] = np.bincount(cell_of[idx], weights=score, minlength=ncell)
        ccnt[ci] = np.bincount(cell_of[idx], minlength=ncell)
    if not csum:
        return blank
    cell_obs = np.bincount(cell_of[obs_sub], minlength=ncell)
    cis = np.array(sorted(csum))
    Ssum = np.stack([csum[c] for c in cis])
    Ncnt = np.stack([ccnt[c] for c in cis])
    mean = np.where(Ncnt > 0, Ssum / np.maximum(Ncnt, 1), np.inf)
    full = np.where(Ncnt >= 0.8 * cell_obs[None, :], mean, np.inf)
    k = np.argmin(full, axis=0)
    bad = ~np.isfinite(full[k, np.arange(ncell)])
    k = np.where(bad, np.argmin(mean, axis=0), k)
    chosen = np.where(cell_obs > 0, cis[k], -1)

    # --- pass 2: the chosen cameras only, at full resolution
    cell_full = ((np.arange(npx) // tw) // CELL) * ncx + ((np.arange(npx) % tw) // CELL)
    for ci in np.unique(chosen[chosen >= 0]):
        pix = np.nonzero((chosen[cell_full] == ci) & inwall)[0]
        if not len(pix):
            continue
        cam = cams[names[ci]]
        res = visible(wall, cam, sv[pix], hgt[pix], prot[pix], P[pix], n[pix], C, sgn, plane,
                      cols, rig, mic)
        if res is None:
            continue
        idx, uu, vv, gsd, _ = res
        g = pix[idx]
        camid[g] = ci
        gsdm[g] = gsd
        im = S["img"](names[ci])
        nsel = len(g)
        rows = (nsel + 4095) // 4096
        mapx = np.zeros(rows * 4096, np.float32); mapx[:nsel] = uu
        mapy = np.zeros(rows * 4096, np.float32); mapy[:nsel] = vv
        col = cv2.remap(im, mapx.reshape(rows, 4096), mapy.reshape(rows, 4096),
                        cv2.INTER_LINEAR, borderMode=cv2.BORDER_REPLICATE)
        rgb[g] = col.reshape(-1, 3)[:nsel]
    return (px0, py0, rgb.reshape(th, tw, 3), camid.reshape(th, tw), gsdm.reshape(th, tw),
            onmesh.reshape(th, tw), inwall.reshape(th, tw))


def _init(wall, geomcache, classes, names, factors, mm, max_inc, cap, rig, doff):
    room, alltri, nrm, plane, _ = wall_geometry(wall, geomcache)
    cams, paths = {}, {}
    for c in classes:
        for n, (cam, p) in U.load_class(c).items():
            cams[c + "/" + n] = cam
            paths[c + "/" + n] = p
    dplane = plane["d = a + b*u + c*h"]
    sgn = WALLS[wall]["sgn"]
    # a camera standing behind the wall can never see its face: drop it once, not per tile
    C0 = np.array([cams[n].center for n in names]) - HALL_O
    side = list(sgn * (C0 @ depth_axis(wall) - dplane[0]) > 0.20)
    _S.update(wall=wall, side=side, doff=doff, room=room, nrm=nrm, plane=dplane, sgn=sgn,
              coarse=coarse_map(wall, alltri) + doff, cams=cams, names=names, mm=mm, rig=rig,
              factors=np.asarray(factors, np.float32), cols=COLUMN_FEET,
              max_inc_cos=float(np.cos(np.radians(max_inc))), img=UO.ImageCache(paths, cap))


# ------------------------------------------------------------------------------------ main
def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--wall", required=True, choices=sorted(WALLS))
    ap.add_argument("--source", default="all", help="day4k | night | walk | all | a,b")
    ap.add_argument("--out", required=True)
    ap.add_argument("--mm", type=float, default=MM_DEFAULT)
    ap.add_argument("--tile", type=int, default=1024)
    ap.add_argument("--workers", type=int, default=12)
    ap.add_argument("--max-inc", type=float, default=75.0)
    ap.add_argument("--cache", type=int, default=14, help="decoded frames held per worker")
    ap.add_argument("--no-rig", action="store_true", help="drop the lighting truss occluder")
    ap.add_argument("--surface-offset", type=float, default=None,
                    help="metres to push the sampling surface towards the room; default is the "
                         "value measured by tools/wall_depth_check.py in <out>/depth-offset-<wall>.json")
    a = ap.parse_args()

    classes = list(U.CLASSES) if a.source == "all" else a.source.split(",")
    for c in classes:
        if c not in U.CLASSES:
            raise SystemExit("unknown source class " + c)
    out = os.path.join(a.out, a.wall, a.source)
    os.makedirs(os.path.join(out, "tiles"), exist_ok=True)
    geomcache = os.path.join(a.out, "wall-%s-geom.npz" % a.wall)
    doff, doff_src = a.surface_offset, "--surface-offset"
    if doff is None:
        f = os.path.join(a.out, "depth-offset-%s.json" % a.wall)
        if os.path.exists(f):
            j = json.load(open(f))
            doff, doff_src = float(j["offset_m"]), j.get("source", f)
        else:
            doff, doff_src = 0.0, "none measured"
    print("surface offset %+.3f m (%s)" % (doff, doff_src), flush=True)
    room, alltri, nrm, plane, gstats = wall_geometry(a.wall, geomcache)
    pl = plane["d = a + b*u + c*h"]
    spec = WALLS[a.wall]
    DN, AN = ("d", "u") if spec["axis"] == "u" else ("u", "d")
    print("%s wall: %s = %.4f %+.6f*%s %+.6f*h   tilt %.3f deg with height, %.4f deg along %s, "
          "bow %.1f mm, %.1f%% of area on the plane (rms %.1f mm)"
          % (a.wall, DN, pl[0], pl[1], AN, pl[2], plane["tilt_with_height_deg"],
             plane["tilt_along_u_deg"], AN, plane["quadratic_bow_over_u_mm"],
             100 * plane["inlier_share_of_area"], plane["inlier_rms_mm"]), flush=True)
    print("  off-plane bands (m of the wall area):", plane["off_plane_bands_m_share"], flush=True)

    W = int(np.ceil(spec["smax"] * 1000.0 / a.mm))
    H = int(np.ceil(TOP * 1000.0 / a.mm))

    loaded, sharp, allnames, factors, sh_all = {}, {}, [], [], {}
    for c in classes:
        loaded[c] = U.load_class(c)
        sharp[c] = UO.sharpness(loaded[c], os.path.join(a.out, "sharpness-%s.json" % c), a.workers)
    med = float(np.median([sharp[c][n] for c in classes for n in loaded[c]])) or 1.0
    for c in classes:
        cc, sh = loaded[c], sharp[c]
        for n in sorted(cc):
            key = c + "/" + n
            f = float(np.clip((med / max(sh[n], 1e-9)) ** 0.5, 0.5, 3.0))
            allnames.append(key)
            factors.append(U.CLASSES[c]["factor"] * f)
            sh_all[key] = {"lapvar": sh[n], "factor": f}
        print("%s: %d frames, class lapvar median %.3f (run median %.3f)"
              % (c, len(cc), float(np.median([sh[n] for n in cc])), med), flush=True)
    print("cameras", len(allnames), "raster", W, "x", H, flush=True)

    tiles = []
    for py0 in range(0, H, a.tile):
        for px0 in range(0, W, a.tile):
            tiles.append((px0, py0, min(a.tile, W - px0), min(a.tile, H - py0)))

    meta = {"wall": a.wall, "source": a.source,
            "classes": {c: U.CLASSES[c]["note"] for c in classes},
            "raster": {"mm_per_px": a.mm, "width": W, "height": H,
                       "across_axis": AN, "depth_axis": DN, "top_m": TOP,
                       "across_at_col0_m": (spec["smax"] if spec["flip"] else 0.0),
                       "pixel_centre": ("%s = %s(px + 0.5) * mm_per_px / 1000 ; "
                                        "h = %.1f - (py + 0.5) * mm_per_px / 1000"
                                        % (AN, ("%.3f - " % spec["smax"]) if spec["flip"] else "", TOP)),
                       "orientation": ("col 0 = %s %.3f, %s %s; row 0 = %.1f m above the carpet, "
                                       "height downward"
                                       % (AN, (spec["smax"] if spec["flip"] else 0.0), AN,
                                          "decreasing" if spec["flip"] else "increasing", TOP)),
                       "wall_across_range_m": [spec["s0"], spec["s1"]],
                       "world_from_hall": "world = (%.6f, %.6f, %.6f) + u*(%.6f, 0, %.6f) "
                                          "+ d*(%.6f, 0, %.6f) + (0, h, 0)"
                                          % (HALL_O[0], HALL_O[1], HALL_O[2], HALL_U[0], HALL_U[2],
                                             HALL_D[0], HALL_D[2])},
            "surface": {"kind": ("index.html buildEndWalls quads, z-buffered"
                                 if spec["plane"] is not None else
                                 "model.glb room-facing faces, z-buffered; fitted plane where "
                                 "the GLB has no face"),
                        "plane": plane, "geometry": gstats,
                        "sign": spec["sgn"], "band_depth_m": spec["band"],
                        "measured_offset_m": doff, "measured_offset_source": doff_src},
            "max_incidence_deg": a.max_inc, "cell_px": CELL,
            "occluders": {"columns": len(COLUMN_FEET), "column_radius_m": COLUMN_R,
                          "lighting_truss": (not a.no_rig),
                          "truss_u_m": RIG_U, "truss_d_m": RIG_D, "truss_h_m": RIG_H,
                          "self_occlusion_map_mm": COARSE_MM},
            "cameras": allnames, "factors": [float(f) for f in factors], "frame_stats": sh_all}
    json.dump(meta, open(os.path.join(out, "meta.json"), "w"), indent=1)

    from multiprocessing import Pool
    t0 = time.time()
    todo = [t for t in tiles if not os.path.exists(os.path.join(out, "tiles", "t_%d_%d.npz" % (t[1], t[0])))]
    print("tiles", len(tiles), "to render", len(todo), flush=True)
    if todo:
        with Pool(a.workers, initializer=_init,
                  initargs=(a.wall, geomcache, classes, allnames, factors, a.mm, a.max_inc,
                            a.cache, not a.no_rig, doff)) as p:
            for k, (px0, py0, rgb, camid, gsdm, onmesh, inwall) in enumerate(
                    p.imap_unordered(render_tile, todo, chunksize=1)):
                np.savez_compressed(os.path.join(out, "tiles", "t_%d_%d.npz" % (py0, px0)),
                                    rgb=rgb, cam=camid, gsd=gsdm, mesh=onmesh, wall=inwall)
                sel = inwall
                print("tile %d/%d (%d,%d) observed %.1f%%  %ds"
                      % (k + 1, len(todo), px0, py0,
                         100.0 * ((camid != NOCAM) & sel).sum() / max(sel.sum(), 1),
                         round(time.time() - t0)), flush=True)

    # ------------------------------------------------------------------- assemble + report
    RGB = np.zeros((H, W, 3), np.uint8)
    CAM = np.full((H, W), NOCAM, np.uint16)
    GSD = np.zeros((H, W), np.uint16)
    MESH = np.zeros((H, W), bool)
    WALL = np.zeros((H, W), bool)
    for px0, py0, tw, th in tiles:
        z = np.load(os.path.join(out, "tiles", "t_%d_%d.npz" % (py0, px0)))
        RGB[py0:py0 + th, px0:px0 + tw] = z["rgb"]
        CAM[py0:py0 + th, px0:px0 + tw] = z["cam"]
        GSD[py0:py0 + th, px0:px0 + tw] = np.clip(z["gsd"], 0, 65535).astype(np.uint16)
        MESH[py0:py0 + th, px0:px0 + tw] = z["mesh"]
        WALL[py0:py0 + th, px0:px0 + tw] = z["wall"]
    mask = CAM != NOCAM
    cv2.imwrite(os.path.join(out, "ortho.png"), cv2.cvtColor(RGB, cv2.COLOR_RGB2BGR))
    cv2.imwrite(os.path.join(out, "mask.png"), (mask * 255).astype(np.uint8))
    cv2.imwrite(os.path.join(out, "gsd.png"), GSD)
    cv2.imwrite(os.path.join(out, "cam.png"), CAM)
    cv2.imwrite(os.path.join(out, "surface.png"), (MESH * 255).astype(np.uint8))
    prev = cv2.resize(cv2.cvtColor(RGB, cv2.COLOR_RGB2BGR), (W // 8, H // 8), interpolation=cv2.INTER_AREA)
    cv2.imwrite(os.path.join(out, "preview.png"), prev)

    rep = {"wall_px": int(WALL.sum()), "observed_px": int(mask.sum()),
           "on_modelled_surface_share": float(MESH[WALL].mean()),
           "across_axis": AN,
           "coverage": float(mask[WALL].mean()), "per_across_5m": {}, "per_h_2m": {},
           "per_class": {}, "gsd_mm": {}}
    ux = px_to_s(a.wall, np.arange(W), a.mm)
    hy = TOP - (np.arange(H) + 0.5) * a.mm / 1000.0
    for k in range(0, int(np.ceil(spec["smax"] / 5.0)) * 5, 5):
        col = (ux >= k) & (ux < k + 5)
        sel = WALL & col[None, :]
        if sel.any():
            rep["per_across_5m"]["%s%d_%d" % (AN, k, k + 5)] = {
                "wall_px": int(sel.sum()), "coverage": round(float(mask[sel].mean()), 4),
                "gsd_median_mm": (float(np.median(GSD[sel & mask])) if (sel & mask).any() else None)}
    for k in range(0, 14, 2):
        row = (hy >= k) & (hy < k + 2)
        sel = WALL & row[:, None]
        if sel.any():
            rep["per_h_2m"]["h%d_%d" % (k, k + 2)] = {
                "wall_px": int(sel.sum()), "coverage": round(float(mask[sel].mean()), 4),
                "gsd_median_mm": (float(np.median(GSD[sel & mask])) if (sel & mask).any() else None)}
    g = GSD[mask]
    if g.size:
        rep["gsd_mm"] = {p: float(np.percentile(g, p)) for p in (5, 10, 25, 50, 75, 90, 95)}
    idx = CAM[mask].astype(int)
    cls_of = np.array([n.split("/")[0] for n in allnames])
    for c in classes:
        sel = np.isin(idx, np.nonzero(cls_of == c)[0])
        rep["per_class"][c] = {"pixels": int(sel.sum()),
                               "share_of_observed": float(sel.mean()) if sel.size else 0.0,
                               "frames_used": int(len(np.unique(idx[sel])))}
    # which class won, per 5 m of u, so the report can say where night beat day
    rep["class_win_per_across_5m"] = {}
    for k in range(0, int(np.ceil(spec["smax"] / 5.0)) * 5, 5):
        col = (ux >= k) & (ux < k + 5)
        sel = mask & WALL & col[None, :]
        if sel.any():
            ii = CAM[sel].astype(int)
            rep["class_win_per_across_5m"]["%s%d_%d" % (AN, k, k + 5)] = {
                c: round(float(np.isin(ii, np.nonzero(cls_of == c)[0]).mean()), 3) for c in classes}
    rep["frames_used_total"] = int(len(np.unique(idx)))
    meta["report"] = rep
    json.dump(meta, open(os.path.join(out, "meta.json"), "w"), indent=1)
    print(json.dumps(rep, indent=1))
    print("done", round(time.time() - t0), "s ->", out, flush=True)


if __name__ == "__main__":
    main()
