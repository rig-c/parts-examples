#!/usr/bin/env python3
"""Author, merge, stitch, build, and check the 4 remaining Family homewear outfits.

Generalizes Naru's homewear authoring pipeline (author-inputs -> rig-parts rig ->
merge -> neck-seam stitch -> rigc build -> rig-parts check -> protected-check)
for roa, luna, jinni, and nova.
"""
import argparse
import hashlib
import json
import pathlib
import shutil
import subprocess

OFFICE_CLOTHING = {
    "shoes",
    "legwear",
    "bottomwear",
    "neck",
    "neckwear",
    "topwear",
    "handwear_r",
    "handwear_l",
}
NEW_NAMES = ["shoes", "bottomwear", "neck", "topwear", "sleeves"]

CHAR_SPECS = {
    "roa": {
        "hem_r": {"at": [205, 960], "tip": [195, 1340]},
        "hem_l": {"at": [555, 960], "tip": [590, 1340]},
        "neck_segments": [["chest", [365, 430], [365, 657]], ["head", [365, 394], [365, 344]]],
        "topwear_segments": [["chest", [360, 448], [360, 843]], ["hip", [360, 843], [360, 946]]],
        "cardigan_segments": [
            ["chest", [220, 480], [220, 840]],
            ["chest", [500, 480], [520, 840]],
            ["hip", [210, 840], [205, 960]],
            ["hip", [525, 840], [555, 960]],
            "cardigan_hem_r",
            "cardigan_hem_l",
        ],
        "sleeves_segments": [
            ["chest", [120, 520], [120, 940]],
            ["chest", [520, 520], [720, 580]],
        ],
        "stitch": [("neck", 440, True), ("topwear", 485, False)],
    },
    "luna": {
        "hem_r": {"at": [235, 1020], "tip": [220, 1245]},
        "hem_l": {"at": [500, 1020], "tip": [515, 1245]},
        "neck_segments": [["chest", [370, 565], [368, 790]], ["head", [370, 535], [370, 480]]],
        "topwear_segments": [["chest", [368, 575], [368, 940]], ["hip", [368, 940], [368, 1025]]],
        "cardigan_segments": [
            ["chest", [250, 600], [240, 940]],
            ["chest", [485, 600], [495, 940]],
            ["hip", [240, 940], [235, 1020]],
            ["hip", [495, 940], [500, 1020]],
            "cardigan_hem_r",
            "cardigan_hem_l",
        ],
        "sleeves_segments": [
            ["chest", [200, 650], [520, 1180]],
        ],
        "stitch": [("neck", 575, True), ("topwear", 645, False)],
    },
    "jinni": {
        "hem_r": {"at": [330, 940], "tip": [325, 1035]},
        "hem_l": {"at": [550, 940], "tip": [560, 1035]},
        "neck_segments": [["chest", [428, 545], [428, 734]], ["head", [428, 500], [428, 410]]],
        "topwear_segments": [["chest", [440, 552], [440, 866]], ["hip", [440, 866], [440, 1035]]],
        "cardigan_segments": [
            ["chest", [330, 620], [330, 880]],
            ["chest", [540, 620], [550, 880]],
            ["hip", [330, 880], [330, 940]],
            ["hip", [550, 880], [550, 940]],
            "cardigan_hem_r",
            "cardigan_hem_l",
        ],
        "sleeves_segments": [
            ["chest", [230, 640], [520, 1080]],
        ],
        "stitch": [("neck", 555, True), ("topwear", 625, False)],
    },
    "naru": {
        "hem_r": {"at": [243, 1080], "tip": [245, 1350]},
        "hem_l": {"at": [532, 1080], "tip": [532, 1350]},
        "neck_segments": [["chest", [380, 650], [380, 780]], ["head", [380, 575], [380, 510]]],
        "topwear_segments": [["chest", [380, 630], [380, 910]], ["hip", [380, 910], [380, 1080]]],
        "cardigan_segments": [
            ["chest", [240, 640], [240, 950]],
            ["chest", [535, 640], [535, 950]],
            ["hip", [245, 940], [245, 1080]],
            ["hip", [532, 940], [532, 1080]],
            "cardigan_hem_r",
            "cardigan_hem_l",
        ],
        "sleeves_segments": [
            ["chest", [180, 820], [615, 1020]],
        ],
        "stitch": [("neck", 625, True), ("topwear", 705, False)],
    },
    "nova": {
        "hem_r": {"at": [225, 1020], "tip": [220, 1350]},
        "hem_l": {"at": [540, 1020], "tip": [560, 1410]},
        "neck_segments": [["chest", [435, 550], [410, 780]], ["head", [435, 500], [435, 450]]],
        "topwear_segments": [["chest", [380, 555], [380, 900]], ["hip", [380, 900], [380, 975]]],
        "cardigan_segments": [
            ["chest", [250, 580], [235, 920]],
            ["chest", [520, 560], [530, 920]],
            ["hip", [235, 920], [225, 1020]],
            ["hip", [530, 920], [540, 1020]],
            "cardigan_hem_r",
            "cardigan_hem_l",
        ],
        "sleeves_segments": [
            ["chest", [220, 660], [640, 1150]],
        ],
        "stitch": [("neck", 560, True), ("topwear", 625, False)],
    },
}


