#!/usr/bin/env python3
"""Combine public authored clothing with the exact accepted common character.

Emits a consumer rig specification only. The ordinary rigc build and public
parts check must gate the resulting model before a viewer loads it.
"""
import json
import pathlib
import shutil

family = pathlib.Path(__file__).resolve().parents[1]
home = family / "outfits/homewear/naru"
authored = home / "authoring/rig"
baseline = family / "naru/out"
out = home / "out"
if out.exists():
    raise RuntimeError("HOMEWEAR_MERGE_FRESH_OUTPUT_REQUIRED")
rig = json.loads((baseline / "rig/rig.json").read_text())
new = json.loads((authored / "rig.json").read_text())
common = [s["name"] for s in rig["slots"] if s["name"] not in ["shoes", "legwear", "bottomwear", "neck", "topwear"]]
new_names = ["shoes", "bottomwear", "neck", "topwear", "sleeves"]
used = {"root", "hip", "chest", "chest_ctl", "neck", "head", "head_ctl", "boob_r", "boob_l"}
old_bones = {b["name"]: b for b in rig["bones"]}
new_bones = {b["name"]: b for b in new["bones"]}
for name in used:
    if old_bones[name] != new_bones[name]:
        raise RuntimeError("HOMEWEAR_BIND_FRAME_CHANGED " + name)
extra = [b for b in new["bones"] if b["name"] not in old_bones]
if {b["name"] for b in extra} != {"cardigan_hem_r", "cardigan_hem_l"}:
    raise RuntimeError("HOMEWEAR_UNEXPECTED_NEW_BONE")
rig["bones"] += extra
old_constraints = {(c["type"], c["name"]) for c in rig["constraints"]}
rig["constraints"] += [c for c in new.get("constraints", []) if (c["type"], c["name"]) not in old_constraints]
old_slots = {s["name"]: s for s in rig["slots"]}
new_slots = {s["name"]: s for s in new["slots"]}
order = ["hair_back", *new_names, *[n for n in common if n != "hair_back"]]
rig["slots"] = [new_slots[n] if n in new_names else old_slots[n] for n in order]
rig["skins"]["default"] = {n: new["skins"]["default"][n] if n in new_names else rig["skins"]["default"][n] for n in order}
(out / "rig/images").mkdir(parents=True)
(out / "parts").mkdir()
for n in order:
    source = authored if n in new_names else baseline / "rig"
    for attachment in rig["skins"]["default"][n].values():
        shutil.copy2(source / "images" / attachment["image"], out / "rig/images" / attachment["image"])
    source_parts = home / "authoring/inputs" if n in new_names else baseline
    shutil.copy2(source_parts / "parts" / (n + ".png"), out / "parts" / (n + ".png"))
old_parts = {p["name"]: p for p in json.loads((baseline / "parts.json").read_text())["parts"]}
new_parts = {p["name"]: p for p in json.loads((home / "authoring/inputs/parts.json").read_text())["parts"]}
parts = {"rig_size": [800, 2284], "scale_rig_per_source": 1, "ghost_px": {},
    "parts": [new_parts[n] if n in new_names else old_parts[n] for n in order]}
old_reports = json.loads((baseline / "rig/mesh_report.json").read_text())
new_reports = json.loads((authored / "mesh_report.json").read_text())
(out / "rig/mesh_report.json").write_text(json.dumps([r for r in old_reports if r["part"] in common] + new_reports, indent=2) + "\n")
(out / "parts.json").write_text(json.dumps(parts, indent=2) + "\n")
(out / "rig/rig.json").write_text(json.dumps(rig, indent=2) + "\n")
shutil.copy2(baseline / "rig/motion.json", out / "rig/motion.json")
shutil.copy2(home / "prepared/assembled-white.png", home / "inputs/painting.png")
(out / "assembly.json").write_text(json.dumps({"spec": "family-homewear-assembly/1",
    "commonBonePrefix": len(old_bones), "commonSlots": common,
    "newClothingSlots": new_names, "appendedBones": [b["name"] for b in extra],
    "motion": "Exact accepted motion bytes", "commonPhysics": "Exact accepted constraint prefix",
    "sourceReference": "Registered full static composition with exact accepted head assets; this is the intended composite reference, not untouched original artwork. Original crop remains painting-clothing-source.png.",
    "status": "AWAITING_OFFICIAL_BUILD_CHECK"}, indent=2) + "\n")
print(json.dumps({"status": "RIG_SPEC_READY_FOR_GATE", "bones": len(rig["bones"]), "slots": len(order)}))
