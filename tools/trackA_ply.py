"""Minimal binary_little_endian PLY vertex reader (numpy memmap) for the sitecapture clouds."""
import numpy as np

_TYPES = {"float": "<f4", "float32": "<f4", "double": "<f8", "uchar": "|u1", "uint8": "|u1",
          "int": "<i4", "uint": "<u4", "short": "<i2", "ushort": "<u2"}


def read_ply_header(path):
    with open(path, "rb") as f:
        lines = []
        while True:
            ln = f.readline()
            if not ln:
                raise ValueError("no end_header")
            lines.append(ln.decode("ascii", "replace").strip())
            if lines[-1] == "end_header":
                break
        off = f.tell()
    n = None
    props = []
    in_vertex = False
    for ln in lines:
        p = ln.split()
        if p[0] == "format" and p[1] != "binary_little_endian":
            raise ValueError("only binary_little_endian: " + ln)
        if p[0] == "element":
            in_vertex = p[1] == "vertex"
            if in_vertex:
                n = int(p[2])
        elif p[0] == "property" and in_vertex:
            if p[1] == "list":
                raise ValueError("list property in vertex")
            props.append((p[2], _TYPES[p[1]]))
    return n, props, off


def read_ply(path, fields=("x", "y", "z")):
    n, props, off = read_ply_header(path)
    dt = np.dtype(props)
    mm = np.memmap(path, dtype=dt, mode="r", offset=off, shape=(n,))
    return mm, dt


if __name__ == "__main__":
    import sys
    n, props, off = read_ply_header(sys.argv[1])
    print(n, props, off)