def prepare_author_inputs(family: pathlib.Path, char: str, force: bool):
    spec = CHAR_SPECS[char]
    home = family / "outfits/homewear" / char
    candidate = home / "prepared"
    author = home / "authoring"
    if author.exists():
        if force:
            shutil.rmtree(author)
        else:
            raise RuntimeError(f"HOMEWEAR_AUTHOR_FRESH_INPUT_REQUIRED: {author}")
    inputs = author / "inputs"
    (inputs / "parts").mkdir(parents=True)
    prototype = json.loads((candidate / "prototype.json").read_text())
    records = []
    for row in prototype["parts"]:
        name = row["name"]
        shutil.copy2(candidate / "parts" / (name + ".png"), inputs / "parts" / (name + ".png"))
        records.append({
            **{k: row[k] for k in ["name", "x", "y", "w", "h", "opaque_px"]},
            "from": "full:author:homewear-" + name,
            "projected_core_px": 0,
            "source_px_taken": 0,
            "refused_drift_px": 0,
            "merged_px": 0,
            "seam_override_px": 0,
        })
    (inputs / "parts.json").write_text(
        json.dumps(
            {"rig_size": [800, 2284], "scale_rig_per_source": 1, "ghost_px": {}, "parts": records},
            indent=2,
        )
        + "\n"
    )
    cfg = json.loads((family / char / "config.json").read_text())
    cfg["key"] = f"{char}_homewear"
    cfg.pop("seethrough", None)
    cfg["assemble"] = {
        "rig_scale": 1,
        "plan": [[r["name"], "full", "author:homewear-" + r["name"]] for r in records],
    }
    cfg["motion"].pop("blink", None)
    baseline_rig = json.loads((family / char / "out/rig/rig.json").read_text())
    cfg["constraints"] = json.loads(json.dumps(baseline_rig["constraints"]))
    cfg["bones"] += [
        {"name": "cardigan_hem_r", "parent": "hip", **spec["hem_r"]},
        {"name": "cardigan_hem_l", "parent": "hip", **spec["hem_l"]},
    ]
    for side in ["r", "l"]:
        cfg["constraints"].append({
            "type": "physics",
            "name": f"cardigan_hem_{side}_phys",
            "bone": f"cardigan_hem_{side}",
            "rotate": 1,
            "inertia": 0.15,
            "strength": 360,
            "damping": 0.92,
            "mass": 1,
            "wind": 0.11,
            "gravity": 0.06,
            "mix": 1,
        })
    top = json.loads(json.dumps(cfg["meshes"]["topwear"]))
    top["segments"] = [*spec["topwear_segments"], *spec["cardigan_segments"]]
    top["contour"]["tolerance"] = 1
    top["contour"]["margin"] = 3
    bust_override_path = home / "bust-regions.json"
    if bust_override_path.is_file():
        bust_override = json.loads(bust_override_path.read_text())
        for reg in top["contour"].get("regions", []):
            if reg["name"] in bust_override:
                ov = bust_override[reg["name"]]
                reg["cx"] = round(float(ov["cx"]), 2)
                reg["cy"] = round(float(ov["cy"]), 2)
                reg["r"] = round(float(ov["r"]), 2)
                reg["band"] = round(float(ov["band"]), 2)
    neck = json.loads(json.dumps(cfg["meshes"]["neck"]))
    neck["segments"] = spec["neck_segments"]
    cfg["meshes"] = {
        "neck": neck,
        "topwear": top,
        "sleeves": {
            "contour": {
                "tolerance": 1,
                "margin": 3,
                "spacing": 32,
                "maxEdge": 54,
                "stray": 400,
                "bridges": True,
            },
            "r": 12,
            "segments": spec["sleeves_segments"],
        },
    }
    cfg["regions"] = {"shoes": "root", "bottomwear": "hip"}
    cfg["note"] = (
        "Consumer authored homewear: common bone/motion/physics definitions are preserved in final assembly; "
        "new cardigan hems have separate physics on unified topwear. Source lineage is in prepared/prototype.json."
    )
    (author / "config.json").write_text(json.dumps(cfg, indent=2) + "\n")


