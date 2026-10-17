#!/usr/bin/env python3
"""Prepare the reviewed clothing pieces for the public parts authoring CLI.

This writes inputs, not compiler output. Existing accepted character files are
read only. Custom authored pieces use author provenance; original model tag
coverage and pixel lineage remain in the static candidate's prototype.json.
"""
import json
import pathlib
import shutil

family = pathlib.Path(__file__).resolve().parents[1]
home = family / "outfits/homewear/naru"
candidate = home / "prepared"
author = home / "authoring"
inputs = author / "inputs"
if inputs.exists():
    raise RuntimeError("HOMEWEAR_AUTHOR_FRESH_INPUT_REQUIRED")
(inputs / "parts").mkdir(parents=True)
prototype = json.loads((candidate / "prototype.json").read_text())
records = []
for row in prototype["parts"]:
    name = row["name"]
    shutil.copy2(candidate / "parts" / (name + ".png"), inputs / "parts" / (name + ".png"))
    records.append({**{k: row[k] for k in ["name", "x", "y", "w", "h", "opaque_px"]},
                    "from": "full:author:homewear-" + name,
                    "projected_core_px": 0, "source_px_taken": 0,
                    "refused_drift_px": 0, "merged_px": 0, "seam_override_px": 0})
(inputs / "parts.json").write_text(json.dumps({"rig_size": [800, 2284],
    "scale_rig_per_source": 1, "ghost_px": {}, "parts": records}, indent=2) + "\n")
cfg = json.loads((family / "naru/config.json").read_text())
cfg["key"] = "naru_homewear"
cfg.pop("seethrough", None)
cfg["assemble"] = {"rig_scale": 1, "plan": [[r["name"], "full", "author:homewear-" + r["name"]] for r in records]}
cfg["motion"].pop("blink", None)
cfg["bones"] += [
    {"name": "cardigan_hem_r", "parent": "hip", "at": [243, 1080], "tip": [245, 1350]},
    {"name": "cardigan_hem_l", "parent": "hip", "at": [532, 1080], "tip": [532, 1350]},
]
for side in ["r", "l"]:
    cfg["constraints"].append({"type": "physics", "name": "cardigan_hem_" + side + "_phys",
        "bone": "cardigan_hem_" + side, "rotate": 1, "inertia": .15,
        "strength": 240, "damping": .92, "mass": 1, "wind": .15,
        "gravity": .06, "mix": 1})
top = json.loads(json.dumps(cfg["meshes"]["topwear"]))
top["contour"]["tolerance"] = 1
top["contour"]["margin"] = 3
top["segments"] = [
    *top.get("segments", []),
    ["chest", [240, 640], [240, 950]],
    ["chest", [535, 640], [535, 950]],
    ["hip", [245, 940], [245, 1080]],
    ["hip", [532, 940], [532, 1080]],
    "cardigan_hem_r",
    "cardigan_hem_l",
]
neck = json.loads(json.dumps(cfg["meshes"]["neck"]))
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
        "segments": [["chest", [180, 820], [615, 1020]]],
    },
}
cfg["regions"] = {"shoes": "root", "bottomwear": "hip"}
cfg["note"] = "Consumer authored homewear: common bone/motion/physics definitions are preserved in final assembly; new cardigan hems have separate physics on unified topwear. Source lineage is in prepared/prototype.json."
(author / "config.json").write_text(json.dumps(cfg, indent=2) + "\n")
print(json.dumps({"status": "AUTHOR_INPUTS_READY", "parts": len(records)}))
