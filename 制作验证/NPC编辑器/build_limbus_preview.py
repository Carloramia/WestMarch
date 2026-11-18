"""Prepare local setup-pose layers from exported Spine SD models."""
import argparse
import base64
import json
import math
from pathlib import Path

from PIL import Image, ImageDraw


ROOT = Path(__file__).resolve().parent
SIZE = 560
IDENTITY = (1, 0, 0, 1, 0, 0)


def compose(m, p):
    a, b, c, d, x, y = m
    e, f, g, h, u, v = p
    return (a*e+b*g, a*f+b*h, c*e+d*g, c*f+d*h, a*u+b*v+x, c*u+d*v+y)


def transform(m, x, y):
    a, b, c, d, u, v = m
    return a*x+b*y+u, c*x+d*y+v


def matrix(data):
    angle = data.get("rotation", 0)
    rx = math.radians(angle + data.get("shearX", 0))
    ry = math.radians(angle + 90 + data.get("shearY", 0))
    sx, sy = data.get("scaleX", 1), data.get("scaleY", 1)
    return math.cos(rx)*sx, math.cos(ry)*sy, math.sin(rx)*sx, math.sin(ry)*sy, data.get("x", 0), data.get("y", 0)


def atlas_images(folder):
    pages = {}
    current = {}
    for raw in (folder / "original.atlas").read_text("utf-8-sig").splitlines():
        line = raw.strip()
        if not line:
            continue
        if ":" in line:
            key, value = line.split(":", 1)
            current[key] = value.strip()
        elif line.lower().endswith(".png"):
            pages[line] = {}
            current = page = pages[line]
        else:
            current = page.setdefault("regions", {})[line] = {}
    images = {}
    for filename, page in pages.items():
        with Image.open(folder / filename) as texture:
            texture = texture.convert("RGBA")
            width, height = map(int, page["size"].split(","))
            if texture.size != (width, height):
                texture = texture.resize((width, height), Image.Resampling.BILINEAR)
            for name, info in page.get("regions", {}).items():
                x, y, w, h = map(int, info["bounds"].split(","))
                degrees = {"true": 90, "false": 0}.get(info.get("rotate"), info.get("rotate", 0))
                degrees = int(degrees)
                fw, fh = (h, w) if degrees % 180 == 90 else (w, h)
                crop = texture.crop((x, y, x+fw, y+fh))
                if degrees:
                    crop = crop.rotate(-degrees, expand=True)
                if "offsets" in info:
                    ox, oy, ow, oh = map(int, info["offsets"].split(","))
                    full = Image.new("RGBA", (ow, oh))
                    full.paste(crop, (ox, oh-h-oy))
                    crop = full
                images[name] = crop
    return images


def geometry(data):
    bones = {}
    for bone in data["bones"]:
        bones[bone["name"]] = compose(bones.get(bone.get("parent"), IDENTITY), matrix(bone))
    bone_list = list(bones.values())
    attachments = next(skin["attachments"] for skin in data["skins"] if skin["name"] == "default")
    for slot in data["slots"]:
        name, key = slot["name"], slot.get("attachment")
        attach = attachments.get(name, {}).get(key)
        if not attach:
            continue
        parent = bones[slot["bone"]]
        kind = attach.get("type", "region")
        if kind == "region":
            local = compose(parent, matrix(attach))
            w, h = attach["width"]/2, attach["height"]/2
            points = [transform(local, x, y) for x, y in [(-w,h),(w,h),(w,-h),(-w,-h)]]
            uvs, faces = [(0,0),(1,0),(1,1),(0,1)], [0,1,2,0,2,3]
        elif kind == "mesh":
            uv = attach["uvs"]
            uvs = list(zip(uv[::2], uv[1::2]))
            verts = attach["vertices"]
            if len(verts) == len(uv):
                points = [transform(parent, x, y) for x, y in zip(verts[::2], verts[1::2])]
            else:
                points = []
                source = iter(verts)
                for _ in uvs:
                    x = y = 0
                    for _ in range(int(next(source))):
                        bone = bone_list[int(next(source))]
                        px, py = transform(bone, next(source), next(source))
                        weight = next(source)
                        x += px*weight
                        y += py*weight
                    points.append((x, y))
            faces = attach["triangles"]
        else:
            raise ValueError(f"Unsupported setup attachment {kind}: {name}")
        yield name, attach.get("path", key), points, uvs, faces