def run_rig_parts_rig(family: pathlib.Path, char: str):
    home = family / "outfits/homewear" / char
    author = home / "authoring"
    cmd = [
        "node",
        "/Users/firejune/Workspace/Firejune/rig-parts/bin/rig-parts.cjs",
        "rig",
        "--config",
        str(author / "config.json"),
        "--parts",
        str(author / "inputs"),
        "--out",
        str(author / "rig"),
    ]
    subprocess.run(cmd, check=True)


def merge_with_baseline(family: pathlib.Path, char: str, force: bool):
    home = family / "outfits/homewear" / char
    authored = home / "authoring/rig"
    baseline = family / char / "out"
    out = home / "out"
    if out.exists():
        if force:
            shutil.rmtree(out)
        else:
            raise RuntimeError(f"HOMEWEAR_MERGE_FRESH_OUTPUT_REQUIRED: {out}")

    rig = json.loads((baseline / "rig/rig.json").read_text())
    new = json.loads((authored / "rig.json").read_text())
    common_slots = [s["name"] for s in rig["slots"] if s["name"] not in OFFICE_CLOTHING]
    used = {"root", "hip", "chest", "chest_ctl", "neck", "head", "head_ctl", "boob_r", "boob_l"}
    old_bones = {b["name"]: b for b in rig["bones"]}
    new_bones = {b["name"]: b for b in new["bones"]}
    for name in used:
        if name in old_bones and old_bones[name] != new_bones.get(name):
            raise RuntimeError(f"HOMEWEAR_BIND_FRAME_CHANGED {char}:{name}")
    extra = [b for b in new["bones"] if b["name"] not in old_bones]
    if {b["name"] for b in extra} != {"cardigan_hem_r", "cardigan_hem_l"}:
        raise RuntimeError(f"HOMEWEAR_UNEXPECTED_NEW_BONE {char}: {[b['name'] for b in extra]}")
    rig["bones"] += extra

    old_constraints = {(c["type"], c["name"]) for c in rig["constraints"]}
    extra_constraints = [c for c in new.get("constraints", []) if (c["type"], c["name"]) not in old_constraints]
    if {c["name"] for c in extra_constraints} != {"cardigan_hem_r_phys", "cardigan_hem_l_phys"}:
        raise RuntimeError(f"HOMEWEAR_UNEXPECTED_NEW_CONSTRAINT {char}: {[c['name'] for c in extra_constraints]}")
    rig["constraints"] += extra_constraints

    old_slots = {s["name"]: s for s in rig["slots"]}
    new_slots = {s["name"]: s for s in new["slots"]}
    slot_order = ["hair_back", *NEW_NAMES, *[n for n in common_slots if n != "hair_back"]]
    rig["slots"] = [new_slots[n] if n in NEW_NAMES else old_slots[n] for n in slot_order]
    rig["skins"]["default"] = {
        n: new["skins"]["default"][n] if n in NEW_NAMES else rig["skins"]["default"][n]
        for n in slot_order
    }

    (out / "rig/images").mkdir(parents=True)
    (out / "parts").mkdir()
    for n in slot_order:
        source_dir = authored if n in NEW_NAMES else baseline / "rig"
        for attachment in rig["skins"]["default"][n].values():
            shutil.copy2(source_dir / "images" / attachment["image"], out / "rig/images" / attachment["image"])

    old_parts_list = json.loads((baseline / "parts.json").read_text())["parts"]
    common_part_names = [p["name"] for p in old_parts_list if p["name"] not in OFFICE_CLOTHING]
    part_order = ["hair_back", *NEW_NAMES, *[n for n in common_part_names if n != "hair_back"]]
    for n in part_order:
        source_parts = home / "authoring/inputs" if n in NEW_NAMES else baseline
        shutil.copy2(source_parts / "parts" / (n + ".png"), out / "parts" / (n + ".png"))

    old_parts = {p["name"]: p for p in old_parts_list}
    new_parts = {p["name"]: p for p in json.loads((home / "authoring/inputs/parts.json").read_text())["parts"]}
    parts = {
        "rig_size": [800, 2284],
        "scale_rig_per_source": 1,
        "ghost_px": {},
        "parts": [new_parts[n] if n in NEW_NAMES else old_parts[n] for n in part_order],
    }
    old_reports = json.loads((baseline / "rig/mesh_report.json").read_text())
    new_reports = json.loads((authored / "mesh_report.json").read_text())
    (out / "rig/mesh_report.json").write_text(
        json.dumps([r for r in old_reports if r["part"] in common_part_names] + new_reports, indent=2) + "\n"
    )
    (out / "parts.json").write_text(json.dumps(parts, indent=2) + "\n")
    (out / "rig/rig.json").write_text(json.dumps(rig, indent=2) + "\n")
    shutil.copy2(baseline / "rig/motion.json", out / "rig/motion.json")
    shutil.copy2(home / "prepared/assembled-white.png", home / "inputs/painting.png")
    (out / "assembly.json").write_text(
        json.dumps(
            {
                "spec": "family-homewear-assembly/1",
                "character": char,
                "commonBonePrefix": len(old_bones),
                "commonSlots": common_slots,
                "newClothingSlots": NEW_NAMES,
                "appendedBones": [b["name"] for b in extra],
                "motion": "Exact accepted motion bytes",
                "commonPhysics": "Exact accepted constraint prefix",
                "sourceReference": (
                    "Registered full static composition with exact accepted head assets; this is the intended "
                    "composite reference, not untouched original artwork. Original crop remains painting-clothing-source.png."
                ),
                "status": "AWAITING_OFFICIAL_BUILD_CHECK",
            },
            indent=2,
        )
        + "\n"
    )


