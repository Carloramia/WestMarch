"""Index scene hierarchy and sprite assignments in Ruina character bundles."""
import argparse
import csv
from pathlib import Path
import sys


def pointer_fields(ptr):
    return (ptr.m_FileID, ptr.m_PathID) if ptr is not None else ("", "")


def coords(value):
    return "/".join(str(getattr(value, key)) for key in ("x", "y", "z"))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--bundles", type=Path, required=True)
    parser.add_argument("--unity-reader", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    sys.path.insert(0, str(args.unity_reader))
    import UnityPy

    args.output.parent.mkdir(parents=True, exist_ok=True)
    with args.output.open("w", encoding="utf-8-sig", newline="") as stream:
        writer = csv.writer(stream)
        writer.writerow(("package", "cab", "component_id", "component_type", "object_file_id", "object_id",
                         "object_name", "target_file_id", "target_id", "position_xyz", "scale_xyz",
                         "sorting_layer", "sorting_order", "enabled", "error"))
        for package in sorted(args.bundles.glob("*.pres")):
            try:
                env = UnityPy.load(str(package))
                names = {(obj.assets_file.name, obj.path_id): obj.peek_name() or ""
                         for obj in env.objects if obj.type.name == "GameObject"}
                for obj in env.objects:
                    kind = obj.type.name
                    if kind not in {"Transform", "RectTransform", "SpriteRenderer"}:
                        continue
                    cab = obj.assets_file.name
                    start = (package.name, cab, obj.path_id, kind)
                    try:
                        data = obj.read()
                        owner_file, owner_id = pointer_fields(data.m_GameObject)
                        owner_name = names.get((cab, owner_id), "") if owner_file == 0 else ""
                        prefix = (*start, owner_file, owner_id, owner_name)
                        if kind == "SpriteRenderer":
                            writer.writerow((*prefix, *pointer_fields(data.m_Sprite), "", "",
                                             data.m_SortingLayer, data.m_SortingOrder, data.m_Enabled, ""))
                        else:
                            writer.writerow((*prefix, *pointer_fields(data.m_Father), coords(data.m_LocalPosition),
                                             coords(data.m_LocalScale), "", "", "", ""))
                    except Exception as error:
                        writer.writerow((*start, *([""] * 10), str(error)))
            except Exception as error:
                writer.writerow((package.name, *([""] * 13), str(error)))


if __name__ == "__main__":
    main()

