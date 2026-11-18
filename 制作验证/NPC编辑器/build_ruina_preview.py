"""Build a local browser manifest from extracted Ruina sprite placement data."""
import csv
import json
from pathlib import Path
import re

from PIL import Image

ROOT = Path(__file__).resolve().parent
DATA = ROOT / ".local-unpacked" / "ruina"
PATTERN = re.compile(r"^(FrontHair|BackHair|Eye|Eyebrow|Mouth)_(FrontLayer|SideLayer|Front|Side)_(?:(Normal|Atk|Damaged)_)?(\d+)_(\d+)$")


def load_csv(name):
    with (DATA / name).open(encoding="utf-8-sig", newline="") as stream:
        return list(csv.DictReader(stream))


def pair(value):
    return [float(part) for part in value.split("/")]


def main():
    objects = load_csv("objects.csv")
    images = {row["path_id"]: row["image"] for row in objects
              if row["package"] == "resources.assets" and row["type"] == "Sprite" and row["image"]}
    items = {}
    for row in load_csv("appearance_parts.csv"):
        path_id = row["path_id"]
        if path_id in {"23412", "22263"}:
            key = "Head.Front" if path_id == "23412" else "Head.Side"
        elif match := PATTERN.fullmatch(row["name"]):
            slot, direction, expression, group, variant = match.groups()
            key = ".".join((slot, direction, expression or "Normal", f"{group}-{variant}"))
        else:
            continue
        image = DATA / images[path_id]
        with Image.open(image) as sprite:
            width, height = sprite.size
        _, _, canvas_width, canvas_height = pair(row["sprite_rect_xywh"])
        x, y = pair(row["render_offset_xy"])
        pivot_x, pivot_y = pair(row["pivot_xy"])
        items[key] = {"path": image.relative_to(ROOT).as_posix(), "name": row["name"],
                      "x": round(x - canvas_width * pivot_x, 3),
                      "y": round(canvas_height * (1 - pivot_y) - y - height, 3),
                      "w": width, "h": height}
    outfits = {
        "char_182": ("深色束带长衣", "-5473650899342581838", 0.51, 0.07),
        "char_119": ("蓝纹仪式袍", "-8365668712419883770", 0.48, 0.05),
        "char_130": ("红花礼服", "-9173574411218917604", 0.45, 0.09),
        "char_192": ("蓝肩战装", "8559639038256005256", 0.66, 0.11),
        "char_197": ("黑色斗篷", "-3921635876140183123", 0.49, 0.10),
    }
    garment_objects = {(Path(row["package"]).stem, row["path_id"]): row["image"]
                       for row in objects if row["type"] == "Sprite" and row["image"]}
    for bundle, (name, path_id, neck_x, neck_y) in outfits.items():
        image = DATA / garment_objects[bundle, path_id]
        with Image.open(image) as sprite:
            width, height = sprite.size
        items["Outfit." + bundle] = {"name": name, "path": image.relative_to(ROOT).as_posix(),
                                     "w": width, "h": height, "neckX": neck_x, "neckY": neck_y}
    print(f"{len(items)} original sprite entries")
    (DATA / "editor-parts.js").write_text("window.RUINA_PARTS = " + json.dumps(items, ensure_ascii=False) + ";\n", encoding="utf-8")


if __name__ == "__main__":
    main()