def draw_triangle(output, source, target, uv):
    (x0,y0),(x1,y1),(x2,y2) = target
    a,b,c,d = x1-x0, y1-y0, x2-x0, y2-y0
    det = a*d-b*c
    if abs(det) < 1e-8:
        return
    u0,v0 = uv[0]
    u1,v1 = uv[1][0]-u0, uv[1][1]-v0
    u2,v2 = uv[2][0]-u0, uv[2][1]-v0
    ux,uy = (d*u1-b*u2)/det, (a*u2-c*u1)/det
    vx,vy = (d*v1-b*v2)/det, (a*v2-c*v1)/det
    left = max(0, math.floor(min(x for x,y in target)))
    top = max(0, math.floor(min(y for x,y in target)))
    right = min(output.width, math.ceil(max(x for x,y in target))+1)
    bottom = min(output.height, math.ceil(max(y for x,y in target))+1)
    if right <= left or bottom <= top:
        return
    dims = right-left, bottom-top
    warp = source.transform(dims, Image.Transform.AFFINE,
                            (ux, uy, u0+ux*(left-x0)+uy*(top-y0),
                             vx, vy, v0+vx*(left-x0)+vy*(top-y0)), Image.Resampling.BILINEAR)
    mask = Image.new("L", dims)
    ImageDraw.Draw(mask).polygon([(x-left,y-top) for x,y in target], fill=255)
    output.paste(warp, (left, top), mask)


def render(folder, output):
    data = json.loads((folder / "skeleton.json").read_bytes())
    if any(bone.get("transform", "normal") != "normal" for bone in data["bones"]):
        raise ValueError("Unsupported bone transform inheritance")
    images = {}
    for atlas in folder.glob("atlas-*"):
        images.update(atlas_images(atlas))
    layers = list(geometry(data))
    if not layers:
        raise ValueError("No setup layers")
    all_points = [point for _, _, points, _, _ in layers for point in points]
    xs, ys = zip(*all_points)
    body_pts = [p for slot, _, ps, _, _ in layers if "weapon" not in slot.lower() for p in ps]
    bx, by = zip(*(body_pts or all_points))
    scale = min(460/max(max(xs)-min(xs),1), 455/max(max(ys)-min(ys),1))
    cx = (max(bx)+min(bx))/2
    cy = max(24, (SIZE-(max(ys)-min(ys))*scale)/2)+max(ys)*scale
    x_shift = min(max(SIZE/2, 12-(min(xs)-cx)*scale), SIZE-12-(max(xs)-cx)*scale)
    output.mkdir(parents=True, exist_ok=True)
    result = []
    for index, (slot, key, points, uvs, faces) in enumerate(layers):
        source = images[key]
        p = [((x-cx)*scale+x_shift, cy-y*scale) for x,y in points]
        uv = [(u*source.width, v*source.height) for u,v in uvs]
        layer = Image.new("RGBA", (SIZE, SIZE))
        for i in range(0,len(faces),3):
            ids = faces[i:i+3]
            draw_triangle(layer, source, [p[j] for j in ids], [uv[j] for j in ids])
        bbox = layer.getbbox()
        if bbox:
            cropped = layer.crop(bbox)
            filename = output / f"{index:02d}.png"
            cropped.save(filename)
            result.append({"slot": "head" if slot.casefold() == "head" else slot, "image": filename.relative_to(ROOT).as_posix(),
                           "x": bbox[0], "y": bbox[1], "w": cropped.width, "h": cropped.height})
    if not any(item["slot"]=="head" for item in result):
        raise ValueError("No rendered head")
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", type=Path, default=ROOT / ".local-unpacked/limbus-cache/samples")
    parser.add_argument("--output", type=Path, default=ROOT / ".local-unpacked/limbus-cache/editor")
    parser.add_argument("--identities", type=Path)
    args = parser.parse_args()
    names = {"10201":"基础浮士德", "10401":"基础良秀", "10204":"握紧之人浮士德", "10901":"基础罗佳"}
    sources = {key: args.source / key for key in names}
    if args.identities:
        index = json.loads((args.identities / "spine_samples.json").read_text("utf-8"))
        for key, item in index.items():
            if key not in names and "path" in item and item.get("atlases"):
                names[key] = Path(item["path"]).stem.replace("_", " ")
                sources[key] = args.identities / key
    packs = {}
    failures = {}
    for key, name in names.items():
        try:
            layers = render(sources[key], args.output / key)
            embedded = {layer["image"]: base64.b64encode((ROOT / layer["image"]).read_bytes()).decode("ascii")
                        for layer in layers}
            path = args.output / key / "export-data.js"
            path.write_text("window.LIMBUS_EXPORT_IMAGES ||= {}; Object.assign(window.LIMBUS_EXPORT_IMAGES,"
                            + json.dumps(embedded) + ");\n", encoding="utf-8")
            packs[key] = {"name": name, "layers": layers, "exportData": path.relative_to(ROOT).as_posix()}
        except Exception as error:
            failures[key] = f"{type(error).__name__}: {error}"
    if not packs:
        raise SystemExit("No supported sample produced layers")
    (args.output / "parts.js").write_text("window.LIMBUS_PARTS = "+json.dumps(packs, ensure_ascii=False)+";\n", encoding="utf-8")
    (args.output / "preview_issues.json").write_text(json.dumps(failures, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"{len(packs)} rendered, {len(failures)} need separate review")


if __name__ == "__main__":
    main()