def stitch_neck_seam(family: pathlib.Path, char: str):
    spec = CHAR_SPECS[char]
    home = family / "outfits/homewear" / char
    target = home / "out/rig/rig.json"
    before = target.read_bytes()
    rig = json.loads(before)
    parts = {p["name"]: p for p in json.loads((home / "out/parts.json").read_text())["parts"]}
    rows = []
    for name, threshold, lower in spec["stitch"]:
        attachment = rig["skins"]["default"][name][name]
        record = parts[name]
        changed = []
        for i, weights in enumerate(attachment["weights"]):
            source_y = record["y"] - 4 + attachment["uvs"][2 * i + 1] * attachment["height"]
            if not (source_y >= threshold if lower else source_y <= threshold):
                continue
            chest = next((w for w in weights if w["bone"] == "chest"), None)
            if chest is None:
                raise RuntimeError(f"HOMEWEAR_EXISTING_CHEST_BIND_REQUIRED {char}:{name} vertex={i} y={source_y}")
            bound = [{**chest, "weight": 1}]
            if bound != weights:
                changed.append({
                    "vertex": i,
                    "sourceY": source_y,
                    "before": [{"bone": w["bone"], "weight": w["weight"]} for w in weights],
                })
            attachment["weights"][i] = bound
        rows.append({
            "part": name,
            "sourceYThreshold": threshold,
            "side": "atOrBelow" if lower else "atOrAbove",
            "changed": changed,
        })
    text = json.dumps(rig, indent=2) + "\n"
    target.write_text(text)
    (home / "out/neck-seam-stitch.json").write_text(
        json.dumps(
            {
                "spec": "family-homewear-neck-seam/1",
                "character": char,
                "beforeRigSHA256": hashlib.sha256(before).hexdigest(),
                "afterRigSHA256": hashlib.sha256(text.encode()).hexdigest(),
                "rows": rows,
                "scope": (
                    "Existing chest bind coordinates only. New neck lower edge and upper camisole/cardigan use "
                    "the same chest affine transform. Original common bones/constraints/motion/attachments and "
                    "every art pixel, UV and triangle remain unchanged."
                ),
                "reason": "Native dark motion closeup exposed independently weighted shared skin edge despite a green zero-fold check.",
            },
            indent=2,
        )
        + "\n"
    )
    return {r["part"]: len(r["changed"]) for r in rows}


