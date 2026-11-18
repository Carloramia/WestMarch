"""Read-only inventory of local Limbus Company Unity cache bundles."""
import argparse
from collections import Counter
import csv
import json
from pathlib import Path
import re
import sys
import warnings

WATCH = {"AssetBundle", "TextAsset", "Texture2D", "SpriteAtlas", "AnimationClip", "AnimatorController"}


def name_for(obj):
    try:
        return obj.peek_name() or ""
    except Exception:
        return ""


def scan(cache, output, unity):
    output.mkdir(parents=True, exist_ok=True)
    bundles = sorted(cache.glob("*/*/__data"))
    if not bundles:
        raise SystemExit(f"No Unity cache bundles at {cache}")
    issues = []
    totals = Counter()
    indexed = 0
    with (output / "cache_bundles.csv").open("w", encoding="utf-8-sig", newline="") as bundles_file, \
         (output / "cache_entries.csv").open("w", encoding="utf-8-sig", newline="") as entries_file, \
         (output / "spine_objects.csv").open("w", encoding="utf-8-sig", newline="") as spine_file:
        bw, ew, sw = map(csv.writer, (bundles_file, entries_file, spine_file))
        bw.writerow(("cache_path", "size", "entry_count", "object_count", "unity_types"))
        ew.writerow(("cache_path", "unity_path", "cab", "path_id", "type"))
        sw.writerow(("cache_path", "cab", "path_id", "type", "name"))
        for number, bundle in enumerate(bundles, 1):
            key = bundle.relative_to(cache).as_posix()
            try:
                env = unity.load(str(bundle))
                objects = env.objects
                if not objects:
                    raise ValueError("No serialized objects")
                entries = env.container
                by_type = Counter(obj.type.name for obj in objects)
                bw.writerow((key, bundle.stat().st_size, len(entries), len(objects), json.dumps(by_type, sort_keys=True)))
                for entry, pointer in entries.items():
                    try:
                        obj = pointer.deref()
                        ew.writerow((key, entry, obj.assets_file.name, obj.path_id, obj.type.name))
                    except Exception as error:
                        ew.writerow((key, entry, "", pointer.m_PathID, "unresolved"))
                        issues.append({"cache_path": key, "entry": entry, "error": str(error)})
                for obj in objects:
                    kind = obj.type.name
                    if kind not in WATCH:
                        continue
                    name = name_for(obj)
                    if kind == "AssetBundle" or re.search(r"spine|skeleton|atlas|skel", name, re.I):
                        sw.writerow((key, obj.assets_file.name, obj.path_id, kind, name))
                indexed += 1
                totals.update(by_type)
            except Exception as error:
                issues.append({"cache_path": key, "error": str(error)})
            if number % 200 == 0 or number == len(bundles):
                print(f"{number}/{len(bundles)} inspected, {indexed} readable", flush=True)
    summary = {"source": str(cache), "bundles": len(bundles), "readable": indexed,
               "objects": sum(totals.values()), "types": dict(totals), "issues": len(issues)}
    for filename, value in (("summary.json", summary), ("issues.json", issues)):
        (output / filename).write_text(json.dumps(value, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps({k: v for k, v in summary.items() if k != "types"}, ensure_ascii=False), flush=True)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--cache", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--unity-reader", type=Path, required=True)
    args = parser.parse_args()
    sys.path.insert(0, str(args.unity_reader))
    import UnityPy
    UnityPy.config.FALLBACK_UNITY_VERSION = "6000.3.12f1"
    warnings.filterwarnings("ignore", category=UnityPy.config.UnityVersionFallbackWarning)
    scan(args.cache, args.output, UnityPy)


if __name__ == "__main__":
    main()

