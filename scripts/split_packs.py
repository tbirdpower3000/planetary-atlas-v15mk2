#!/usr/bin/env python3
"""Split each world's single pack file into a folder with one file per layer.

    python scripts/split_packs.py            # rebuild worlds/ from the pack files and note each folder in index.json
    python scripts/split_packs.py --check    # exit 1 if worlds/ is out of date with the pack files

The pack files beside the page (mars.json, moon.json, ...) stay the master copy: edit those, then run this. For each
world it writes

    worlds/<id>/world.json    everything but the heavy data: names, sites, and for each layer its file name
    worlds/<id>/<grid>.bin    a grid's numbers as they are (16-bit, little-endian, rows x cols), no longer as text
    worlds/<id>/<image>.jpg   a picture layer as a picture file

Each site in world.json carries "gv": its value in each of the first four grids, worked out from the full grids, so
the page can list them without fetching those grids. Each grid in world.json also carries "pv": a small preview (every 4th or 8th sample, about 91 x 180) so a value can
be read from a layer before its full grid has arrived. The page opens a world from its folder when index.json gives
one ("dir"), and falls back to the single pack file when it does not, so other data folders keep working.

Pure standard library.
"""
import base64, hashlib, json, math, struct, sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "worlds"
PREVIEW_ROWS = 91


def preview(b64, rows, cols):
    """Every k-th sample of a rows x cols 16-bit grid, as its own small grid (text, since it sits inside world.json)."""
    k = max(1, (rows - 1) // (PREVIEW_ROWS - 1))
    if k == 1 or (rows - 1) % k or cols % k:
        return None
    raw = base64.b64decode(b64)
    out = bytearray()
    for i in range(0, rows, k):
        row = raw[i * cols * 2:(i + 1) * cols * 2]
        for j in range(0, cols, k):
            out += row[j * 2:j * 2 + 2]
    return {"rows": (rows - 1) // k + 1, "cols": cols // k, "b64": base64.b64encode(bytes(out)).decode()}


def samp(a, rows, cols, k, lat, lon):
    """The page's own samp(), step for step, so a value worked out here is the value the page would show."""
    st = 180 / (rows - 1)
    y = (90 - lat) / st
    x = math.fmod(math.fmod(lon, 360) + 360, 360) / st
    i = min(max(math.floor(y), 0), rows - 2)
    fy = min(1, max(0, y - i))
    j = math.floor(x) % cols
    j1 = (j + 1) % cols
    fx = x - math.floor(x)
    return ((a[i * cols + j] * (1 - fx) + a[i * cols + j1] * fx) * (1 - fy)
            + (a[(i + 1) * cols + j] * (1 - fx) + a[(i + 1) * cols + j1] * fx) * fy) * k


def split(pack):
    """-> ({relative file name: bytes}, world dict)"""
    files, w = {}, dict(pack)
    w["grids"] = []
    for g in pack.get("grids", []):
        d = {k: v for k, v in g.items() if k != "b64"}
        raw = base64.b64decode(g["b64"])
        if len(raw) != g["rows"] * g["cols"] * 2:
            sys.exit(f"FAIL: grid {pack['id']}/{g['id']} is {len(raw)} bytes, not rows x cols x 2")
        d["file"] = g["id"] + ".bin"
        d["bytes"] = len(raw)
        pv = preview(g["b64"], g["rows"], g["cols"])
        if pv:
            d["pv"] = pv
        files[d["file"]] = raw
        w["grids"].append(d)
    # each site's value in each of the first four grids (the ones the page lists), worked out here from the full
    # grids, so the page can show them exactly without fetching a grid it is not otherwise using
    first = [(g, struct.unpack(f"<{g['rows'] * g['cols']}h", base64.b64decode(g["b64"]))) for g in pack.get("grids", [])[:4]]
    if first and pack.get("sites"):
        w["sites"] = []
        for s in pack["sites"]:
            s = dict(s)
            if isinstance(s.get("lat"), (int, float)) and isinstance(s.get("lon"), (int, float)):
                s["gv"] = {g["id"]: samp(a, g["rows"], g["cols"], g.get("scale") or 1, s["lat"], s["lon"]) for g, a in first}
            w["sites"].append(s)
    w["images"] = []
    for im in pack.get("images", []):
        d = {k: v for k, v in im.items() if k != "src"}
        head, _, data = im["src"].partition(",")
        if not head.startswith("data:image/") or ";base64" not in head:
            sys.exit(f"FAIL: image {pack['id']}/{im['id']} is not an embedded picture")
        ext = {"jpeg": "jpg"}.get(head[11:].split(";")[0], head[11:].split(";")[0])
        d["file"] = f"{im['id']}.{ext}"
        files[d["file"]] = base64.b64decode(data)
        d["bytes"] = len(files[d["file"]])
        w["images"].append(d)
    w["layout"] = 1
    return files, w


def main():
    check = "--check" in sys.argv
    index = json.loads((ROOT / "index.json").read_text(encoding="utf-8"))
    stale, total_old, total_new = [], 0, 0
    for e in index:
        src = ROOT / Path(e["file"]).name
        pack = json.loads(src.read_text(encoding="utf-8"))
        files, world = split(pack)
        files["world.json"] = json.dumps(world, ensure_ascii=False, separators=(",", ":")).encode("utf-8")
        folder = OUT / e["id"]
        total_old += src.stat().st_size
        total_new += sum(len(b) for b in files.values())
        for name, data in files.items():
            p = folder / name
            if not p.exists() or hashlib.sha1(p.read_bytes()).digest() != hashlib.sha1(data).digest():
                stale.append(str(p.relative_to(ROOT)))
                if not check:
                    folder.mkdir(parents=True, exist_ok=True)
                    p.write_bytes(data)
        if folder.exists():
            for p in folder.iterdir():
                if p.name not in files:
                    stale.append(str(p.relative_to(ROOT)) + " (no longer used)")
                    if not check:
                        p.unlink()
        if e.get("dir") != f"worlds/{e['id']}/":
            stale.append(f"index.json: {e['id']} has no dir")
            e["dir"] = f"worlds/{e['id']}/"
    if check:
        if stale:
            print("worlds/ is out of date with the pack files. Run: python scripts/split_packs.py")
            print("\n".join("  " + s for s in stale[:20]))
            sys.exit(1)
        print(f"worlds/ matches the {len(index)} pack files.")
        return
    (ROOT / "index.json").write_text(json.dumps(index, ensure_ascii=False, indent=0) + "\n", encoding="utf-8")
    print(f"{len(index)} worlds: {total_old / 1e6:.1f} MB as single files, {total_new / 1e6:.1f} MB as folders. {len(stale)} file(s) written or changed.")


if __name__ == "__main__":
    main()