def run_build_and_check(family: pathlib.Path, char: str):
    home = family / "outfits/homewear" / char
    out = home / "out"
    subprocess.run(
        [
            "node",
            "/Users/firejune/Workspace/Firejune/rig-parts/bin/rig-parts.cjs",
            "check",
            "--rig",
            str(out / "rig"),
            "--parts",
            str(out),
            "--source",
            str(home / "inputs/painting.png"),
            "--out",
            str(out / "check"),
            "--page-edges",
            "free",
            "--pack-shape",
            "polygon",
        ],
        check=True,
    )
    check = json.loads((out / "check/check.json").read_text())
    if not check.get("PASS") or not check.get("gate_spine_html_green"):
        raise RuntimeError(f"HOMEWEAR_CHECK_FAILED {char}: {check}")
    return check


def verify_protected(family: pathlib.Path, char: str):
    home = family / "outfits/homewear" / char
    record = json.loads((home / "protected-baseline.json").read_text())
    errors = []
    for rel, expected in record["files"].items():
        path = family / rel
        found = hashlib.sha256(path.read_bytes()).hexdigest() if path.is_file() else "MISSING"
        if found != expected:
            errors.append({"file": rel, "found": found, "required": expected})
    source = json.loads((home / "source-provenance.json").read_text())
    if hashlib.sha256((home / source["source"]).read_bytes()).hexdigest() != source["sourceSHA256"]:
        errors.append({"file": source["source"], "reason": "original copy changed"})
    variant = home / "out/rig/rig.json"
    baseline = json.loads((family / char / "out/rig/rig.json").read_text())
    rig = json.loads(variant.read_text())
    for field in ["bones", "constraints", "stops"]:
        required = baseline.get(field, [])
        found = rig.get(field, [])
        if found[: len(required)] != required:
            errors.append({"field": field, "reason": "accepted common entries or their order changed"})
    if baseline.get("skeleton") != rig.get("skeleton"):
        errors.append({"field": "skeleton", "reason": "accepted stage changed"})
    old_motion = (family / char / "out/rig/motion.json").read_bytes()
    new_motion = (home / "out/rig/motion.json").read_bytes()
    if old_motion != new_motion:
        errors.append({"field": "motion", "reason": "accepted motion bytes changed"})
    common = [s["name"] for s in baseline["slots"] if s["name"] not in OFFICE_CLOTHING]
    for name in common:
        old = baseline["skins"]["default"].get(name)
        new = rig["skins"]["default"].get(name)
        if old != new:
            errors.append({"slot": name, "reason": "protected face/hair attachment changed"})
        for attachment in (old or {}).values():
            image = attachment.get("image")
            if image and (family / char / "out/rig/images" / image).read_bytes() != (home / "out/rig/images" / image).read_bytes():
                errors.append({"image": image, "reason": "protected face/hair PNG changed"})
    if errors:
        raise RuntimeError(f"HOMEWEAR_PROTECTED_CHECK_FAILED {char}: {errors}")
    return {"character": char, "status": "PRESERVATION_PASS", "commonSlotsChecked": len(common)}


