"""Track A geometry: hall/GLB world <-> huv plate frame, canopy lattice + relief, the
roof-void -> hall similarity chain, and the COLMAP OPENCV camera projection.

Frames
  hall  : GLB world of model.glb (y up, metres)
  huv   : plate frame, hu = x*CU + z*SU, hv = -x*SU + z*CU
  void  : roof-void register frame (rebuild-roofvoid/build/model == void4k-register/mapped)

Void -> hall chain of record here (see track A report):
  x_hall = s*R@x_void + t with (s,R,t) = SHIFT o HANDSET, i.e.
  roofvoid-to-hall-transform-20260830-handset.json followed by roofvoid-shift-one-bay-20260831.json.
Optionally a 2D similarity correction in the huv plane is applied after (from fit).
"""
import json
import numpy as np

CU, SU = 0.975681, 0.219196
PU, PV = 7.4285, 7.3855
HU0, HV0 = -45.492375, 11.237070          # funnel vertex lattice phase
PLATE_HU = (-56.635125, -4.635625)
PLATE_HV = (0.158820, 14.929820)
RISE = 0.86
SITE = "E:/sitecapture-captures/ngv-site/"


def xz_to_huv(x, z):
    return x * CU + z * SU, -x * SU + z * CU


def huv_to_xz(hu, hv):
    return hu * CU - hv * SU, hu * SU + hv * CU


def vertex_plane_y(hu, hv):
    return 11.493768 - 0.00051022 * hu - 0.0139082 * hv


def relief(hu, hv):
    """Relief above the vertex plane at (hu,hv): index.html coffRelief."""
    i = np.round((hu - HU0) / PU)
    j = np.round((hv - HV0) / PV)
    du = hu - (HU0 + i * PU)
    dv = hv - (HV0 + j * PV)
    a = PU / 2 - 0.225
    b = PV / 2 - 0.225
    t = np.maximum(np.abs(du) / a, np.abs(dv) / b)
    over = np.maximum(np.abs(du) - a, np.abs(dv) - b)
    r = np.where(t <= 1, RISE * t, RISE - 0.03 * np.minimum(1.0, over / 0.225))
    return r


def surface_y(hu, hv, slab=0.06):
    return vertex_plane_y(hu, hv) + relief(hu, hv) + slab


def surface_xyz(hu, hv, slab=0.06):
    x, z = huv_to_xz(hu, hv)
    return np.stack([x, surface_y(hu, hv, slab), z], axis=-1)


def bay_index(hu, hv):
    """bay i=0..6 from the west end (bay i centred on vertex index i-1), j=0 south / 1 north."""
    bi = np.floor((hu - (HU0 - PU / 2)) / PU).astype(int) + 1
    bj = np.floor((hv - (HV0 - PV / 2)) / PV).astype(int) + 1
    return bi, bj


# ---------------------------------------------------------------- transforms
def load_sim(path, key="transform"):
    j = json.load(open(path))
    t = j[key]
    return float(t["scale"]), np.array(t["R"], float), np.array(t["t"], float)


def compose(first, second):
    """x -> second(first(x))"""
    s1, R1, t1 = first
    s2, R2, t2 = second
    return s1 * s2, R2 @ R1, s2 * R2 @ t1 + t2


def void_to_hall_chain(name="d"):
    a = load_sim(SITE + "roofvoid-to-hall-transform.json")
    b = load_sim(SITE + "roofvoid-to-hall-transform-20260828.json")
    c = load_sim(SITE + "roofvoid-to-hall-transform-20260830-handset.json")
    sh = load_sim(SITE + "roofvoid-shift-one-bay-20260831.json")
    d = compose(c, sh)
    return {"a": a, "b": b, "c": c, "d": d}[name]


def apply_sim(sim, X):
    s, R, t = sim
    return s * (X @ R.T) + t


def invert_sim(sim):
    s, R, t = sim
    return 1.0 / s, R.T, -(R.T @ t) / s


# ---------------------------------------------------------------- cameras
class Cam:
    """COLMAP camera (PINHOLE or OPENCV) with a world->camera pose, in whatever frame X is given."""

    def __init__(self, model, width, height, params, R, t):
        self.model, self.w, self.h = model, int(width), int(height)
        self.params = np.asarray(params, float)
        self.R, self.t = np.asarray(R, float), np.asarray(t, float)

    @property
    def center(self):
        return -self.R.T @ self.t

    def to_frame(self, sim):
        """Return this camera expressed in the frame x' = s R x + t (sim maps this frame -> new)."""
        s, Rs, ts = sim
        # x_cam = R x + t ; x = (x' - ts)/s @ Rs  => x_cam = R Rs^T (x'-ts)/s + t
        Rn = self.R @ Rs.T
        tn = self.t - Rn @ ts / s
        # scale: x_cam = (Rn x' + tn*s)/s ; camera scaled by 1/s. Fold s into a metric camera by
        # scaling t: x_cam_metric = Rn x' + s*tn (distance units of the new frame)
        return Cam(self.model, self.w, self.h, self.params, Rn, s * tn)

    def project(self, X):
        """X (N,3) world -> (u,v) pixels, depth z. Applies OPENCV distortion."""
        Xc = X @ self.R.T + self.t
        z = Xc[:, 2]
        with np.errstate(divide="ignore", invalid="ignore"):
            xn = Xc[:, 0] / z
            yn = Xc[:, 1] / z
        p = self.params
        if self.model == "PINHOLE":
            fx, fy, cx, cy = p
            u = fx * xn + cx
            v = fy * yn + cy
        elif self.model == "OPENCV":
            fx, fy, cx, cy, k1, k2, p1, p2 = p
            r2 = xn * xn + yn * yn
            rad = 1 + k1 * r2 + k2 * r2 * r2
            xd = xn * rad + 2 * p1 * xn * yn + p2 * (r2 + 2 * xn * xn)
            yd = yn * rad + p1 * (r2 + 2 * yn * yn) + 2 * p2 * xn * yn
            u = fx * xd + cx
            v = fy * yd + cy
        else:
            raise ValueError(self.model)
        return u, v, z

    def inside(self, u, v, z, margin=0):
        return (z > 0) & (u >= margin) & (u < self.w - margin) & (v >= margin) & (v < self.h - margin)


def load_stills(mapped_dir, sim=None):
    """Return {name: Cam} for the void4k stills of the mapped model, optionally re-expressed in
    the frame reached by sim (void -> that frame)."""
    import sys, os
    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
    from colmap_bin import read_model
    cams, imgs, _ = read_model(mapped_dir, with_points2d=False)
    out = {}
    for im in imgs.values():
        if not im.name.startswith("void4k"):
            continue
        c = cams[im.camera_id]
        cam = Cam(c.model, c.width, c.height, c.params, im.R(), im.t)
        if sim is not None:
            cam = cam.to_frame(sim)
        out[os.path.basename(im.name)[:-4]] = cam
    return out
