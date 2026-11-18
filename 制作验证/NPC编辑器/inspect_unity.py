"""Index local Unity game packages and export readable sprite PNGs."""
import argparse
import csv
import json
from pathlib import Path
from time import perf_counter
import re
import sys

GAMES = {
    "ruina": ("Library Of Ruina", "LibraryOfRuina_Data"),
    "limbus": ("Limbus Company", "LimbusCompany_Data"),
    "lobotomy": ("LobotomyCorp", "LobotomyCorp_Data"),
}
SUFFIXES = {".assets", ".pres", ".bundle"}
PRIMARY = {"Sprite", "Texture2D", "GameObject", "AnimationClip", "AnimatorController", "SpriteAtlas", "TextAsset", "MonoBehaviour"}
STEAM = Path("C:/Program Files (x86)/Steam/steamapps/common")


def safe_name(value):
    return re.sub(r"[^\w.-]+", "_", value, flags=re.UNICODE)[:80].strip(" .") or "unnamed"


def name_of(obj):
    if hasattr(obj, "peek_name"):
        return obj.peek_name() or ""
    if obj.type.name in PRIMARY:
        return getattr(obj.read(), "m_Name", "") or ""
    return ""


def scan(game, root, output, unity, export_sprites, limit, only_bundles):
    folder, data = GAMES[game]
    source = root / folder / data
    packages = sorted(p for p in source.rglob("*") if p.is_file() and (p.suffix.lower() in SUFFIXES or re.fullmatch(r"level\d+|globalgamemanagers", p.name)))
    version_file = source / "globalgamemanagers"
    if version_file.is_file():
        version = re.search(rb"(?:20\d{2}|6000)\.\d+\.\d+[fp]\d+", version_file.read_bytes()[:4096])
        if version:
            unity.config.FALLBACK_UNITY_VERSION = version.group().decode("ascii")
    if only_bundles:
        packages = [package for package in packages if package.suffix.lower() == ".bundle"]
    if limit:
        packages = packages[:limit]
    if not packages:
        raise RuntimeError(f"No packages found at {source}")
    output.mkdir(parents=True, exist_ok=True)
    started = perf_counter()
    issues = []
    counts = {"packages": len(packages), "loaded": 0, "objects": 0, "sprites_exported": 0, "textures_exported": 0}
    with (output / "objects.csv").open("w", encoding="utf-8-sig", newline="") as stream:
        writer = csv.writer(stream)
        writer.writerow(("package", "serialized_file", "path_id", "type", "name", "image"))
        for package_no, package in enumerate(packages, start=1):
            relative = package.relative_to(source).as_posix()
            try:
                env = unity.load(str(package))
                objects = env.objects
                if not objects:
                    issues.append({"package": relative, "stage": "load", "error": "No serialized objects returned"})
                else:
                    counts["loaded"] += 1
                for obj in objects:
                    kind = obj.type.name
                    file_name = getattr(obj.assets_file, "name", "")
                    obj_name = ""
                    image_path = ""
                    counts["objects"] += 1
                    try:
                        if kind in PRIMARY:
                            obj_name = name_of(obj)
                        if export_sprites and kind in {"Sprite", "Texture2D"}:
                            image = obj.read().image
                            destination = output / kind / f"{package_no:04d}-{safe_name(package.stem)}"
                            destination.mkdir(parents=True, exist_ok=True)
                            target = destination / f"{safe_name(file_name)}-{obj.path_id}-{safe_name(obj_name)}.png"
                            image.save(target)
                            image_path = target.relative_to(output).as_posix()
                            counts["sprites_exported" if kind == "Sprite" else "textures_exported"] += 1
                    except Exception as error:
                        issues.append({"package": relative, "file": file_name, "path_id": obj.path_id, "stage": "object", "error": str(error)})
                    writer.writerow((relative, file_name, obj.path_id, kind, obj_name, image_path))
            except Exception as error:
                issues.append({"package": relative, "stage": "load", "error": str(error)})
            if package_no % 50 == 0 or package_no == len(packages):
                print(f"{game}: {package_no}/{len(packages)} {counts}", flush=True)
    summary = {"game": game, "source": str(source), **counts, "issues": len(issues), "seconds": round(perf_counter() - started, 1)}
    (output / "summary.json").write_text(json.dumps(summary, indent=2, ensure_ascii=False), encoding="utf-8")
    (output / "issues.json").write_text(json.dumps(issues, indent=2, ensure_ascii=False), encoding="utf-8")
    return summary


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--steam", type=Path, default=STEAM)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--game", choices=GAMES, action="append")
    parser.add_argument("--unity-reader", type=Path)
    parser.add_argument("--export-sprites", action="store_true")
    parser.add_argument("--limit", type=int)
    parser.add_argument("--only-bundles", action="store_true")
    args = parser.parse_args()
    if args.unity_reader:
        sys.path.insert(0, str(args.unity_reader))
    try:
        import UnityPy
    except ImportError as error:
        parser.exit(2, f"UnityPy unavailable: {error}\n")
    for game in args.game or GAMES:
        print(json.dumps(scan(game, args.steam, args.output / game, UnityPy, args.export_sprites, args.limit, args.only_bundles), ensure_ascii=False), flush=True)


if __name__ == "__main__":
    main()




