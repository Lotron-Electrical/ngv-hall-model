"""Shrink a clean-hall GLB for phones: a flat-colour material does not need a 4096 x 4096 atlas.

    python tools/slim_glb.py <in.glb> <out.glb>

WHY. The bake packs every flat-shipped surface (the twelve columns, the ceiling void) into its own
atlas at the same size as the photographed ones, so the shipped model carried sixteen 4096-square
textures: 1,023 MB decoded on the GPU, 871 MB of it solid colour. A desktop shrugs; iOS Safari
kills the tab past about a gigabyte and shows a white page, which is what a visitor saw on
2026-08-28. Each flat image becomes a 4 x 4 PNG of its own mean colour; the photo atlases are
untouched. The materials keep their texture slots, so the page's shader path is the same.
"""
import io
import json
import struct
import sys
from pathlib import Path

import numpy as np
from PIL import Image

src, dst = Path(sys.argv[1]), Path(sys.argv[2])
b = src.read_bytes()
assert b[:4] == b"glTF", "not a GLB"
jlen = struct.unpack_from("<I", b, 12)[0]
js = json.loads(b[20:20 + jlen])
boff = 20 + jlen
blen = struct.unpack_from("<I", b, boff)[0]
assert b[boff + 4:boff + 8] == b"BIN\0"
bin_ = b[boff + 8:boff + 8 + blen]

bvs = js["bufferViews"]
mats = js["materials"]
texs = js.get("textures", [])
imgs = js.get("images", [])

# which images are used only by flat materials
users = {}
for m in mats:
    t = m.get("pbrMetallicRoughness", {}).get("baseColorTexture", {}).get("index")
    if t is not None:
        users.setdefault(texs[t]["source"], []).append(m["name"])
flat = {i for i, names in users.items() if all(n.startswith("flat-") for n in names)}

# new payloads per bufferView: replaced images get a 4x4 PNG of the mean colour
payload = {}
before = after = 0
for i, im in enumerate(imgs):
    bv = bvs[im["bufferView"]]
    data = bin_[bv["byteOffset"]:bv["byteOffset"] + bv["byteLength"]]
    pil = Image.open(io.BytesIO(data)).convert("RGB")
    before += pil.width * pil.height * 4
    if i in flat:
        # the painted rect is a fraction of the atlas and the rest is black gutter, so the colour is
        # the median of the texels that carry paint, never a mean over the sheet
        px = np.asarray(pil, dtype=np.float64).reshape(-1, 3)
        px = px[px.sum(axis=1) > 6]
        colour = tuple(int(round(v)) for v in np.median(px, axis=0))
        out = io.BytesIO()
        Image.new("RGB", (4, 4), colour).save(out, format="PNG")
        payload[im["bufferView"]] = out.getvalue()
        im["mimeType"] = "image/png"
        after += 4 * 4 * 4
        print(f"image {i}: {pil.width}x{pil.height} -> 4x4 {colour} for {users[i]}")
    else:
        after += pil.width * pil.height * 4
        print(f"image {i}: {pil.width}x{pil.height} kept for {users.get(i)}")

# rebuild the binary chunk in bufferView order, 4-byte aligned, and re-point every view
new = bytearray()
for k, bv in enumerate(bvs):
    data = payload.get(k, bin_[bv["byteOffset"]:bv["byteOffset"] + bv["byteLength"]])
    while len(new) % 4:
        new += b"\0"
    bv["byteOffset"] = len(new)
    bv["byteLength"] = len(data)
    new += data
while len(new) % 4:
    new += b"\0"
js["buffers"][0]["byteLength"] = len(new)

jb = json.dumps(js, separators=(",", ":")).encode()
while len(jb) % 4:
    jb += b" "
total = 12 + 8 + len(jb) + 8 + len(new)
with dst.open("wb") as f:
    f.write(b"glTF" + struct.pack("<II", 2, total))
    f.write(struct.pack("<I", len(jb)) + b"JSON" + jb)
    f.write(struct.pack("<I", len(new)) + b"BIN\0" + bytes(new))
print(f"decoded texture memory {before / 1e6:.0f} MB -> {after / 1e6:.0f} MB; file {len(b) / 1e6:.2f} MB -> {total / 1e6:.2f} MB; wrote {dst}")
