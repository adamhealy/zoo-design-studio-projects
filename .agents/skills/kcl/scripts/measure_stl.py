"""Print the bounding box, triangle count and volume of an STL file.

Handles both ASCII STL (what `zoo kcl export --output-format stl` writes)
and binary STL. Standard library only.

Usage: python3 -I measure_stl.py path/to/file.stl
"""

import re
import struct
import sys


def load_triangles(path):
    data = open(path, "rb").read()
    if data[:5] == b"solid" and b"facet" in data[:1000]:
        nums = re.findall(rb"vertex\s+(\S+)\s+(\S+)\s+(\S+)", data)
        verts = [tuple(map(float, v)) for v in nums]
        return [verts[i : i + 3] for i in range(0, len(verts), 3)]
    count = struct.unpack("<I", data[80:84])[0]
    tris = []
    for i in range(count):
        v = struct.unpack("<12f", data[84 + 50 * i : 84 + 50 * i + 48])
        tris.append((v[3:6], v[6:9], v[9:12]))
    return tris


def main():
    tris = load_triangles(sys.argv[1])
    pts = [p for t in tris for p in t]
    for k, axis in enumerate("XYZ"):
        lo = min(p[k] for p in pts)
        hi = max(p[k] for p in pts)
        print(f"{axis}: {lo:9.3f} .. {hi:9.3f}   size {hi - lo:.3f}")
    # Signed volume via the divergence theorem (needs a closed, consistently
    # wound mesh, which engine exports are).
    vol = 0.0
    for a, b, c in tris:
        vol += (
            a[0] * (b[1] * c[2] - b[2] * c[1])
            - a[1] * (b[0] * c[2] - b[2] * c[0])
            + a[2] * (b[0] * c[1] - b[1] * c[0])
        ) / 6
    print(f"triangles: {len(tris)}   volume: {vol:.1f} (units^3)")


if __name__ == "__main__":
    main()
