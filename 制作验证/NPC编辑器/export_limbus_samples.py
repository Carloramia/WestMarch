"""Export inspected Limbus battle prefab Spine dependencies for local study."""
import argparse
import csv
from hashlib import sha256
import json
from pathlib import Path
import re
import sys
import warnings


def descendants(root):
    yield root
    for component in root.m_Component:
        obj = component.component.deref()
        if obj.type.name == "Transform":
            for child in obj.read().m_Children:
                yield from descendants(child.deref().read().m_GameObject.deref().read())


def script_bytes(obj):
    value = obj.read().m_Script
    return value if isinstance(value, bytes) else value.encode("utf-8", "surrogateescape")


def by_ref(owner, ref):
    from UnityPy.classes import PPtr
    file_id, path_id = ref["m_FileID"], ref["m_PathID"]
    try:
        return PPtr(m_FileID=file_id, m_PathID=path_id, assetsfile=owner.assets_file).deref()
    except FileNotFoundError:
        if file_id <= 0:
            raise
        import UnityPy
        external = Path(owner.assets_file.externals[file_id-1].path).name.lower()
        package = CACHE_CABS.get(external)
        if package is None:
            raise
        env = UnityPy.load(str(package))
        return next(obj for obj in env.objects
                    if obj.path_id == path_id and obj.assets_file.name.lower() == external)


def inspect_model(prefab, output):
    for node in descendants(prefab.read()):
        if node.m_Name != "[SpinePivot]":
            continue
        for renderer in descendants(node):
            for part in renderer.m_Component:
                comp = part.component.deref()
                if comp.type.name != "MonoBehaviour":
                    continue
                tree = comp.read_typetree()
                if tree.get("skeletonDataAsset", {}).get("m_PathID"):
                    return export_spine(comp, tree["skeletonDataAsset"], output)
    for node in descendants(prefab.read()):
        if not re.search(r"SpRenderer|SpriteRenderer", node.m_Name, re.I):
            continue
        for part in node.m_Component:
            comp = part.component.deref()
            if comp.type.name != "SpriteRenderer":
                continue
            pointer = comp.read().m_Sprite
            if not pointer.m_PathID:
                continue
            sprite = by_ref(comp, {"m_FileID": pointer.m_FileID, "m_PathID": pointer.m_PathID})
            image = sprite.read().image
            if image.width <= 1 or image.height <= 1 or not image.getbbox():
                continue
            output.mkdir(parents=True, exist_ok=True)
            image.save(output / "default-sprite.png")
            return {"kind": "SpriteRenderer", "sprite_path_id": sprite.path_id,
                    "image": "default-sprite.png", "width": image.width, "height": image.height}
    raise ValueError("No linked default Spine component or nonempty default SpriteRenderer")


def export_spine(component, reference, output):
    skeleton_data = by_ref(component, reference)
    skeleton_tree = skeleton_data.read_typetree()
    source = by_ref(skeleton_data, skeleton_tree["skeletonJSON"])
    raw = script_bytes(source)
    data = json.loads(raw)
    output.mkdir(parents=True, exist_ok=True)
    (output / "skeleton.json").write_bytes(raw)
    atlases = []
    for index, ref in enumerate(skeleton_tree["atlasAssets"], 1):
        atlas_asset = by_ref(skeleton_data, ref)
        atlas_tree = atlas_asset.read_typetree()
        atlas_text = by_ref(atlas_asset, atlas_tree["atlasFile"])
        text = script_bytes(atlas_text).decode("utf-8-sig")
        folder = output / f"atlas-{index}"
        folder.mkdir(exist_ok=True)
        (folder / "original.atlas").write_text(text, encoding="utf-8", newline="")
        pages = re.findall(r"(?im)^([^:\r\n]+\.png)[ \t]*\r?$", text)
        materials = atlas_tree["materials"]
        if len(pages) != len(materials):
            raise ValueError(f"Atlas pages/material count differs: {pages} vs {len(materials)}")
        page_meta = []
        for page_name, material_ref in zip(pages, materials, strict=True):
            if Path(page_name).name != page_name:
                raise ValueError(f"Invalid page filename: {page_name}")
            material = by_ref(atlas_asset, material_ref)
            envs = dict(material.read_typetree()["m_SavedProperties"]["m_TexEnvs"])
            tex = by_ref(material, envs["_MainTex"]["m_Texture"])
            image = tex.read().image
            image.save(folder / page_name)
            page_meta.append({"file": page_name, "width": image.width, "height": image.height,
                              "texture_path_id": tex.path_id})
        atlases.append({"atlas_path_id": atlas_text.path_id, "pages": page_meta})
    return {"kind": "Spine", "spine": data["skeleton"].get("spine"), "skeleton_path_id": source.path_id,
            "slots": [slot["name"] for slot in data["slots"]],
            "animations": list(data.get("animations", {})), "atlases": atlases}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--cache", type=Path, required=True)
    parser.add_argument("--index", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--unity-reader", type=Path, required=True)
    parser.add_argument("--all-prefabs", action="store_true")
    parser.add_argument("--retry", action="store_true")
    parser.add_argument("identities", nargs="*")
    args = parser.parse_args()
    sys.path.insert(0, str(args.unity_reader))
    import UnityPy
    UnityPy.config.FALLBACK_UNITY_VERSION = "6000.3.12f1"
    warnings.filterwarnings("ignore", category=UnityPy.config.UnityVersionFallbackWarning)
    candidates = {}
    global CACHE_CABS
    CACHE_CABS = {}
    with args.index.open(encoding="utf-8-sig", newline="") as stream:
        for row in csv.DictReader(stream):
            if row["cab"]:
                CACHE_CABS.setdefault(row["cab"].lower(), args.cache / row["cache_path"])
            if row["type"] != "GameObject":
                continue
            if args.all_prefabs and "/Prefab/SD/" in row["unity_path"]:
                path = row["unity_path"]
                label = re.sub(r"[^\w.-]", "_", Path(path).stem)[:55]
                candidates[label + "-" + sha256(path.encode()).hexdigest()[:8]] = row
                continue
            match = re.search(r"/Prefab/SD/Personality/(\d+)_", row["unity_path"])
            if match and (not args.identities or match[1] in args.identities):
                candidates[match[1]] = row
    report = args.output / "spine_samples.json"
    results = json.loads(report.read_text("utf-8")) if args.retry and report.exists() else {}
    identities = args.identities or sorted(candidates)
    if args.retry:
        identities = [key for key in identities if key not in results or "error" in results[key]]
    for number, identity in enumerate(identities, 1):
        try:
            row = candidates[identity]
            env = UnityPy.load(str(args.cache / row["cache_path"]))
            prefab = next(obj for obj in env.objects if obj.path_id == int(row["path_id"])
                          and obj.assets_file.name == row["cab"])
            results[identity] = {"path": row["unity_path"], "cache_path": row["cache_path"],
                                 **inspect_model(prefab, args.output / identity)}
        except Exception as error:
            row = candidates.get(identity, {})
            results[identity] = {"path": row.get("unity_path", ""), "cache_path": row.get("cache_path", ""),
                                 "error": f"{type(error).__name__}: {error}"}
        if number % 25 == 0 or number == len(identities):
            print(f"{number}/{len(identities)} inspected", flush=True)
    args.output.mkdir(parents=True, exist_ok=True)
    (args.output / "spine_samples.json").write_text(json.dumps(results, indent=2, ensure_ascii=False), encoding="utf-8")
    print(json.dumps({"total": len(results), "exported": sum("error" not in row for row in results.values())}, ensure_ascii=False))


if __name__ == "__main__":
    main()