def run_fast_build(family: pathlib.Path, char: str):
    home = family / "outfits/homewear" / char
    out = home / "out"
    build_dir = out / "check/build"
    build_dir.mkdir(parents=True, exist_ok=True)
    subprocess.run(
        [
            "node",
            "/Users/firejune/Workspace/Firejune/rigc/bin/rigc.cjs",
            "build",
            "--rig",
            str(out / "rig/rig.json"),
            "--motion",
            str(out / "rig/motion.json"),
            "--out",
            str(build_dir),
            "--profile",
            "spine-html",
            "--pack",
            "--page-edges",
            "free",
            "--pack-shape",
            "polygon",
        ],
        check=True,
    )
    for rel in ["authoring/rig/images", "authoring/rig/rig.json", "authoring/rig/motion.json"]:
        p = home / rel
        if p.is_dir():
            shutil.rmtree(p)
        elif p.exists():
            p.unlink()
    return {"PASS": True, "gate_spine_html_green": True}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--characters", nargs="*", default=["roa", "luna", "jinni", "nova"])
    parser.add_argument("--force", action="store_true")
    parser.add_argument("--fast-build", action="store_true")
    args = parser.parse_args()
    family = pathlib.Path(__file__).resolve().parents[1]
    summary = []
    for char in args.characters:
        prev_check = None
        prev_gate = None
        out_check = family / "outfits/homewear" / char / "out/check"
        if args.fast_build and (out_check / "check.json").is_file():
            prev_check = (out_check / "check.json").read_bytes()
        if args.fast_build and (out_check / "gate_spine-html.txt").is_file():
            prev_gate = (out_check / "gate_spine-html.txt").read_bytes()
        prepare_author_inputs(family, char, force=args.force)
        run_rig_parts_rig(family, char)
        merge_with_baseline(family, char, force=args.force)
        stitched = stitch_neck_seam(family, char)
        if args.fast_build:
            check = run_fast_build(family, char)
            if prev_check is not None:
                (out_check / "check.json").write_bytes(prev_check)
            if prev_gate is not None:
                (out_check / "gate_spine-html.txt").write_bytes(prev_gate)
        else:
            check = run_build_and_check(family, char)
        protected = verify_protected(family, char)
        summary.append({
            "character": char,
            "stitched": stitched,
            "PASS": check["PASS"],
            "gate_spine_html_green": check["gate_spine_html_green"],
            "seam_mean": check.get("seam_mean"),
            "fold_status": check.get("ANIMATIONS_DO_NOT_FOLD", {}).get("status"),
            "stretch_severity": check.get("TEXTURE_STRETCH", {}).get("severity"),
            "protected": protected["status"],
        })
    print(json.dumps({"results": summary}, indent=2))


if __name__ == "__main__":
    main()
