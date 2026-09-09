"""Minimal COLMAP binary model reader (cameras.bin, images.bin, points3D.bin).

Format per COLMAP src/colmap/scene/reconstruction_io.cc (binary):
  cameras.bin : u64 n; per camera: i32 camera_id, i32 model_id, u64 width, u64 height, f64 params[k]
  images.bin  : u64 n; per image: i32 image_id, f64 qw qx qy qz, f64 tx ty tz, i32 camera_id,
                name (NUL-terminated), u64 n_points2D, then n x (f64 x, f64 y, i64 point3D_id)
  points3D.bin: u64 n; per point: i64 id, f64 xyz[3], u8 rgb[3], f64 error, u64 track_len,
                track_len x (i32 image_id, i32 point2D_idx)
Poses are world->camera: x_cam = R(q) @ x_world + t.

Usage as a library:
  from colmap_bin import read_model
  cams, imgs, pts = read_model(dir)
"""
import struct
import numpy as np
import os
import sys

CAMERA_MODELS = {
    0: ("SIMPLE_PINHOLE", 3), 1: ("PINHOLE", 4), 2: ("SIMPLE_RADIAL", 4), 3: ("RADIAL", 5),
    4: ("OPENCV", 8), 5: ("OPENCV_FISHEYE", 8), 6: ("FULL_OPENCV", 12), 7: ("FOV", 5),
    8: ("SIMPLE_RADIAL_FISHEYE", 4), 9: ("RADIAL_FISHEYE", 5), 10: ("THIN_PRISM_FISHEYE", 12),
    11: ("RAD_TAN_THIN_PRISM_FISHEYE", 16),
}


class Camera:
    __slots__ = ("id", "model", "width", "height", "params")

    def __init__(self, id, model, width, height, params):
        self.id, self.model, self.width, self.height, self.params = id, model, width, height, params


class Image:
    __slots__ = ("id", "q", "t", "camera_id", "name", "xys", "p3d_ids")

    def __init__(self, id, q, t, camera_id, name, xys, p3d_ids):
        self.id, self.q, self.t, self.camera_id, self.name, self.xys, self.p3d_ids = id, q, t, camera_id, name, xys, p3d_ids

    def R(self):
        return qvec2rotmat(self.q)

    def center(self):
        return -self.R().T @ self.t


def qvec2rotmat(q):
    w, x, y, z = q
    return np.array([
        [1 - 2 * y * y - 2 * z * z, 2 * x * y - 2 * w * z, 2 * x * z + 2 * w * y],
        [2 * x * y + 2 * w * z, 1 - 2 * x * x - 2 * z * z, 2 * y * z - 2 * w * x],
        [2 * x * z - 2 * w * y, 2 * y * z + 2 * w * x, 1 - 2 * x * x - 2 * y * y]])


def read_cameras(path):
    cams = {}
    with open(path, "rb") as f:
        n = struct.unpack("<Q", f.read(8))[0]
        for _ in range(n):
            cid, model_id, w, h = struct.unpack("<iiQQ", f.read(24))
            name, k = CAMERA_MODELS[model_id]
            params = np.array(struct.unpack("<" + "d" * k, f.read(8 * k)))
            cams[cid] = Camera(cid, name, w, h, params)
    return cams


def read_images(path, with_points2d=True):
    imgs = {}
    with open(path, "rb") as f:
        data = f.read()
    off = 0
    n = struct.unpack_from("<Q", data, off)[0]; off += 8
    for _ in range(n):
        iid = struct.unpack_from("<i", data, off)[0]; off += 4
        q = np.array(struct.unpack_from("<4d", data, off)); off += 32
        t = np.array(struct.unpack_from("<3d", data, off)); off += 24
        cam_id = struct.unpack_from("<i", data, off)[0]; off += 4
        end = data.index(b"\x00", off)
        name = data[off:end].decode("utf-8"); off = end + 1
        n2 = struct.unpack_from("<Q", data, off)[0]; off += 8
        if with_points2d and n2 > 0:
            arr = np.frombuffer(data, dtype=np.dtype([("x", "<f8"), ("y", "<f8"), ("id", "<i8")]), count=n2, offset=off)
            xys = np.stack([arr["x"], arr["y"]], axis=1).copy()
            p3d = arr["id"].copy()
        else:
            xys, p3d = None, None
        off += n2 * 24
        imgs[iid] = Image(iid, q, t, cam_id, name, xys, p3d)
    return imgs


def read_points3d(path, with_tracks=False):
    with open(path, "rb") as f:
        data = f.read()
    off = 0
    n = struct.unpack_from("<Q", data, off)[0]; off += 8
    ids = np.empty(n, dtype=np.int64)
    xyz = np.empty((n, 3), dtype=np.float64)
    rgb = np.empty((n, 3), dtype=np.uint8)
    err = np.empty(n, dtype=np.float64)
    tracks = [] if with_tracks else None
    tlen = np.empty(n, dtype=np.int64)
    for i in range(n):
        pid = struct.unpack_from("<q", data, off)[0]; off += 8
        xyz[i] = struct.unpack_from("<3d", data, off); off += 24
        rgb[i] = struct.unpack_from("<3B", data, off); off += 3
        err[i] = struct.unpack_from("<d", data, off)[0]; off += 8
        tl = struct.unpack_from("<Q", data, off)[0]; off += 8
        ids[i] = pid; tlen[i] = tl
        if with_tracks:
            tr = np.frombuffer(data, dtype=np.dtype([("img", "<i4"), ("p2", "<i4")]), count=tl, offset=off)
            tracks.append(tr.copy())
        off += tl * 8
    return {"id": ids, "xyz": xyz, "rgb": rgb, "err": err, "track_len": tlen, "tracks": tracks}


def read_model(d, with_points2d=True, with_tracks=False):
    cams = read_cameras(os.path.join(d, "cameras.bin"))
    imgs = read_images(os.path.join(d, "images.bin"), with_points2d)
    pts = read_points3d(os.path.join(d, "points3D.bin"), with_tracks)
    return cams, imgs, pts


if __name__ == "__main__":
    d = sys.argv[1]
    cams, imgs, pts = read_model(d, with_points2d=False)
    print("cameras:")
    for c in cams.values():
        print("  ", c.id, c.model, c.width, c.height, np.array2string(c.params, precision=4, max_line_width=200))
    names = sorted(i.name for i in imgs.values())
    print("images:", len(imgs))
    prefixes = {}
    for n in names:
        p = n.split("/")[0] if "/" in n else n.split("_")[0]
        prefixes[p] = prefixes.get(p, 0) + 1
    print("  by prefix:", prefixes)
    print("  first/last:", names[:3], names[-3:])
    print("points3D:", len(pts["id"]), "xyz min", pts["xyz"].min(0), "max", pts["xyz"].max(0))
    C = np.array([i.center() for i in imgs.values()])
    print("camera centres min", C.min(0), "max", C.max(0))
