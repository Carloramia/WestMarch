"""Record Unity Sprite placement data for Library of Ruina appearance parts."""
import argparse
import csv
from pathlib import Path
import re
import sys


def vector(value, fields):
    return "/".join(str(getattr(value, key)) for key in fields) if value is not None else ""


def slot(name):
    match = re.match(r"^(FrontHair|BackHair|Eyebrow|Mouth|Eye|Head|HairAccessory)(?:_|$)", name, re.I)
    return match.group(1) if match else ""


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--resources", type=Path, required=True)
    parser.add_argument("--unity-reader", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    sys.path.insert(0, str(args.unity_reader))
    import UnityPy

    args.output.parent.mkdir(parents=True, exist_ok=True)
    env = UnityPy.load(str(args.resources))
    with args.output.open("w", encoding="utf-8-sig", newline="") as stream:
        writer = csv.writer(stream)
        writer.writerow(("path_id", "name", "slot", "direction", "texture_file_id", "texture_path_id",
                         "sprite_rect_xywh", "render_rect_xywh", "render_offset_xy", "pivot_xy",
                         "sprite_offset_xy", "pixels_per_unit", "packing_flags", "error"))
        for obj in env.objects:
            if obj.type.name != "Sprite":
                continue
            name = obj.peek_name() or ""
            part = slot(name)
            if not part:
                continue
            side = re.search(r"(?:^|_)(Front|Side)(?:_|$)", name)
            start = (obj.path_id, name, part, side.group(1) if side else "")
            try:
                sprite = obj.read()
                render = sprite.m_RD
                writer.writerow((*start, render.texture.m_FileID, render.texture.m_PathID,
                                 vector(sprite.m_Rect, ("x", "y", "width", "height")),
                                 vector(render.textureRect, ("x", "y", "width", "height")),
                                 vector(render.textureRectOffset, ("x", "y")),
                                 vector(sprite.m_Pivot, ("x", "y")),
                                 vector(sprite.m_Offset, ("x", "y")),
                                 sprite.m_PixelsToUnits, render.settingsRaw, ""))
            except Exception as error:
                writer.writerow((*start, *([""] * 9), str(error)))


if __name__ == "__main__":
    main()

